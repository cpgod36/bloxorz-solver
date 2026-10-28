"""Turn a benchmark CSV into report-ready tables and charts.

``benchmark.py`` writes one row per (level, algorithm). This module reads that CSV and
produces, for the written report:

* ``report_tables.md``: per-level tables (one per difficulty group) and a group summary.
* ``fig_metrics_by_group.png``: the four metrics, averaged per difficulty group.
* ``fig_cost_ratio.png``: extra solution cost over the cheapest cost found on each level.
* ``fig_hardest_levels.png``: time and expanded nodes on the g4 levels, where the
  algorithms separate the most.

Usage (from ``Source/``):
    python -m benchmark.report benchmark/results/benchmark_full_20261026.csv
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path
from typing import Any

ALGORITHMS = ["BFS", "DFS", "IDS", "UCS", "A*"]
GROUP_TITLES = {
    "g1": "Group 1 - basic",
    "g2": "Group 2 - fragile tiles",
    "g3": "Group 3 - switches and bridges",
    "g4": "Group 4 - combined",
}
HARDEST_GROUP = "g4"
# Okabe-Ito palette: distinguishable for colour-blind readers and in greyscale print.
COLORS = {"BFS": "#0072B2", "DFS": "#D55E00", "IDS": "#009E73", "UCS": "#CC79A7", "A*": "#E69F00"}


def load_records(csv_path: Path) -> list[dict[str, Any]]:
    """Read the benchmark CSV, converting numeric columns. Only SOLVED rows are kept."""
    records: list[dict[str, Any]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["status"] != "SOLVED":
                continue
            records.append({
                "level": row["level_file"].removesuffix(".json"),
                "group": row["level_file"].split("_")[0],
                "algorithm": row["algorithm"],
                "moves": int(row["solution_length"]),
                "cost": float(row["solution_cost"]),
                "expanded": int(row["expanded_nodes"]),
                "time_ms": float(row["search_time_sec"]) * 1000,
                "memory_kb": float(row["peak_memory_kb"]),
            })
    return records


def _cell(records: list[dict[str, Any]], level: str, algorithm: str) -> dict[str, Any] | None:
    return next((r for r in records if r["level"] == level and r["algorithm"] == algorithm), None)


def best_cost_per_level(records: list[dict[str, Any]]) -> dict[str, float]:
    """Cheapest ``physics_cost`` any solver found on each level (UCS/A* are optimal)."""
    best: dict[str, float] = {}
    for r in records:
        best[r["level"]] = min(r["cost"], best.get(r["level"], float("inf")))
    return best


def group_mean(records: list[dict[str, Any]], group: str, algorithm: str, key: str,
               geometric: bool = True) -> float:
    """Mean of ``key`` over a group's levels; geometric by default.

    Metrics such as expanded nodes span orders of magnitude across levels, so an
    arithmetic mean would be decided by the single hardest level.
    """
    values = [r[key] for r in records if r["group"] == group and r["algorithm"] == algorithm]
    if not values:  # the solver solved no level of this group (e.g. timed out on all)
        return float("nan")
    return statistics.geometric_mean(values) if geometric else statistics.fmean(values)


def build_tables(records: list[dict[str, Any]]) -> str:
    """Markdown tables: one per group (every level x algorithm) plus a group summary."""
    lines: list[str] = []
    for group, title in GROUP_TITLES.items():
        levels = sorted({r["level"] for r in records if r["group"] == group})
        if not levels:
            continue
        lines += [f"### {title}", "",
                  "| Level | Algorithm | Moves | Cost | Expanded | Time (ms) | Peak memory (KB) |",
                  "|---|---|---:|---:|---:|---:|---:|"]
        for level in levels:
            best_cost = min(r["cost"] for r in records if r["level"] == level)
            for algo in ALGORITHMS:
                r = _cell(records, level, algo)
                if r is None:
                    continue
                cost = f"{r['cost']:g}" + (" *" if r["cost"] == best_cost else "")
                lines.append(f"| {level} | {algo} | {r['moves']} | {cost} | {r['expanded']:,} | "
                             f"{r['time_ms']:.2f} | {r['memory_kb']:.1f} |")
        lines.append("")
    lines += ["`*` marks the lowest cost found on that level (the cost UCS and A* minimise).", ""]

    lines += ["### Summary per group (geometric mean over the group's levels)", "",
              "| Group | Algorithm | Moves | Cost | Expanded | Time (ms) | Peak memory (KB) |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for group in GROUP_TITLES:
        if not any(r["group"] == group for r in records):
            continue
        for algo in ALGORITHMS:
            if not any(r["group"] == group and r["algorithm"] == algo for r in records):
                continue
            g = lambda key: group_mean(records, group, algo, key)  # noqa: E731
            lines.append(f"| {group} | {algo} | {g('moves'):.1f} | {g('cost'):.1f} | "
                         f"{g('expanded'):,.0f} | {g('time_ms'):.2f} | {g('memory_kb'):.1f} |")
    lines.append("")
    return "\n".join(lines)


def _grouped_bars(ax, categories: list[str], values: dict[str, list[float]],
                  label_fmt: str | None = None) -> None:
    width = 0.8 / len(values)
    for i, (algo, ys) in enumerate(values.items()):
        xs = [x + i * width for x in range(len(categories))]
        bars = ax.bar(xs, ys, width, label=algo, color=COLORS[algo])
        if label_fmt:
            ax.bar_label(bars, fmt=label_fmt, fontsize=6, rotation=90, padding=2)
    ax.set_xticks([x + width * (len(values) - 1) / 2 for x in range(len(categories))])
    ax.set_xticklabels(categories)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)


def plot_metrics_by_group(records: list[dict[str, Any]], out: Path) -> None:
    import matplotlib.pyplot as plt

    groups = [g for g in GROUP_TITLES if any(r["group"] == g for r in records)]
    panels = [("time_ms", "Search time (ms, log)", True),
              ("memory_kb", "Peak memory (KB, log)", True),
              ("expanded", "Expanded nodes (log)", True),
              ("moves", "Solution length (moves)", False)]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (key, label, log) in zip(axes.flat, panels):
        _grouped_bars(ax, groups, {a: [group_mean(records, g, a, key) for g in groups]
                                   for a in ALGORITHMS})
        ax.set_ylabel(label)
        if log:
            ax.set_yscale("log")
    axes[0, 0].legend(ncol=3, fontsize=8)
    fig.suptitle("Solver comparison per difficulty group (geometric mean)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def plot_cost_ratio(records: list[dict[str, Any]], out: Path) -> None:
    """Extra cost over the best cost on each level; 0% means optimal for physics_cost."""
    import matplotlib.pyplot as plt

    best = best_cost_per_level(records)
    groups = [g for g in GROUP_TITLES if any(r["group"] == g for r in records)]
    values = {}
    for algo in ALGORITHMS:
        values[algo] = []
        for g in groups:
            ratios = [r["cost"] / best[r["level"]] for r in records
                      if r["group"] == g and r["algorithm"] == algo]
            values[algo].append((statistics.geometric_mean(ratios) - 1) * 100 if ratios
                                else float("nan"))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _grouped_bars(ax, groups, values, label_fmt="%.1f")
    ax.set_ylim(top=max(v for ys in values.values() for v in ys if v == v) * 1.15)
    ax.set_ylabel("Extra cost over the best solution (%, 0 = optimal)")
    ax.set_title("How far each solver is from the cheapest solution", fontweight="bold")
    ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def plot_hardest_levels(records: list[dict[str, Any]], out: Path) -> None:
    import matplotlib.pyplot as plt

    levels = sorted({r["level"] for r in records if r["group"] == HARDEST_GROUP})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, (key, label) in zip(axes, [("time_ms", "Search time (ms, log)"),
                                       ("expanded", "Expanded nodes (log)")]):
        _grouped_bars(ax, levels, {a: [(_cell(records, lv, a) or {key: float("nan")})[key]
                                       for lv in levels] for a in ALGORITHMS})
        ax.set_yscale("log")
        ax.set_ylabel(label)
        ax.tick_params(axis="x", labelrotation=20)
    axes[0].legend(ncol=3, fontsize=8)
    fig.suptitle(f"Hardest levels ({GROUP_TITLES[HARDEST_GROUP]})", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def generate_report(csv_path: Path, out_dir: Path) -> list[Path]:
    """Write the tables and charts for ``csv_path`` into ``out_dir``; return the paths."""
    records = load_records(csv_path)
    if not records:
        raise ValueError(f"No SOLVED rows in {csv_path}")
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = out_dir / "report_tables.md"
    tables.write_text(build_tables(records), encoding="utf-8")
    charts = [(plot_metrics_by_group, out_dir / "fig_metrics_by_group.png"),
              (plot_cost_ratio, out_dir / "fig_cost_ratio.png")]
    if any(r["group"] == HARDEST_GROUP for r in records):
        charts.append((plot_hardest_levels, out_dir / "fig_hardest_levels.png"))
    for plot, path in charts:
        plot(records, path)
    return [tables] + [path for _, path in charts]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build report tables and charts from a benchmark CSV")
    parser.add_argument("csv", type=Path, help="CSV produced by benchmark.py")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output directory (default: a 'report' folder next to the CSV)")
    args = parser.parse_args()
    for path in generate_report(args.csv, args.out or args.csv.parent / "report"):
        print(f"[OK] {path}")


if __name__ == "__main__":
    main()
