"""Shared metrics tracking for search algorithms.

This module provides a unified interface for recording performance metrics
across all solvers (BFS, DFS/IDS, UCS, A*) as specified in the project requirements.
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from bloxorz.core import Action


@dataclass(frozen=True)
class SearchMetrics:
    """Immutable performance metrics collected during a search run.

    Attributes:
        search_time: Total search duration in seconds measured using time.perf_counter().
            time.perf_counter() provides the highest available resolution clock with
            monotonic guarantees, unaffected by system clock adjustments.
        peak_memory: Peak RAM consumed by Python during the search in bytes, measured
            via tracemalloc.
        expanded_nodes: Total count of nodes popped from the frontier whose successors
            were generated. Solvers must increment this synchronously on each node pop.
        solution_length: Number of actions/moves in the returned path. If no solution
            exists (unsolvable), this defaults to 0.
    """

    search_time: float
    peak_memory: int
    expanded_nodes: int
    solution_length: int


class SearchResult(NamedTuple):
    """Standard return type for all solvers containing the path and search metrics.

    Because this inherits from NamedTuple, callers can either:
    1. Unpack directly:
        path, metrics = bfs(problem)
    2. Access attributes by name:
        result = bfs(problem)
        print(result.path, result.metrics.search_time)
    """

    path: list[Action] | None
    metrics: SearchMetrics


class MetricsTracker:
    """Context manager to measure search time, peak memory usage, and node expansions.

    Usage:
        with MetricsTracker() as tracker:
            ...
            tracker.count_expansion()  # Called whenever a node is popped & expanded
            ...
            return tracker.make_result(path)

    Design details:
    - Automatically manages tracemalloc lifecycle: if tracemalloc is already running
      (e.g., during pytest or an outer benchmark harness), it resets peak memory without
      stopping the global tracing. If tracemalloc was not running, it starts it on entry
      and cleanly stops it on exit.
    - Accurately computes incremental peak memory: records a baseline memory right after
      reset_peak() in __enter__ and subtracts baseline from peak in make_metrics, preventing
      pre-allocated memory from polluting the search measurement.
    - Supports ``trace_memory=False`` to bypass tracemalloc overhead during benchmarks.
    - Records start timestamp via time.perf_counter().
    - Thread-safe for sequential single-thread searches.
    """

    def __init__(self, trace_memory: bool = True) -> None:
        self.trace_memory: bool = trace_memory
        self.expanded_nodes: int = 0
        self._start_time: float = 0.0
        self._was_tracing: bool = False
        self._baseline_memory: int = 0

    def __enter__(self) -> MetricsTracker:
        if self.trace_memory:
            # Check if tracemalloc was already activated in the surrounding environment
            self._was_tracing = tracemalloc.is_tracing()
            if not self._was_tracing:
                tracemalloc.start()
            # Reset peak memory counter for this search
            tracemalloc.reset_peak()
            # Record baseline so pre-existing memory allocations are subtracted from peak
            self._baseline_memory, _ = tracemalloc.get_traced_memory()

        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        # Only stop tracemalloc if we were the one who started it
        if self.trace_memory and not self._was_tracing and tracemalloc.is_tracing():
            tracemalloc.stop()

    def count_expansion(self) -> None:
        """Record that a node has been popped from the frontier and its successors generated.

        This must be called exactly once per popped node that has successors generated,
        ensuring uniform metrics across all search algorithms.
        """
        self.expanded_nodes += 1

    def make_metrics(self, path: list[Action] | None) -> SearchMetrics:
        """Compute and return the final SearchMetrics object.

        Args:
            path: The list of actions reaching the goal, or None if unsolvable.

        Returns:
            A populated, immutable SearchMetrics instance.
        """
        elapsed = time.perf_counter() - self._start_time
        if self.trace_memory:
            _, peak = tracemalloc.get_traced_memory()
            peak_memory = max(0, peak - self._baseline_memory)
        else:
            peak_memory = 0

        return SearchMetrics(
            search_time=elapsed,
            peak_memory=peak_memory,
            expanded_nodes=self.expanded_nodes,
            solution_length=len(path) if path is not None else 0,
        )

    def make_result(self, path: list[Action] | None) -> SearchResult:
        """Package the solution path and computed metrics into a SearchResult.

        Args:
            path: The list of actions reaching the goal, or None if unsolvable.

        Returns:
            A SearchResult namedtuple containing (path, metrics).
        """
        return SearchResult(path=path, metrics=self.make_metrics(path))
