"""Automated benchmarking script for Bloxorz solvers.

Executes search algorithms across game levels, records performance metrics
(search time, peak memory, expanded nodes, solution length), exports results to CSV,
and can generate comparison charts using matplotlib.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import inspect
import multiprocessing
import queue
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable

# Ensure Source/ is on sys.path when executed directly as a script
SOURCE_DIR = Path(__file__).resolve().parent.parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from bloxorz.core import BloxorzProblem, format_actions, load_level, replay
from bloxorz.solvers import SearchResult, bfs, dfs, ids, physics_cost, solve_astar, solve_ucs

# Solver mapping: name -> function
SOLVERS: dict[str, Callable[..., SearchResult]] = {
    "BFS": bfs,
    "DFS": dfs,
    "IDS": ids,
    "UCS": solve_ucs,
    "A*": solve_astar,
}

# Cost function each solver optimises. BFS/DFS/IDS count moves (unit cost); UCS and A*
# use the default ``cost_fn`` of their signature, so this stays in sync with the solvers.
COST_FUNCTION_NAMES: dict[str, str] = {
    name: (
        inspect.signature(fn).parameters["cost_fn"].default.__name__
        if "cost_fn" in inspect.signature(fn).parameters
        else "unit_moves"
    )
    for name, fn in SOLVERS.items()
}

# Runs shorter than this are repeated and their median time is reported (tiny levels
# finish in a few ms, so one sample is mostly noise). Slower runs are measured once.
REPEAT_BELOW_SEC = 1.0
POLL_INTERVAL_SEC = 0.05


def _solver_worker(
    solver_fn: Callable[..., SearchResult],
    problem: BloxorzProblem,
    trace_memory: bool,
    out: "multiprocessing.Queue[tuple[str, Any]]",
) -> None:
    """Child-process entry point: run one solver and send back its result.

    Lives at module level so it can be pickled by the ``spawn`` start method (Windows).
    """
    try:
        out.put(("OK", solver_fn(problem, trace_memory=trace_memory)))
    except Exception as exc:  # report to the parent instead of dying silently
        out.put(("ERROR", f"{type(exc).__name__}: {exc}"))


def run_solver_with_timeout(
    solver_fn: Callable[..., SearchResult],
    problem: BloxorzProblem,
    timeout_sec: float,
    trace_memory: bool = True,
) -> tuple[str, SearchResult | None]:
    """Execute solver_fn in a separate process with a wall-clock timeout.

    A process is used instead of ``signal.SIGALRM`` because SIGALRM does not exist on
    Windows. On timeout the process is terminated.

    Returns:
        (status, SearchResult or None)
        status is one of "SOLVED", "UNSOLVABLE", "LIMIT", "TIMEOUT", "ERROR"
    """
    ctx = multiprocessing.get_context()
    out: multiprocessing.Queue = ctx.Queue()
    proc = ctx.Process(target=_solver_worker, args=(solver_fn, problem, trace_memory, out))
    proc.start()

    deadline = time.monotonic() + timeout_sec
    message: tuple[str, Any] | None = None
    try:
        # Read before join(): a child blocked on a full pipe would never exit.
        while message is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return "TIMEOUT", None
            try:
                message = out.get(timeout=min(POLL_INTERVAL_SEC, remaining))
            except queue.Empty:
                if not proc.is_alive():
                    try:
                        message = out.get(timeout=POLL_INTERVAL_SEC)  # result may be in flight
                    except queue.Empty:
                        print(f"    [!] Solver process died (exit code {proc.exitcode})")
                        return "ERROR", None
    finally:
        if proc.is_alive():
            proc.terminate()
        proc.join()
        out.close()

    kind, payload = message
    if kind == "ERROR":
        print(f"    [!] Error during execution: {payload}")
        return "ERROR", None

    result: SearchResult = payload
    if result.path is not None:
        return "SOLVED", result
    if result.metrics.hit_depth_limit:
        return "LIMIT", result
    return "UNSOLVABLE", result


def path_cost(problem: BloxorzProblem, path: list) -> float:
    """Total ``physics_cost`` of a path, so every solver is compared on the same scale."""
    states = replay(problem, path)
    return sum(physics_cost(a, act, b) for a, act, b in zip(states, path, states[1:]))


def collect_levels(levels_dir: Path) -> list[Path]:
    """Collect all .json level files sorted by filename."""
    if not levels_dir.exists():
        return []
    levels = sorted(levels_dir.glob("*.json"))
    # If no levels in root of directory, check subdirectories
    if not levels:
        levels = sorted(levels_dir.glob("**/*.json"))
    return [lvl for lvl in levels if not lvl.name.startswith(".")]


def measure(
    solver_fn: Callable[..., SearchResult],
    problem: BloxorzProblem,
    timeout_sec: float,
    repeats: int,
) -> dict[str, Any]:
    """Measure one (level, solver) pair.

    Time comes from runs with ``trace_memory=False`` (tracemalloc slows a search by
    about 3x); fast runs are repeated and the median is kept. Peak memory comes from
    one extra run with ``trace_memory=True``.
    """
    status, first = run_solver_with_timeout(solver_fn, problem, timeout_sec, trace_memory=False)
    if first is None:
        return {"status": status, "result": None, "time": timeout_sec if status == "TIMEOUT" else 0.0,
                "peak_memory": None, "repeats": 0}

    times = [first.metrics.search_time]
    if first.metrics.search_time < REPEAT_BELOW_SEC:
        for _ in range(repeats - 1):
            _, again = run_solver_with_timeout(solver_fn, problem, timeout_sec, trace_memory=False)
            if again is None:
                break
            times.append(again.metrics.search_time)

    peak_memory: int | None = None
    _, traced = run_solver_with_timeout(solver_fn, problem, timeout_sec, trace_memory=True)
    if traced is not None:
        peak_memory = traced.metrics.peak_memory

    return {"status": status, "result": first, "time": statistics.median(times),
            "peak_memory": peak_memory, "repeats": len(times)}


def run_benchmark(
    levels: list[Path],
    selected_solvers: list[str],
    timeout_sec: float = 30.0,
    repeats: int = 3,
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

        print(f"> Level: {lvl_path.name} ({lvl.name})")

        for solver_name in selected_solvers:
            print(f"   [{solver_name:4s}] Running...", end="", flush=True)

            m = measure(SOLVERS[solver_name], prob, timeout_sec, repeats)
            status, res = m["status"], m["result"]
            peak_bytes = m["peak_memory"]

            if res is not None:
                path_str = format_actions(res.path) if res.path is not None else ""
                sol_len = res.metrics.solution_length
                sol_cost = path_cost(prob, res.path) if res.path is not None else ""
                exp_nodes = res.metrics.expanded_nodes
            else:
                path_str = ""
                sol_len = 0
                sol_cost = ""
                exp_nodes = 0

            record = {
                "timestamp": now_iso,
                "level_file": lvl_path.name,
                "level_name": lvl.name,
                "algorithm": solver_name,
                "cost_function": COST_FUNCTION_NAMES[solver_name],
                "status": status,
                "solution_length": sol_len,
                "solution_cost": sol_cost,
                "expanded_nodes": exp_nodes,
                "search_time_sec": round(m["time"], 6),
                "time_repeats": m["repeats"],
                "peak_memory_bytes": "" if peak_bytes is None else peak_bytes,
                "peak_memory_kb": "" if peak_bytes is None else round(peak_bytes / 1024, 2),
                "actions": path_str,
            }
            records.append(record)

            if status == "SOLVED":
                ram = "n/a" if peak_bytes is None else f"{peak_bytes / 1024:7.1f} KB"
                print(f" Done in {m['time']*1000:.2f}ms | Length: {sol_len:3d} | Expanded: {exp_nodes:7d} | RAM: {ram}")
            else:
                print(f" {status}")

        print()

    return records


CSV_FIELDS = [
    "timestamp",
    "level_file",
    "level_name",
    "algorithm",
    "cost_function",
    "status",
    "solution_length",
    "solution_cost",
    "expanded_nodes",
    "search_time_sec",
    "time_repeats",
    "peak_memory_bytes",
    "peak_memory_kb",
    "actions",
]


def export_csv(records: list[dict[str, Any]], output_path: Path) -> None:
    """Save benchmark records to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, restval="")
        writer.writeheader()
        writer.writerows(records)
    print(f"[OK] Benchmark results saved to: {output_path}")


