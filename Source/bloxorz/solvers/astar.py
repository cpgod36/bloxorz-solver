"""A* Search solver for Bloxorz."""

from __future__ import annotations

import heapq
from itertools import count

from bloxorz.core import Action, BloxorzProblem, State

from .cost import CostFunction, physics_cost
from .heuristic import HeuristicFunction, make_admissible_heuristic
from .metrics import MetricsTracker, SearchResult


def _reconstruct_path(parent: dict[State, tuple[State, Action] | None], goal_state: State) -> list[Action]:
    """Reconstruct sequence of actions from initial state to goal state."""
    path: list[Action] = []
    curr: State = goal_state
    while parent[curr] is not None:
        step_info = parent[curr]
        assert step_info is not None
        prev_state, action = step_info
        path.append(action)
        curr = prev_state
    path.reverse()
    return path


def solve_astar(
    problem: BloxorzProblem,
    cost_fn: CostFunction = physics_cost,
    heuristic: HeuristicFunction | None = None,
    trace_memory: bool = True,
) -> SearchResult:
    """Solve a Bloxorz problem using A* Search and record performance metrics.

    Algorithm characteristics:
    - **Optimality**: Uses evaluation function f(n) = g(n) + h(n). Since h(n)
      is admissible (never overestimates the true remaining cost), goal-testing
      upon popping from the priority queue guarantees an optimal path.
    - **Priority Queue**: Python's ``heapq`` storing ``(f_cost, g_cost, tie_breaker, state)``.
    - **Duplicate Handling**: Lazy deletion; if a popped state has g_cost strictly
      greater than its best recorded cost in ``best_g``, it is pruned.
    - **Metrics Tracking**: Wrapped with ``MetricsTracker`` to uniformly capture
      search time, peak memory usage, expanded nodes, and solution path length.

    Args:
        problem: The BloxorzProblem instance to solve.
        cost_fn: Step cost function c(s, a, s') (defaults to physics_cost).
        heuristic: Heuristic function h(state) -> float. Defaults to
            ``make_admissible_heuristic(problem)``.
        trace_memory: Whether to track peak memory using tracemalloc (default: True).

    Returns:
        SearchResult containing the optimal path and search metrics.
    """
    if heuristic is None:
        heuristic = make_admissible_heuristic(problem)

    with MetricsTracker(trace_memory=trace_memory) as tracker:
        start_state = problem.initial_state

        if problem.is_goal(start_state):
            return tracker.make_result([])

        # 1. Frontier (Priority Queue) stores: (f_cost, g_cost, tie_breaker, state)
        tie_breaker = count()
        initial_h = heuristic(start_state)
        frontier: list[tuple[float, float, int, State]] = [
            (initial_h, 0.0, next(tie_breaker), start_state)
        ]

        # 2. Tracking structures
        best_g: dict[State, float] = {start_state: 0.0}
        parent: dict[State, tuple[State, Action] | None] = {start_state: None}

        # 3. Search loop
        while frontier:
            f_cost, g_cost, _, current = heapq.heappop(frontier)

            # Lazy deletion: skip if a cheaper path to this state was already found
            if g_cost > best_g.get(current, float("inf")):
                continue

            # Goal test on pop
            if problem.is_goal(current):
                path = _reconstruct_path(parent, current)
                return tracker.make_result(path)

            # A node is expanded when popped and its successors are generated
            tracker.count_expansion()
            for action, next_state in problem.successors(current):
                step_cost = cost_fn(current, action, next_state)
                new_g = g_cost + step_cost

                if new_g < best_g.get(next_state, float("inf")):
                    best_g[next_state] = new_g
                    parent[next_state] = (current, action)
                    h_cost = heuristic(next_state)
                    new_f = new_g + h_cost
                    heapq.heappush(frontier, (new_f, new_g, next(tie_breaker), next_state))

        return tracker.make_result(None)


# Convenient alias
astar = solve_astar
