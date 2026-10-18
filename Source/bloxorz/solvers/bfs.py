"""Breadth-First Search (BFS) solver for Bloxorz.

This module implements a standard Graph-Search BFS solver designed to find
the shortest solution path (minimum number of rolls/moves) to solve a Bloxorz level.
"""

from __future__ import annotations

from collections import deque
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
            # Reached initial state (its parent entry is None)
            break
        prev_state, action = entry
        actions.append(action)
        curr = prev_state

    # Reverse because we traversed from goal back to initial state
    actions.reverse()
    return actions


def bfs(problem: BloxorzProblem) -> SearchResult:
    """Solve the Bloxorz problem using Breadth-First Search (BFS).

    Algorithm characteristics:
    - **Completeness & Optimality**: Since every move in Bloxorz has uniform step cost
      (1 move per roll/switch), BFS is guaranteed to find an optimal (shortest) path.
    - **Frontier**: Implemented via ``collections.deque`` (double-ended queue) for
      O(1) FIFO operations (``append`` to push right, ``popleft`` to pop left).
    - **Repeated States & Cycle Detection**: Tracked using a ``parent`` dictionary
      keyed by the immutable, hashable ``State``. If a state has already been seen,
      it is not re-added to the frontier.
    - **Memory Optimization**: Instead of storing the growing list of actions on
      every item in the frontier queue (which would consume O(b^d * d) memory),
      the frontier only stores ``State`` objects, and each reached state references its
      immediate predecessor in ``parent``.
    - **Early Goal Test**: Per standard AI textbook convention (Russell & Norvig, AIMA),
      when step costs are uniform, goal testing is performed immediately upon generating
      a child state. This avoids having to expand an entire extra layer of nodes before
      confirming the goal.
    - **Expansion Metric**: Exactly aligns with project guidelines: a node is counted
      as expanded when it is popped from the frontier and its legal successors are generated.

    Args:
        problem: The Bloxorz search problem instance providing ``initial_state``,
            ``successors(state)``, and ``is_goal(state)``.

    Returns:
        A SearchResult tuple: ``(path, metrics)``.
        - ``path``: List of Actions to solve the stage, or ``None`` if unsolvable.
        - ``metrics``: SearchMetrics with time, peak memory, expanded nodes, and path length.
    """
    with MetricsTracker() as tracker:
        initial = problem.initial_state

        # Edge case: initial state is already the goal (0 moves, 0 expansions)
        if problem.is_goal(initial):
            return tracker.make_result([])

        # Frontier: FIFO queue holding states to be expanded
        frontier: deque[State] = deque([initial])

        # Parent table: maps state -> (parent_state, action)
        # Also serves as the closed / visited set to prevent loops
        parent: dict[State, tuple[State, Action] | None] = {initial: None}

        while frontier:
            # Pop the oldest node in the frontier (FIFO)
            state = frontier.popleft()

            # Record node expansion: successors will now be generated
            tracker.count_expansion()

            # problem.successors() generates legal (action, next_state) pairs
            # in deterministic order: Up, Down, Left, Right (and Switch if split)
            for action, next_state in problem.successors(state):
                # Only explore unvisited states (avoids infinite loops and redundant work)
                if next_state not in parent:
                    # Record predecessor for path reconstruction
                    parent[next_state] = (state, action)

                    # Early goal test: check if next_state achieves the goal condition
                    if problem.is_goal(next_state):
                        path = _reconstruct_path(parent, next_state)
                        return tracker.make_result(path)

                    # Add unvisited successor to frontier for future expansion
                    frontier.append(next_state)

        # Frontier exhausted without reaching goal: puzzle is unsolvable
        return tracker.make_result(None)


# Alias for explicit naming
solve_bfs = bfs
