"""Search performance metrics shared across all solvers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchMetrics:
    """Metrics recorded for a single solver run.

    Attributes:
        search_time: Execution time in seconds, measured via time.perf_counter.
        peak_memory: Peak memory usage in bytes, measured via tracemalloc.
        expanded_nodes: Number of nodes popped from frontier whose successors were generated.
        solution_length: Number of moves in the returned solution, or 0 if unsolved.
    """

    search_time: float
    peak_memory: int
    expanded_nodes: int
    solution_length: int
