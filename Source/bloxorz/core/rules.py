"""Tile rules: which placements are legal and what happens after a move lands.

The search-facing interface (``BloxorzProblem``) calls only ``is_legal`` and
``apply_effects``. Switch behaviour, splitting and merging belong to Long
(docs/PHAN_CONG.md); the parts marked TODO(Long) are theirs to implement.
"""

from __future__ import annotations

from .geometry import Block, Cell, Orientation
from .level import BridgeEffect, Level, Switch, SwitchKind, Tile
from .state import State


def is_passable(level: Level, cell: Cell, bridges: int) -> bool:
    """Whether a cell can carry weight at all: on the board, not void, not a closed bridge."""
    tile = level.tile(cell)
    if tile is Tile.VOID:
        return False
    if tile is Tile.BRIDGE:
        return bool(bridges >> level.bridge_bit[cell] & 1)
    return True


def try_merge(c1: Cell, c2: Cell) -> Block | None:
    """Merge two adjacent 1x1x1 cubes into a lying 1x1x2 block if Manhattan distance is 1.

    Returns the merged Block (HORIZONTAL or VERTICAL), or None if not adjacent.
    (docs/SPECIAL_TILES.md, 4.4).
    """
    r1, c1_col = c1
    r2, c2_col = c2
    dr = abs(r1 - r2)
    dc = abs(c1_col - c2_col)
    if dr + dc != 1:
        return None
    if dr == 0:  # Same row, adjacent columns -> HORIZONTAL
        return Block(r1, min(c1_col, c2_col), Orientation.HORIZONTAL)
    # dr == 1, dc == 0: Same column, adjacent rows -> VERTICAL
    return Block(min(r1, r2), c1_col, Orientation.VERTICAL)


def is_legal(level: Level, state: State) -> bool:
    """Whether the block (or both cubes) can rest where ``state`` puts them."""
    # Two cubes cannot physically occupy the exact same cell (docs/SPECIAL_TILES.md, 4.5).
    if state.is_split:
        assert state.cubes is not None
        if state.cubes[0] == state.cubes[1]:
            return False
    if not all(is_passable(level, cell, state.bridges) for cell in state.cells()):
        return False
    # A standing block puts all its weight on one tile and breaks a fragile one.
    if state.is_standing and level.tile(state.block.cells()[0]) is Tile.FRAGILE:
        return False
    # A single cube may rest safely on a fragile tile (docs/SPECIAL_TILES.md, 3.1).
    return True


def pressed_switches(level: Level, state: State) -> list[Switch]:
    """Switches activated by the placement in ``state`` (spec section 2.5).

    Soft switches fire under any part of the block or under a cube; heavy and
    split switches fire only under the whole block standing upright.

    In split mode, only the cube that just moved (cubes[0]) triggers switches
    (docs/SPECIAL_TILES.md, 4.2).
    """
    pressed = []
    cells = (state.cubes[0],) if state.is_split else state.cells()
    for cell in cells:
        switch = level.switches.get(cell)
        if switch is None:
            continue
        if switch.kind is SwitchKind.SOFT or state.is_standing:
            pressed.append(switch)
    return pressed


def _apply_switch(switch: Switch, bridges: int) -> int:
    """Apply the bridge effect (toggle/open/close) of a switch to the bridges bitmask."""
    if switch.effect is BridgeEffect.TOGGLE:
        return bridges ^ switch.bridge_mask
    if switch.effect is BridgeEffect.OPEN:
        return bridges | switch.bridge_mask
    if switch.effect is BridgeEffect.CLOSE:
        return bridges & ~switch.bridge_mask
    return bridges


def apply_effects(level: Level, state: State) -> State | None:
    """Return the state after the tiles under the landed block react, or None if the block falls.

    Called after every legal move (not after a SWITCH action). Must return a
    new ``State`` or ``None``; never mutate ``level``.
    """
    bridges = state.bridges
    for switch in pressed_switches(level, state):
        if switch.kind in (SwitchKind.SOFT, SwitchKind.HEAVY):
            bridges = _apply_switch(switch, bridges)
        elif switch.kind is SwitchKind.SPLIT:
            # Block standing on a split switch teleports and splits into two cubes (spec 2.5).
            assert switch.targets is not None
            t1, t2 = switch.targets

            # Edge Case 10: target on closed bridge or void -> falls into void
            if not (is_passable(level, t1, bridges) and is_passable(level, t2, bridges)):
                return None

            # Edge Case 9: cube landing on a soft switch activates it immediately
            for target in (t1, t2):
                target_sw = level.switches.get(target)
                if target_sw is not None and target_sw.kind is SwitchKind.SOFT:
                    bridges = _apply_switch(target_sw, bridges)

            # Verify both cubes still have support after switch effects
            if not (is_passable(level, t1, bridges) and is_passable(level, t2, bridges)):
                return None

            # targets[0] receives control first (docs/SPECIAL_TILES.md, 3.5)
            return State(None, (t1, t2), bridges)

    # If a switch closes the bridge the block is resting on, the block loses support
    # and falls into the void (docs/SPECIAL_TILES.md, 4.1).
    if not all(is_passable(level, cell, bridges) for cell in state.cells()):
        return None

    # Handle cube merging when two cubes are adjacent (docs/SPECIAL_TILES.md, 4.4)
    if state.is_split:
        assert state.cubes is not None
        merged = try_merge(state.cubes[0], state.cubes[1])
        if merged is not None:
            return State(merged, None, bridges)

    if bridges == state.bridges:
        return state
    return State(state.block, state.cubes, bridges)

