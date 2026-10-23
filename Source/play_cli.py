"""Terminal CLI Bloxorz Game & Solver Visualizer."""

from __future__ import annotations

import msvcrt
import os
import sys
import time
from pathlib import Path

from bloxorz.core import (
    Action,
    Block,
    BloxorzProblem,
    BridgeEffect,
    Orientation,
    State,
    SwitchKind,
    Tile,
    load_level,
    rules,
)
from bloxorz.core.rules import is_passable, pressed_switches
from bloxorz.solvers import physics_cost, solve_astar, solve_ucs

# Local CLI hook to play switch and split levels while rules.py is being developed
_orig_apply = rules.apply_effects

def _cli_apply(level, state):
    try:
        return _orig_apply(level, state)
    except NotImplementedError:
        pressed = []
        if state.is_split:
            curr_cell = state.cubes[0]
            sw = level.switches.get(curr_cell)
            if sw and sw.kind is SwitchKind.SOFT:
                pressed.append(sw)
        else:
            for c in state.cells():
                sw = level.switches.get(c)
                if sw:
                    if sw.kind is SwitchKind.SOFT or state.is_standing:
                        pressed.append(sw)

        b = state.bridges
        split_targets = None
        for sw in pressed:
            if sw.kind is SwitchKind.SPLIT:
                split_targets = sw.targets
            elif sw.effect == BridgeEffect.TOGGLE:
                b ^= sw.bridge_mask
            elif sw.effect == BridgeEffect.OPEN:
                b |= sw.bridge_mask
            elif sw.effect == BridgeEffect.CLOSE:
                b &= ~sw.bridge_mask

        if split_targets is not None:
            return State(None, split_targets, b)

        if state.is_split:
            c1, c2 = state.cubes
            if c1 == c2:
                return None
            r1, col1 = c1
            r2, col2 = c2
            dr = abs(r1 - r2)
            dc = abs(col1 - col2)
            if dr + dc == 1:
                if dr == 0:
                    merged = Block(r1, min(col1, col2), Orientation.HORIZONTAL)
                else:
                    merged = Block(min(r1, r2), col1, Orientation.VERTICAL)
                return State(merged, None, b)
            return state._replace(bridges=b)

        if not all(is_passable(level, c, b) for c in state.cells()):
            return None
        return state._replace(bridges=b)

rules.apply_effects = _cli_apply


LEVELS_DIR = Path(__file__).resolve().parent / "levels"

