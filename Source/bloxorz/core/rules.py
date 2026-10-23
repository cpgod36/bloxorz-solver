"""Tile rules: which placements are legal and what happens after a move lands.

The search-facing interface (``BloxorzProblem``) calls only ``is_legal`` and
``apply_effects``. Switch behaviour, splitting and merging belong to Long
(docs/PHAN_CONG.md); the parts marked TODO(Long) are theirs to implement.
"""

from __future__ import annotations

from .geometry import Cell
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


def is_legal(level: Level, state: State) -> bool:
    """Whether the block (or both cubes) can rest where ``state`` puts them."""
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


def apply_effects(level: Level, state: State) -> State | None:
    """Return the state after the tiles under the landed block react, or None if the block falls.

    Called after every legal move (not after a SWITCH action). Must return a
    new ``State`` or ``None``; never mutate ``level``.
    """
    bridges = state.bridges
    for switch in pressed_switches(level, state):
        if switch.kind in (SwitchKind.SOFT, SwitchKind.HEAVY):
            if switch.effect is BridgeEffect.TOGGLE:
                bridges ^= switch.bridge_mask
            elif switch.effect is BridgeEffect.OPEN:
                bridges |= switch.bridge_mask
            elif switch.effect is BridgeEffect.CLOSE:
                bridges &= ~switch.bridge_mask
        elif switch.kind is SwitchKind.SPLIT:
            raise NotImplementedError("split switch is implemented in the next milestone (owner: Long)")

    # If a switch closes the bridge the block is resting on, the block loses support
    # and falls into the void (docs/SPECIAL_TILES.md, 4.1).
    if not all(is_passable(level, cell, bridges) for cell in state.cells()):
        return None

    if state.is_split:
        raise NotImplementedError("cube merging is not implemented yet (owner: Long)")

    if bridges == state.bridges:
        return state
    return State(state.block, state.cubes, bridges)

