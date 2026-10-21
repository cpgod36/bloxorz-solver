"""Unit tests for Depth-First Search (DFS) and Iterative Deepening Search (IDS) solvers."""

from dataclasses import replace
from pathlib import Path

from bloxorz.core import (
    BloxorzProblem,
    format_actions,
    load_level,
    parse_level,
    replay,
)
from bloxorz.solvers import bfs, dfs, ids, solve_dfs, solve_ids

FIXTURES = Path(__file__).parent / "fixtures"


def make_problem(*grid, switches=()):
    """Helper to construct a BloxorzProblem directly from grid strings."""
    return BloxorzProblem(parse_level({"grid": list(grid), "switches": list(switches)}))


# ============================================================================
# DFS Tests
# ============================================================================


def test_dfs_solves_classic_stage_1():
    """Verify that DFS finds a valid (not necessarily optimal) path on Stage 1."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    path, metrics = dfs(p)

    assert path is not None
    assert metrics.solution_length == len(path)
    assert metrics.search_time > 0
    assert metrics.peak_memory > 0
    assert metrics.expanded_nodes > 0

    # Verify that the found path is valid and wins
    states = replay(p, path)
    assert p.is_goal(states[-1])


def test_solve_dfs_alias_works():
    """Verify that solve_dfs works identically to dfs."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    res = solve_dfs(p)
    assert res.path is not None
    assert p.is_goal(replay(p, res.path)[-1])


def test_dfs_unsolvable_level():
    """Verify that DFS returns None when no solution exists."""
    p = make_problem(
        "S.",
        "..",
        ".G",
    )
    path, metrics = dfs(p)
    assert path is None
    assert metrics.solution_length == 0
    assert metrics.expanded_nodes == 1


def test_dfs_start_is_already_goal():
    """Verify that DFS returns an empty path when start == goal."""
    level = parse_level({"grid": ["S#G"]})
    p = BloxorzProblem(replace(level, start=level.goal))

    path, metrics = dfs(p)
    assert path == []
    assert metrics.solution_length == 0
    assert metrics.expanded_nodes == 0


def test_dfs_max_depth_cutoff():
    """Verify that DFS cuts off when depth exceeds max_depth."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    # Optimal path is 7 moves, so depth limit 3 cannot reach goal
    path, metrics = dfs(p, max_depth=3)
    assert path is None
    assert metrics.solution_length == 0


def test_dfs_with_trace_memory_false():
    """Verify that DFS supports trace_memory=False."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    res = dfs(p, trace_memory=False)
    assert res.path is not None
    assert res.metrics.peak_memory == 0
    assert res.metrics.search_time > 0


def test_dfs_handles_fragile_tiles():
    """Verify that DFS does not stand upright on fragile tiles."""
    p = make_problem(
        "S####",
        "##F##",
        "####G",
    )
    path, metrics = dfs(p)
    assert path is not None
    states = replay(p, path)
    assert p.is_goal(states[-1])


def test_dfs_deterministic():
    """Verify that DFS produces the exact same path and expansions across runs."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    res1 = dfs(p)
    res2 = dfs(p)
    assert res1.path == res2.path
    assert res1.metrics.expanded_nodes == res2.metrics.expanded_nodes


# ============================================================================
# IDS Tests
# ============================================================================


def test_ids_finds_optimal_path_on_classic_stage_1():
    """Verify that IDS finds the shortest (optimal) 7-move solution on Stage 1."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    path, metrics = ids(p)

    assert path is not None
    # Known optimal solution is 7 moves (matching BFS)
    assert len(path) == 7
    assert metrics.solution_length == 7
    assert format_actions(path) == "RDDRRDR"
    assert metrics.search_time > 0
    assert metrics.peak_memory > 0
    assert metrics.expanded_nodes > 0

    states = replay(p, path)
    assert p.is_goal(states[-1])


def test_ids_matches_bfs_solution_length():
    """Verify that IDS and BFS find paths of identical length on a level with detours."""
    p = make_problem(
        "S####.",
        "######",
        "######",
        "..###G",
    )
    bfs_res = bfs(p)
    ids_res = ids(p)

    assert bfs_res.path is not None
    assert ids_res.path is not None
    assert len(ids_res.path) == len(bfs_res.path)
    assert ids_res.metrics.solution_length == 6


def test_solve_ids_alias_works():
    """Verify that solve_ids alias works as expected."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    res = solve_ids(p)
    assert res.path is not None
    assert len(res.path) == 7


def test_ids_unsolvable_level():
    """Verify that IDS terminates and returns None on an unsolvable level."""
    p = make_problem(
        "S.",
        "..",
        ".G",
    )
    path, metrics = ids(p, max_depth=5)
    assert path is None
    assert metrics.solution_length == 0


def test_ids_start_is_already_goal():
    """Verify that IDS returns [] when start == goal."""
    level = parse_level({"grid": ["S#G"]})
    p = BloxorzProblem(replace(level, start=level.goal))

    path, metrics = ids(p)
    assert path == []
    assert metrics.solution_length == 0
    assert metrics.expanded_nodes == 0


def test_ids_with_trace_memory_false():
    """Verify that IDS supports trace_memory=False."""
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    res = ids(p, trace_memory=False)
    assert res.path is not None
    assert len(res.path) == 7
    assert res.metrics.peak_memory == 0
