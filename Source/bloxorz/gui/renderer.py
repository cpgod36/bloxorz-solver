"""3D perspective board and animated block rendering routines for the Bloxorz GUI."""

from __future__ import annotations

from dataclasses import dataclass
import math
import pygame

from bloxorz.core import Action, Level, Orientation, State, Tile
from . import theme

Color = tuple[int, int, int]
Point2D = tuple[int, int]
Vec3 = tuple[float, float, float]


@dataclass
class MoveTransition:
    """Describes an in-progress 3D roll/step or sink/fall animation."""

    start_state: State
    action: Action | None = None
    progress: float = 0.0  # 0.0 -> 1.0 roll/step interpolation
    z_offset: float = 0.0  # vertical offset for goal-sink or abyss-fall


def shade(color: Color, factor: float) -> Color:
    """Multiply RGB channels by ``factor`` and clamp to [0, 255]."""
    return (
        max(0, min(255, int(color[0] * factor))),
        max(0, min(255, int(color[1] * factor))),
        max(0, min(255, int(color[2] * factor))),
    )


@dataclass(frozen=True)
class Camera3D:
    """Projects 3D board coordinates (r, c, z) onto 2D screen pixels with perspective depth."""

    scale: float
    origin_x: float
    origin_y: float
    center_r: float = 0.0
    center_c: float = 0.0
    span_depth: float = 1.0

    def relative_depth(self, r: float, c: float, z: float = 0.0) -> float:
        """Signed depth relative to the board center (+ means closer to camera)."""
        dr = r - self.center_r
        dc = c - self.center_c
        return (
            dr * theme.DEPTH_VEC[0]
            + dc * theme.DEPTH_VEC[1]
            + z * theme.DEPTH_VEC[2]
        )

    def depth_shade_factor(self, r: float, c: float) -> float:
        """Atmospheric depth cueing: tiles closer to the viewer are brighter than distant tiles."""
        norm_d = self.relative_depth(r, c, 0.0) / max(self.span_depth, 1.0)
        return max(0.84, min(1.06, 0.96 + 0.14 * norm_d))

    def project(self, r: float, c: float, z: float = 0.0) -> Point2D:
        """Project (r, c, z) with perspective foreshortening."""
        dr = r - self.center_r
        dc = c - self.center_c

        # Linear camera-space coordinates centered on the board
        lx = dc * theme.VEC_C[0] + dr * theme.VEC_R[0] + z * theme.VEC_Z[0]
        ly = dc * theme.VEC_C[1] + dr * theme.VEC_R[1] + z * theme.VEC_Z[1]

        # Perspective factor: closer objects (+depth) scale up, distant objects (-depth) recede
        depth = self.relative_depth(r, c, z)
        persp = 1.0 / max(0.55, 1.0 - theme.PERSPECTIVE_STRENGTH * depth)

        px = self.origin_x + self.scale * lx * persp
        py = self.origin_y + self.scale * ly * persp
        return (int(round(px)), int(round(py)))


def compute_camera(level: Level) -> Camera3D:
    """Compute an auto-scaled and centered 3D perspective camera for ``level``."""
    center_r = level.rows / 2.0
    center_c = level.cols / 2.0
    span_depth = max(1.0, (level.rows + level.cols) * 0.5)

    unit_cam = Camera3D(
        scale=1.0,
        origin_x=0.0,
        origin_y=0.0,
        center_r=center_r,
        center_c=center_c,
        span_depth=span_depth,
    )
    sample_points = [
        unit_cam.project(r, c, z)
        for r in (0.0, float(level.rows))
        for c in (0.0, float(level.cols))
        for z in (theme.ABYSS_SHADOW_Z, 2.2)
    ]
    xs = [p[0] for p in sample_points]
    ys = [p[1] for p in sample_points]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)

    avail_w = theme.BOARD_AREA_WIDTH - 2 * theme.BOARD_PADDING
    avail_h = theme.WINDOW_HEIGHT - 2 * theme.BOARD_PADDING
    scale = min(avail_w / max(span_x, 1.0), avail_h / max(span_y, 1.0))
    scale = max(theme.MIN_TILE_SCALE, min(theme.MAX_TILE_SCALE, scale))

    scaled_xs = [x * scale for x in xs]
    scaled_ys = [y * scale for y in ys]
    cx = (min(scaled_xs) + max(scaled_xs)) / 2.0
    cy = (min(scaled_ys) + max(scaled_ys)) / 2.0

    origin_x = theme.BOARD_AREA_WIDTH / 2.0 - cx
    origin_y = theme.WINDOW_HEIGHT / 2.0 - cy
    return Camera3D(
        scale=scale,
        origin_x=origin_x,
        origin_y=origin_y,
        center_r=center_r,
        center_c=center_c,
        span_depth=span_depth,
    )


