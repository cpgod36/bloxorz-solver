"""Unit tests for the A* Search solver and heuristic functions."""

from pathlib import Path

import pytest

from bloxorz.core import (
    Action,
    BloxorzProblem,
    Orientation,
    State,
    load_level,
    parse_level,
    replay,
)
from bloxorz.solvers import (
    make_admissible_heuristic,
    null_heuristic,
    physics_cost,
    solve_astar,
    solve_ucs,
    unit_cost,
)

LEVELS_DIR = Path(__file__).resolve().parent.parent / "levels"


def test_astar_trivial_level():
    level = parse_level({"grid": ["S##G"]})
    problem = BloxorzProblem(level)

    path, metrics = solve_astar(problem)

    assert path == [Action.RIGHT, Action.RIGHT]
    assert metrics.solution_length == 2
    assert metrics.expanded_nodes > 0
    assert metrics.search_time >= 0
    assert metrics.peak_memory > 0

    states = replay(problem, path)
    assert problem.is_goal(states[-1])


def test_astar_unsolvable_level():
    level = parse_level({"grid": ["S#..#G"]})
    problem = BloxorzProblem(level)

    path, metrics = solve_astar(problem)

    assert path is None
    assert metrics.solution_length == 0
    assert metrics.expanded_nodes > 0


def test_null_heuristic_astar_matches_ucs():
    # With h(n) = 0, A* behaves exactly like UCS
    level = parse_level({"grid": ["S#####", "######", "#####G"]})
    problem = BloxorzProblem(level)

    path_ucs, m_ucs = solve_ucs(problem, cost_fn=physics_cost)
    path_astar, m_astar = solve_astar(problem, cost_fn=physics_cost, heuristic=null_heuristic)

    assert path_ucs is not None
    assert path_astar is not None
    assert len(path_astar) == len(path_ucs)
    assert m_astar.expanded_nodes == m_ucs.expanded_nodes


def test_astar_expands_fewer_or_equal_nodes_than_ucs():
    # On non-trivial levels, informed A* should expand fewer nodes than UCS
    level = load_level(LEVELS_DIR / "g1_basic_04.json")
    problem = BloxorzProblem(level)

    _, m_ucs = solve_ucs(problem, cost_fn=physics_cost)
    _, m_astar = solve_astar(problem, cost_fn=physics_cost)

    assert m_astar.expanded_nodes <= m_ucs.expanded_nodes
    assert m_astar.solution_length == m_ucs.solution_length


def test_heuristic_split_switch_teleport_bound():
    # Level where goal is far (col 10), but split switch teleports near goal (col 9)
    level_data = {
        "grid": [
            "S#T.....##G",
            "###........",
        ],
        "switches": [
            {"pos": [0, 2], "targets": [[0, 8], [0, 9]]}
        ]
    }
    level = parse_level(level_data)
    problem = BloxorzProblem(level)
    h_fn = make_admissible_heuristic(problem)

    initial_h = h_fn(problem.initial_state)

    # Direct distance to goal (col 0 to 9) is ceil(9 / 2) = 5
    # Via switch at (0, 2): dist(0, 2) is 1 move. Then 1 move trigger + 0 moves to goal
    # Heuristic must account for teleport shortcut without overestimating
    assert initial_h <= 5.0
    assert initial_h >= 0.0


@pytest.mark.parametrize("level_file", sorted(LEVELS_DIR.glob("g1_basic_*.json")))
def test_all_g1_basic_levels_are_solved_by_astar(level_file: Path):
    level = load_level(level_file)
    problem = BloxorzProblem(level)

    path, metrics = solve_astar(problem)

    assert path is not None, f"A* must solve {level_file.name}!"
    assert metrics.solution_length == len(path)
    assert metrics.expanded_nodes > 0

    states = replay(problem, path)
    assert problem.is_goal(states[-1]), f"Final state of {level_file.name} must be goal"
