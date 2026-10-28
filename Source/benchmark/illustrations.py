"""Explanatory figures for the report: how each search algorithm moves through a level.

The solvers are not modified. ``TracingProblem`` wraps a problem and records every
``successors`` call; each call is one expanded node (the same definition the solvers
use for their ``expanded_nodes`` metric), so the recorded order is the real expansion
order of the real solver.

Figures written by ``generate_illustrations``:

* ``fig_level_groups.png``: one level from each difficulty group, with the tile legend.
* ``fig_exploration_order.png``: BFS, DFS and IDS on one level; cells are coloured by
  when the search first reached them and the returned solution is drawn on top.
* ``fig_bfs_layers.png``: nodes expanded by BFS at each depth.
* ``fig_ids_passes.png``: nodes expanded by each depth-limited pass of IDS.

Usage (from ``Source/``):
    python -m benchmark.illustrations
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from benchmark.report import COLORS
from bloxorz.core import BloxorzProblem, load_level, replay
from bloxorz.core.level import Level, Tile
from bloxorz.core.state import State
from bloxorz.solvers import SearchResult, bfs, dfs, ids

SOURCE_DIR = Path(__file__).resolve().parent.parent
LEVELS_DIR = SOURCE_DIR / "levels"

GROUP_EXAMPLES = ["g1_basic_01", "g2_fragile_02", "g3_switch_02", "g4_combined_01"]
EXPLORATION_LEVEL = "g1_basic_03"
BFS_LAYERS_LEVEL = "g4_combined_03"
IDS_PASSES_LEVEL = "g3_switch_03"

TILE_COLORS = {
    Tile.FLOOR: "#d9d9d9",
    Tile.GOAL: "#4d4d4d",
    Tile.FRAGILE: "#E69F00",
    Tile.BRIDGE: "#56B4E9",
    Tile.SOFT_SWITCH: "#f2f2f2",
    Tile.HEAVY_SWITCH: "#f2f2f2",
    Tile.SPLIT_SWITCH: "#f2f2f2",
}
TILE_SYMBOLS = {Tile.SOFT_SWITCH: "O", Tile.HEAVY_SWITCH: "X", Tile.SPLIT_SWITCH: "T",
                Tile.GOAL: "G"}
LEGEND = [("Floor", Tile.FLOOR), ("Goal", Tile.GOAL), ("Fragile", Tile.FRAGILE),
          ("Bridge (hatched = closed at start)", Tile.BRIDGE),
          ("Soft switch (O)", Tile.SOFT_SWITCH), ("Heavy switch (X)", Tile.HEAVY_SWITCH),
          ("Split switch (T)", Tile.SPLIT_SWITCH)]


class TracingProblem:
    """A problem that records the state passed to every ``successors`` call."""

    def __init__(self, problem: BloxorzProblem) -> None:
        self._problem = problem
        self.expansions: list[State] = []

    @property
    def initial_state(self) -> State:
        return self._problem.initial_state

    def is_goal(self, state: State) -> bool:
        return self._problem.is_goal(state)

    def successors(self, state: State):
        self.expansions.append(state)
        return self._problem.successors(state)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._problem, name)


def trace(solver: Callable[..., SearchResult], problem: BloxorzProblem
          ) -> tuple[SearchResult, list[State]]:
    """Run ``solver`` and return its result with the states it expanded, in order."""
    traced = TracingProblem(problem)
    result = solver(traced, trace_memory=False)
    return result, traced.expansions


def first_reached(expansions: list[State]) -> dict[tuple[int, int], int]:
    """For each cell, the index of the first expansion whose block or cubes covered it."""
    first: dict[tuple[int, int], int] = {}
    for index, state in enumerate(expansions):
        for cell in state.cells():
            first.setdefault(cell, index)
    return first


def expansions_per_depth(problem: BloxorzProblem, expansions: list[State]) -> list[int]:
    """Nodes expanded at each depth by a breadth-first order of ``expansions``."""
    depth = {problem.initial_state: 0}
    counts: list[int] = []
    for state in expansions:
        d = depth[state]
        while len(counts) <= d:
            counts.append(0)
        counts[d] += 1
        for _, nxt in problem.successors(state):
            depth.setdefault(nxt, d + 1)
    return counts


def expansions_per_pass(problem: BloxorzProblem, expansions: list[State]) -> list[int]:
    """Nodes expanded by each IDS pass; a pass starts when the initial state is expanded."""
    counts: list[int] = []
    for state in expansions:
        if state == problem.initial_state:
            counts.append(0)
        counts[-1] += 1
    return counts


def _load(name: str, levels_dir: Path) -> tuple[Level, BloxorzProblem]:
    level = load_level(levels_dir / f"{name}.json")
    return level, BloxorzProblem(level)


def _draw_board(ax, level: Level, cell_colors: dict[tuple[int, int], Any] | None = None) -> None:
    """Draw the tiles of ``level``; ``cell_colors`` overrides the colour of listed cells."""
    from matplotlib.patches import Rectangle

    for r in range(level.rows):
        for c in range(level.cols):
            tile = level.grid[r][c]
            if tile is Tile.VOID:
                continue
            color = (cell_colors or {}).get((r, c), TILE_COLORS[tile])
            closed = tile is Tile.BRIDGE and not level.initial_bridges >> level.bridge_bit[(r, c)] & 1
            ax.add_patch(Rectangle((c, r), 1, 1, facecolor=color, edgecolor="white",
                                   linewidth=1, hatch="///" if closed else None))
            symbol = TILE_SYMBOLS.get(tile)
            if symbol:
                ax.text(c + 0.5, r + 0.5, symbol, ha="center", va="center", fontsize=8,
                        color="white" if tile is Tile.GOAL else "black", fontweight="bold")
    sr, sc = level.start
    ax.text(sc + 0.5, sr + 0.5, "S", ha="center", va="center", fontsize=8,
            color="#006400", fontweight="bold")
    ax.set_xlim(0, level.cols)
    ax.set_ylim(level.rows, 0)
    ax.set_aspect("equal")
    ax.axis("off")


def plot_level_groups(out: Path, levels_dir: Path = LEVELS_DIR) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fig, axes = plt.subplots(1, len(GROUP_EXAMPLES), figsize=(14, 3.6))
    for ax, name in zip(axes, GROUP_EXAMPLES):
        level, _ = _load(name, levels_dir)
        _draw_board(ax, level)
        ax.set_title(name, fontsize=9)
    fig.legend(handles=[Patch(facecolor=TILE_COLORS[t], edgecolor="grey", label=label)
                        for label, t in LEGEND], loc="lower center", ncol=len(LEGEND), fontsize=7)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def plot_exploration_order(out: Path, name: str = EXPLORATION_LEVEL,
                           levels_dir: Path = LEVELS_DIR) -> None:
    """BFS, DFS and IDS side by side: when each cell was first reached, plus the solution."""
    import matplotlib.pyplot as plt
    from matplotlib import colormaps
    from matplotlib.cm import ScalarMappable

    level, problem = _load(name, levels_dir)
    cmap = colormaps["viridis_r"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.6))
    for ax, (label, solver) in zip(axes, [("BFS", bfs), ("DFS", dfs), ("IDS", ids)]):
        result, expansions = trace(solver, problem)
        first = first_reached(expansions)
        total = max(len(expansions) - 1, 1)
        _draw_board(ax, level, {cell: cmap(i / total) for cell, i in first.items()})
        states = replay(problem, result.path)
        xs = [sum(c for _, c in s.cells()) / len(s.cells()) + 0.5 for s in states]
        ys = [sum(r for r, _ in s.cells()) / len(s.cells()) + 0.5 for s in states]
        ax.plot(xs, ys, color="black", linewidth=1.6, marker="o", markersize=2.5)
        ax.set_title(f"{label}: {result.metrics.expanded_nodes} nodes expanded, "
                     f"{result.metrics.solution_length} moves", fontsize=9)
    bar = fig.colorbar(ScalarMappable(cmap=cmap), ax=axes, orientation="horizontal",
                       fraction=0.06, pad=0.04, aspect=60)
    bar.set_label("Time a cell is first reached (0 = start of search, 1 = end); "
                  "black line = returned solution (block centre)", fontsize=8)
    bar.set_ticks([0, 1])
    fig.suptitle(f"Exploration order on {name}", fontweight="bold")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_bfs_layers(out: Path, name: str = BFS_LAYERS_LEVEL, levels_dir: Path = LEVELS_DIR) -> None:
    import matplotlib.pyplot as plt

    _, problem = _load(name, levels_dir)
    result, expansions = trace(bfs, problem)
    counts = expansions_per_depth(problem, expansions)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(range(len(counts)), counts, color=COLORS["BFS"])
    ax.set_xlabel("Depth (number of moves from the start)")
    ax.set_ylabel("Nodes expanded at this depth")
    ax.set_title(f"BFS expands one layer at a time ({name})", fontweight="bold")
    ax.text(0.02, 0.95, f"{sum(counts):,} nodes expanded in total\n"
            f"solution found at depth {result.metrics.solution_length}",
            transform=ax.transAxes, va="top", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def plot_ids_passes(out: Path, name: str = IDS_PASSES_LEVEL, levels_dir: Path = LEVELS_DIR) -> None:
    import matplotlib.pyplot as plt

    _, problem = _load(name, levels_dir)
    bfs_nodes = bfs(problem, trace_memory=False).metrics.expanded_nodes
    result, expansions = trace(ids, problem)
    counts = expansions_per_pass(problem, expansions)
    limits = range(1, len(counts) + 1)  # a pass with limit 0 expands nothing
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(limits, counts, color=COLORS["IDS"])
    ax.set_yscale("log")
    ax.set_xlabel("Depth limit of the pass")
    ax.set_ylabel("Nodes expanded in this pass (log)")
    ax.set_title(f"IDS repeats the shallow levels in every pass ({name})", fontweight="bold")
    ax.text(0.02, 0.95, f"IDS total: {sum(counts):,} nodes\nBFS total: {bfs_nodes:,} nodes",
            transform=ax.transAxes, va="top", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def generate_illustrations(out_dir: Path, levels_dir: Path = LEVELS_DIR) -> list[Path]:
    """Write every figure of this module into ``out_dir``; return the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(plot_level_groups, "fig_level_groups.png"),
            (plot_exploration_order, "fig_exploration_order.png"),
            (plot_bfs_layers, "fig_bfs_layers.png"),
            (plot_ids_passes, "fig_ids_passes.png")]
    paths = []
    for plot, filename in jobs:
        path = out_dir / filename
        plot(path, levels_dir=levels_dir)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Build explanatory figures for the report")
    parser.add_argument("--out", type=Path, default=SOURCE_DIR / "benchmark" / "results" / "report",
                        help="Output directory (default: Source/benchmark/results/report)")
    args = parser.parse_args()
    for path in generate_illustrations(args.out):
        print(f"[OK] {path}")


if __name__ == "__main__":
    main()