def draw_prism(
    surface: pygame.Surface,
    cam: Camera3D,
    r0: float,
    r1: float,
    c0: float,
    c1: float,
    z0: float,
    z1: float,
    base_color: Color,
    edge_color: Color,
    edge_width: int = 1,
) -> None:
    """Draw a 3D axis-aligned rectangular prism with shaded Top, Front, and Right faces."""
    top_poly = [
        cam.project(r0, c0, z1),
        cam.project(r0, c1, z1),
        cam.project(r1, c1, z1),
        cam.project(r1, c0, z1),
    ]
    front_poly = [
        cam.project(r1, c0, z1),
        cam.project(r1, c1, z1),
        cam.project(r1, c1, z0),
        cam.project(r1, c0, z0),
    ]
    right_poly = [
        cam.project(r0, c1, z1),
        cam.project(r1, c1, z1),
        cam.project(r1, c1, z0),
        cam.project(r0, c1, z0),
    ]

    pygame.draw.polygon(surface, shade(base_color, 0.72), front_poly)
    pygame.draw.polygon(surface, shade(base_color, 0.54), right_poly)
    pygame.draw.polygon(surface, base_color, top_poly)

    if edge_width > 0:
        pygame.draw.polygon(surface, edge_color, front_poly, edge_width)
        pygame.draw.polygon(surface, edge_color, right_poly, edge_width)
        pygame.draw.polygon(surface, edge_color, top_poly, edge_width)


def _rotate_point(
    pt: Vec3,
    action: Action | None,
    theta: float,
    r_min: float,
    r_max: float,
    c_min: float,
    c_max: float,
    z_offset: float,
) -> Vec3:
    """Rotate a 3D point (r, c, z) around the rolling pivot edge by angle ``theta``."""
    r, c, z = pt
    if action is None or theta == 0.0:
        return (r, c, z + z_offset)

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    if action is Action.UP:
        rp = r_min
        dr = r - rp
        nr = rp + dr * cos_t - z * sin_t
        nz = z * cos_t + dr * sin_t
        return (nr, c, nz + z_offset)
    if action is Action.DOWN:
        rp = r_max
        dr = r - rp
        nr = rp + dr * cos_t + z * sin_t
        nz = z * cos_t - dr * sin_t
        return (nr, c, nz + z_offset)
    if action is Action.LEFT:
        cp = c_min
        dc = c - cp
        nc = cp + dc * cos_t - z * sin_t
        nz = z * cos_t + dc * sin_t
        return (r, nc, nz + z_offset)
    if action is Action.RIGHT:
        cp = c_max
        dc = c - cp
        nc = cp + dc * cos_t + z * sin_t
        nz = z * cos_t - dc * sin_t
        return (r, nc, nz + z_offset)
    return (r, c, z + z_offset)


def _rotate_normal(normal: Vec3, action: Action | None, theta: float) -> Vec3:
    """Rotate a 3D unit normal vector by ``theta`` around the rolling axis."""
    if action is None or theta == 0.0:
        return normal
    nr, nc, nz = normal
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    if action is Action.UP:
        return (nr * cos_t - nz * sin_t, nc, nz * cos_t + nr * sin_t)
    if action is Action.DOWN:
        return (nr * cos_t + nz * sin_t, nc, nz * cos_t - nr * sin_t)
    if action is Action.LEFT:
        return (nr, nc * cos_t - nz * sin_t, nz * cos_t + nc * sin_t)
    if action is Action.RIGHT:
        return (nr, nc * cos_t + nz * sin_t, nz * cos_t - nc * sin_t)
    return normal


