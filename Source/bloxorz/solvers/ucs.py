"""Uniform-Cost Search (UCS) solver for Bloxorz."""

from __future__ import annotations

import heapq
from itertools import count

from bloxorz.core import Action, BloxorzProblem, State

from .cost import CostFunction, physics_cost
from .metrics import MetricsTracker, SearchResult


def _reconstruct_path(parent: dict[State, tuple[State, Action] | None], goal_state: State) -> list[Action]:
    """Reconstruct the sequence of actions from initial state to goal state."""
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


def solve_ucs(problem: BloxorzProblem, cost_fn: CostFunction = physics_cost, trace_memory: bool = True) -> SearchResult:
    """Solve a Bloxorz problem using Uniform-Cost Search (UCS) and record performance metrics.

    Algorithm characteristics:
    - **Optimality**: UCS expands nodes in order of cumulative path cost g(n).
      By performing the goal test when a node is *popped* from the priority queue,
      it is mathematically guaranteed to return the optimal (lowest cost) path.
    - **Priority Queue**: Uses Python's ``heapq`` storing ``(g_cost, tie_breaker, state)``.
    - **Duplicate Handling**: Employs lazy deletion; if a popped state has a cost strictly
      greater than its best recorded cost in ``best_cost``, it is discarded.
    - **Metrics Tracking**: Managed via ``MetricsTracker`` to uniformly capture execution
      time, peak memory (tracemalloc), expanded nodes, and solution path length.

    Args:
        problem: The BloxorzProblem instance to solve.
        cost_fn: Step cost function c(s, a, s') (defaults to physics_cost).
        trace_memory: Whether to track peak memory using tracemalloc (default: True).

    Returns:
        SearchResult containing the optimal path and search metrics.
    """
    with MetricsTracker(trace_memory=trace_memory) as tracker:
        start_state = problem.initial_state

        if problem.is_goal(start_state):
            return tracker.make_result([])

        # 1. Frontier (Priority Queue) stores: (g_cost, tie_breaker, state)
        tie_breaker = count()
        frontier: list[tuple[float, int, State]] = [(0.0, next(tie_breaker), start_state)]

        # 2. Tracking structures
        best_cost: dict[State, float] = {start_state: 0.0}
        parent: dict[State, tuple[State, Action] | None] = {start_state: None}

        # 3. Main search loop
        while frontier:
            current_cost, _, current_state = heapq.heappop(frontier)

            # Lazy deletion: skip if a cheaper path to this state was already found
            if current_cost > best_cost.get(current_state, float("inf")):
                continue

            # Goal test on pop (guarantees optimal solution cost in UCS)
            if problem.is_goal(current_state):
                path = _reconstruct_path(parent, current_state)
                return tracker.make_result(path)

            # A node is expanded when popped and its successors are generated
            tracker.count_expansion()
            for action, next_state in problem.successors(current_state):
                step_cost = cost_fn(current_state, action, next_state)
                new_cost = current_cost + step_cost

                if new_cost < best_cost.get(next_state, float("inf")):
                    best_cost[next_state] = new_cost
                    parent[next_state] = (current_state, action)
                    heapq.heappush(frontier, (new_cost, next(tie_breaker), next_state))

        return tracker.make_result(None)


# Convenient alias
ucs = solve_ucs
