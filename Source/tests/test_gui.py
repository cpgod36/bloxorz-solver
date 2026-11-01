"""Headless tests for the GUI controller (no window is opened)."""

import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame = pytest.importorskip("pygame")

from bloxorz.gui.app import EMPTY_METRICS, BloxorzApp, GameStatus  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def solve_and_wait(app, algo, timeout=30.0):
    """Run a solver through the GUI and pump results until the worker thread has answered."""
    app.run_solver(algo)
    deadline = time.time() + timeout
    while app.status is GameStatus.SOLVING and time.time() < deadline:
        app._process_solver_results()
        time.sleep(0.01)
    assert app.status is not GameStatus.SOLVING


@pytest.fixture
def app():
    gui = BloxorzApp([FIXTURES / "classic_01.json", FIXTURES / "all_tiles.json"])
    yield gui
    pygame.quit()


def test_solver_metrics_are_shown_after_solving(app):
    solve_and_wait(app, "BFS")

    assert app.metrics_info["Algorithm"] == "BFS"
    assert app.metrics_info["Solution Length"] == "7"


@pytest.mark.parametrize("change_stage", ["next_level", "prev_level", "new_game"])
def test_changing_stage_clears_solver_metrics(app, change_stage):
    solve_and_wait(app, "BFS")
    assert app.metrics_info != EMPTY_METRICS

    getattr(app, change_stage)()

    assert app.metrics_info == EMPTY_METRICS