def draw_rotated_box(
    surface: pygame.Surface,
    cam: Camera3D,
    r0: float,
    r1: float,
    c0: float,
    c1: float,
    z0: float,
    z1: float,
    pivot_bounds: tuple[float, float, float, float],
    action: Action | None,
    theta: float,
    z_offset: float,
    base_color: Color,
    edge_color: Color,
    seam_segments: list[tuple[Vec3, Vec3, Vec3]] | None = None,
    clip_below_zero: bool = False,
) -> None:
    """Render a 3D box that may be mid-rotation around a pivot edge."""
    pr_min, pr_max, pc_min, pc_max = pivot_bounds

    if clip_below_zero and z_offset < 0.0:
        z1 = max(0.0, z1 + z_offset)
        z_offset = 0.0
        if z1 <= z0 + 0.02:
            return

    def xform(pt: Vec3) -> Vec3:
        return _rotate_point(pt, action, theta, pr_min, pr_max, pc_min, pc_max, z_offset)

    faces: list[tuple[list[Vec3], Vec3]] = [
        ([(r0, c0, z1), (r0, c1, z1), (r1, c1, z1), (r1, c0, z1)], (0.0, 0.0, 1.0)),   # Top (+z)
        ([(r0, c0, z0), (r1, c0, z0), (r1, c1, z0), (r0, c1, z0)], (0.0, 0.0, -1.0)),  # Bottom (-z)
        ([(r1, c0, z1), (r1, c1, z1), (r1, c1, z0), (r1, c0, z0)], (1.0, 0.0, 0.0)),   # Front (+r)
        ([(r0, c1, z1), (r0, c0, z1), (r0, c0, z0), (r0, c1, z0)], (-1.0, 0.0, 0.0)),  # Back (-r)
        ([(r0, c1, z1), (r1, c1, z1), (r1, c1, z0), (r0, c1, z0)], (0.0, 1.0, 0.0)),   # Right (+c)
        ([(r0, c0, z1), (r1, c0, z1), (r1, c0, z0), (r0, c0, z0)], (0.0, -1.0, 0.0)),  # Left (-c)
    ]

    cam_vr, cam_vc, cam_vz = 0.8272, 0.3696, 0.7692

    visible_faces: list[tuple[float, list[Point2D], Color]] = []
    for raw_verts, raw_norm in faces:
        norm = _rotate_normal(raw_norm, action, theta)
        facing_dot = norm[0] * cam_vr + norm[1] * cam_vc + norm[2] * cam_vz
        if facing_dot <= 0.01:
            continue

        t_verts = [xform(v) for v in raw_verts]
        depth = sum(v[0] * cam_vr + v[1] * cam_vc + v[2] * cam_vz for v in t_verts) / 4.0

        brightness = (
            1.00 * max(0.0, norm[2])
            + 0.72 * max(0.0, norm[0])
            + 0.56 * max(0.0, norm[1])
            + 0.50 * max(0.0, -norm[0])
            + 0.62 * max(0.0, -norm[1])
            + 0.45 * max(0.0, -norm[2])
        )
        brightness = max(0.45, min(1.05, brightness))
        poly_2d = [cam.project(*v) for v in t_verts]
        visible_faces.append((depth, poly_2d, shade(base_color, brightness)))

    visible_faces.sort(key=lambda item: item[0])
    for _, poly_2d, col in visible_faces:
        pygame.draw.polygon(surface, col, poly_2d)
        pygame.draw.polygon(surface, edge_color, poly_2d, 2)

    if seam_segments:
        for p_start, p_end, face_norm in seam_segments:
            if clip_below_zero and (p_start[2] > z1 or p_end[2] > z1):
                continue
            rot_norm = _rotate_normal(face_norm, action, theta)
            if rot_norm[0] * cam_vr + rot_norm[1] * cam_vc + rot_norm[2] * cam_vz <= 0.01:
                continue
            s1 = cam.project(*xform(p_start))
            s2 = cam.project(*xform(p_end))
            pygame.draw.line(surface, theme.BLOCK_SEAM_COLOR, s1, s2, 2)


