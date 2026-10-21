"""Automated benchmarking script for Bloxorz solvers.

Executes search algorithms across game levels, records performance metrics
(search time, peak memory, expanded nodes, solution length), exports results to CSV,
and can generate comparison charts using matplotlib.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import importlib
import os
import signal
import sys
from pathlib import Path
from typing import Any, Callable

# Ensure Source/ is on sys.path when executed directly as a script
SOURCE_DIR = Path(__file__).resolve().parent.parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from bloxorz.core import BloxorzProblem, format_actions, load_level
from bloxorz.solvers import SearchResult, bfs, dfs, ids

# Solver mapping: name -> function
SOLVERS: dict[str, Callable[[BloxorzProblem], SearchResult]] = {
    "BFS": bfs,
    "DFS": dfs,
    "IDS": ids,
}

# Dynamically discover UCS and A* if Minh or Cao have implemented them
for extra_name, module_name, func_name in [
    ("UCS", "bloxorz.solvers.ucs", "solve_ucs"),
    ("A*", "bloxorz.solvers.astar", "solve_astar"),
]:
    try:
        mod = importlib.import_module(module_name)
        SOLVERS[extra_name] = getattr(mod, func_name)
    except (ImportError, AttributeError):
        pass


class BenchmarkTimeoutError(Exception):
    """Raised when a solver exceeds the timeout limit."""


def _alarm_handler(signum: int, frame: Any) -> None:
    raise BenchmarkTimeoutError("Solver timed out")


def run_solver_with_timeout(
    solver_fn: Callable[[BloxorzProblem], SearchResult],
    problem: BloxorzProblem,
    timeout_sec: float,
) -> tuple[str, SearchResult | None]:
    """Execute solver_fn with a timeout limit.

    Returns:
        (status, SearchResult or None)
        status is one of "SOLVED", "UNSOLVABLE", "TIMEOUT", "ERROR"
    """
    has_alarm = hasattr(signal, "SIGALRM")
    if has_alarm and timeout_sec > 0:
        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(int(timeout_sec) if timeout_sec >= 1 else 1)

    try:
        result = solver_fn(problem)
        if result.path is not None:
            status = "SOLVED"
        else:
            status = "UNSOLVABLE"
        return status, result
    except BenchmarkTimeoutError:
        return "TIMEOUT", None
    except Exception as exc:
        print(f"    [!] Error during execution: {exc}")
        return "ERROR", None
    finally:
        if has_alarm and timeout_sec > 0:
            signal.alarm(0)


def collect_levels(levels_dir: Path) -> list[Path]:
    """Collect all .json level files sorted by filename."""
    if not levels_dir.exists():
        return []
    levels = sorted(levels_dir.glob("*.json"))
    # If no levels in root of directory, check subdirectories
    if not levels:
        levels = sorted(levels_dir.glob("**/*.json"))
    return [lvl for lvl in levels if not lvl.name.startswith(".")]


def run_benchmark(
    levels: list[Path],
    selected_solvers: list[str],
    timeout_sec: float = 30.0,
) -> list[dict[str, Any]]:
    """Run all selected solvers on the given levels and return record list."""
    records: list[dict[str, Any]] = []
    now_iso = datetime.datetime.now().isoformat()

    print(f"\n{'='*70}")
    print(f"Starting Bloxorz Solver Benchmark ({len(levels)} levels, {len(selected_solvers)} solvers)")
    print(f"{'='*70}\n")

    for lvl_path in levels:
        try:
            lvl = load_level(lvl_path)
            prob = BloxorzProblem(lvl)
        except Exception as exc:
            print(f"Failed to load level {lvl_path.name}: {exc}")
            continue

        print(f"▶ Level: {lvl_path.name} ({lvl.name})")

        for solver_name in selected_solvers:
            solver_fn = SOLVERS[solver_name]
            print(f"   [{solver_name:4s}] Running...", end="", flush=True)

            status, res = run_solver_with_timeout(solver_fn, prob, timeout_sec)

            if res is not None:
                path_str = format_actions(res.path) if res.path is not None else ""
                sol_len = res.metrics.solution_length
                exp_nodes = res.metrics.expanded_nodes
                time_sec = res.metrics.search_time
                peak_bytes = res.metrics.peak_memory
                peak_kb = round(peak_bytes / 1024, 2)
            else:
                path_str = ""
                sol_len = 0
                exp_nodes = 0
                time_sec = timeout_sec if status == "TIMEOUT" else 0.0
                peak_bytes = 0
                peak_kb = 0.0

            record = {
                "timestamp": now_iso,
                "level_file": lvl_path.name,
                "level_name": lvl.name,
                "algorithm": solver_name,
                "status": status,
                "solution_length": sol_len,
                "expanded_nodes": exp_nodes,
                "search_time_sec": round(time_sec, 6),
                "peak_memory_bytes": peak_bytes,
                "peak_memory_kb": peak_kb,
                "actions": path_str,
            }
            records.append(record)

            if status == "SOLVED":
                print(f" Done in {time_sec*1000:.2f}ms | Length: {sol_len:2d} | Expanded: {exp_nodes:5d} | RAM: {peak_kb:7.1f} KB")
            else:
                print(f" {status}")

        print()

    return records


def export_csv(records: list[dict[str, Any]], output_path: Path) -> None:
    """Save benchmark records to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "timestamp",
        "level_file",
        "level_name",
        "algorithm",
        "status",
        "solution_length",
        "expanded_nodes",
        "search_time_sec",
        "peak_memory_bytes",
        "peak_memory_kb",
        "actions",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"✓ Benchmark results saved to: {output_path}")


