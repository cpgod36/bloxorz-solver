"""Admissible heuristics for A* search in Bloxorz.

Theoretical Framework & Proof of Admissibility:
----------------------------------------------
A heuristic h(s) is admissible if it never overestimates the true cost h*(s)
to reach the goal:
    0 <= h(s) <= h*(s)  for all states s.

In Bloxorz with `physics_cost`:
1. Terminal Goal Condition:
   - A state s is a goal state if and only if the full 1 x 1 x 2 block is
     STANDNG vertically on the single goal tile G:
       is_goal(s) <=> (s.is_standing and s.block.cells() == [G]).
   - For any state s where is_goal(s) is True, remaining cost h*(s) = 0.0.

2. Final Step Cost Lower Bound:
   - To transition from any non-goal state into the goal state, the block must
     land upright in the STANDING orientation.
   - Under `physics_cost`, standing upright has step cost c(s, a, s') = 3.0
     (reflecting the potential energy barrier required to tilt the block).
   - Therefore, the final move into G ALWAYS incurs a cost of at least 3.0.
   - For every non-goal state s (where is_goal(s) is False), reaching the goal
     requires at least 1 move. Hence:
       h*(s) >= 3.0  for all non-goal states s.

3. Distance & Movement Lower Bound:
   - Rolling a 1 x 1 x 2 block can cover at most 2 grid cells per step.
   - Thus, covering Manhattan distance d requires at least ceil(d / 2) moves.
   - Under minimum step cost c_min = 1.0, direct movement without teleports
     requires at least ceil(d / 2) cost.

4. Split Switch Shortcut Handling:
   - When a split switch T exists, stepping upright on T splits the block into
     two 1 x 1 cubes at predetermined targets (t1, t2).
   - The heuristic computes:
       h(s) = min(direct_cost(s, G), min_T (direct_cost(s, T) + 1.0 + split_cost(targets, G)))
   - By taking the minimum over all possible teleport shortcuts and direct geometric
     bounds, h(s) is guaranteed to never overestimate the true optimal cost h*(s).
"""

from __future__ import annotations

from collections.abc import Callable
from bloxorz.core import BloxorzProblem, Cell, State, SwitchKind

HeuristicFunction = Callable[[State], float]


def _manhattan(c1: Cell, c2: Cell) -> int:
    """Manhattan distance between two grid cells."""
    return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])


def _split_cost(cubes: tuple[Cell, Cell], target: Cell) -> float:
    """Lower-bound cost for two split cubes to reach a target cell.

    Each cube rolls 1 cell per step. To recombine near target, both cubes must
    travel Manhattan distance to target.
    """
    d = _manhattan(cubes[0], target) + _manhattan(cubes[1], target)
    return float((d + 1) // 2)


def _direct_cost(state: State, target: Cell) -> float:
    """Lower-bound cost for a state to reach a target cell standing.

    Since each roll covers at most 2 cells in distance, Manhattan distance
    gives lower bound ceil(min_dist / 2).
    """
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
    """Create an admissible heuristic accounting for split-switch teleports.

    Computes lower-bound cost to reach the goal:
      h(s) = min(direct_cost(s, goal), min_T (direct_cost(s, T) + 1 + split_cost(targets, goal)))

    Admissibility proof:
      - Direct distance ceil(d / 2) is a relaxed path bound (ignoring holes and bridges).
      - Teleport paths via split switches are lower-bounded by 1 trigger step + split distances.
      - Taking the minimum over all potential shortcuts guarantees h(s) <= h*(s).
    """
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