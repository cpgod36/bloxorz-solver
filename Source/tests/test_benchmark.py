"""Unit tests for the benchmark module."""

import csv
import time
from pathlib import Path

from benchmark.benchmark import (
    COST_FUNCTION_NAMES,
    SOLVERS,
    collect_levels,
    export_csv,
    run_benchmark,
    run_solver_with_timeout,
)
from bloxorz.core import BloxorzProblem, load_level
from bloxorz.solvers import bfs, ids

FIXTURES = Path(__file__).parent / "fixtures"


def sleepy_solver(problem, trace_memory=True):
    """Module-level (picklable) solver that never finishes within a short timeout."""
    time.sleep(30)


def shallow_ids(problem, trace_memory=True):
    return ids(problem, max_depth=3, trace_memory=trace_memory)


def crashing_solver(problem, trace_memory=True):
    raise RuntimeError("boom")


def test_collect_levels_finds_fixtures():
    levels = collect_levels(FIXTURES)
    assert len(levels) >= 2
    names = [lvl.name for lvl in levels]
    assert "classic_01.json" in names


def test_run_solver_with_timeout_success():
    prob = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    status, result = run_solver_with_timeout(bfs, prob, timeout_sec=10.0)
    assert status == "SOLVED"
    assert result is not None
    assert result.path is not None
    assert len(result.path) == 7


def test_export_csv_writes_valid_file(tmp_path: Path):
    output_csv = tmp_path / "test_benchmark.csv"
    records = [
        {
            "timestamp": "2026-10-21T12:00:00",
            "level_file": "classic_01.json",
            "level_name": "Classic stage 1",
            "algorithm": "BFS",
            "status": "SOLVED",
            "solution_length": 7,
            "expanded_nodes": 48,
            "search_time_sec": 0.0012,
            "peak_memory_bytes": 16000,
            "peak_memory_kb": 15.6,
            "actions": "RDDRRDR",
        }
    ]
    export_csv(records, output_csv)
    assert output_csv.exists()

    with open(output_csv, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["algorithm"] == "BFS"
        assert reader[0]["solution_length"] == "7"
        assert reader[0]["actions"] == "RDDRRDR"


def test_run_benchmark_runs_solvers():
    classic = [FIXTURES / "classic_01.json"]
    records = run_benchmark(classic, selected_solvers=["BFS", "DFS"], timeout_sec=5.0)
    assert len(records) == 2
    assert records[0]["algorithm"] == "BFS"
    assert records[0]["status"] == "SOLVED"
    assert records[1]["algorithm"] == "DFS"
    assert records[1]["status"] == "SOLVED"


def test_run_solver_with_timeout_reports_timeout():
    prob = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    start = time.monotonic()
    status, result = run_solver_with_timeout(sleepy_solver, prob, timeout_sec=0.3)
    assert status == "TIMEOUT"
    assert result is None
    assert time.monotonic() - start < 10  # the child was terminated, not awaited


def test_run_solver_with_timeout_reports_error():
    prob = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    status, result = run_solver_with_timeout(crashing_solver, prob, timeout_sec=10.0)
    assert status == "ERROR"
    assert result is None


def test_run_solver_with_timeout_reports_limit():
    prob = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    # classic_01 needs 7 moves, so IDS capped at depth 3 gives up without a proof.
    status, result = run_solver_with_timeout(shallow_ids, prob, timeout_sec=10.0)
    assert status == "LIMIT"
    assert result is not None
    assert result.path is None


def test_run_benchmark_records_cost_function_and_all_solvers():
    classic = [FIXTURES / "classic_01.json"]
    records = run_benchmark(classic, selected_solvers=list(SOLVERS), timeout_sec=30.0, repeats=1)
    assert [r["algorithm"] for r in records] == list(SOLVERS)
    assert all(r["status"] == "SOLVED" for r in records)
    assert all(r["cost_function"] == COST_FUNCTION_NAMES[r["algorithm"]] for r in records)
    assert COST_FUNCTION_NAMES["BFS"] == "unit_moves"
    assert COST_FUNCTION_NAMES["UCS"] == COST_FUNCTION_NAMES["A*"] == "physics_cost"
    assert all(r["peak_memory_bytes"] != "" for r in records)
    # UCS and A* minimise physics cost, so no solver can beat them on solution_cost.
    best = min(r["solution_cost"] for r in records)
    assert {r["algorithm"]: r["solution_cost"] for r in records}["UCS"] == best
