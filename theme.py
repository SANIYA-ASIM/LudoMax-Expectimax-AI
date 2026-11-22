"""
theme.py — Warm Wooden Styling, Palettes, and Typography for Ludo Verse
========================================================================
Centralizes color definitions, fonts, sizes, and palettes for both
Light Wood and Dark Wood themes.
"""
import os
from typing import Dict, Any, Tuple
import pygame

# ── Dimensions ─────────────────────────────────────────────────────────────────
GRID_CELL_SIZE = 44
BOARD_GRID_DIM = 15
BOARD_PIXEL_DIM = GRID_CELL_SIZE * BOARD_GRID_DIM  # 660 px
SIDE_PANEL_WIDTH = 340
DEFAULT_WINDOW_WIDTH = BOARD_PIXEL_DIM + SIDE_PANEL_WIDTH  # 1000 px
DEFAULT_WINDOW_HEIGHT = BOARD_PIXEL_DIM                    # 660 px

# ── Asset Paths ────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(_BASE_DIR, 'assets', 'fonts')

FONT_DISPLAY_PATH = os.path.join(FONTS_DIR, 'LilitaOne-Regular.ttf')
FONT_BOLD_PATH = os.path.join(FONTS_DIR, 'Poppins-Bold.ttf')
FONT_REGULAR_PATH = os.path.join(FONTS_DIR, 'Poppins-Regular.ttf')


def load_font(font_path: str, size: int, fallback_names: list = None, bold: bool = False) -> pygame.font.Font:
    """Load bundled TTF font with graceful fallback to system fonts."""
    if not pygame.font.get_init():
        pygame.font.init()

    if font_path and os.path.isfile(font_path):
        try:
            return pygame.font.Font(font_path, size)
        except Exception:
            pass

    # Fallback to matching system fonts without throwing UserWarning
    fallback_candidates = fallback_names or ['arialrounded', 'segoeui', 'trebuchetms', 'arial']
    for name in fallback_candidates:
        matched = pygame.font.match_font(name, bold=bold)
        if matched:
            try:
                return pygame.font.Font(matched, size)
            except Exception:
                continue

    return pygame.font.Font(None, size)


