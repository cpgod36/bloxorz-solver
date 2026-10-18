"""Uniform-Cost Search (UCS) solver for Bloxorz."""

from __future__ import annotations

import heapq
import time
import tracemalloc
from itertools import count

from bloxorz.core import Action, BloxorzProblem, State

from .cost import CostFunction, physics_cost
from .metrics import SearchMetrics


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


def _ucs_search(problem: BloxorzProblem, cost_fn: CostFunction) -> tuple[list[Action] | None, int]:
    """Core Uniform-Cost Search algorithm.

    Finds the optimal path with minimum cumulative cost.
    Returns:
        (solution_path, expanded_nodes)
    """
    start_state = problem.initial_state

    # 1. Frontier (Priority Queue) stores: (g_cost, tie_breaker, state)
    tie_breaker = count()
    frontier: list[tuple[float, int, State]] = [(0.0, next(tie_breaker), start_state)]

    # 2. Tracking structures
    best_cost: dict[State, float] = {start_state: 0.0}
    parent: dict[State, tuple[State, Action] | None] = {start_state: None}
    expanded_nodes = 0

    # 3. Main search loop
    while frontier:
        current_cost, _, current_state = heapq.heappop(frontier)

        # Lazy deletion: skip if a cheaper path to this state was already found
        if current_cost > best_cost.get(current_state, float("inf")):
            continue

        # Goal test on pop (guarantees optimal solution cost in UCS)
        if problem.is_goal(current_state):
            path = _reconstruct_path(parent, current_state)
            return path, expanded_nodes

        # A node is expanded when popped and its successors are generated
        expanded_nodes += 1
        for action, next_state in problem.successors(current_state):
            step_cost = cost_fn(current_state, action, next_state)
            new_cost = current_cost + step_cost

            if new_cost < best_cost.get(next_state, float("inf")):
                best_cost[next_state] = new_cost
                parent[next_state] = (current_state, action)
                heapq.heappush(frontier, (new_cost, next(tie_breaker), next_state))

    return None, expanded_nodes


def solve_ucs(problem: BloxorzProblem, cost_fn: CostFunction = physics_cost) -> tuple[list[Action] | None, SearchMetrics]:
    """Solve a Bloxorz problem using UCS and record performance metrics.

    Args:
        problem: The BloxorzProblem to solve.
        cost_fn: Step cost function (defaults to physics_cost).

    Returns:
        (solution_path, metrics)
    """
    tracing_already = tracemalloc.is_tracing()
    if not tracing_already:
        tracemalloc.start()
    tracemalloc.reset_peak()
    start_time = time.perf_counter()

    path, expanded_nodes = _ucs_search(problem, cost_fn)

    search_time = time.perf_counter() - start_time
    _, peak_memory = tracemalloc.get_traced_memory()
    if not tracing_already:
        tracemalloc.stop()

    metrics = SearchMetrics(
        search_time=search_time,
        peak_memory=peak_memory,
        expanded_nodes=expanded_nodes,
        solution_length=len(path) if path is not None else 0,
    )

    return path, metrics


# Convenient alias
ucs = solve_ucs
