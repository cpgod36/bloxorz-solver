"""Cost functions for Uniform-Cost Search (UCS) and A*."""

from __future__ import annotations

from collections.abc import Callable

from bloxorz.core import Action, State

CostFunction = Callable[[State, Action, State], float]


def physics_cost(state: State, action: Action, next_state: State) -> float:
    """Non-uniform cost function based on block mechanics and potential energy.

    - Standing up (next_state.is_standing): Lifting the center of mass from height
      0.5 to 1.0 requires positive work against gravity -> cost = 2.0.
    - Lying down or rolling sideways: Gravity assists or center of mass stays at 0.5 -> cost = 1.0.
    - Splitting / switching cubes: Standard movement cost -> cost = 1.0.

    Properties:
      - Minimum step cost c_min = 1.0.
      - Strictly positive (c(s, a, s') >= 1.0).
      - Allows admissible heuristics for A* (scaled by c_min = 1.0).
    """
    if next_state.is_standing:
        return 2.0
    return 1.0


def unit_cost(state: State, action: Action, next_state: State) -> float:
    """Uniform cost where every valid move costs 1.0 (reduces UCS to BFS)."""
    return 1.0