# ── Color Palettes (Light Wood and Dark Wood) ─────────────────────────────────
WOOD_THEMES: Dict[str, Dict[str, Any]] = {
    'light': {
        # Background & Panels
        'bg_primary': (222, 148, 72),          # Warm amber wood base
        'bg_grain': (200, 128, 55),            # Subtle darker grain fiber
        'bg_highlight': (240, 172, 98),        # Gentle sunlit wood sheen
        'panel_bg': (198, 126, 62),            # Carved wooden side panel
        'panel_card_bg': (176, 108, 48),       # Inset wooden card slot
        'panel_card_active': (224, 150, 70),   # Active player glowing slot
        'panel_subcard': (155, 92, 38),        # Deeper carved inset
        'panel_border': (115, 65, 24),         # Dark carved walnut border
        'border_bevel_light': (250, 185, 115), # Top-left light reflection
        'border_bevel_dark': (95, 52, 18),     # Bottom-right carved shadow

        # Board & Track
        'board_frame_outer': (105, 58, 22),    # Deep rich mahogany/walnut frame
        'board_frame_mid': (148, 86, 38),      # Mid oak frame ridge
        'board_frame_inner': (78, 42, 15),     # Deep carved bevel groove
        'board_canvas': (242, 234, 218),       # Warm natural parchment/cream tile bed
        'tile_cream': (252, 246, 235),         # Crisp smooth cream tile face
        'tile_shadow': (220, 210, 192),        # Subtle bevel under tiles
        'tile_border': (185, 172, 150),        # Gentle cream tile separation
        'safe_square_tint': (255, 238, 175),   # Gentle gold tint on star squares
        'star_gold': (255, 195, 15),           # Brilliant 5-point star
        'star_outline': (190, 135, 5),         # Star rim

        # Buttons
        'btn_wood_top': (235, 155, 68),        # Natural polished oak plank top
        'btn_wood_bottom': (182, 105, 38),     # Natural oak gradient bottom
        'btn_wood_hover_top': (255, 178, 88),  # Lifted highlight state
        'btn_wood_hover_bottom': (205, 125, 48),
        'btn_wood_pressed_top': (165, 92, 32), # Depressed/pressed state
        'btn_wood_pressed_bottom': (140, 75, 24),
        'btn_wood_border': (88, 46, 16),       # Deep dark-brown wooden rim
        'btn_wood_inner_rim': (255, 205, 135), # Crisp carved inner highlight
        'btn_text': (255, 255, 255),           # Crisp bold white title
        'btn_text_shadow': (65, 32, 10),       # Carved shadow behind text

        # General Text & UI
        'text_white': (255, 255, 255),
        'text_cream': (255, 243, 214),        # #FFF3D6 High-contrast cream
        'text_dark': (42, 26, 16),
        'text_shadow': (58, 31, 10),          # #3A1F0A Dark-brown outline / shadow
        'text_muted': (255, 243, 214),        # High-contrast cream for subheaders
        'table_row_bg': (35, 18, 8, 75),      # 25-30% semi-transparent dark-brown overlay
        'highlight_gold': (255, 212, 45),
        'gold_border': (215, 158, 22),
        'shadow': (0, 0, 0, 85),
    },
    'dark': {
        # Background & Panels
        'bg_primary': (120, 68, 32),           # Deep roasted chestnut/walnut base
        'bg_grain': (95, 50, 20),              # Deep rich dark grain fibers
        'bg_highlight': (145, 85, 42),         # Subdued warm sheen
        'panel_bg': (105, 58, 26),             # Dark walnut side panel
        'panel_card_bg': (82, 44, 18),         # Deep carved dark card slot
        'panel_card_active': (140, 80, 36),    # Active player glowing slot
        'panel_subcard': (65, 34, 12),         # Darkest recessed niche
        'panel_border': (52, 26, 8),           # Deepest carved border
        'border_bevel_light': (165, 98, 48),   # Bevel highlight
        'border_bevel_dark': (42, 20, 6),      # Bevel shadow

        # Board & Track
        'board_frame_outer': (68, 34, 12),     # Dark mahogany frame
        'board_frame_mid': (96, 52, 22),       # Dark carved ridge
        'board_frame_inner': (46, 22, 8),      # Deep groove
        'board_canvas': (218, 206, 188),       # Vintage antique cream tile bed
        'tile_cream': (236, 226, 210),         # Antique smooth tile face
        'tile_shadow': (195, 182, 164),        # Bevel under tiles
        'tile_border': (158, 142, 124),        # Gentle cream tile separation
        'safe_square_tint': (235, 210, 145),   # Golden antique tint
        'star_gold': (245, 185, 20),           # Warm star
        'star_outline': (160, 110, 8),

        # Buttons
        'btn_wood_top': (155, 92, 42),         # Polished dark oak plank top
        'btn_wood_bottom': (112, 60, 24),      # Dark oak gradient bottom
        'btn_wood_hover_top': (180, 110, 52),  # Brighter hover
        'btn_wood_hover_bottom': (132, 72, 30),
        'btn_wood_pressed_top': (100, 50, 18), # Depressed/pressed state
        'btn_wood_pressed_bottom': (80, 38, 14),
        'btn_wood_border': (48, 22, 6),        # Very dark brown rim
        'btn_wood_inner_rim': (210, 140, 75),  # Inner warm highlight
        'btn_text': (255, 255, 255),
        'btn_text_shadow': (35, 15, 4),

        # General Text & UI
        'text_white': (255, 255, 255),
        'text_cream': (255, 243, 214),        # #FFF3D6 High-contrast cream
        'text_dark': (35, 18, 6),
        'text_shadow': (35, 18, 6),           # #231206 Dark-brown outline / shadow
        'text_muted': (255, 243, 214),        # High-contrast cream for subheaders
        'table_row_bg': (20, 10, 4, 90),       # 25-30% semi-transparent dark-brown overlay
        'highlight_gold': (255, 205, 45),
        'gold_border': (190, 140, 18),
        'shadow': (0, 0, 0, 110),
    }
}