def print_summary_table(records: list[dict[str, Any]]) -> None:
    """Print an ASCII summary table grouped by level and solver."""
    if not records:
        return

    header = (
        f"{'Level':<20} | {'Algo':<4} | {'Status':<10} | {'Moves':<5} | {'Cost':<6} | "
        f"{'Expanded':<8} | {'Time (ms)':<10} | {'Peak RAM':<10}"
    )
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)

    for r in records:
        time_ms = f"{r['search_time_sec']*1000:.2f}"
        ram_str = "n/a" if r["peak_memory_kb"] == "" else f"{r['peak_memory_kb']:.1f} KB"
        print(
            f"{r['level_file'][:20]:<20} | "
            f"{r['algorithm']:<4} | "
            f"{r['status']:<10} | "
            f"{r['solution_length']:<5} | "
            f"{r['solution_cost']:<6} | "
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
                value = match[0][metric_key] if match else ""
                values.append(float("nan") if value == "" else value)
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
        print(f"[OK] Chart generated: {chart_path}")

    # Generate charts for the 4 core metrics
    make_grouped_bar_chart(
        "search_time_sec",
        "Search Time by Algorithm",
        "Time (seconds, log scale)",
        "chart_search_time.png",
        log_scale=True,
    )
    make_grouped_bar_chart(
        "peak_memory_kb",
        "Peak Memory by Algorithm",
        "Peak Memory (KB, log scale)",
        "chart_peak_memory.png",
        log_scale=True,
    )
    make_grouped_bar_chart(
        "expanded_nodes",
        "Expanded Nodes by Algorithm",
        "Expanded Nodes Count (log scale)",
        "chart_expanded_nodes.png",
        log_scale=True,
    )
    make_grouped_bar_chart(
        "solution_length",
        "Solution Length by Algorithm",
        "Number of Moves",
        "chart_solution_length.png",
    )


def main() -> None:
    # Windows consoles default to a legacy codepage; never crash on printing.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
        "--repeats",
        type=int,
        default=3,
        help=f"Timing runs per fast (<{REPEAT_BELOW_SEC:g}s) solver; the median is reported (default: 3)",
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
    records = run_benchmark(levels, selected_solvers, timeout_sec=args.timeout, repeats=max(1, args.repeats))

    # Output results
    print_summary_table(records)
    export_csv(records, output_csv)

    if args.plot:
        plot_charts(records, results_dir)


if __name__ == "__main__":
    main()
