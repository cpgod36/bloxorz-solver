"""The search problem shared by every solver and by the GUI."""

from __future__ import annotations

from collections.abc import Iterable

from . import rules
from .geometry import MOVES, SPLIT_ACTIONS, Action, Block, Orientation, roll, step
from .level import Level
from .state import State


class IllegalMoveError(ValueError):
    """Raised by ``replay`` when an action makes the block fall."""


class BloxorzProblem:
    """Formal search problem for one level.

    - initial state: block standing on the start cell, bridges as in the level
    - actions: Up, Down, Left, Right (+ Switch while split), in that fixed order
    - transition: ``result``; ``None`` means the move is illegal (the block falls)
    - goal test: whole block standing on the goal cell

    Step costs are not defined here; each solver takes its own cost function.
    """

    def __init__(self, level: Level) -> None:
        self.level = level
        start = Block(level.start[0], level.start[1], Orientation.STANDING)
        self.initial_state = State(start, None, level.initial_bridges)

    def actions(self, state: State) -> tuple[Action, ...]:
        return SPLIT_ACTIONS if state.is_split else MOVES

    def result(self, state: State, action: Action) -> State | None:
        """State after ``action``, or ``None`` if the block would fall."""
        if action is Action.SWITCH:
            if not state.is_split:
                raise ValueError("SWITCH is only available while the block is split")
            controlled, other = state.cubes
            return State(None, (other, controlled), state.bridges)

        if state.is_split:
            controlled, other = state.cubes
            landed = State(None, (step(controlled, action), other), state.bridges)
        else:
            landed = State(roll(state.block, action), None, state.bridges)

        if not rules.is_legal(self.level, landed):
            return None
        return rules.apply_effects(self.level, landed)

    def successors(self, state: State) -> list[tuple[Action, State]]:
        """Legal (action, next state) pairs in the fixed action order."""
        out = []
        for action in self.actions(state):
            nxt = self.result(state, action)
            if nxt is not None:
                out.append((action, nxt))
        return out

    def is_goal(self, state: State) -> bool:
        return state.is_standing and (state.block.row, state.block.col) == self.level.goal


def replay(problem: BloxorzProblem, actions: Iterable[Action]) -> list[State]:
    """States visited by applying ``actions`` from the initial state (initial included).

    Useful for animating a solution and for checking one in tests.
    """
    states = [problem.initial_state]
    for i, action in enumerate(actions):
        nxt = problem.result(states[-1], action)
        if nxt is None:
            raise IllegalMoveError(f"action #{i} ({action.name}) makes the block fall")
        states.append(nxt)
    return states


def parse_actions(text: str) -> list[Action]:
    """Parse a compact plan such as ``"RRDS"`` into actions."""
    return [Action(ch) for ch in text.upper() if not ch.isspace()]


def format_actions(actions: Iterable[Action]) -> str:
    return "".join(a.value for a in actions)
