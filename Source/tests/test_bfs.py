"""Unit tests for the Breadth-First Search (BFS) solver."""

from dataclasses import replace
from pathlib import Path

from bloxorz.core import (
    Action,
    BloxorzProblem,
    format_actions,
    load_level,
    parse_actions,
    parse_level,
    replay,
)
from bloxorz.solvers import bfs, solve_bfs

FIXTURES = Path(__file__).parent / "fixtures"


def make_problem(*grid, switches=()):
    """Helper to construct a BloxorzProblem directly from a list of grid strings."""
    return BloxorzProblem(parse_level({"grid": list(grid), "switches": list(switches)}))


def test_bfs_solves_classic_stage_1_with_optimal_path():
    """Verify BFS finds the known 7-move optimal solution on Stage 1 of original Bloxorz."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    path, metrics = bfs(p)

    assert path is not None
    # Known optimal solution is exactly 7 moves: R -> D -> D -> R -> R -> D -> R
    assert len(path) == 7
    assert metrics.solution_length == 7
    assert format_actions(path) == "RDDRRDR"

    # Metrics validation
    assert metrics.search_time > 0
    assert metrics.peak_memory > 0
    assert metrics.expanded_nodes > 0

    # Ensure replaying the actions leads to a winning goal state
    states = replay(p, path)
    assert p.is_goal(states[-1])


def test_solve_bfs_alias_works():
    """Verify that solve_bfs behaves identically as an alias to bfs."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    res = solve_bfs(p)
    assert res.path is not None
    assert len(res.path) == 7
    assert res.metrics.solution_length == 7


def test_bfs_unsolvable_level():
    """Verify that BFS returns None for path and 0 for solution_length on an impossible level."""
    # S is isolated on a 1x1 platform; rolling any direction drops the block off the board
    p = make_problem(
        "S.",
        "..",
        ".G",
    )
    path, metrics = bfs(p)
    assert path is None
    assert metrics.solution_length == 0
    # Initial state S was popped and expanded (all 4 roll attempts resulted in illegal falls)
    assert metrics.expanded_nodes == 1


def test_bfs_start_is_already_goal():
    """Verify that if the initial state is already at the goal, 0 moves and 0 expansions occur."""
    level = parse_level({"grid": ["S#G"]})
    p = BloxorzProblem(replace(level, start=level.goal))

    path, metrics = bfs(p)
    assert path == []
    assert metrics.solution_length == 0
    assert metrics.expanded_nodes == 0


def test_bfs_finds_shortest_path_when_multiple_paths_exist():
    """Verify that BFS picks the strictly shortest route when alternative detour paths exist."""
    p = make_problem(
        "S####.",
        "######",
        "######",
        "..###G",
    )
    path, metrics = bfs(p)
    assert path is not None
    # 6 moves is the shortest possible path on this layout
    assert len(path) == 6
    states = replay(p, path)
    assert p.is_goal(states[-1])


def test_bfs_handles_fragile_tiles():
    """Verify that BFS safely navigates across fragile tiles (F) without standing upright on them."""
    p = make_problem(
        "S####",
        "##F##",
        "####G",
    )
    path, metrics = bfs(p)
    assert path is not None
    states = replay(p, path)
    assert p.is_goal(states[-1])


def test_bfs_deterministic():
    """Verify that BFS produces identical paths and expansion counts across multiple runs."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    res1 = bfs(p)
    res2 = bfs(p)
    assert res1.path == res2.path
    assert res1.metrics.expanded_nodes == res2.metrics.expanded_nodes
    assert res1.metrics.solution_length == res2.metrics.solution_length


def test_bfs_with_trace_memory_false():
    """Verify that BFS runs properly and sets peak_memory=0 when trace_memory=False."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    res = bfs(p, trace_memory=False)
    assert res.path is not None
    assert len(res.path) == 7
    assert res.metrics.solution_length == 7
    assert res.metrics.peak_memory == 0
    assert res.metrics.search_time > 0
    assert res.metrics.expanded_nodes > 0

