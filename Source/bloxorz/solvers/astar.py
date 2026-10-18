"""A* Search solver for Bloxorz."""

from __future__ import annotations

import heapq
import time
import tracemalloc
from itertools import count

from bloxorz.core import Action, BloxorzProblem, State

from .cost import CostFunction, physics_cost
from .heuristic import HeuristicFunction, make_admissible_heuristic
from .metrics import SearchMetrics


def _reconstruct_path(
    parent: dict[State, tuple[State, Action] | None],
    goal_state: State,
) -> list[Action]:
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


def _astar_search(
    problem: BloxorzProblem,
    cost_fn: CostFunction,
    heuristic: HeuristicFunction,
) -> tuple[list[Action] | None, int]:
    """Core A* Search algorithm.

    Priority queue order is evaluated by f(n) = g(n) + h(n).
    Goal testing is performed upon popping to guarantee optimality
    with an admissible heuristic.

    Returns:
        (solution_path, expanded_nodes)
    """
    start_state = problem.initial_state

    # 1. Frontier (Priority Queue) stores: (f_cost, g_cost, tie_breaker, state)
    tie_breaker = count()
    initial_h = heuristic(start_state)
    frontier: list[tuple[float, float, int, State]] = [
        (initial_h, 0.0, next(tie_breaker), start_state)
    ]

    # 2. Tracking structures
    best_g: dict[State, float] = {start_state: 0.0}
    parent: dict[State, tuple[State, Action] | None] = {start_state: None}
    expanded_nodes = 0

    # 3. Search loop
    while frontier:
        f_cost, g_cost, _, current = heapq.heappop(frontier)

        # Lazy deletion: skip if a cheaper path to this state was already found
        if g_cost > best_g.get(current, float("inf")):
            continue

        # Goal test on pop
        if problem.is_goal(current):
            path = _reconstruct_path(parent, current)
            return path, expanded_nodes

        # A node is expanded when popped and its successors are generated
        expanded_nodes += 1
        for action, next_state in problem.successors(current):
            step_cost = cost_fn(current, action, next_state)
            new_g = g_cost + step_cost

            if new_g < best_g.get(next_state, float("inf")):
                best_g[next_state] = new_g
                parent[next_state] = (current, action)
                h_cost = heuristic(next_state)
                new_f = new_g + h_cost
                heapq.heappush(frontier, (new_f, new_g, next(tie_breaker), next_state))

    return None, expanded_nodes


def solve_astar(
    problem: BloxorzProblem,
    cost_fn: CostFunction = physics_cost,
    heuristic: HeuristicFunction | None = None,
) -> tuple[list[Action] | None, SearchMetrics]:
    """Solve a Bloxorz problem using A* Search and record performance metrics.

    Args:
        problem: The BloxorzProblem to solve.
        cost_fn: Step cost function (defaults to physics_cost).
        heuristic: Heuristic function h(state) -> float.
                   Defaults to the admissible heuristic from make_admissible_heuristic.

    Returns:
        (solution_path, metrics)
    """
    if heuristic is None:
        heuristic = make_admissible_heuristic(problem)

    tracing_already = tracemalloc.is_tracing()
    if not tracing_already:
        tracemalloc.start()
    tracemalloc.reset_peak()
    start_time = time.perf_counter()

    path, expanded_nodes = _astar_search(problem, cost_fn, heuristic)

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
astar = solve_astar
