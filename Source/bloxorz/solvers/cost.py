"""Cost functions for Uniform-Cost Search (UCS) and A*."""

from __future__ import annotations

from collections.abc import Callable

from bloxorz.core import Action, State

CostFunction = Callable[[State, Action, State], float]


def physics_cost(state: State, action: Action, next_state: State) -> float:
    """Non-uniform step cost based on gravitational potential energy.

    Why does standing up cost 3.0 instead of 1.0?
    ---------------------------------------------
    A standard Bloxorz block has dimensions 1 x 1 x 2:

    1. Rolling while lying down (cost = 1.0):
       - The center of mass rests at height 0.5.
       - When rolling sideways, the center of mass only rises to ~0.71 at its peak
         (a lift of Δh ≈ 0.21).
       - We choose this minimum mechanical effort as the baseline cost: 1.0.

    2. Tilting upright into STANDING (cost = 3.0):
       - To stand the block upright, it pivots around its short bottom edge.
       - The center of mass must be lifted up to ~1.12 at its highest point
         (a lift of Δh ≈ 0.62).
       - The gravitational work required is about 3 times larger:
           0.62 / 0.21 ≈ 2.98 ≈ 3.0.
       - Hence, cost = 3.0 is a natural integer reflection of the physical work
         needed to stand the block up against gravity.

    3. Other moves (cost = 1.0):
       - Rolling from standing to lying down (gravity assists).
       - Moving a single 1 x 1 cube after splitting.

    Properties:
      - Minimum step cost c_min = 1.0.
      - Strictly positive: c(s, a, s') >= 1.0 for all valid moves.
      - Admissibility: allows A* heuristics scaled with c_min = 1.0.
    """
    if next_state.is_standing:
        return 3.0
    return 1.0


def unit_cost(state: State, action: Action, next_state: State) -> float:
    """Uniform cost where every valid move costs 1.0 (reduces UCS to BFS)."""
    return 1.0
