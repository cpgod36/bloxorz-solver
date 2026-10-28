"""Main Pygame application for Bloxorz with 3D roll, sink, and fall animations."""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
import queue
import threading
import pygame

from bloxorz.core import Action, BloxorzProblem, State, load_level, replay, roll, step
from bloxorz.solvers import SearchMetrics, astar, bfs, dfs, physics_cost, ucs
from . import renderer, theme
from .renderer import MoveTransition
from .widgets import Button


class GameStatus(Enum):
    PLAYING = auto()
    WON = auto()
    LOST = auto()
    SOLVING = auto()
    ANIMATING = auto()


KEY_TO_ACTION: dict[int, Action] = {
    pygame.K_UP: Action.UP,
    pygame.K_w: Action.UP,
    pygame.K_DOWN: Action.DOWN,
    pygame.K_s: Action.DOWN,
    pygame.K_LEFT: Action.LEFT,
    pygame.K_a: Action.LEFT,
    pygame.K_RIGHT: Action.RIGHT,
    pygame.K_d: Action.RIGHT,
    pygame.K_SPACE: Action.SWITCH,
}

ROLL_DURATION_MS = 155
END_EFFECT_DURATION_MS = 320

# Button label -> solver function. All return SearchResult(path, metrics).
SOLVERS = {
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "A*": astar,
}


