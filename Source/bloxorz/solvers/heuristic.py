"""Admissible heuristics for A* search in Bloxorz."""

from __future__ import annotations

from collections.abc import Callable
from bloxorz.core import BloxorzProblem, Cell, State, SwitchKind

HeuristicFunction = Callable[[State], float]


def _manhattan(c1: Cell, c2: Cell) -> int:
    """Manhattan distance between two grid cells."""
    return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])


def _split_cost(cubes: tuple[Cell, Cell], target: Cell) -> float:
    """Lower-bound cost for two split cubes to reach a target cell."""
    d = _manhattan(cubes[0], target) + _manhattan(cubes[1], target)
    return float((d + 1) // 2)


def _direct_cost(state: State, target: Cell) -> float:
    """Lower-bound cost for a state to reach a target cell standing."""
    if state.is_split:
        return _split_cost(state.cubes, target)

    min_dist = min(_manhattan(c, target) for c in state.cells())
    if min_dist == 0:
        return 0.0 if state.is_standing else 2.0

    return float((min_dist + 1) // 2)


def null_heuristic(state: State) -> float:
    """Zero heuristic h(n) = 0. Turns A* into UCS."""
    return 0.0


def make_admissible_heuristic(problem: BloxorzProblem) -> HeuristicFunction:
    """Create an admissible heuristic accounting for split-switch teleports."""
    goal = problem.level.goal

    # Pre-compute (switch_position, remaining_cost_to_goal) for split switches
    teleports = [
        (sw.pos, 1.0 + _split_cost(sw.targets, goal))
        for sw in problem.level.switches.values()
        if sw.kind is SwitchKind.SPLIT and sw.targets
    ]

    def heuristic(state: State) -> float:
        direct = _direct_cost(state, goal)
        if not teleports or state.is_split:
            return direct

        via_switch = min(
            _direct_cost(state, pos) + rem_cost for pos, rem_cost in teleports
        )
        return min(direct, via_switch)

    return heuristic