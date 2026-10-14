"""Search state: block placement plus the open/closed status of every bridge."""

from __future__ import annotations

from typing import NamedTuple

from .geometry import Block, Cell, Orientation


class State(NamedTuple):
    """Immutable, hashable search state.

    Exactly one of ``block`` and ``cubes`` is set:

    - ``block``: the whole 1x1x2 block.
    - ``cubes``: the two 1x1x1 cubes after a split, as (controlled, other).
      Swapping the pair is how control passes to the other cube.

    ``bridges`` is a bitmask: bit i is set when bridge i of the level is open
    (see ``Level.bridge_bit``). Same placement + different bridges = different state.
    """

    block: Block | None
    cubes: tuple[Cell, Cell] | None
    bridges: int

    @property
    def is_split(self) -> bool:
        return self.cubes is not None

    @property
    def is_standing(self) -> bool:
        return self.block is not None and self.block.orientation is Orientation.STANDING

    def cells(self) -> tuple[Cell, ...]:
        """Every cell currently occupied by the block or the cubes."""
        if self.block is not None:
            return self.block.cells()
        assert self.cubes is not None
        return self.cubes

    def bridge_open(self, bit: int) -> bool:
        return bool(self.bridges >> bit & 1)
