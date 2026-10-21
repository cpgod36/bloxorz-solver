"""Unit tests for the benchmark module."""

import csv
from pathlib import Path

from benchmark.benchmark import (
    collect_levels,
    export_csv,
    run_benchmark,
    run_solver_with_timeout,
)
from bloxorz.core import BloxorzProblem, load_level
from bloxorz.solvers import bfs

FIXTURES = Path(__file__).parent / "fixtures"


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
