"""Block geometry: orientations, actions and the orientation transition table.

Coordinates are (row, col) with row 0 at the top. A block is anchored at its
top-left cell:

    STANDING    occupies (r, c)
    HORIZONTAL  occupies (r, c) and (r, c + 1)
    VERTICAL    occupies (r, c) and (r + 1, c)
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

Cell = tuple[int, int]


class Orientation(Enum):
    STANDING = "standing"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class Action(Enum):
    UP = "U"
    DOWN = "D"
    LEFT = "L"
    RIGHT = "R"
    SWITCH = "S"  # hand control to the other cube (split mode only)


# Fixed order so that search results are reproducible across runs.
MOVES: tuple[Action, ...] = (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT)
SPLIT_ACTIONS: tuple[Action, ...] = MOVES + (Action.SWITCH,)

DELTAS: dict[Action, tuple[int, int]] = {
    Action.UP: (-1, 0),
    Action.DOWN: (1, 0),
    Action.LEFT: (0, -1),
    Action.RIGHT: (0, 1),
}


class Block(NamedTuple):
    """The whole 1x1x2 block: anchor cell plus orientation."""

    row: int
    col: int
    orientation: Orientation

    def cells(self) -> tuple[Cell, ...]:
        r, c = self.row, self.col
        if self.orientation is Orientation.STANDING:
            return ((r, c),)
        if self.orientation is Orientation.HORIZONTAL:
            return ((r, c), (r, c + 1))
        return ((r, c), (r + 1, c))


S, H, V = Orientation.STANDING, Orientation.HORIZONTAL, Orientation.VERTICAL

# (orientation, direction) -> (new orientation, row offset, col offset) of the anchor.
TRANSITIONS: dict[tuple[Orientation, Action], tuple[Orientation, int, int]] = {
    # Standing tips over onto the two cells in the rolling direction.
    (S, Action.UP): (V, -2, 0),
    (S, Action.DOWN): (V, 1, 0),
    (S, Action.LEFT): (H, 0, -2),
    (S, Action.RIGHT): (H, 0, 1),
    # Lying along the rolling direction stands up; across it, rolls sideways.
    (H, Action.UP): (H, -1, 0),
    (H, Action.DOWN): (H, 1, 0),
    (H, Action.LEFT): (S, 0, -1),
    (H, Action.RIGHT): (S, 0, 2),
    (V, Action.UP): (S, -1, 0),
    (V, Action.DOWN): (S, 2, 0),
    (V, Action.LEFT): (V, 0, -1),
    (V, Action.RIGHT): (V, 0, 1),
}

del S, H, V


def roll(block: Block, action: Action) -> Block:
    """Roll the whole block one step. Does not check the board."""
    orientation, dr, dc = TRANSITIONS[(block.orientation, action)]
    return Block(block.row + dr, block.col + dc, orientation)


def step(cell: Cell, action: Action) -> Cell:
    """Move a single cube one cell. Does not check the board."""
    dr, dc = DELTAS[action]
    return (cell[0] + dr, cell[1] + dc)
