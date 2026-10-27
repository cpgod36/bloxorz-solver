"""Unit tests for benchmark.report (tables and charts built from a benchmark CSV)."""

import csv

import pytest

from benchmark.benchmark import CSV_FIELDS
from benchmark.report import (
    best_cost_per_level,
    build_tables,
    generate_report,
    group_mean,
    load_records,
)


def _row(level, algo, moves, cost, expanded, status="SOLVED"):
    return {"level_file": f"{level}.json", "algorithm": algo, "status": status,
            "solution_length": moves, "solution_cost": cost, "expanded_nodes": expanded,
            "search_time_sec": 0.002, "peak_memory_kb": 10.0}


@pytest.fixture
def csv_path(tmp_path):
    rows = [
        _row("g1_basic_01", "BFS", 8, 14, 40),
        _row("g1_basic_01", "A*", 9, 13, 30),
        _row("g1_basic_01", "DFS", 0, "", 0, status="TIMEOUT"),
        _row("g1_basic_02", "BFS", 4, 8, 10),
        _row("g1_basic_02", "A*", 4, 8, 10),
    ]
    path = tmp_path / "bench.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, restval="")
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_load_records_keeps_only_solved_rows(csv_path):
    records = load_records(csv_path)
    assert len(records) == 4
    assert {r["algorithm"] for r in records} == {"BFS", "A*"}
    assert records[0]["level"] == "g1_basic_01"
    assert records[0]["group"] == "g1"


def test_best_cost_per_level_takes_the_minimum(csv_path):
    best = best_cost_per_level(load_records(csv_path))
    assert best == {"g1_basic_01": 13.0, "g1_basic_02": 8.0}


def test_group_mean_is_geometric_by_default(csv_path):
    records = load_records(csv_path)
    assert group_mean(records, "g1", "BFS", "expanded") == pytest.approx(20.0)  # sqrt(40 * 10)
    assert group_mean(records, "g1", "BFS", "expanded", geometric=False) == pytest.approx(25.0)


def test_build_tables_marks_cheapest_solution(csv_path):
    tables = build_tables(load_records(csv_path))
    assert "| g1_basic_01 | A* | 9 | 13 * |" in tables
    assert "| g1_basic_01 | BFS | 8 | 14 |" in tables


def test_generate_report_writes_tables_and_charts(csv_path, tmp_path):
    paths = generate_report(csv_path, tmp_path / "out")
    assert all(p.exists() and p.stat().st_size > 0 for p in paths)
    assert {p.name for p in paths} >= {"report_tables.md", "fig_metrics_by_group.png",
                                       "fig_cost_ratio.png"}


def test_generate_report_rejects_csv_without_solved_rows(tmp_path):
    path = tmp_path / "empty.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, restval="")
        writer.writeheader()
        writer.writerow(_row("g1_basic_01", "BFS", 0, "", 0, status="TIMEOUT"))
    with pytest.raises(ValueError):
        generate_report(path, tmp_path / "out")
