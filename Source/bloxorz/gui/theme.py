"""Visual constants, 3D perspective parameters, and color palette for the Bloxorz GUI."""

from __future__ import annotations

WINDOW_WIDTH = 1120
WINDOW_HEIGHT = 720
SIDEBAR_WIDTH = 320
FPS = 60

# Board viewport area (left side of the window)
BOARD_AREA_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH
BOARD_PADDING = 54
MAX_TILE_SCALE = 66.0
MIN_TILE_SCALE = 24.0

# 3D camera basis vectors (before perspective divide):
# +c goes right and slightly down; +r goes down-left toward the viewer; +z goes straight up.
VEC_C: tuple[float, float] = (0.94, 0.22)
VEC_R: tuple[float, float] = (-0.42, 0.72)
VEC_Z: tuple[float, float] = (0.0, -0.88)

# Depth axis vector pointing toward the viewer (+r is primary depth, +c is secondary, +z is up)
DEPTH_VEC: tuple[float, float, float] = (0.78, 0.28, 0.18)
PERSPECTIVE_STRENGTH = 0.032  # Foreshortening per unit of depth

# 3D slab & foundation depths
TILE_THICKNESS = 0.24
FOUNDATION_DEPTH = 0.56  # Deep under-slab stone pillar depth
BRIDGE_THICKNESS = 0.16
ABYSS_SHADOW_Z = -1.35   # Depth of the floating shadow plane below the board

# Colors (R, G, B)
BG_COLOR = (16, 20, 28)
SIDEBAR_BG = (32, 38, 50)
SIDEBAR_BORDER = (52, 62, 80)
PANEL_BG = (26, 31, 42)

TEXT_COLOR = (235, 240, 245)
MUTED_TEXT = (155, 165, 182)
ACCENT_COLOR = (86, 164, 255)
SUCCESS_COLOR = (72, 210, 130)
DANGER_COLOR = (245, 95, 95)
WARNING_COLOR = (245, 185, 70)

TILE_COLORS = {
    "floor": (200, 208, 220),
    "start": (175, 202, 235),
    "fragile": (240, 140, 56),
    "foundation": (72, 82, 102),
    "goal_rim": (164, 176, 194),
    "goal_pit": (10, 13, 20),
    "bridge_open": (118, 192, 138),
    "bridge_closed": (68, 78, 98),
    "border": (48, 56, 70),
    "switch_soft": (62, 72, 90),
    "switch_heavy": (52, 60, 76),
    "switch_split": (88, 155, 245),
}

BLOCK_STANDING_COLOR = (68, 142, 250)
BLOCK_LYING_COLOR = (54, 122, 228)
BLOCK_EDGE_COLOR = (220, 238, 255)
BLOCK_SEAM_COLOR = (34, 82, 165)

CUBE_ACTIVE_COLOR = (78, 158, 255)
CUBE_INACTIVE_COLOR = (52, 108, 196)
CUBE_ACTIVE_EDGE = (255, 222, 75)
CUBE_INACTIVE_EDGE = (175, 195, 220)

# Typography configuration (change font names here to customize the whole UI)
FONT_TITLE_FAMILY = "Bahnschrift, Century Gothic, Trebuchet MS, Verdana"
FONT_BUTTON_FAMILY = "Bahnschrift, Trebuchet MS, Verdana"
FONT_UI_FAMILY = "Bahnschrift, Calibri, Verdana"
FONT_VALUE_FAMILY = "Consolas, Bahnschrift, Lucida Console"

