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
            "S#T....###G",
            "###........",
        ],
        "switches": [
            {"pos": [0, 2], "targets": [[0, 7], [0, 9]]}
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


@pytest.mark.parametrize("level_file", sorted(LEVELS_DIR.glob("g*.json")))
def test_all_committed_levels_are_solved_by_astar(level_file: Path):
    level = load_level(level_file)
    problem = BloxorzProblem(level)

    try:
        path, metrics = solve_astar(problem)
    except NotImplementedError:
        pytest.skip(f"Switch/split tile effects for {level_file.name} pending in rules.py (owner: Long)")

    assert path is not None, f"A* must solve {level_file.name}!"
    assert metrics.solution_length == len(path)
    assert metrics.expanded_nodes > 0

    states = replay(problem, path)
    assert problem.is_goal(states[-1]), f"Final state of {level_file.name} must be goal"


def test_group_3_switch_levels_solvability_with_switch_rules(monkeypatch):
    """Verify all Group 3 switch levels are proven solvable under standard switch bridge rules."""
    from bloxorz.core import BridgeEffect, rules
    from bloxorz.core.rules import is_passable, pressed_switches

    def switch_effects(level, state):
        pressed = pressed_switches(level, state)
        if not pressed:
            return state
        b = state.bridges
        for sw in pressed:
            if sw.effect == BridgeEffect.TOGGLE:
                b ^= sw.bridge_mask
            elif sw.effect == BridgeEffect.OPEN:
                b |= sw.bridge_mask
            elif sw.effect == BridgeEffect.CLOSE:
                b &= ~sw.bridge_mask
        if not all(is_passable(level, c, b) for c in state.cells()):
            return None
        return state._replace(bridges=b)

    monkeypatch.setattr(rules, "apply_effects", switch_effects)

    for level_file in sorted(LEVELS_DIR.glob("g3_switch_*.json")):
        level = load_level(level_file)
        problem = BloxorzProblem(level)
        path, metrics = solve_astar(problem)
        assert path is not None, f"Level {level_file.name} must be solvable!"
        assert metrics.solution_length == len(path)
        states = replay(problem, path)
        assert problem.is_goal(states[-1])


def test_group_4_combined_levels_solvability_with_rules(monkeypatch):
    """Verify all Group 4 combined levels are proven solvable under standard split/switch/merge rules."""
    from bloxorz.core import Block, BridgeEffect, Orientation, State, SwitchKind, rules
    from bloxorz.core.rules import is_passable

    def full_effects(level, state):
        pressed = []
        if state.is_split:
            curr_cell = state.cubes[0]
            sw = level.switches.get(curr_cell)
            if sw and sw.kind is SwitchKind.SOFT:
                pressed.append(sw)
        else:
            for c in state.cells():
                sw = level.switches.get(c)
                if sw:
                    if sw.kind is SwitchKind.SOFT or state.is_standing:
                        pressed.append(sw)

        b = state.bridges
        split_targets = None
        for sw in pressed:
            if sw.kind is SwitchKind.SPLIT:
                split_targets = sw.targets
            elif sw.effect == BridgeEffect.TOGGLE:
                b ^= sw.bridge_mask
            elif sw.effect == BridgeEffect.OPEN:
                b |= sw.bridge_mask
            elif sw.effect == BridgeEffect.CLOSE:
                b &= ~sw.bridge_mask

        if split_targets is not None:
            return State(None, split_targets, b)

        if state.is_split:
            c1, c2 = state.cubes
            if c1 == c2:
                return None
            r1, col1 = c1
            r2, col2 = c2
            dr = abs(r1 - r2)
            dc = abs(col1 - col2)
            if dr + dc == 1:
                if dr == 0:
                    merged = Block(r1, min(col1, col2), Orientation.HORIZONTAL)
                else:
                    merged = Block(min(r1, r2), col1, Orientation.VERTICAL)
                return State(merged, None, b)
            return state._replace(bridges=b)

        if not all(is_passable(level, c, b) for c in state.cells()):
            return None
        return state._replace(bridges=b)

    monkeypatch.setattr(rules, "apply_effects", full_effects)

    for level_file in sorted(LEVELS_DIR.glob("g4_combined_*.json")):
        level = load_level(level_file)
        problem = BloxorzProblem(level)
        path, metrics = solve_astar(problem)
        assert path is not None, f"Level {level_file.name} must be solvable!"
        assert metrics.solution_length == len(path)
        states = replay(problem, path)
        assert problem.is_goal(states[-1])