class BloxorzApp:
    """Top-level GUI controller for playing and solving Bloxorz stages."""

    def __init__(self, level_paths: list[Path] | None = None) -> None:
        pygame.init()
        pygame.display.set_caption("Bloxorz Solver")
        self.screen = pygame.display.set_mode((theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.bg_surface = self._create_background(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)

        self.font_title = pygame.font.SysFont(theme.FONT_TITLE_FAMILY, 22, bold=True)
        self.font_banner = pygame.font.SysFont(theme.FONT_TITLE_FAMILY, 26, bold=True)
        self.font_button = pygame.font.SysFont(theme.FONT_BUTTON_FAMILY, 15, bold=True)
        self.font_section = pygame.font.SysFont(theme.FONT_UI_FAMILY, 15, bold=True)
        self.font_ui = pygame.font.SysFont(theme.FONT_UI_FAMILY, 15)
        self.font_small = pygame.font.SysFont(theme.FONT_UI_FAMILY, 14)
        self.font_value = pygame.font.SysFont(theme.FONT_VALUE_FAMILY, 14, bold=True)

        self.level_paths = level_paths or self._discover_levels()
        if not self.level_paths:
            raise FileNotFoundError("No level JSON files found in levels/ or tests/fixtures/")
        self.level_index = 0

        self.problem: BloxorzProblem
        self.state: State
        self.status = GameStatus.PLAYING
        self.moves_count = 0
        self.status_message = ""
        self.status_color = theme.ACCENT_COLOR

        # Single-move 3D roll / sink / fall animation state
        self.transition: MoveTransition | None = None
        self.transition_elapsed_ms = 0
        self.transition_target_state: State | None = None
        self.end_effect_timer_ms = 0
        self.end_effect_active = False

        # Solver replay animation state (Phase 2)
        self.anim_actions: list[Action] = []
        self.anim_states: list[State] = []
        self.anim_index = 0
        self.anim_timer_ms = 0
        self.anim_step_delay_ms = 210
        self.metrics_info: dict[str, str] = {
            "Algorithm": "-",
            "Solution Length": "-",
            "Expanded Nodes": "-",
            "Search Time": "-",
            "Cost": "-",
        }
        # Worker thread -> main thread channel: (kind, algo_name, result).
        # Only the main thread mutates GUI state.
        self.solver_results: queue.Queue[tuple[str, str, object]] = queue.Queue()

        self.buttons = self._create_buttons()
        self.load_current_level()

    def _discover_levels(self) -> list[Path]:
        base = Path(__file__).resolve().parents[2]
        levels_dir = base / "levels"
        paths = sorted(levels_dir.rglob("*.json")) if levels_dir.exists() else []
        if not paths:
            fixtures_dir = base / "tests" / "fixtures"
            for name in ("classic_01.json", "all_tiles.json"):
                candidate = fixtures_dir / name
                if candidate.exists():
                    paths.append(candidate)
        return paths

    def _create_buttons(self) -> list[Button]:
        x = theme.BOARD_AREA_WIDTH + 20
        w = theme.SIDEBAR_WIDTH - 40
        half = (w - 10) // 2
        return [
            Button((x, 100, half, 34), "< Prev", self.prev_level),
            Button((x + half + 10, 100, half, 34), "Next >", self.next_level),
            Button((x, 142, half, 34), "New Game", self.new_game),
            Button((x + half + 10, 142, half, 34), "Restart (R)", self.restart_level),
            # Phase 2 Solver buttons
            Button((x, 212, half, 34), "Solve BFS", lambda: self.run_solver("BFS")),
            Button((x + half + 10, 212, half, 34), "Solve DFS", lambda: self.run_solver("DFS")),
            Button((x, 254, half, 34), "Solve UCS", lambda: self.run_solver("UCS")),
            Button((x + half + 10, 254, half, 34), "Solve A*", lambda: self.run_solver("A*")),
        ]

    def new_game(self) -> None:
        """Reset to the first stage."""
        if self.status is GameStatus.SOLVING:
            return
        self.level_index = 0
        self.load_current_level()

    def load_current_level(self) -> None:
        level = load_level(self.level_paths[self.level_index])
        self.problem = BloxorzProblem(level)
        self.restart_level()

    def restart_level(self) -> None:
        if self.status is GameStatus.SOLVING:
            return
        self.state = self.problem.initial_state
        self.status = GameStatus.PLAYING
        self.moves_count = 0
        self.transition = None
        self.transition_target_state = None
        self.end_effect_active = False
        self.anim_actions = []
        self.anim_states = []
        self.status_message = "Arrows / WASD: Roll | Space: Switch"
        self.status_color = theme.ACCENT_COLOR

    def prev_level(self) -> None:
        if self.status is GameStatus.SOLVING:
            return
        self.level_index = (self.level_index - 1) % len(self.level_paths)
        self.load_current_level()

    def next_level(self) -> None:
        if self.status is GameStatus.SOLVING:
            return
        self.level_index = (self.level_index + 1) % len(self.level_paths)
        self.load_current_level()

    def _finish_pending_roll(self) -> None:
        """Snap any in-progress player roll to its destination immediately."""
        if self.transition is not None and not self.end_effect_active:
            if self.transition_target_state is not None:
                self.state = self.transition_target_state
            self.transition = None
            self.transition_target_state = None

    def _compute_illegal_landed_state(self, state: State, action: Action) -> State:
        """Compute the unvalidated placement after ``action`` so a falling block can be drawn."""
        if state.is_split:
            assert state.cubes is not None
            controlled, other = state.cubes
            return State(None, (step(controlled, action), other), state.bridges)
        assert state.block is not None
        return State(roll(state.block, action), None, state.bridges)

    def handle_player_action(self, action: Action) -> None:
        # Finish any in-progress normal roll so fast consecutive keypresses never drop
        if self.status is GameStatus.PLAYING and self.transition is not None:
            self._finish_pending_roll()

        if self.status is not GameStatus.PLAYING:
            return
        if action is Action.SWITCH and not self.state.is_split:
            self.status_message = "Switch (Space) only works when split."
            self.status_color = theme.WARNING_COLOR
            return

        prev_state = self.state
        try:
            nxt = self.problem.result(prev_state, action)
        except NotImplementedError as exc:
            self.status_message = str(exc)
            self.status_color = theme.WARNING_COLOR
            return

        self.moves_count += 1
        if nxt is None:
            self.status = GameStatus.LOST
            self.status_message = "Block fell! Press R to restart."
            self.status_color = theme.DANGER_COLOR
            self.state = self._compute_illegal_landed_state(prev_state, action)
            self.transition = MoveTransition(start_state=prev_state, action=action, progress=0.0)
            self.transition_elapsed_ms = 0
            self.end_effect_active = False
            return

        self.state = nxt
        if action is Action.SWITCH:
            self.status_message = "Switched active cube."
            self.status_color = theme.ACCENT_COLOR
            return

        self.transition = MoveTransition(start_state=prev_state, action=action, progress=0.0)
        self.transition_target_state = nxt
        self.transition_elapsed_ms = 0
        self.end_effect_active = False

        if self.problem.is_goal(nxt):
            self.status = GameStatus.WON
            self.status_message = f"Cleared in {self.moves_count} moves!"
            self.status_color = theme.SUCCESS_COLOR
        else:
            self.status_message = f"Last move: {action.name}"
            self.status_color = theme.ACCENT_COLOR

    def run_solver(self, algo_name: str) -> None:
        """Run the selected solver on a background thread so the GUI stays responsive."""
        if self.status is GameStatus.SOLVING:
            return
        # Solvers start from the initial state, so show it. Must run before
        # setting SOLVING because restart_level() returns early while SOLVING.
        self.restart_level()

        self.status = GameStatus.SOLVING
        self.status_message = f"Solving with {algo_name}..."
        self.status_color = theme.WARNING_COLOR
        solver = SOLVERS[algo_name]
        problem = self.problem  # captured locally; the worker never touches self's GUI state

        def _worker() -> None:
            try:
                # tracemalloc hooks every allocation in the process, including the render
                # loop, making solving 3-4x slower and the GUI stutter. Memory is measured
                # by the benchmark instead.
                result = solver(problem, trace_memory=False)
                self.solver_results.put(("SUCCESS", algo_name, result))
            except Exception as exc:  # never leave the GUI stuck in SOLVING
                self.solver_results.put(("ERROR", algo_name, str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _path_cost(self, path: list[Action] | None) -> float | None:
        """Total physics_cost of a path, the cost UCS and A* minimise, for every solver alike."""
        if path is None:
            return None
        states = replay(self.problem, path)
        return sum(physics_cost(s, a, t) for s, a, t in zip(states, path, states[1:]))

    @staticmethod
    def _format_metrics(algo_name: str, metrics: SearchMetrics, cost: float | None) -> dict[str, str]:
        """Convert SearchMetrics into the sidebar's display strings."""
        return {
            "Algorithm": algo_name,
            "Solution Length": f"{metrics.solution_length}" if metrics.solution_length is not None else "-",
            "Expanded Nodes": f"{metrics.expanded_nodes}" if metrics.expanded_nodes is not None else "-",
            "Search Time": f"{metrics.search_time * 1000:.3f} ms" if metrics.search_time is not None else "-",
            "Cost": f"{cost:g}" if cost is not None else "-",
        }

    def _process_solver_results(self) -> None:
        """Pick up a finished solver result (if any). Called on the main thread every frame."""
        try:
            kind, algo_name, result = self.solver_results.get_nowait()
        except queue.Empty:
            return  # nothing finished yet this frame

        if kind == "ERROR":
            self.status = GameStatus.PLAYING
            self.status_message = f"{algo_name} solver error: {result}"
            self.status_color = theme.DANGER_COLOR
            return

        path, metrics = result
        self.metrics_info = self._format_metrics(algo_name, metrics, self._path_cost(path))

        if path is None:
            self.status = GameStatus.PLAYING
            self.status_message = f"{algo_name} solver found no solution."
            self.status_color = theme.WARNING_COLOR
        elif not path:
            self.status = GameStatus.WON
            self.status_message = f"{algo_name} solver found a trivial solution (0 moves)."
            self.status_color = theme.SUCCESS_COLOR
        else:
            self.start_animation(path, self.metrics_info)

    def start_animation(self, actions: list[Action], metrics: dict[str, str]) -> None:
        """Replay a solution path step by step on the 3D board."""
        self.anim_actions = list(actions)
        self.anim_states = replay(self.problem, self.anim_actions)
        self.anim_index = 0
        self.anim_timer_ms = 0
        self.state = self.anim_states[0]
        self.moves_count = 0
        self.metrics_info = metrics
        self.status = GameStatus.ANIMATING
        self.status_message = "Replaying solution..."
        self.status_color = theme.ACCENT_COLOR
        if self.anim_actions:
            self.transition = MoveTransition(
                start_state=self.anim_states[0],
                action=self.anim_actions[0],
                progress=0.0,
            )

    def update(self, dt_ms: int) -> None:
        # 0. Receive results from the solver thread
        self._process_solver_results()

        # 1. Solver solution replay mode
        if self.status is GameStatus.ANIMATING and self.anim_states:
            self.anim_timer_ms += dt_ms
            if self.anim_index < len(self.anim_actions):
                prog = min(1.0, self.anim_timer_ms / max(1, self.anim_step_delay_ms))
                self.transition = MoveTransition(
                    start_state=self.anim_states[self.anim_index],
                    action=self.anim_actions[self.anim_index],
                    progress=prog,
                )
                if self.anim_timer_ms >= self.anim_step_delay_ms:
                    self.anim_timer_ms = 0
                    self.anim_index += 1
                    self.state = self.anim_states[self.anim_index]
                    self.moves_count = self.anim_index
                    if self.anim_index >= len(self.anim_actions):
                        self.transition = None
                        if self.problem.is_goal(self.state):
                            self.status = GameStatus.WON
                            self.status_message = f"Solved in {self.moves_count} moves!"
                            self.status_color = theme.SUCCESS_COLOR
                            self.end_effect_active = True
                            self.end_effect_timer_ms = 0
                            self.transition = MoveTransition(start_state=self.state, z_offset=0.0)
                        else:
                            self.status = GameStatus.PLAYING
            return

        # 2. Single-move 3D roll animation
        if self.transition is not None and not self.end_effect_active:
            self.transition_elapsed_ms += dt_ms
            prog = min(1.0, self.transition_elapsed_ms / ROLL_DURATION_MS)
            self.transition.progress = prog
            if prog >= 1.0:
                if self.status in (GameStatus.WON, GameStatus.LOST):
                    self.end_effect_active = True
                    self.end_effect_timer_ms = 0
                    self.transition = MoveTransition(start_state=self.state, z_offset=0.0)
                else:
                    self.transition = None
                    self.transition_target_state = None
            return

        # 3. Goal-sinking (WON) or abyss-falling (LOST) vertical animation
        if self.end_effect_active and self.transition is not None:
            self.end_effect_timer_ms += dt_ms
            t = min(1.0, self.end_effect_timer_ms / END_EFFECT_DURATION_MS)
            if self.status is GameStatus.WON:
                # Smoothly slide standing block down into the goal hole
                self.transition.z_offset = -2.0 * (t * t)
            else:
                # Accelerate falling block down into the void
                self.transition.z_offset = -3.8 * (t * t)

    def _create_background(self, width: int, height: int) -> pygame.Surface:
        bg = pygame.Surface((width, height))
        top_color = (14, 18, 28)
        bottom_color = (11, 35, 59)
        for y in range(height):
            t = y / height
            r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
            g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
            b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
            pygame.draw.line(bg, (r, g, b), (0, y), (width, y))
        return bg

    def draw_overlay_banner(self) -> None:
        """Draw a translucent victory/defeat banner once the sink/fall animation finishes."""
        if self.status not in (GameStatus.WON, GameStatus.LOST):
            return
        if self.end_effect_active and self.end_effect_timer_ms < END_EFFECT_DURATION_MS:
            return

        banner = pygame.Surface((theme.BOARD_AREA_WIDTH, 84), pygame.SRCALPHA)
        banner.fill((12, 16, 26, 210))
        y_pos = theme.WINDOW_HEIGHT - 110
        self.screen.blit(banner, (0, y_pos))
        pygame.draw.line(
            self.screen,
            self.status_color,
            (0, y_pos),
            (theme.BOARD_AREA_WIDTH, y_pos),
            2,
        )

        text = (
            f"STAGE CLEARED IN {self.moves_count} MOVES!"
            if self.status is GameStatus.WON
            else "BLOCK FELL! PRESS 'R' TO RESTART"
        )
        surf = self.font_banner.render(text, True, self.status_color)
        rect = surf.get_rect(center=(theme.BOARD_AREA_WIDTH // 2, y_pos + 42))
        self.screen.blit(surf, rect)

    def draw_sidebar(self) -> None:
        sidebar_rect = pygame.Rect(
            theme.BOARD_AREA_WIDTH, 0, theme.SIDEBAR_WIDTH, theme.WINDOW_HEIGHT
        )
        pygame.draw.rect(self.screen, theme.SIDEBAR_BG, sidebar_rect)
        pygame.draw.line(
            self.screen,
            theme.SIDEBAR_BORDER,
            (theme.BOARD_AREA_WIDTH, 0),
            (theme.BOARD_AREA_WIDTH, theme.WINDOW_HEIGHT),
            2,
        )

        x = theme.BOARD_AREA_WIDTH + 20
        w = theme.SIDEBAR_WIDTH - 40

        level_name = self.problem.level.name
        if len(level_name) > 26:
            level_name = level_name[:25] + "…"
        title = self.font_title.render(level_name, True, theme.TEXT_COLOR)
        self.screen.blit(title, (x, 22))

        sub = self.font_ui.render(
            f"Stage {self.level_index + 1}/{len(self.level_paths)}   |   Moves: {self.moves_count}",
            True,
            theme.MUTED_TEXT,
        )
        self.screen.blit(sub, (x, 54))

        solver_label = self.font_section.render("AI SOLVERS", True, theme.MUTED_TEXT)
        self.screen.blit(solver_label, (x, 186))

        for btn in self.buttons:
            btn.draw(self.screen, self.font_button)

        status_box = pygame.Rect(x, 304, w, 42)
        pygame.draw.rect(self.screen, theme.PANEL_BG, status_box, border_radius=6)
        pygame.draw.rect(self.screen, theme.SIDEBAR_BORDER, status_box, width=1, border_radius=6)
        msg_surf = self.font_ui.render(self.status_message, True, self.status_color)
        self.screen.blit(msg_surf, (x + 12, 315))

        metrics_box = pygame.Rect(x, 360, w, 150)
        pygame.draw.rect(self.screen, theme.PANEL_BG, metrics_box, border_radius=6)
        pygame.draw.rect(self.screen, theme.SIDEBAR_BORDER, metrics_box, width=1, border_radius=6)

        m_title = self.font_section.render("SOLVER METRICS", True, theme.TEXT_COLOR)
        self.screen.blit(m_title, (x + 12, 368))
        y_offset = 396
        for key, val in self.metrics_info.items():
            key_surf = self.font_small.render(f"{key}:", True, theme.MUTED_TEXT)
            val_surf = self.font_value.render(val, True, theme.ACCENT_COLOR if val != "-" else theme.MUTED_TEXT)
            self.screen.blit(key_surf, (x + 12, y_offset))
            self.screen.blit(val_surf, (x + 150, y_offset))
            y_offset += 21

        legend_box = pygame.Rect(x, 524, w, 174)
        pygame.draw.rect(self.screen, theme.PANEL_BG, legend_box, border_radius=6)
        pygame.draw.rect(self.screen, theme.SIDEBAR_BORDER, legend_box, width=1, border_radius=6)
        l_title = self.font_section.render("LEGEND & CONTROLS", True, theme.TEXT_COLOR)
        self.screen.blit(l_title, (x + 12, 532))

        legend_rows = [
            ("Arrows / WASD", "Roll block"),
            ("Space", "Switch split cube"),
            ("R", "Restart stage"),
            ("Orange tile", "Fragile (no standing)"),
            ("Green / Hollow", "Bridge (open / closed)"),
            ("O / X / ( )", "Soft / Heavy / Split"),
        ]
        ly = 560
        for key_txt, desc_txt in legend_rows:
            k_surf = self.font_small.render(key_txt, True, theme.TEXT_COLOR)
            d_surf = self.font_small.render(desc_txt, True, theme.MUTED_TEXT)
            self.screen.blit(k_surf, (x + 12, ly))
            self.screen.blit(d_surf, (x + 128, ly))
            ly += 21

    def run(self) -> None:
        running = True
        while running:
            dt_ms = self.clock.tick(theme.FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.restart_level()
                    elif event.key in KEY_TO_ACTION:
                        self.handle_player_action(KEY_TO_ACTION[event.key])
                for btn in self.buttons:
                    btn.handle_event(event)

            self.update(dt_ms)

            self.screen.blit(self.bg_surface, (0, 0))
            renderer.draw_board(self.screen, self.problem.level, self.state, self.transition)
            self.draw_overlay_banner()
            self.draw_sidebar()
            pygame.display.flip()

        pygame.quit()
