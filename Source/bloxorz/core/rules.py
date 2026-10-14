"""Tile rules: which placements are legal and what happens after a move lands.

The search-facing interface (``BloxorzProblem``) calls only ``is_legal`` and
``apply_effects``. Switch behaviour, splitting and merging belong to Long
(docs/PHAN_CONG.md); the parts marked TODO(Long) are theirs to implement.
"""

from __future__ import annotations

from .geometry import Cell
from .level import Level, Switch, SwitchKind, Tile
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
    # TODO(Long): decide whether a single cube may rest on a fragile tile
    # (in the original game it may) and enforce it here if not.
    return True


def pressed_switches(level: Level, state: State) -> list[Switch]:
    """Switches activated by the placement in ``state`` (spec section 2.5).

    Soft switches fire under any part of the block or under a cube; heavy and
    split switches fire only under the whole block standing upright.
    """
    pressed = []
    for cell in state.cells():
        switch = level.switches.get(cell)
        if switch is None:
            continue
        if switch.kind is SwitchKind.SOFT or state.is_standing:
            pressed.append(switch)
    return pressed


def apply_effects(level: Level, state: State) -> State:
    """Return the state after the tiles under the landed block react.

    Called after every legal move (not after a SWITCH action). Must return a
    new ``State``; never mutate ``level``.

    TODO(Long): implement
      - soft/heavy switches: update ``state.bridges`` with ``switch.bridge_mask``
        according to ``switch.effect`` (toggle / open / close);
      - split switch: replace the block with two cubes at ``switch.targets``;
      - merge: two cubes on adjacent cells become one lying block;
      - decide and document: what happens if a switch closes the bridge the
        block is resting on.
    """
    if pressed_switches(level, state):
        raise NotImplementedError("switch effects are not implemented yet (owner: Long)")
    if state.is_split:
        raise NotImplementedError("cube merging is not implemented yet (owner: Long)")
    return state