def _draw_abyss_depth_layer(
    surface: pygame.Surface, cam: Camera3D, level: Level, state: State
) -> None:
    """Render a 3D reference grid and floating board drop-shadow deep in the abyss."""
    overlay = pygame.Surface((theme.BOARD_AREA_WIDTH, theme.WINDOW_HEIGHT), pygame.SRCALPHA)
    sz = theme.ABYSS_SHADOW_Z

    # 1. Faint 3D perspective horizon grid on the abyss floor
    grid_col = (55, 75, 110, 34)
    for r in range(-1, level.rows + 2):
        p1 = cam.project(float(r), -1.0, sz)
        p2 = cam.project(float(r), float(level.cols + 1), sz)
        pygame.draw.line(overlay, grid_col, p1, p2, 1)
    for c in range(-1, level.cols + 2):
        p1 = cam.project(-1.0, float(c), sz)
        p2 = cam.project(float(level.rows + 1), float(c), sz)
        pygame.draw.line(overlay, grid_col, p1, p2, 1)

    # 2. Translucent drop shadow cast by every solid tile onto the abyss floor
    for r in range(level.rows):
        for c in range(level.cols):
            tile = level.tile((r, c))
            if tile is Tile.VOID:
                continue
            if tile is Tile.BRIDGE and not state.bridge_open(level.bridge_bit[(r, c)]):
                continue
            shadow_poly = [
                cam.project(r - 0.02, c - 0.02, sz),
                cam.project(r - 0.02, c + 1.02, sz),
                cam.project(r + 1.02, c + 1.02, sz),
                cam.project(r + 1.02, c - 0.02, sz),
            ]
            pygame.draw.polygon(overlay, (6, 8, 14, 95), shadow_poly)

    surface.blit(overlay, (0, 0))


def _draw_single_tile_3d(
    surface: pygame.Surface,
    cam: Camera3D,
    level: Level,
    state: State,
    r: int,
    c: int,
    occupied_cells: set[tuple[int, int]],
) -> None:
    """Draw a single tile at (r, c) with its deep 3D foundation pillar and surface detail."""
    tile = level.tile((r, c))
    if tile is Tile.VOID:
        return

    if tile is Tile.BRIDGE:
        bit = level.bridge_bit[(r, c)]
        _draw_bridge_3d(surface, cam, r, c, state.bridge_open(bit))
        return

    if tile is Tile.GOAL:
        _draw_goal_3d(surface, cam, r, c)
        return

    depth_k = cam.depth_shade_factor(r, c)
    if tile is Tile.FRAGILE:
        base_col = shade(theme.TILE_COLORS["fragile"], depth_k)
    elif (r, c) == level.start:
        base_col = shade(theme.TILE_COLORS["start"], depth_k)
    else:
        base_col = shade(theme.TILE_COLORS["floor"], depth_k)

    # 1. Deep lower architectural foundation pillar (-FOUNDATION_DEPTH to -TILE_THICKNESS)
    f_gap = 0.09
    found_col = shade(theme.TILE_COLORS["foundation"], depth_k)
    draw_prism(
        surface,
        cam,
        r + f_gap,
        r + 1.0 - f_gap,
        c + f_gap,
        c + 1.0 - f_gap,
        -theme.FOUNDATION_DEPTH,
        -theme.TILE_THICKNESS,
        found_col,
        shade(found_col, 0.55),
        edge_width=1,
    )

    # 2. Upper stone tile slab (-TILE_THICKNESS to 0.0)
    gap = 0.025
    draw_prism(
        surface,
        cam,
        r + gap,
        r + 1.0 - gap,
        c + gap,
        c + 1.0 - gap,
        -theme.TILE_THICKNESS,
        0.0,
        base_col,
        theme.TILE_COLORS["border"],
        edge_width=1,
    )

    # 3. Inner bevel highlight on the top face
    bevel_pad = 0.13
    bevel_poly = [
        cam.project(r + bevel_pad, c + bevel_pad, 0.0),
        cam.project(r + bevel_pad, c + 1.0 - bevel_pad, 0.0),
        cam.project(r + 1.0 - bevel_pad, c + 1.0 - bevel_pad, 0.0),
        cam.project(r + 1.0 - bevel_pad, c + bevel_pad, 0.0),
    ]
    pygame.draw.polygon(surface, shade(base_col, 1.05), bevel_poly)

    # 4. Soft ambient contact shadow on tiles currently under the resting block
    if (r, c) in occupied_cells:
        shadow_poly = [
            cam.project(r + 0.06, c + 0.06, 0.002),
            cam.project(r + 0.06, c + 0.94, 0.002),
            cam.project(r + 0.94, c + 0.94, 0.002),
            cam.project(r + 0.94, c + 0.06, 0.002),
        ]
        pygame.draw.polygon(surface, shade(base_col, 0.74), shadow_poly)

    _draw_switch_3d(surface, cam, r, c, tile)