GROUP_TITLES = {
    "g1": "Group 1: Basic Platforms",
    "g2": "Group 2: Fragile Tiles (Orange)",
    "g3": "Group 3: Switches & Bridges",
    "g4": "Group 4: Combined Challenges",
}


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def render_board(problem: BloxorzProblem, current_state, message: str = "") -> None:
    clear_screen()
    level = problem.level

    # Determine cells occupied by block or split cubes
    block_cells: set[tuple[int, int]] = set()
    controlled_cube = None
    other_cube = None
    if current_state:
        if current_state.is_split:
            controlled_cube, other_cube = current_state.cubes
            block_cells = {controlled_cube, other_cube}
        elif current_state.block:
            block_cells = set(current_state.block.cells())

    print("\033[96m========================================================\033[0m")
    print(f"\033[97;1m  BLOXORZ CLI  -  {level.name}\033[0m")
    print("\033[96m========================================================\033[0m\n")

    for r in range(level.rows):
        row_str = "  "
        for c in range(level.cols):
            cell = (r, c)
            if cell in block_cells:
                if current_state and current_state.is_split:
                    if cell == controlled_cube:
                        row_str += "\033[93;1m■■\033[0m "  # Active controlled 1x1 cube
                    else:
                        row_str += "\033[33m□□\033[0m "   # Passive 1x1 cube
                elif current_state and current_state.is_standing:
                    row_str += "\033[93;1m██\033[0m "      # Standing 1x1 block
                else:
                    row_str += "\033[93;1m▓▓\033[0m "      # Lying 1x2 block
            else:
                tile = level.tile(cell)
                if tile is Tile.GOAL:
                    row_str += "\033[91;1m[G]\033[0m"       # Goal hole
                elif tile is Tile.FLOOR:
                    row_str += "\033[90m·· \033[0m"        # Floor tile
                elif tile is Tile.FRAGILE:
                    row_str += "\033[38;5;208m░░ \033[0m"   # Fragile orange tile
                elif tile is Tile.BRIDGE:
                    is_open = bool(current_state.bridges >> level.bridge_bit[cell] & 1) if current_state else False
                    if is_open:
                        row_str += "\033[96m══ \033[0m"     # Open bridge
                    else:
                        row_str += "\033[90m-- \033[0m"     # Closed bridge
                elif tile is Tile.SOFT_SWITCH:
                    row_str += "\033[95m(O)\033[0m"         # Soft round switch
                elif tile is Tile.HEAVY_SWITCH:
                    row_str += "\033[95;1m[X]\033[0m"       # Heavy cross switch
                elif tile is Tile.SPLIT_SWITCH:
                    row_str += "\033[92m<S>\033[0m"         # Split switch
                else:
                    row_str += "   "                   # Void / space
        print(row_str)

    print("\n\033[90m--------------------------------------------------------\033[0m")
    if current_state:
        if current_state.is_split:
            status_desc = f"\033[93;1mSPLIT CUBES\033[0m (Active: {controlled_cube}, Other: {other_cube})"
        else:
            orient = current_state.block.orientation.value.upper() if current_state.block else "NONE"
            status_desc = f"\033[94mOrientation:\033[0m {orient}"
        print(f"  {status_desc}")
    if message:
        print(f"  {message}")
    print("\033[90m--------------------------------------------------------\033[0m")
    ctrls = "  \033[37m[W/A/S/D] or [Arrows]\033[0m: Roll"
    if current_state and current_state.is_split:
        ctrls += "  |  \033[93m[TAB]\033[0m: Switch Cube"
    ctrls += "  |  \033[37m[U]\033[0m: UCS  |  \033[37m[SPACE]\033[0m: A*  |  \033[37m[R]\033[0m: Restart  |  \033[37m[Q]\033[0m: Menu"
    print(ctrls)


def get_key() -> str:
    """Read a single keypress on Windows without waiting for Enter."""
    ch = msvcrt.getch()
    if ch in (b"\x00", b"\xe0"):  # Special keys (Arrows)
        ch2 = msvcrt.getch()
        mapping = {b"H": "UP", b"P": "DOWN", b"K": "LEFT", b"M": "RIGHT"}
        return mapping.get(ch2, "")
    try:
        if ch == b"\t":
            return "tab"
        decoded = ch.decode("utf-8").lower()
        if decoded in ("w", "a", "s", "d", "r", "u", "q", " "):
            return " " if decoded == " " else decoded
        if ch == b"\x1b":  # ESC
            return "q"
    except Exception:
        pass
    return ""


