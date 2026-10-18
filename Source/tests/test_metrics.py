"""Unit tests for the search metrics module."""

import time
import tracemalloc

from bloxorz.core import Action
from bloxorz.solvers import MetricsTracker, SearchMetrics, SearchResult


def test_search_metrics_attributes():
    """Verify that SearchMetrics stores and exposes all four required fields correctly."""
    m = SearchMetrics(search_time=0.123, peak_memory=1024, expanded_nodes=42, solution_length=7)
    assert m.search_time == 0.123
    assert m.peak_memory == 1024
    assert m.expanded_nodes == 42
    assert m.solution_length == 7


def test_search_result_unpacking():
    """Verify that SearchResult can be unpacked as a 2-tuple (path, metrics) or accessed by attribute."""
    m = SearchMetrics(search_time=0.01, peak_memory=500, expanded_nodes=5, solution_length=2)
    actions = [Action.UP, Action.RIGHT]
    res = SearchResult(path=actions, metrics=m)

    # 1. Unpacking as a 2-tuple: path, metrics = solver(problem)
    path, metrics = res
    assert path == actions
    assert metrics == m

    # 2. Accessing by attribute: res.path, res.metrics
    assert res.path == actions
    assert res.metrics == m


def test_metrics_tracker_records_time_and_memory():
    """Verify that MetricsTracker measures non-zero duration, RAM consumption, and expansions."""
    with MetricsTracker() as tracker:
        tracker.count_expansion()
        tracker.count_expansion()

        # Allocate memory so tracemalloc registers positive peak consumption
        _ = [i for i in range(50000)]
        time.sleep(0.01)

        result = tracker.make_result([Action.DOWN])

    assert result.path == [Action.DOWN]
    assert result.metrics.expanded_nodes == 2
    assert result.metrics.solution_length == 1
    assert result.metrics.search_time > 0.005
    assert result.metrics.peak_memory > 0


def test_metrics_tracker_handles_none_path():
    """Verify that when no solution exists (path=None), solution_length is safely set to 0."""
    with MetricsTracker() as tracker:
        result = tracker.make_result(None)

    assert result.path is None
    assert result.metrics.solution_length == 0
    assert result.metrics.expanded_nodes == 0


def test_metrics_tracker_restores_tracemalloc_state():
    """Verify that MetricsTracker does not corrupt external tracemalloc tracing state."""
    # Case A: tracemalloc was not tracing before entering context
    if tracemalloc.is_tracing():
        tracemalloc.stop()

    with MetricsTracker():
        assert tracemalloc.is_tracing()
    # Must be stopped cleanly upon exit
    assert not tracemalloc.is_tracing()

    # Case B: tracemalloc was already active before entering context
    tracemalloc.start()
    try:
        with MetricsTracker():
            assert tracemalloc.is_tracing()
        # Must still be active upon exit (not prematurely terminated)
        assert tracemalloc.is_tracing()
    finally:
        tracemalloc.stop()