# ── Player Base Colors & Gradients (Rich Glossy Ludo Colors) ──────────────────
# Green, Yellow, Red, Blue matching reference vertical gradients & jewel pawns
PLAYER_THEMES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    'green': {
        'base_top': (88, 210, 75),
        'base_bottom': (42, 155, 38),
        'base_border': (24, 105, 22),
        'base_inner_rim': (145, 235, 135),
        'slot_fill': (22, 95, 20),
        'slot_shadow': (14, 65, 12),
        'pawn_main': (52, 188, 48),
        'pawn_highlight': (175, 255, 160),
        'pawn_rim': (210, 165, 45),
        'home_lane': (110, 215, 95),
        'triangle': (58, 182, 45),
    },
    'yellow': {
        'base_top': (255, 226, 45),
        'base_bottom': (235, 175, 15),
        'base_border': (165, 115, 8),
        'base_inner_rim': (255, 245, 140),
        'slot_fill': (155, 105, 10),
        'slot_shadow': (110, 75, 6),
        'pawn_main': (255, 205, 20),
        'pawn_highlight': (255, 252, 185),
        'pawn_rim': (180, 125, 20),
        'home_lane': (255, 228, 90),
        'triangle': (245, 195, 20),
    },
    'red': {
        'base_top': (245, 82, 88),
        'base_bottom': (195, 36, 48),
        'base_border': (130, 20, 28),
        'base_inner_rim': (255, 155, 160),
        'slot_fill': (120, 18, 26),
        'slot_shadow': (80, 10, 16),
        'pawn_main': (225, 48, 58),
        'pawn_highlight': (255, 175, 180),
        'pawn_rim': (220, 165, 45),
        'home_lane': (255, 125, 130),
        'triangle': (220, 45, 55),
    },
    'blue': {
        'base_top': (68, 152, 248),
        'base_bottom': (28, 98, 210),
        'base_border': (16, 62, 145),
        'base_inner_rim': (145, 198, 255),
        'slot_fill': (18, 55, 135),
        'slot_shadow': (10, 35, 90),
        'pawn_main': (42, 125, 235),
        'pawn_highlight': (170, 218, 255),
        'pawn_rim': (215, 170, 50),
        'home_lane': (125, 180, 255),
        'triangle': (35, 115, 225),
    },
}

# Compatibility lookup
PLAYER_ACCENTS = {
    'yellow': PLAYER_THEMES['yellow']['pawn_main'],
    'blue':   PLAYER_THEMES['blue']['pawn_main'],
    'red':    PLAYER_THEMES['red']['pawn_main'],
    'green':  PLAYER_THEMES['green']['pawn_main'],
}

# ── Speed Profiles (Exact Pacing Targets in Seconds) ──────────────────────────
# Slow:   dice roll 1.8 | result hold 1.0 | AI think delay 1.0 | hop per tile 0.35 | pause between turns 1.2 | capture animation 0.9
# Normal: dice roll 0.9 | result hold 0.5 | AI think delay 0.5 | hop per tile 0.18 | pause between turns 0.5 | capture animation 0.5
# Fast:   dice roll 0.45 | result hold 0.2 | AI think delay 0.15 | hop per tile 0.08 | pause between turns 0.15 | capture animation 0.25

SPEED_PROFILES: Dict[str, Dict[str, float]] = {
    'slow': {
        'label': 'Slow',
        'dice_roll': 1.8,
        'result_hold': 1.0,
        'ai_think': 1.0,
        'hop_per_tile': 0.35,
        'pause_turn': 1.2,
        'capture_anim': 0.9,
    },
    'normal': {
        'label': 'Normal',
        'dice_roll': 0.9,
        'result_hold': 0.5,
        'ai_think': 0.5,
        'hop_per_tile': 0.18,
        'pause_turn': 0.5,
        'capture_anim': 0.5,
    },
    'fast': {
        'label': 'Fast',
        'dice_roll': 0.45,
        'result_hold': 0.2,
        'ai_think': 0.15,
        'hop_per_tile': 0.08,
        'pause_turn': 0.15,
        'capture_anim': 0.25,
    },
}

# ── 3D Realistic Dice Aesthetics ──────────────────────────────────────────────
DICE_THEME: Dict[str, Any] = {
    'face_top':          (255, 251, 242),  # #FFFBF2 Pristine bright ivory front
    'face_side_top':     (255, 248, 231),  # #FFF8E7 Warm ivory top sliver
    'face_side_right':   (242, 232, 208),  # #F2E8D0 Soft warm right sliver (>=85% brightness)
    'edge_bevel':        (255, 255, 255),  # Crisp highlight bevel
    'edge_dark':         (101, 59, 24),    # Thin brown outline (1-2px)
    'pip_dark':          (42, 26, 16),     # #2A1A10 Near-black dimple
    'pip_red':           (225, 42, 42),    # Red pip for 1
    'pip_mid':           (70, 48, 32),     # Dimple radial shadow
    'pip_rim_highlight': (255, 255, 255),  # Lower edge specular reflection
    'shadow':            (45, 25, 10),     # Small subtle semi-transparent brown (20-25% opacity)
}
