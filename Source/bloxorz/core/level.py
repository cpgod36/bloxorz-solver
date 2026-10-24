"""Stage description and the JSON level loader.

Level file format (full description in docs/CORE.md)::

    {
      "name": "optional title",
      "grid": ["S##", "#-G"],
      "switches": [
        {"pos": [r, c], "effect": "toggle" | "open" | "close", "bridges": [[r, c], ...]},
        {"pos": [r, c], "targets": [[r1, c1], [r2, c2]]}
      ]
    }

Grid characters are listed in ``GRID_CHARS``. The kind of each switch is taken
from its grid character, so a switch entry never repeats it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any

from .geometry import Cell


class Tile(Enum):
    VOID = "void"
    FLOOR = "floor"
    GOAL = "goal"
    FRAGILE = "fragile"
    BRIDGE = "bridge"
    SOFT_SWITCH = "soft_switch"
    HEAVY_SWITCH = "heavy_switch"
    SPLIT_SWITCH = "split_switch"


class SwitchKind(Enum):
    SOFT = "soft"    # any part of the block or a cube presses it
    HEAVY = "heavy"  # whole block standing on it
    SPLIT = "split"  # whole block standing on it; splits the block into two cubes


class BridgeEffect(Enum):
    TOGGLE = "toggle"  # flip every linked bridge
    OPEN = "open"      # permanent: linked bridges become open
    CLOSE = "close"    # permanent: linked bridges become closed


GRID_CHARS: dict[str, Tile] = {
    ".": Tile.VOID,
    "#": Tile.FLOOR,
    "S": Tile.FLOOR,         # start cell, block starts standing here
    "G": Tile.GOAL,
    "F": Tile.FRAGILE,
    "-": Tile.BRIDGE,        # bridge, initially closed
    "=": Tile.BRIDGE,        # bridge, initially open
    "O": Tile.SOFT_SWITCH,
    "X": Tile.HEAVY_SWITCH,
    "T": Tile.SPLIT_SWITCH,  # "T" for teleport
}

SWITCH_KINDS: dict[Tile, SwitchKind] = {
    Tile.SOFT_SWITCH: SwitchKind.SOFT,
    Tile.HEAVY_SWITCH: SwitchKind.HEAVY,
    Tile.SPLIT_SWITCH: SwitchKind.SPLIT,
}


class LevelFormatError(ValueError):
    """Raised when a level file is malformed."""


@dataclass(frozen=True)
class Switch:
    pos: Cell
    kind: SwitchKind
    effect: BridgeEffect | None = None         # soft / heavy only
    bridges: tuple[Cell, ...] = ()             # soft / heavy only
    bridge_mask: int = 0                       # bitmask of ``bridges``
    targets: tuple[Cell, Cell] | None = None   # split only: where the two cubes land


@dataclass(frozen=True, eq=False)
class Level:
    name: str
    grid: tuple[tuple[Tile, ...], ...]
    start: Cell
    goal: Cell
    switches: dict[Cell, Switch] = field(default_factory=dict)
    bridge_cells: tuple[Cell, ...] = ()        # bridge i is bridge_cells[i]
    bridge_bit: dict[Cell, int] = field(default_factory=dict)
    initial_bridges: int = 0                   # bitmask of bridges open at start

    @property
    def rows(self) -> int:
        return len(self.grid)

    @property
    def cols(self) -> int:
        return len(self.grid[0])

    def in_bounds(self, cell: Cell) -> bool:
        r, c = cell
        return 0 <= r < self.rows and 0 <= c < self.cols

    def tile(self, cell: Cell) -> Tile:
        """Tile at ``cell``; cells outside the board are VOID."""
        if not self.in_bounds(cell):
            return Tile.VOID
        return self.grid[cell[0]][cell[1]]


def load_level(path: str | Path) -> Level:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LevelFormatError(f"{path.name}: invalid JSON: {exc}") from exc
    return parse_level(data, default_name=path.stem)


def parse_level(data: dict[str, Any], default_name: str = "untitled") -> Level:
    _check_keys(data, required={"grid"}, optional={"name", "switches"}, where="level")
    rows = data["grid"]
    if not isinstance(rows, list) or not rows or not all(isinstance(r, str) for r in rows):
        raise LevelFormatError("'grid' must be a non-empty list of strings")

    # Shorter rows are padded with void so levels can be written without trailing dots.
    width = max(len(r) for r in rows)
    rows = [r.ljust(width, ".") for r in rows]

    grid: list[tuple[Tile, ...]] = []
    starts: list[Cell] = []
    goals: list[Cell] = []
    bridge_cells: list[Cell] = []
    open_bridges: set[Cell] = set()
    switch_cells: dict[Cell, Tile] = {}

    for r, row in enumerate(rows):
        tiles = []
        for c, ch in enumerate(row):
            if ch not in GRID_CHARS:
                raise LevelFormatError(f"unknown grid character {ch!r} at ({r}, {c})")
            tile = GRID_CHARS[ch]
            tiles.append(tile)
            if ch == "S":
                starts.append((r, c))
            elif tile is Tile.GOAL:
                goals.append((r, c))
            elif tile is Tile.BRIDGE:
                bridge_cells.append((r, c))
                if ch == "=":
                    open_bridges.add((r, c))
            elif tile in SWITCH_KINDS:
                switch_cells[(r, c)] = tile
        grid.append(tuple(tiles))

    if len(starts) != 1:
        raise LevelFormatError(f"expected exactly one start 'S', found {len(starts)}")
    if len(goals) != 1:
        raise LevelFormatError(f"expected exactly one goal 'G', found {len(goals)}")

    bridge_bit = {cell: i for i, cell in enumerate(bridge_cells)}
    initial_bridges = sum(1 << bridge_bit[cell] for cell in open_bridges)

    level = Level(
        name=str(data.get("name", default_name)),
        grid=tuple(grid),
        start=starts[0],
        goal=goals[0],
        bridge_cells=tuple(bridge_cells),
        bridge_bit=bridge_bit,
        initial_bridges=initial_bridges,
    )
    switches = _parse_switches(data.get("switches", []), switch_cells, level)
    return replace(level, switches=switches)


def _parse_switches(
    entries: Any, switch_cells: dict[Cell, Tile], level: Level
) -> dict[Cell, Switch]:
    if not isinstance(entries, list):
        raise LevelFormatError("'switches' must be a list")

    switches: dict[Cell, Switch] = {}
    for i, entry in enumerate(entries):
        where = f"switches[{i}]"
        if not isinstance(entry, dict):
            raise LevelFormatError(f"{where} must be an object")
        pos = _cell(entry.get("pos"), f"{where}.pos")
        if pos not in switch_cells:
            raise LevelFormatError(f"{where}.pos {pos} is not a switch cell (O, X or T) in the grid")
        if pos in switches:
            raise LevelFormatError(f"{where}: duplicate entry for switch at {pos}")
        kind = SWITCH_KINDS[switch_cells[pos]]

        if kind is SwitchKind.SPLIT:
            _check_keys(entry, required={"pos", "targets"}, optional=set(), where=where)
            targets = entry["targets"]
            if not isinstance(targets, list) or len(targets) != 2:
                raise LevelFormatError(f"{where}.targets must be a list of two cells")
            t1 = _cell(targets[0], f"{where}.targets[0]")
            t2 = _cell(targets[1], f"{where}.targets[1]")
            if t1 == t2:
                raise LevelFormatError(f"{where}.targets must be two different cells")
            # Adjacent cubes would merge right after splitting (docs/SPECIAL_TILES.md, 4.10).
            if abs(t1[0] - t2[0]) + abs(t1[1] - t2[1]) == 1:
                raise LevelFormatError(f"{where}.targets {t1} and {t2} must not be adjacent")
            for t in (t1, t2):
                if level.tile(t) is Tile.VOID:
                    raise LevelFormatError(f"{where}: target {t} is void or off the board")
            switches[pos] = Switch(pos, kind, targets=(t1, t2))
        else:
            _check_keys(entry, required={"pos", "effect", "bridges"}, optional=set(), where=where)
            try:
                effect = BridgeEffect(entry["effect"])
            except ValueError:
                raise LevelFormatError(
                    f"{where}.effect must be one of: toggle, open, close"
                ) from None
            raw = entry["bridges"]
            if not isinstance(raw, list) or not raw:
                raise LevelFormatError(f"{where}.bridges must be a non-empty list of cells")
            bridges = tuple(_cell(b, f"{where}.bridges[{j}]") for j, b in enumerate(raw))
            for b in bridges:
                if b not in level.bridge_bit:
                    raise LevelFormatError(f"{where}: {b} is not a bridge cell ('-' or '=')")
            mask = sum(1 << level.bridge_bit[b] for b in set(bridges))
            switches[pos] = Switch(pos, kind, effect=effect, bridges=bridges, bridge_mask=mask)

    missing = sorted(set(switch_cells) - set(switches))
    if missing:
        raise LevelFormatError(f"switch cells without a 'switches' entry: {missing}")
    return switches


def _cell(value: Any, where: str) -> Cell:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    ):
        raise LevelFormatError(f"{where} must be [row, col], got {value!r}")
    return (value[0], value[1])


def _check_keys(obj: dict[str, Any], required: set[str], optional: set[str], where: str) -> None:
    if not isinstance(obj, dict):
        raise LevelFormatError(f"{where} must be an object")
    missing = required - obj.keys()
    if missing:
        raise LevelFormatError(f"{where}: missing key(s) {sorted(missing)}")
    unknown = obj.keys() - required - optional
    if unknown:
        raise LevelFormatError(f"{where}: unknown key(s) {sorted(unknown)}")