def draw_board(
    surface: pygame.Surface,
    level: Level,
    state: State,
    transition: MoveTransition | None = None,
) -> Camera3D:
    """Render the 3D abyss shadow layer, deep board tiles, and depth-sorted block/cubes."""
    cam = compute_camera(level)
    active_state = transition.start_state if transition is not None else state
    occupied_cells = set(active_state.cells()) if transition is None else set()

    # Draw deep abyss grid and floating board shadow first
    _draw_abyss_depth_layer(surface, cam, level, state)

    # Check if the block is falling into the void below the board surface (z_offset < -0.1)
    is_abyss_fall = (
        transition is not None
        and transition.action is None
        and transition.z_offset < -0.05
        and not (active_state.is_standing and (active_state.block.row, active_state.block.col) == level.goal)
    )

    if not is_abyss_fall:
        for r in range(level.rows):
            for c in range(level.cols):
                _draw_single_tile_3d(surface, cam, level, state, r, c, occupied_cells)
        draw_state_pieces(surface, cam, state, transition)
    else:
        # True 3D depth occlusion when the block falls below the board:
        # Tiles behind the falling block are drawn first, then the falling block, then front tiles.
        fall_cells = active_state.cells()
        max_fall_r = max(cell[0] for cell in fall_cells)
        max_fall_c = max(cell[1] for cell in fall_cells)

        for r in range(level.rows):
            for c in range(level.cols):
                if r <= max_fall_r and c <= max_fall_c:
                    _draw_single_tile_3d(surface, cam, level, state, r, c, occupied_cells)

        draw_state_pieces(surface, cam, state, transition)

        for r in range(level.rows):
            for c in range(level.cols):
                if not (r <= max_fall_r and c <= max_fall_c):
                    _draw_single_tile_3d(surface, cam, level, state, r, c, occupied_cells)

    return cam