def run_game(level_path: Path) -> None:
    level = load_level(level_path)
    problem = BloxorzProblem(level)
    state = problem.initial_state
    moves_history: list[Action] = []
    total_cost = 0.0

    while True:
        # Check Win
        if problem.is_goal(state):
            render_board(
                problem,
                state,
                f"\033[92;1m🎉 YOU WIN! Reached goal in {len(moves_history)} moves (Physics Cost: {total_cost:.1f})!\033[0m",
            )
            print("\n  Press any key to return to menu...")
            msvcrt.getch()
            break

        render_board(
            problem,
            state,
            f"Moves: \033[97;1m{len(moves_history)}\033[0m  |  Cost: \033[97;1m{total_cost:.1f}\033[0m",
        )

        key = get_key()
        if key == "q":
            break
        if key == "r":
            state = problem.initial_state
            moves_history.clear()
            total_cost = 0.0
            continue
        if key in ("u", " "):
            is_astar = (key == " ")
            algo_name = "A*" if is_astar else "UCS"
            render_board(problem, state, f"\033[93m🤖 AI ({algo_name}) is calculating optimal path...\033[0m")
            path, metrics = solve_astar(problem) if is_astar else solve_ucs(problem)
            if not path:
                render_board(problem, state, "\033[91m❌ No solution found for this level!\033[0m")
                time.sleep(2)
                continue

            # Animate solution
            curr = problem.initial_state
            anim_cost = 0.0
            for i, act in enumerate(path, 1):
                nxt = problem.result(curr, act)
                anim_cost += physics_cost(curr, act, nxt)
                curr = nxt
                render_board(
                    problem,
                    curr,
                    f"\033[92m🤖 {algo_name}: Step {i}/{len(path)} ({act.name}) | Time: {metrics.search_time*1000:.1f}ms | Nodes: {metrics.expanded_nodes}\033[0m",
                )
                time.sleep(0.28)

            print(f"\n  \033[92;1m🎉 {algo_name} solved in {len(path)} moves! (Expanded: {metrics.expanded_nodes} nodes) Press any key...\033[0m")
            msvcrt.getch()
            break

        # Map key to Action
        action = None
        if key in ("w", "UP"):
            action = Action.UP
        elif key in ("s", "DOWN"):
            action = Action.DOWN
        elif key in ("a", "LEFT"):
            action = Action.LEFT
        elif key in ("d", "RIGHT"):
            action = Action.RIGHT
        elif key == "tab" and state.is_split:
            action = Action.SWITCH

        if action is not None:
            nxt = problem.result(state, action)
            if nxt is None:
                # Fall into void or fragile break
                render_board(
                    problem,
                    None,
                    "\033[91;1m💥 THE BLOCK FELL OFF OR BROKE FRAGILE TILE! Press 'R' to restart.\033[0m",
                )
                while True:
                    k = get_key()
                    if k == "r":
                        state = problem.initial_state
                        moves_history.clear()
                        total_cost = 0.0
                        break
                    elif k == "q":
                        return
            else:
                total_cost += physics_cost(state, action, nxt)
                state = nxt
                moves_history.append(action)


def main() -> None:
    while True:
        clear_screen()
        print("\033[96m========================================================\033[0m")
        print("\033[97;1m           BLOXORZ - SELECT A LEVEL TO PLAY             \033[0m")
        print("\033[96m========================================================\033[0m\n")

        all_level_files = sorted(LEVELS_DIR.glob("*.json"))
        if not all_level_files:
            print("  No levels found in Source/levels/!")
            break

        # Group levels by prefix (g1, g2, g3, g4, etc.)
        current_group_prefix = None
        level_index_map: dict[int, Path] = {}
        counter = 1

        for lvl_path in all_level_files:
            prefix = lvl_path.stem[:2] if len(lvl_path.stem) >= 2 else "other"
            if prefix != current_group_prefix:
                current_group_prefix = prefix
                group_title = GROUP_TITLES.get(prefix, f"Other Levels ({prefix})")
                print(f"  \033[94;1m► {group_title}\033[0m")

            try:
                lvl = load_level(lvl_path)
                print(f"    \033[93;1m[{counter:2d}]\033[0m {lvl_path.name:<20} \033[90m— {lvl.name}\033[0m")
            except Exception:
                print(f"    \033[93;1m[{counter:2d}]\033[0m {lvl_path.name:<20}")

            level_index_map[counter] = lvl_path
            counter += 1

        print(f"\n  \033[91m [Q]\033[0m Quit")
        print("\033[90m--------------------------------------------------------\033[0m")
        try:
            choice = input(f"  Select level (1-{counter - 1}): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == "q":
            clear_screen()
            print("Goodbye!\n")
            break

        if choice.isdigit():
            idx = int(choice)
            if idx in level_index_map:
                run_game(level_index_map[idx])


if __name__ == "__main__":
    main()