def print_summary_table(records: list[dict[str, Any]]) -> None:
    """Print an ASCII summary table grouped by level and solver."""
    if not records:
        return

    header = f"{'Level':<20} | {'Algorithm':<6} | {'Status':<10} | {'Moves':<5} | {'Expanded':<8} | {'Time (ms)':<10} | {'Peak RAM':<10}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)

    for r in records:
        time_ms = f"{r['search_time_sec']*1000:.2f}"
        ram_str = f"{r['peak_memory_kb']:.1f} KB"
        print(
            f"{r['level_file'][:20]:<20} | "
            f"{r['algorithm']:<6} | "
            f"{r['status']:<10} | "
            f"{r['solution_length']:<5} | "
            f"{r['expanded_nodes']:<8} | "
            f"{time_ms:<10} | "
            f"{ram_str:<10}"
        )
    print(sep + "\n")


def plot_charts(records: list[dict[str, Any]], output_dir: Path) -> None:
    """Generate comparison charts using matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[!] matplotlib not installed, skipping chart generation.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter solved records
    solved = [r for r in records if r["status"] == "SOLVED"]
    if not solved:
        print("[!] No solved runs to generate charts.")
        return

    levels = sorted(list({r["level_file"] for r in solved}))
    algorithms = sorted(list({r["algorithm"] for r in solved}))

    # Helper to build grouped bar chart
    def make_grouped_bar_chart(
        metric_key: str,
        title: str,
        ylabel: str,
        filename: str,
        log_scale: bool = False,
    ) -> None:
        fig, ax = plt.subplots(figsize=(max(8, len(levels) * 2), 5))
        bar_width = 0.8 / len(algorithms)
        import numpy as np
        x = np.arange(len(levels))

        for idx, algo in enumerate(algorithms):
            values = []
            for lvl in levels:
                match = [r for r in solved if r["level_file"] == lvl and r["algorithm"] == algo]
                values.append(match[0][metric_key] if match else 0)
            ax.bar(x + idx * bar_width, values, bar_width, label=algo)

        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("Level", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_xticks(x + bar_width * (len(algorithms) - 1) / 2)
        ax.set_xticklabels(levels, rotation=30, ha="right")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        if log_scale:
            ax.set_yscale("log")

        plt.tight_layout()
        chart_path = output_dir / filename
        plt.savefig(chart_path, dpi=150)
        plt.close(fig)
        print(f"✓ Chart generated: {chart_path}")

    # Generate charts for the 4 core metrics
    make_grouped_bar_chart(
        "search_time_sec",
        "Search Time by Algorithm",
        "Time (seconds)",
        "chart_search_time.png",
    )
    make_grouped_bar_chart(
        "peak_memory_kb",
        "Peak Memory by Algorithm",
        "Peak Memory (KB)",
        "chart_peak_memory.png",
    )
    make_grouped_bar_chart(
        "expanded_nodes",
        "Expanded Nodes by Algorithm",
        "Expanded Nodes Count",
        "chart_expanded_nodes.png",
    )
    make_grouped_bar_chart(
        "solution_length",
        "Solution Length by Algorithm",
        "Number of Moves",
        "chart_solution_length.png",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Bloxorz Search Algorithm Benchmark Runner")
    parser.add_argument(
        "--levels-dir",
        type=Path,
        default=SOURCE_DIR / "levels",
        help="Directory containing JSON level files (default: Source/levels)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to output CSV file (default: Source/benchmark/results/benchmark_<timestamp>.csv)",
    )
    parser.add_argument(
        "--solvers",
        type=str,
        default="all",
        help=f"Comma-separated list of solvers to test ({','.join(SOLVERS.keys())}) or 'all'",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout in seconds per solver run (default: 30.0)",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate comparison plots (.png) using matplotlib",
    )
    args = parser.parse_args()

    # Discover levels
    levels = collect_levels(args.levels_dir)
    if not levels:
        # Fallback to test fixtures if levels/ is empty
        fixture_dir = SOURCE_DIR / "tests" / "fixtures"
        levels = collect_levels(fixture_dir)
        if levels:
            print(f"[i] No levels in {args.levels_dir}; falling back to fixture levels in {fixture_dir}")
        else:
            print(f"[!] No levels found in {args.levels_dir} or {fixture_dir}. Exiting.")
            sys.exit(1)

    # Filter solvers
    if args.solvers.lower() == "all":
        selected_solvers = list(SOLVERS.keys())
    else:
        chosen = [s.strip().upper() for s in args.solvers.split(",")]
        selected_solvers = [s for s in SOLVERS if s.upper() in chosen]
        if not selected_solvers:
            print(f"[!] No valid solvers chosen. Available: {list(SOLVERS.keys())}")
            sys.exit(1)

    # Determine output paths
    results_dir = SOURCE_DIR / "benchmark" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    if args.output is None:
        timestamp_slug = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv = results_dir / f"benchmark_{timestamp_slug}.csv"
    else:
        output_csv = args.output

    # Run benchmark
    records = run_benchmark(levels, selected_solvers, timeout_sec=args.timeout)

    # Output results
    print_summary_table(records)
    export_csv(records, output_csv)

    if args.plot:
        plot_charts(records, results_dir)


if __name__ == "__main__":
    main()
