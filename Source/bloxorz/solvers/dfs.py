"""Depth-First Search (DFS) and Iterative Deepening Search (IDS) solvers for Bloxorz."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .metrics import MetricsTracker, SearchResult

if TYPE_CHECKING:
    from bloxorz.core import Action, BloxorzProblem, State


def _reconstruct_path(
    parent: dict[State, tuple[State, Action] | None],
    goal_state: State,
) -> list[Action]:
    """Reconstruct the sequence of actions from initial state to goal_state.

    Traverses backward from goal_state to initial_state using the parent pointer
    dictionary, collecting actions, and reverses the sequence at the end.

    Args:
        parent: Mapping from each reached state to (previous_state, action_taken),
            or None for the initial state.
        goal_state: The terminal goal state that was reached.

    Returns:
        List of Actions from start to goal in chronological execution order.
    """
    actions: list[Action] = []
    curr = goal_state
    while True:
        entry = parent[curr]
        if entry is None:
            break
        prev_state, action = entry
        actions.append(action)
        curr = prev_state

    actions.reverse()
    return actions


def dfs(
    problem: BloxorzProblem,
    max_depth: int | None = None,
    trace_memory: bool = True,
) -> SearchResult:
    """Solve the Bloxorz problem using Depth-First Search (DFS).

    Algorithm characteristics:
    - **Explicit Stack**: Implemented iteratively with a Python list (LIFO) to prevent
      RecursionError on deep search spaces.
    - **Graph Search / Cycle Avoidance**: Maintains a visited set of hashable ``State``
      objects to prevent getting trapped in infinite loops.
    - **Action Exploration Order**: Successors are pushed onto the stack in reverse order
      (reversed(successors)) so that the first action (Up) is on top of the stack and
      explored first, maintaining the canonical order: Up, Down, Left, Right.
    - **Node Expansion Metric**: A node is counted as expanded when it is popped from
      the stack and its legal successors are generated.

    Args:
        problem: The Bloxorz search problem instance.
        max_depth: Optional maximum search depth cutoff. If None, search is unbounded.
        trace_memory: Whether to track peak memory using tracemalloc (default: True).

    Returns:
        A SearchResult tuple: ``(path, metrics)``.
        - ``path``: List of Actions to solve the stage, or ``None`` if unsolvable.
        - ``metrics``: SearchMetrics with time, peak memory, expanded nodes, and path length.
    """
    with MetricsTracker(trace_memory=trace_memory) as tracker:
        initial = problem.initial_state

        if problem.is_goal(initial):
            return tracker.make_result([])

        # Stack holds (state, depth)
        stack: list[tuple[State, int]] = [(initial, 0)]
        parent: dict[State, tuple[State, Action] | None] = {initial: None}
        visited: set[State] = {initial}

        while stack:
            state, depth = stack.pop()

            if problem.is_goal(state):
                path = _reconstruct_path(parent, state)
                return tracker.make_result(path)

            if max_depth is not None and depth >= max_depth:
                continue

            tracker.count_expansion()

            # Push in reverse order so the canonical order (Up, Down, Left, Right) is popped first
            for action, next_state in reversed(problem.successors(state)):
                if next_state not in visited:
                    visited.add(next_state)
                    parent[next_state] = (state, action)
                    stack.append((next_state, depth + 1))

        return tracker.make_result(None)


def ids(
    problem: BloxorzProblem,
    max_depth: int = 100,
    trace_memory: bool = True,
) -> SearchResult:
    """Solve the Bloxorz problem using Iterative Deepening Search (IDS).

    Repeatedly applies Depth-Limited Search (DLS) with increasing depth limits
    (0, 1, 2, ..., max_depth). Combines the linear space complexity of DFS with the
    optimality and completeness of BFS (since all move costs are uniform).

    Algorithm characteristics:
    - **Optimality**: Finds the shortest move sequence (minimum solution length).
    - **Explicit Stack**: Each DLS pass uses an explicit stack, avoiding recursion.
    - **Cycle Detection**: Tracks the minimum depth at which each state was reached
      within the current depth limit iteration. If a state is encountered at a depth
      greater than or equal to its previously recorded depth in this iteration, it is pruned.
    - **Total Metrics**: Accurately aggregates total search time, peak memory, and total
      node expansions across all depth limit iterations.

    Args:
        problem: The Bloxorz search problem instance.
        max_depth: Maximum depth limit to iterate up to (default: 100).
        trace_memory: Whether to track peak memory using tracemalloc (default: True).

    Returns:
        A SearchResult tuple: ``(path, metrics)``.
        - ``path``: List of Actions to solve the stage, or ``None`` if unsolvable.
        - ``metrics``: SearchMetrics with time, peak memory, expanded nodes, and path length.
    """
    with MetricsTracker(trace_memory=trace_memory) as tracker:
        initial = problem.initial_state

        if problem.is_goal(initial):
            return tracker.make_result([])

        for limit in range(max_depth + 1):
            # Depth-limited search for this iteration
            stack: list[tuple[State, int]] = [(initial, 0)]
            parent: dict[State, tuple[State, Action] | None] = {initial: None}
            # reached: state -> minimum depth reached in this iteration
            reached: dict[State, int] = {initial: 0}

            while stack:
                state, depth = stack.pop()

                if problem.is_goal(state):
                    path = _reconstruct_path(parent, state)
                    return tracker.make_result(path)

                if depth < limit:
                    tracker.count_expansion()

                    for action, next_state in reversed(problem.successors(state)):
                        next_depth = depth + 1
                        if next_state not in reached or next_depth < reached[next_state]:
                            reached[next_state] = next_depth
                            parent[next_state] = (state, action)
                            stack.append((next_state, next_depth))

        return tracker.make_result(None)


solve_dfs = dfs
solve_ids = ids
