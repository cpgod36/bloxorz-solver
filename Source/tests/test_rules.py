"""Unit tests for special tile rules: fragile, bridges, and soft/heavy switches.

Owner: Long (docs/PHAN_CONG.md, docs/SPECIAL_TILES.md).
"""

from __future__ import annotations

import pytest

from bloxorz.core import (
    Action,
    Block,
    BloxorzProblem,
    Orientation,
    State,
    parse_actions,
    parse_level,
    replay,
    rules,
)

S, H, V = Orientation.STANDING, Orientation.HORIZONTAL, Orientation.VERTICAL


def make_problem(*grid: str, switches=()) -> BloxorzProblem:
    """Helper to build a BloxorzProblem from an ASCII grid and switch specs."""
    return BloxorzProblem(parse_level({"grid": list(grid), "switches": list(switches)}))


# ---------------------------------------------------------------------------
# Fragile Tiles (docs/SPECIAL_TILES.md, Section 3.1)
# ---------------------------------------------------------------------------


def test_fragile_tile_supports_lying_block():
    """A lying block distributes weight and safely rests across fragile tiles."""
    p = make_problem("SFF#G")
    lying = p.result(p.initial_state, Action.RIGHT)
    assert lying == State(Block(0, 1, H), None, 0)
    # Rolling left stands on S (safe)
    assert p.result(lying, Action.LEFT) == p.initial_state


def test_fragile_tile_breaks_under_standing_block():
    """A standing block concentrates all weight on a single tile, breaking fragile floors."""
    p = make_problem("S##F#", "...G.")
    lying = p.result(p.initial_state, Action.RIGHT)
    assert lying == State(Block(0, 1, H), None, 0)
    # Rolling right would make the block stand on F (row 0, col 3) -> falls
    on_fragile = p.result(lying, Action.RIGHT)
    assert on_fragile is None


# ---------------------------------------------------------------------------
# Soft Switch (docs/SPECIAL_TILES.md, Section 3.3)
# ---------------------------------------------------------------------------


def test_soft_switch_activates_when_standing():
    """Soft switch triggers when a standing block presses it."""
    p = make_problem(
        "S##O#G-",
        switches=[{"pos": [0, 3], "effect": "toggle", "bridges": [[0, 6]]}],
    )
    # Roll R -> H on (0, 1) and (0, 2), then Roll R -> S standing on (0, 3) (O tile)
    s_on_o = replay(p, parse_actions("RR"))[-1]
    assert s_on_o.is_standing
    assert s_on_o.bridge_open(0)



def test_soft_switch_activates_when_lying():
    """Soft switch triggers when any part of a lying block presses it."""
    p = make_problem(
        "SO#G-",
        switches=[{"pos": [0, 1], "effect": "open", "bridges": [[0, 4]]}],
    )
    # Rolling right lands horizontally on (0, 1) and (0, 2)
    nxt = p.result(p.initial_state, Action.RIGHT)
    assert nxt is not None
    assert nxt.bridge_open(0)


# ---------------------------------------------------------------------------
# Heavy Switch (docs/SPECIAL_TILES.md, Section 3.4)
# ---------------------------------------------------------------------------


def test_heavy_switch_activates_only_when_standing():
    """Heavy switch triggers when the whole block stands upright on it."""
    # S at (0, 0) -> R gives H at (0, 1) -> R gives S at (0, 3) on X
    p = make_problem(
        "S##X#G-",
        switches=[{"pos": [0, 3], "effect": "toggle", "bridges": [[0, 6]]}],
    )
    # Step 1: R -> lying on (0, 1) and (0, 2)
    s1 = p.result(p.initial_state, Action.RIGHT)
    assert s1 is not None and not s1.bridge_open(0)

    # Step 2: R -> standing on (0, 3) where X is located
    s2 = p.result(s1, Action.RIGHT)
    assert s2 is not None and s2.is_standing
    assert s2.bridge_open(0)


def test_heavy_switch_not_activated_when_lying():
    """Heavy switch does not trigger when a block merely lies across it."""
    p = make_problem(
        "SX##G-",
        switches=[{"pos": [0, 1], "effect": "toggle", "bridges": [[0, 5]]}],
    )
    # Roll R -> H lying on (0, 1) and (0, 2), covering X at (0, 1)
    nxt = p.result(p.initial_state, Action.RIGHT)
    assert nxt is not None
    assert not nxt.bridge_open(0)  # Heavy switch must not trigger when lying


# ---------------------------------------------------------------------------
# Bridge Effects: Open, Close, Toggle (docs/SPECIAL_TILES.md, Section 3.3)
# ---------------------------------------------------------------------------


def test_bridge_effect_open_sets_bridge_open():
    """Effect 'open' permanently opens linked bridges (initially closed '-')."""
    p = make_problem(
        "SO#G-",
        switches=[{"pos": [0, 1], "effect": "open", "bridges": [[0, 4]]}],
    )
    nxt = p.result(p.initial_state, Action.RIGHT)
    assert nxt is not None and nxt.bridge_open(0)


def test_bridge_effect_close_sets_bridge_closed():
    """Effect 'close' permanently closes linked bridges (initially open '=')."""
    p = make_problem(
        "SO#G=",
        switches=[{"pos": [0, 1], "effect": "close", "bridges": [[0, 4]]}],
    )
    assert p.initial_state.bridge_open(0)
    nxt = p.result(p.initial_state, Action.RIGHT)
    assert nxt is not None and not nxt.bridge_open(0)


