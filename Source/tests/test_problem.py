from pathlib import Path

import pytest

from bloxorz.core import (
    Action,
    BloxorzProblem,
    Block,
    IllegalMoveError,
    Orientation,
    State,
    format_actions,
    load_level,
    parse_actions,
    parse_level,
    replay,
)

FIXTURES = Path(__file__).parent / "fixtures"
S, H, V = Orientation.STANDING, Orientation.HORIZONTAL, Orientation.VERTICAL


def problem(*grid, switches=()):
    return BloxorzProblem(parse_level({"grid": list(grid), "switches": list(switches)}))


def test_initial_state_is_standing_on_start():
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    assert p.initial_state == State(Block(1, 1, S), None, 0)
    assert not p.is_goal(p.initial_state)


def test_classic_stage_1_known_optimal_solution_reaches_goal():
    p = BloxorzProblem(load_level(FIXTURES / "classic_01.json"))
    states = replay(p, parse_actions("RDDRRDR"))
    assert p.is_goal(states[-1])
    assert not any(p.is_goal(s) for s in states[:-1])


def test_rolling_off_the_board_is_illegal():
    p = problem("S##G")
    assert p.result(p.initial_state, Action.UP) is None
    assert p.result(p.initial_state, Action.LEFT) is None


def test_rolling_over_void_is_illegal():
    p = problem("S##.G")
    assert p.result(p.initial_state, Action.RIGHT) == State(Block(0, 1, H), None, 0)
    p = problem("S#.#G")  # second cell of the lying block is void
    assert p.result(p.initial_state, Action.RIGHT) is None


def test_successors_follow_fixed_action_order_and_skip_illegal_moves():
    p = problem(
        "..#..",
        "..#..",
        "##S##",
        "..#..",
        "..#G.",
    )
    assert [a for a, _ in p.successors(p.initial_state)] == [
        Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT,
    ]
    p = problem("S##G")
    assert [a for a, _ in p.successors(p.initial_state)] == [Action.RIGHT]


def test_lying_across_the_goal_does_not_win():
    p = problem("S#G#")
    across = p.result(State(Block(0, 1, S), None, 0), Action.RIGHT)
    assert across == State(Block(0, 2, H), None, 0)
    assert not p.is_goal(across)


def test_standing_on_the_goal_wins():
    p = problem("S##G")
    assert p.is_goal(replay(p, parse_actions("RR"))[-1])


def test_fragile_tile_breaks_under_standing_block_only():
    p = problem("SFF#G")
    lying = p.result(p.initial_state, Action.RIGHT)
    assert lying == State(Block(0, 1, H), None, 0)
    assert p.result(lying, Action.LEFT) is not None  # stands on S
    p = problem("S##F#", "...G.")
    on_fragile = p.result(State(Block(0, 1, H), None, 0), Action.RIGHT)
    assert on_fragile is None


def test_closed_bridge_behaves_like_void_and_open_bridge_like_floor():
    closed = problem("S--#G", "O....", switches=[{"pos": [1, 0], "effect": "open", "bridges": [[0, 1]]}])
    assert closed.result(closed.initial_state, Action.RIGHT) is None

    opened = problem("S==#G", "O....", switches=[{"pos": [1, 0], "effect": "open", "bridges": [[0, 1]]}])
    assert opened.result(opened.initial_state, Action.RIGHT) == State(Block(0, 1, H), None, 0b11)


def test_same_placement_different_bridges_are_different_states():
    a = State(Block(0, 0, S), None, 0b01)
    b = State(Block(0, 0, S), None, 0b10)
    assert a != b and len({a, b}) == 2


def test_switch_action_swaps_controlled_cube():
    p = problem("S##G")
    split = State(None, ((0, 0), (0, 3)), 0)
    assert p.actions(split)[-1] is Action.SWITCH
    assert p.result(split, Action.SWITCH) == State(None, ((0, 3), (0, 0)), 0)
    with pytest.raises(ValueError):
        p.result(p.initial_state, Action.SWITCH)


def test_switch_effect_toggles_linked_bridge():
    p = problem("SO#G-", switches=[{"pos": [0, 1], "effect": "toggle", "bridges": [[0, 4]]}])
    nxt = p.result(p.initial_state, Action.RIGHT)
    assert nxt == State(Block(0, 1, H), None, 0b1)



def test_replay_reports_the_falling_action():
    p = problem("S##G")
    with pytest.raises(IllegalMoveError, match="#1"):
        replay(p, parse_actions("RU"))


def test_action_text_round_trip():
    assert format_actions(parse_actions("rd dr s")) == "RDDRS"
