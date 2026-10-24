"""Admissible heuristics for A* search in Bloxorz.

Theoretical Framework & Proof of Admissibility:
----------------------------------------------
A heuristic h(s) is admissible if it never overestimates the true cost h*(s)
to reach the goal:
    0 <= h(s) <= h*(s)  for all states s.

1. Terminal Goal Condition:
   - A state s is a goal state if and only if the full 1 x 1 x 2 block is
     STANDING vertically on the single goal tile G:
       is_goal(s) <=> (s.is_standing and s.block.cells() == [G]).
   - For any state s where is_goal(s) is True, remaining cost h*(s) = 0.0.

2. Final Step Cost Lower Bound:
   - To transition from any non-goal state into the goal state, the block must
     land upright in the STANDING orientation on G.
   - Under `physics_cost`, standing upright has step cost c(s, a, s') = 3.0.
   - Under `unit_cost`, any valid move has step cost 1.0.
   - In general, with standing cost c_stand, any non-goal state requires at least
     one move to reach the goal:
       h*(s) >= c_stand  for all non-goal states s.

3. Distance & Movement Lower Bound:
   - Rolling a 1 x 1 x 2 block covers at most 2 grid cells per step.
   - Covering Manhattan distance d requires at least ceil(d / 2) moves.
   - Under minimum step cost c_min, direct movement requires at least
     ceil(d / 2) * c_min.

4. Split Switch & Cube Merge Lower Bound:
   - When a split switch T exists, stepping upright on T splits the block into
     two 1 x 1 cubes at predetermined targets (t1, t2).
   - Once split, the two individual cubes roll 1 cell per step. To recombine into
     a single block, the cubes must become adjacent (Manhattan distance 1).
   - Each cube step can decrease the Manhattan distance between them by at most 1.
   - Thus, meeting requires at least max(manhattan(c1, c2) - 1, 0) moves.
   - Once merged, reaching and standing on G requires at least c_stand.
   - Stepping on T is itself a roll to T; no additional trigger step cost is added.
   - Teleport shortcut cost is:
       direct_cost(s, T) + split_cost(targets, c_min, c_stand).
   - Direct and teleport bounds combined:
       h(s) = max(min(direct_cost(s, G), min_T (direct_cost(s, T) + split_cost(targets, G))), c_stand).
   - This ensures h(s) <= h*(s) under both `physics_cost` and `unit_cost`.
"""

from __future__ import annotations

from collections.abc import Callable
from bloxorz.core import BloxorzProblem, Cell, State, SwitchKind

HeuristicFunction = Callable[[State], float]


def _manhattan(c1: Cell, c2: Cell) -> int:
    """Manhattan distance between two grid cells."""
    return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])


def _split_cost(
    cubes: tuple[Cell, Cell],
    c_min: float = 1.0,
    c_stand: float = 3.0,
) -> float:
    """Lower-bound cost for two split cubes to merge and reach standing goal.

    Each cube rolls 1 cell per step. To recombine, they must become adjacent
    (Manhattan distance 1). Once merged, reaching and standing on the goal
    requires at least one final stand move costing at least c_stand.
    """
    meet_moves = max(_manhattan(cubes[0], cubes[1]) - 1, 0)
    return float(meet_moves) * c_min + c_stand


def _direct_cost(
    state: State,
    target: Cell,
    c_min: float = 1.0,
    c_stand: float = 3.0,
) -> float:
    """Lower-bound cost for a state to reach a target cell standing.

    Since each roll covers at most 2 cells in distance, Manhattan distance
    gives lower bound ceil(min_dist / 2).
    """
    if state.is_split:
        return _split_cost(state.cubes, c_min, c_stand)

    min_dist = min(_manhattan(c, target) for c in state.cells())
    if min_dist == 0:
        return 0.0 if state.is_standing else c_min

    return float((min_dist + 1) // 2) * c_min


def null_heuristic(state: State) -> float:
    """Zero heuristic h(n) = 0. Turns A* into UCS."""
    return 0.0


def make_admissible_heuristic(
    problem: BloxorzProblem,
    c_min: float = 1.0,
    c_stand: float = 3.0,
) -> HeuristicFunction:
    """Create an admissible heuristic accounting for split-switch teleports.

    Computes lower-bound cost to reach the goal:
      h(s) = min(direct_cost(s, goal), min_T (direct_cost(s, T) + split_cost(targets, c_min, c_stand)))
    enforcing h(s) >= c_stand for all non-goal states s.

    Admissibility proof:
      - Direct distance ceil(d / 2) is a relaxed path bound (ignoring holes and bridges).
      - Teleport paths via split switches are lower-bounded by rolling to T plus split merge cost.
      - Taking the minimum over all potential shortcuts guarantees h(s) <= h*(s).
      - Terminal condition requires standing upright on goal G, so non-goal h(s) >= c_stand.

    Note on Consistency:
      While admissible (h(s) <= h*(s)), this heuristic is NOT consistent (monotone)
      on levels with split switches due to teleport shortcuts creating potential
      step cost under-approximations. A* remains optimal because our search
      implementation updates nodes when a cheaper path is discovered (best_g).
    """
    goal = problem.level.goal

    # Pre-compute (switch_position, remaining_cost_to_goal) for split switches
    teleports = [
        (sw.pos, _split_cost(sw.targets, c_min, c_stand))
        for sw in problem.level.switches.values()
        if sw.kind is SwitchKind.SPLIT and sw.targets
    ]

    def heuristic(state: State) -> float:
        if problem.is_goal(state):
            return 0.0

        if state.is_split:
            return _split_cost(state.cubes, c_min, c_stand)

        direct = _direct_cost(state, goal, c_min, c_stand)
        if not teleports:
            return max(direct, c_stand)

        via_switch = min(
            _direct_cost(state, pos, c_min, c_stand) + rem_cost
            for pos, rem_cost in teleports
        )
        return max(min(direct, via_switch), c_stand)

    return heuristic
