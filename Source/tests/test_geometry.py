import pytest

from bloxorz.core import MOVES, TRANSITIONS, Action, Block, Orientation, roll, step

S, H, V = Orientation.STANDING, Orientation.HORIZONTAL, Orientation.VERTICAL
U, D, L, R = Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT


def test_cells_per_orientation():
    assert Block(2, 3, S).cells() == ((2, 3),)
    assert Block(2, 3, H).cells() == ((2, 3), (2, 4))
    assert Block(2, 3, V).cells() == ((2, 3), (3, 3))


def test_table_covers_every_orientation_and_direction():
    assert set(TRANSITIONS) == {(o, a) for o in Orientation for a in MOVES}


# Expected cells after one roll, starting from anchor (5, 5).
@pytest.mark.parametrize(
    "orientation, action, expected",
    [
        (S, U, {(3, 5), (4, 5)}),
        (S, D, {(6, 5), (7, 5)}),
        (S, L, {(5, 3), (5, 4)}),
        (S, R, {(5, 6), (5, 7)}),
        # Horizontal block on (5,5)-(5,6)
        (H, U, {(4, 5), (4, 6)}),
        (H, D, {(6, 5), (6, 6)}),
        (H, L, {(5, 4)}),
        (H, R, {(5, 7)}),
        # Vertical block on (5,5)-(6,5)
        (V, U, {(4, 5)}),
        (V, D, {(7, 5)}),
        (V, L, {(5, 4), (6, 4)}),
        (V, R, {(5, 6), (6, 6)}),
    ],
)
def test_roll(orientation, action, expected):
    assert set(roll(Block(5, 5, orientation), action).cells()) == expected


OPPOSITE = {U: D, D: U, L: R, R: L}


@pytest.mark.parametrize("orientation", list(Orientation))
@pytest.mark.parametrize("action", MOVES)
def test_rolling_back_restores_the_block(orientation, action):
    block = Block(5, 5, orientation)
    assert roll(roll(block, action), OPPOSITE[action]) == block


@pytest.mark.parametrize("action", MOVES)
def test_standing_block_never_stays_standing(action):
    assert roll(Block(5, 5, S), action).orientation is not S


def test_step_moves_one_cell():
    assert [step((5, 5), a) for a in MOVES] == [(4, 5), (6, 5), (5, 4), (5, 6)]
