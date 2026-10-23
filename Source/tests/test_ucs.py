"""Unit tests for the Uniform-Cost Search (UCS) solver."""

from pathlib import Path

import pytest

from bloxorz.core import (
    Action,
    BloxorzProblem,
    load_level,
    parse_level,
    replay,
)
from bloxorz.solvers import physics_cost, solve_ucs, unit_cost

LEVELS_DIR = Path(__file__).resolve().parent.parent / "levels"


def test_ucs_trivial_level():
    # S at (0, 0), G at (0, 3): move R rolls horizontally to (0, 1)-(0, 2), next R stands on (0, 3)
    level = parse_level({"grid": ["S##G"]})
    problem = BloxorzProblem(level)

    path, metrics = solve_ucs(problem)

    assert path == [Action.RIGHT, Action.RIGHT]
    assert metrics.solution_length == 2
    assert metrics.expanded_nodes > 0
    assert metrics.search_time >= 0
    assert metrics.peak_memory > 0

    states = replay(problem, path)
    assert problem.is_goal(states[-1])


def test_ucs_unsolvable_level():
    # Goal is isolated by void, no path possible
    level = parse_level({"grid": ["S#..#G"]})
    problem = BloxorzProblem(level)

    path, metrics = solve_ucs(problem)

    assert path is None
    assert metrics.solution_length == 0
    assert metrics.expanded_nodes > 0


def test_ucs_unit_cost_vs_physics_cost():
    """Verify that physics_cost produces a distinct path from unit_cost (BFS),
    and that the total physics cost of the UCS path is strictly less than that of the unit_cost path.
    """
    level = load_level(LEVELS_DIR / "g1_basic_03.json")
    problem = BloxorzProblem(level)

    path_unit, _ = solve_ucs(problem, cost_fn=unit_cost)
    path_phys, _ = solve_ucs(problem, cost_fn=physics_cost)

    assert path_unit is not None
    assert path_phys is not None
    assert problem.is_goal(replay(problem, path_unit)[-1])
    assert problem.is_goal(replay(problem, path_phys)[-1])

    # The two cost functions must choose different paths
    assert path_unit != path_phys

    # Unit cost optimizes step count: len(path_unit) < len(path_phys)
    assert len(path_unit) < len(path_phys)

    # Physics cost optimizes total energy: cost(path_phys) < cost(path_unit)
    def total_phys_cost(plan: list[Action]) -> float:
        st = problem.initial_state
        total = 0.0
        for a in plan:
            nxt = problem.result(st, a)
            assert nxt is not None
            total += physics_cost(st, a, nxt)
            st = nxt
        return total

    cost_of_unit_path = total_phys_cost(path_unit)
    cost_of_phys_path = total_phys_cost(path_phys)
    assert cost_of_phys_path < cost_of_unit_path


@pytest.mark.parametrize("level_file", sorted(LEVELS_DIR.glob("g*.json")))
def test_all_committed_levels_are_solvable_by_ucs(level_file: Path):
    level = load_level(level_file)
    problem = BloxorzProblem(level)

    try:
        path, metrics = solve_ucs(problem)
    except NotImplementedError:
        pytest.skip(f"Switch/split tile effects for {level_file.name} pending in rules.py (owner: Long)")

    assert path is not None, f"Level {level_file.name} must be solvable!"
    assert metrics.solution_length == len(path)
    assert metrics.expanded_nodes > 0

    states = replay(problem, path)
    assert problem.is_goal(states[-1]), f"Final state of {level_file.name} must be goal"
