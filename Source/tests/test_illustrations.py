"""Unit tests for benchmark.illustrations (traced runs behind the explanatory figures)."""

from pathlib import Path

import pytest

from benchmark.illustrations import (
    expansions_per_depth,
    expansions_per_pass,
    first_reached,
    plot_bfs_layers,
    plot_exploration_order,
    plot_ids_passes,
    trace,
)
from bloxorz.core import BloxorzProblem, load_level
from bloxorz.solvers import bfs, dfs, ids

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def problem():
    return BloxorzProblem(load_level(FIXTURES / "classic_01.json"))


@pytest.mark.parametrize("solver", [bfs, dfs, ids])
def test_trace_records_exactly_the_expanded_nodes(problem, solver):
    result, expansions = trace(solver, problem)
    assert len(expansions) == result.metrics.expanded_nodes
    assert expansions[0] == problem.initial_state


def test_trace_does_not_change_the_solver_result(problem):
    traced, _ = trace(bfs, problem)
    assert traced.path == bfs(problem).path


def test_first_reached_starts_at_the_start_cell(problem):
    _, expansions = trace(bfs, problem)
    first = first_reached(expansions)
    assert first[problem.level.start] == 0
    assert all(i >= 0 for i in first.values())


def test_bfs_expansions_per_depth_sum_to_total_and_start_with_one(problem):
    result, expansions = trace(bfs, problem)
    counts = expansions_per_depth(problem, expansions)
    assert sum(counts) == result.metrics.expanded_nodes
    assert counts[0] == 1
    assert len(counts) == result.metrics.solution_length  # goal depth is never expanded


def test_ids_expansions_per_pass_sum_to_total(problem):
    result, expansions = trace(ids, problem)
    counts = expansions_per_pass(problem, expansions)
    assert sum(counts) == result.metrics.expanded_nodes
    assert len(counts) == result.metrics.solution_length  # one pass per limit 1..depth


def test_plots_write_non_empty_files(tmp_path):
    for plot, name in [(plot_exploration_order, "a.png"), (plot_bfs_layers, "b.png"),
                       (plot_ids_passes, "c.png")]:
        out = tmp_path / name
        plot(out, name="classic_01", levels_dir=FIXTURES)
        assert out.stat().st_size > 0