def test_bridge_effect_toggle_flips_between_open_and_closed():
    """Effect 'toggle' alternates bridge between open and closed on each press."""
    p = make_problem(
        "SO#G-",
        switches=[{"pos": [0, 1], "effect": "toggle", "bridges": [[0, 4]]}],
    )
    # Roll R onto O: closes -> opens
    s1 = p.result(p.initial_state, Action.RIGHT)
    assert s1 is not None and s1.bridge_open(0)

    # Roll L back to S (standing)
    s2 = p.result(s1, Action.LEFT)
    assert s2 is not None and s2.bridge_open(0)

    # Roll R onto O again: opens -> closes
    s3 = p.result(s2, Action.RIGHT)
    assert s3 is not None and not s3.bridge_open(0)


# ---------------------------------------------------------------------------
# Edge Cases: Multiple Switches & Bridge Collapsing Under Block
# ---------------------------------------------------------------------------


def test_simultaneous_two_soft_switches_toggle_bridge_twice():
    """Lying on two soft switches controlling the same bridge toggles it twice (Edge Case 7)."""
    # Block rolling right from (0, 0) occupies (0, 1) and (0, 2)
    # Both (0, 1) and (0, 2) are soft switches toggling the same bridge [0, 4]
    p = make_problem(
        "SOOG-",
        switches=[
            {"pos": [0, 1], "effect": "toggle", "bridges": [[0, 4]]},
            {"pos": [0, 2], "effect": "toggle", "bridges": [[0, 4]]},
        ],
    )
    nxt = p.result(p.initial_state, Action.RIGHT)
    assert nxt is not None
    # Initially closed (0), toggled twice: 0 -> 1 -> 0
    assert not nxt.bridge_open(0)


def test_switch_closes_bridge_under_resting_block_causes_fall():
    """If a switch closes the bridge the block is resting on, the block falls (Edge Case 1)."""
    # S at (0, 0), rolling right lands horizontally on:
    # - col 1: soft switch O (toggles bridge at col 2)
    # - col 2: initially open bridge '='
    # When O triggers, bridge at col 2 closes under the block -> fall -> None!
    p = make_problem(
        "SO=G",
        switches=[{"pos": [0, 1], "effect": "close", "bridges": [[0, 2]]}],
    )
    nxt = p.result(p.initial_state, Action.RIGHT)
    assert nxt is None  # Block fell because bridge at (0, 2) vanished under its weight


def test_switch_toggles_bridge_under_resting_block_causes_fall():
    """Toggling an open bridge under the resting block closes it and causes a fall (Edge Case 1)."""
    p = make_problem(
        "SO=G",
        switches=[{"pos": [0, 1], "effect": "toggle", "bridges": [[0, 2]]}],
    )
    assert p.initial_state.bridge_open(0)  # bridge initially open '='
    nxt = p.result(p.initial_state, Action.RIGHT)
    assert nxt is None  # Block fell because bridge at (0, 2) was toggled closed under it


def test_fragile_tile_supports_vertical_lying_block():
    """A block lying vertically safely rests across fragile tiles."""
    p = make_problem("S.", "F.", "F.", "G.")
    lying = p.result(p.initial_state, Action.DOWN)
    assert lying == State(Block(1, 0, V), None, 0)
    assert p.result(lying, Action.DOWN) == State(Block(3, 0, S), None, 0)


def test_soft_switch_activates_when_vertical_lying():
    """Soft switch triggers when a vertically lying block presses it."""
    p = make_problem(
        "S.",
        "O.",
        "#.",
        "G-",
        switches=[{"pos": [1, 0], "effect": "toggle", "bridges": [[3, 1]]}],
    )
    lying = p.result(p.initial_state, Action.DOWN)
    assert lying is not None
    assert lying.bridge_open(0)


def test_switch_controls_multiple_bridges_simultaneously():
    """A switch can control multiple bridge tiles at once (spec section 2.5)."""
    p = make_problem(
        "SO#--G",
        switches=[{"pos": [0, 1], "effect": "toggle", "bridges": [[0, 3], [0, 4]]}],
    )
    assert not p.initial_state.bridge_open(0)
    assert not p.initial_state.bridge_open(1)
    nxt = p.result(p.initial_state, Action.RIGHT)
    assert nxt is not None
    # Both bridge bits should now be open
    assert nxt.bridge_open(0) and nxt.bridge_open(1)


def test_pressed_switches_ignores_idle_cube_in_split_mode():
    """In split mode, only the moving cube (cubes[0]) triggers switches (Edge Case 2)."""
    p = make_problem(
        "S-G.O",
        switches=[{"pos": [0, 4], "effect": "toggle", "bridges": [[0, 1]]}],
    )
    # When cube 0 is at (0, 0) and cube 1 is resting on switch at (0, 4):
    idle_on_switch = State(None, ((0, 0), (0, 4)), 0)
    assert rules.pressed_switches(p.level, idle_on_switch) == []

    # When cube 0 moves onto switch at (0, 4) and cube 1 is at (0, 0):
    moved_onto_switch = State(None, ((0, 4), (0, 0)), 0)
    assert len(rules.pressed_switches(p.level, moved_onto_switch)) == 1


def test_apply_effects_returns_same_state_when_bridges_unchanged():
    """apply_effects returns the exact same state instance if no bridge changed."""
    p = make_problem("S##G")
    landed = State(Block(0, 1, H), None, 0)
    assert rules.apply_effects(p.level, landed) is landed

