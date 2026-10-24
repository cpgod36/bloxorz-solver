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


# ---------------------------------------------------------------------------
# Split Switch & Splitting (docs/SPECIAL_TILES.md, Section 3.5)
# ---------------------------------------------------------------------------


def test_split_switch_activates_only_when_standing():
    """Standing on a split switch teleports and splits the block into two 1x1x1 cubes."""
    p = make_problem(
        "S##T.....",
        "....#.#..",
        "....##G..",
        switches=[{"pos": [0, 3], "targets": [[1, 4], [1, 6]]}],
    )
    # Roll R -> H on (0, 1) and (0, 2)
    s1 = p.result(p.initial_state, Action.RIGHT)
    assert s1 is not None and not s1.is_split
    # Roll R -> S standing on (0, 3) (tile T)
    s2 = p.result(s1, Action.RIGHT)
    assert s2 is not None
    assert s2.is_split
    assert s2.block is None
    assert s2.cubes == ((1, 4), (1, 6))


def test_split_switch_not_activated_when_lying():
    """Lying across a split switch does not activate it."""
    p = make_problem(
        "ST###G...",
        "....#.#..",
        switches=[{"pos": [0, 1], "targets": [[1, 4], [1, 6]]}],
    )
    lying = p.result(p.initial_state, Action.RIGHT)
    assert lying is not None
    assert not lying.is_split
    assert lying.block == Block(0, 1, H)


def test_split_switch_target_on_closed_bridge_causes_fall():
    """If a split switch teleports a cube onto a closed bridge, it falls (Edge Case 10)."""
    p = make_problem(
        "S##T...-.",
        "....#.#.G",
        switches=[
            {"pos": [0, 3], "targets": [[0, 7], [1, 6]]},
        ],
    )
    s1 = p.result(p.initial_state, Action.RIGHT)
    assert s1 is not None
    # Standing on T teleports cube 0 to closed bridge [0, 7] -> fall -> None!
    s2 = p.result(s1, Action.RIGHT)
    assert s2 is None


def test_split_switch_target_on_soft_switch_triggers():
    """Landing on a soft switch during teleport immediately activates it (Edge Case 9)."""
    p = make_problem(
        "S##T...O-",
        "....#.#.G",
        switches=[
            {"pos": [0, 3], "targets": [[0, 7], [1, 6]]},
            {"pos": [0, 7], "effect": "open", "bridges": [[0, 8]]},
        ],
    )
    s1 = p.result(p.initial_state, Action.RIGHT)
    assert s1 is not None
    assert not s1.bridge_open(0)
    # Teleport cube 0 to (0, 7) which is soft switch O -> opens bridge [0, 8]
    s2 = p.result(s1, Action.RIGHT)
    assert s2 is not None
    assert s2.is_split
    assert s2.bridge_open(0)


# ---------------------------------------------------------------------------
# Cube Merging (docs/SPECIAL_TILES.md, Section 4.4)
# ---------------------------------------------------------------------------


def test_cubes_merge_horizontally_when_adjacent():
    """Two cubes moving adjacent along the same row merge into HORIZONTAL block."""
    p = make_problem("S##G")
    # Cube 0 at (0, 1), Cube 1 at (0, 3)
    split_state = State(None, ((0, 1), (0, 3)), 0)
    # Move cube 0 RIGHT -> lands at (0, 2), adjacent to cube 1 at (0, 3)
    nxt = p.result(split_state, Action.RIGHT)
    assert nxt is not None
    assert not nxt.is_split
    assert nxt.block == Block(0, 2, H)


def test_cubes_merge_vertically_when_adjacent():
    """Two cubes moving adjacent along the same column merge into VERTICAL block."""
    p = make_problem(
        "S#",
        "##",
        "##",
        "G#",
    )
    # Cube 0 at (1, 1), Cube 1 at (3, 1)
    split_state = State(None, ((1, 1), (3, 1)), 0)
    # Move cube 0 DOWN -> lands at (2, 1), adjacent to cube 1 at (3, 1)
    nxt = p.result(split_state, Action.DOWN)
    assert nxt is not None
    assert not nxt.is_split
    assert nxt.block == Block(2, 1, V)


def test_cubes_do_not_merge_diagonally():
    """Two diagonally adjacent cubes (Manhattan distance = 2) do not merge."""
    p = make_problem(
        "S##",
        "###",
        "G##",
    )
    state_before = State(None, ((0, 0), (1, 2)), 0)
    nxt = p.result(state_before, Action.RIGHT)
    assert nxt is not None
    assert nxt.is_split  # Still split at diagonal (0, 1) and (1, 2)
    assert nxt.cubes == ((0, 1), (1, 2))


def test_cubes_merge_safely_on_fragile_tile():
    """Merging on a fragile tile produces a lying block and does not break (Edge Case 8)."""
    p = make_problem(
        "S#FG",
    )
    # Cube 0 at (0, 3), Cube 1 at (0, 1). Move cube 0 LEFT to (0, 2) [fragile tile F].
    # Adjacent to (0, 1) -> merges into HORIZONTAL block covering (0, 1) and (0, 2)!
    split_state = State(None, ((0, 3), (0, 1)), 0)
    merged = p.result(split_state, Action.LEFT)
    assert merged is not None
    assert not merged.is_split
    assert merged.block == Block(0, 1, H)


def test_single_cube_cannot_activate_heavy_or_split_switch():
    """A single 1x1x1 cube cannot activate heavy (X) or split (T) switches."""
    p = make_problem(
        "SX#.T.#.G-",
        switches=[
            {"pos": [0, 1], "effect": "toggle", "bridges": [[0, 9]]},
            {"pos": [0, 4], "targets": [[0, 2], [0, 6]]},
        ],
    )
    # Cube 0 at (0, 0), other at (0, 6). Moves R onto X at (0, 1)
    cube_on_x = p.result(State(None, ((0, 0), (0, 6)), 0), Action.RIGHT)
    assert cube_on_x is not None
    assert not cube_on_x.bridge_open(0)  # X did not trigger!

    # Cube 0 at (0, 3), other at (0, 6). Moves R onto T at (0, 4)
    cube_on_t = p.result(State(None, ((0, 3), (0, 6)), 0), Action.RIGHT)
    assert cube_on_t is not None
    assert cube_on_t.is_split  # T did not split again!
    assert cube_on_t.cubes == ((0, 4), (0, 6))


def test_single_cube_cannot_win_on_goal():
    """A single cube resting on the goal does not win (spec section 2.5)."""
    p = make_problem("S##G")
    state_on_goal = State(None, ((0, 3), (0, 1)), 0)
    assert not p.is_goal(state_on_goal)


def test_two_cubes_cannot_occupy_same_cell():
    """Two cubes cannot occupy the exact same coordinate (Edge Case 5)."""
    p = make_problem("S##G")
    assert not rules.is_legal(p.level, State(None, ((0, 1), (0, 1)), 0))


def test_bfs_solves_stage_with_split_and_merge():
    """Verify that BFS solver can search and find a solution on a level with split & merge."""
    from bloxorz.solvers import bfs

    p = make_problem(
        "S##T.....",
        "....#####",
        "....####G",
        switches=[{"pos": [0, 3], "targets": [[1, 4], [1, 7]]}],
    )
    path, metrics = bfs(p)
    assert path is not None
    assert metrics.solution_length > 0
    states = replay(p, path)
    assert p.is_goal(states[-1])