def _draw_goal_3d(surface: pygame.Surface, cam: Camera3D, r: int, c: int) -> None:
    """Draw the 3D goal tile with a deep recessed shaft and pulsing cyan rim."""
    gap = 0.025
    depth_k = cam.depth_shade_factor(r, c)
    rim_col = shade(theme.TILE_COLORS["goal_rim"], depth_k)
    border_col = theme.TILE_COLORS["border"]
    R0, R1 = r + gap, r + 1.0 - gap
    C0, C1 = c + gap, c + 1.0 - gap
    z_bot, z_top = -theme.FOUNDATION_DEPTH, 0.0

    # 1. Draw lower foundation pillar first so the upper slab and hole sit on top of it
    f_gap = 0.09
    found_col = shade(theme.TILE_COLORS["foundation"], depth_k)
    draw_prism(
        surface,
        cam,
        r + f_gap,
        r + 1.0 - f_gap,
        c + f_gap,
        c + 1.0 - f_gap,
        -theme.FOUNDATION_DEPTH,
        -theme.TILE_THICKNESS,
        found_col,
        shade(found_col, 0.55),
        edge_width=1,
    )

    # 2. Recessed pit floor and deep vertical chute walls inside the goal hole
    pad = 0.18
    hr0, hr1 = r + pad, r + 1.0 - pad
    hc0, hc1 = c + pad, c + 1.0 - pad
    hole_top = [
        cam.project(hr0, hc0, z_top),
        cam.project(hr0, hc1, z_top),
        cam.project(hr1, hc1, z_top),
        cam.project(hr1, hc0, z_top),
    ]
    pygame.draw.polygon(surface, theme.TILE_COLORS["goal_pit"], hole_top)

    back_wall = [
        cam.project(hr0, hc0, z_top),
        cam.project(hr0, hc1, z_top),
        cam.project(hr0, hc1, z_bot),
        cam.project(hr0, hc0, z_bot),
    ]
    left_wall = [
        cam.project(hr0, hc0, z_top),
        cam.project(hr1, hc0, z_top),
        cam.project(hr1, hc0, z_bot),
        cam.project(hr0, hc0, z_bot),
    ]
    pygame.draw.polygon(surface, (36, 48, 68), back_wall)
    pygame.draw.polygon(surface, (24, 34, 50), left_wall)

    # 3. Top-face rim strips framing the hole
    strips = [
        (R0, hr0, C0, C1),
        (hr1, R1, C0, C1),
        (hr0, hr1, C0, hc0),
        (hr0, hr1, hc1, C1),
    ]
    for sr0, sr1, sc0, sc1 in strips:
        poly = [
            cam.project(sr0, sc0, z_top),
            cam.project(sr0, sc1, z_top),
            cam.project(sr1, sc1, z_top),
            cam.project(sr1, sc0, z_top),
        ]
        pygame.draw.polygon(surface, rim_col, poly)

    # 4. Outer Front and Right faces of the upper slab
    front_poly = [
        cam.project(R1, C0, z_top),
        cam.project(R1, C1, z_top),
        cam.project(R1, C1, -theme.TILE_THICKNESS),
        cam.project(R1, C0, -theme.TILE_THICKNESS),
    ]
    right_poly = [
        cam.project(R0, C1, z_top),
        cam.project(R1, C1, z_top),
        cam.project(R1, C1, -theme.TILE_THICKNESS),
        cam.project(R0, C1, -theme.TILE_THICKNESS),
    ]
    outer_top = [
        cam.project(R0, C0, z_top),
        cam.project(R0, C1, z_top),
        cam.project(R1, C1, z_top),
        cam.project(R1, C0, z_top),
    ]
    pygame.draw.polygon(surface, shade(rim_col, 0.72), front_poly)
    pygame.draw.polygon(surface, shade(rim_col, 0.54), right_poly)
    pygame.draw.polygon(surface, border_col, front_poly, 1)
    pygame.draw.polygon(surface, border_col, right_poly, 1)
    pygame.draw.polygon(surface, border_col, outer_top, 1)

    t_sec = pygame.time.get_ticks() / 1000.0
    pulse = (math.sin(t_sec * 4.0) + 1.0) * 0.5
    glow_col = (int(60 + 55 * pulse), int(145 + 65 * pulse), 255)
    pygame.draw.polygon(surface, glow_col, hole_top, 2)


def _draw_bridge_3d(
    surface: pygame.Surface, cam: Camera3D, r: int, c: int, is_open: bool
) -> None:
    """Draw an open bridge as 3D planks or a closed bridge as a 3D recessed frame."""
    gap = 0.05
    if is_open:
        col = shade(theme.TILE_COLORS["bridge_open"], cam.depth_shade_factor(r, c))
        draw_prism(
            surface,
            cam,
            r + gap,
            r + 1.0 - gap,
            c + gap,
            c + 1.0 - gap,
            -theme.BRIDGE_THICKNESS,
            0.0,
            col,
            shade(col, 0.5),
            edge_width=1,
        )
        for frac in (0.33, 0.67):
            p1 = cam.project(r + frac, c + gap, 0.0)
            p2 = cam.project(r + frac, c + 1.0 - gap, 0.0)
            pygame.draw.line(surface, shade(col, 0.65), p1, p2, 2)
    else:
        poly_top = [
            cam.project(r + gap, c + gap, 0.0),
            cam.project(r + gap, c + 1.0 - gap, 0.0),
            cam.project(r + 1.0 - gap, c + 1.0 - gap, 0.0),
            cam.project(r + 1.0 - gap, c + gap, 0.0),
        ]
        poly_bot = [
            cam.project(r + gap, c + gap, -theme.BRIDGE_THICKNESS),
            cam.project(r + gap, c + 1.0 - gap, -theme.BRIDGE_THICKNESS),
            cam.project(r + 1.0 - gap, c + 1.0 - gap, -theme.BRIDGE_THICKNESS),
            cam.project(r + 1.0 - gap, c + gap, -theme.BRIDGE_THICKNESS),
        ]
        pygame.draw.polygon(surface, shade(theme.TILE_COLORS["bridge_closed"], 0.65), poly_bot, 1)
        pygame.draw.polygon(surface, theme.TILE_COLORS["bridge_closed"], poly_top, 2)


