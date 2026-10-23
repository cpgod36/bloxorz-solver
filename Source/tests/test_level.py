import re
from pathlib import Path

import pytest

from bloxorz.core import BridgeEffect, LevelFormatError, SwitchKind, Tile, load_level, parse_level

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_classic_level():
    level = load_level(FIXTURES / "classic_01.json")
    assert level.name == "Classic stage 1"
    assert (level.rows, level.cols) == (6, 10)
    assert level.start == (1, 1)
    assert level.goal == (4, 7)
    assert level.tile((1, 1)) is Tile.FLOOR
    assert level.tile((0, 5)) is Tile.VOID  # padded short row
    assert level.tile((-1, 0)) is Tile.VOID  # off the board
    assert level.switches == {}


def test_load_every_tile_type():
    level = load_level(FIXTURES / "all_tiles.json")
    assert level.tile((2, 3)) is Tile.FRAGILE
    assert level.bridge_cells == ((0, 3), (0, 4), (1, 3), (1, 4))
    assert level.initial_bridges == 0b0010  # only '=' at (0, 4) starts open

    soft = level.switches[(0, 2)]
    assert soft.kind is SwitchKind.SOFT
    assert soft.effect is BridgeEffect.TOGGLE
    assert soft.bridge_mask == 0b0011

    heavy = level.switches[(1, 2)]
    assert heavy.kind is SwitchKind.HEAVY
    assert heavy.effect is BridgeEffect.OPEN
    assert heavy.bridge_mask == 0b1100

    split = level.switches[(2, 1)]
    assert split.kind is SwitchKind.SPLIT
    assert split.targets == ((0, 0), (2, 0))


def test_name_defaults_to_file_stem(tmp_path):
    path = tmp_path / "my_stage.json"
    path.write_text('{"grid": ["SG"]}', encoding="utf-8")
    assert load_level(path).name == "my_stage"


@pytest.mark.parametrize(
    "data, message",
    [
        ({"grid": ["##G"]}, "one start"),
        ({"grid": ["S#G", "G##"]}, "one goal"),
        ({"grid": ["S?G"]}, "unknown grid character"),
        ({"grid": []}, "non-empty list"),
        ({"grid": ["SG"], "extra": 1}, "unknown key"),
        ({"grid": ["SOG"]}, "without a 'switches' entry"),
        ({"grid": ["S#G"], "switches": [{"pos": [0, 1], "effect": "toggle", "bridges": [[0, 1]]}]},
         "not a switch cell"),
        ({"grid": ["SO#G"], "switches": [{"pos": [0, 1], "effect": "toggle", "bridges": [[0, 2]]}]},
         "not a bridge cell"),
        ({"grid": ["SO-G"], "switches": [{"pos": [0, 1], "effect": "flip", "bridges": [[0, 2]]}]},
         "effect must be one of"),
        ({"grid": ["SO-G"], "switches": [{"pos": [0, 1], "effect": "open", "bridges": []}]},
         "non-empty list"),
        ({"grid": ["ST#G"], "switches": [{"pos": [0, 1], "targets": [[0, 2]]}]},
         "two cells"),
        ({"grid": ["ST#G."], "switches": [{"pos": [0, 1], "targets": [[0, 2], [0, 4]]}]},
         "void or off the board"),
        ({"grid": ["ST##G"], "switches": [{"pos": [0, 1], "targets": [[0, 2], [0, 3]]}]},
         "must not be adjacent"),
        ({"grid": ["ST#", "##G"], "switches": [{"pos": [0, 1], "targets": [[0, 2], [1, 2]]}]},
         "must not be adjacent"),
        ({"grid": ["ST#G"], "switches": [{"pos": [0, 1], "targets": [[0, 2], [0, 0]], "effect": "open"}]},
         "unknown key"),
        ({"grid": ["SO-G"], "switches": [{"pos": [0, 1], "effect": "open", "bridges": [[0, 2]]},
                                         {"pos": [0, 1], "effect": "open", "bridges": [[0, 2]]}]},
         "duplicate"),
        ({"grid": ["SO-G"], "switches": [{"pos": [0], "effect": "open", "bridges": [[0, 2]]}]},
         "must be [row, col]"),
    ],
)
def test_malformed_levels_are_rejected(data, message):
    with pytest.raises(LevelFormatError, match=re.escape(message)):
        parse_level(data)


def test_diagonal_split_targets_are_allowed():
    level = parse_level({"grid": ["ST#", "##G"], "switches": [{"pos": [0, 1], "targets": [[0, 2], [1, 1]]}]})
    assert level.switches[(0, 1)].targets == ((0, 2), (1, 1))


def test_invalid_json_is_reported(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{grid: ", encoding="utf-8")
    with pytest.raises(LevelFormatError, match="invalid JSON"):
        load_level(path)