def _draw_switch_3d(
    surface: pygame.Surface, cam: Camera3D, r: int, c: int, tile: Tile
) -> None:
    """Draw raised 3D switch plates on top of switch tiles."""
    if tile is Tile.SOFT_SWITCH:
        oct_coords = [
            (0.20, 0.36),
            (0.20, 0.64),
            (0.36, 0.80),
            (0.64, 0.80),
            (0.80, 0.64),
            (0.80, 0.36),
            (0.64, 0.20),
            (0.36, 0.20),
        ]
        base_pts = [cam.project(r + dr, c + dc, 0.0) for dr, dc in oct_coords]
        top_pts = [cam.project(r + dr, c + dc, 0.08) for dr, dc in oct_coords]
        col = theme.TILE_COLORS["switch_soft"]
        pygame.draw.polygon(surface, shade(col, 0.55), base_pts)
        pygame.draw.polygon(surface, col, top_pts)
        pygame.draw.polygon(surface, (220, 230, 245), top_pts, 2)
    elif tile is Tile.HEAVY_SWITCH:
        col = theme.TILE_COLORS["switch_heavy"]
        # Raised 3D X bars with vertical thickness
        for z_h, bar_col, w in ((0.0, shade(col, 0.55), 7), (0.05, col, 5)):
            p1 = cam.project(r + 0.20, c + 0.20, z_h)
            p2 = cam.project(r + 0.80, c + 0.80, z_h)
            p3 = cam.project(r + 0.20, c + 0.80, z_h)
            p4 = cam.project(r + 0.80, c + 0.20, z_h)
            pygame.draw.line(surface, bar_col, p1, p2, w)
            pygame.draw.line(surface, bar_col, p3, p4, w)
    elif tile is Tile.SPLIT_SWITCH:
        pad = 0.22
        draw_prism(
            surface,
            cam,
            r + pad,
            r + 1.0 - pad,
            c + pad,
            c + 1.0 - pad,
            0.0,
            0.08,
            theme.TILE_COLORS["switch_split"],
            (225, 242, 255),
            edge_width=1,
        )
        left_br = [
            cam.project(r + 0.32, c + 0.42, 0.085),
            cam.project(r + 0.50, c + 0.30, 0.085),
            cam.project(r + 0.68, c + 0.42, 0.085),
        ]
        right_br = [
            cam.project(r + 0.32, c + 0.58, 0.085),
            cam.project(r + 0.50, c + 0.70, 0.085),
            cam.project(r + 0.68, c + 0.58, 0.085),
        ]
        pygame.draw.lines(surface, (240, 248, 255), False, left_br, 2)
        pygame.draw.lines(surface, (240, 248, 255), False, right_br, 2)


def draw_state_pieces(
    surface: pygame.Surface,
    cam: Camera3D,
    state: State,
    transition: MoveTransition | None = None,
) -> None:
    """Draw the 3D 1x1x2 rectangular block or the two split 1x1x1 cubes (with 3D animation)."""
    render_state = transition.start_state if transition is not None else state
    action = transition.action if transition is not None else None
    progress = transition.progress if transition is not None else 0.0
    z_offset = transition.z_offset if transition is not None else 0.0

    eased = 1.0 - (1.0 - progress) ** 2
    theta = (
        eased * (math.pi / 2.0)
        if action in (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT)
        else 0.0
    )

    pad = 0.06
    if not render_state.is_split:
        assert render_state.block is not None
        r, c = render_state.block.row, render_state.block.col
        ori = render_state.block.orientation

        if ori is Orientation.STANDING:
            r0, r1 = r + pad, r + 1.0 - pad
            c0, c1 = c + pad, c + 1.0 - pad
            z0, z1 = 0.0, 2.0 - pad
            pivot_bounds = (float(r), float(r + 1), float(c), float(c + 1))
            base_col = theme.BLOCK_STANDING_COLOR
            seams = [
                ((r1, c0, 1.0), (r1, c1, 1.0), (1.0, 0.0, 0.0)),
                ((r0, c0, 1.0), (r0, c1, 1.0), (-1.0, 0.0, 0.0)),
                ((r0, c1, 1.0), (r1, c1, 1.0), (0.0, 1.0, 0.0)),
                ((r0, c0, 1.0), (r1, c0, 1.0), (0.0, -1.0, 0.0)),
            ]
        elif ori is Orientation.HORIZONTAL:
            r0, r1 = r + pad, r + 1.0 - pad
            c0, c1 = c + pad, c + 2.0 - pad
            z0, z1 = 0.0, 1.0 - pad
            pivot_bounds = (float(r), float(r + 1), float(c), float(c + 2))
            base_col = theme.BLOCK_LYING_COLOR
            mid_c = c + 1.0
            seams = [
                ((r0, mid_c, z1), (r1, mid_c, z1), (0.0, 0.0, 1.0)),
                ((r0, mid_c, z0), (r1, mid_c, z0), (0.0, 0.0, -1.0)),
                ((r1, mid_c, z0), (r1, mid_c, z1), (1.0, 0.0, 0.0)),
                ((r0, mid_c, z0), (r0, mid_c, z1), (-1.0, 0.0, 0.0)),
            ]
        else:
            r0, r1 = r + pad, r + 2.0 - pad
            c0, c1 = c + pad, c + 1.0 - pad
            z0, z1 = 0.0, 1.0 - pad
            pivot_bounds = (float(r), float(r + 2), float(c), float(c + 1))
            base_col = theme.BLOCK_LYING_COLOR
            mid_r = r + 1.0
            seams = [
                ((mid_r, c0, z1), (mid_r, c1, z1), (0.0, 0.0, 1.0)),
                ((mid_r, c0, z0), (mid_r, c1, z0), (0.0, 0.0, -1.0)),
                ((mid_r, c1, z0), (mid_r, c1, z1), (0.0, 1.0, 0.0)),
                ((mid_r, c0, z0), (mid_r, c0, z1), (0.0, -1.0, 0.0)),
            ]

        is_goal_sink = (
            transition is not None
            and transition.action is None
            and transition.z_offset < 0.0
            and render_state.is_standing
        )
        draw_rotated_box(
            surface,
            cam,
            r0,
            r1,
            c0,
            c1,
            z0,
            z1,
            pivot_bounds,
            action,
            theta,
            z_offset,
            base_col,
            theme.BLOCK_EDGE_COLOR,
            seam_segments=seams,
            clip_below_zero=is_goal_sink,
        )
    else:
        assert render_state.cubes is not None
        controlled, other = render_state.cubes
        cubes_with_flag = [(other, False), (controlled, True)]
        cubes_with_flag.sort(key=lambda item: (item[0][0] + item[0][1], item[0][0], item[0][1]))

        t_sec = pygame.time.get_ticks() / 1000.0
        bob = 0.08 * math.sin(t_sec * 5.5)

        for (r, c), is_active in cubes_with_flag:
            base_col = theme.CUBE_ACTIVE_COLOR if is_active else theme.CUBE_INACTIVE_COLOR
            edge_col = theme.CUBE_ACTIVE_EDGE if is_active else theme.CUBE_INACTIVE_EDGE
            cube_action = action if is_active else None
            cube_theta = theta if is_active else 0.0
            cube_z_off = z_offset if is_active else 0.0
            pivot_bounds = (float(r), float(r + 1), float(c), float(c + 1))

            draw_rotated_box(
                surface,
                cam,
                r + pad,
                r + 1.0 - pad,
                c + pad,
                c + 1.0 - pad,
                0.0,
                1.0 - pad,
                pivot_bounds,
                cube_action,
                cube_theta,
                cube_z_off,
                base_col,
                edge_col,
            )
            if is_active and cube_theta == 0.0:
                tip = cam.project(r + 0.5, c + 0.5, 1.25 + bob + cube_z_off)
                top = (tip[0], tip[1] - 12)
                left = (tip[0] - 6, tip[1] - 6)
                right = (tip[0] + 6, tip[1] - 6)
                pygame.draw.polygon(surface, theme.CUBE_ACTIVE_EDGE, [top, right, tip, left])
