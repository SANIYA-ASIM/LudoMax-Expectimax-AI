"""
ui_utils.py — Reusable Drawing Helpers and Procedural Wood Rendering for Ludo Verse
==================================================================================
Provides fast, pre-renderable wooden UI components, textured planks,
carved buttons, outlined typography, and glossy cabochon pawns.
"""
import math
import random
from typing import Tuple, List, Optional
import pygame

from theme import WOOD_THEMES, PLAYER_THEMES, FONT_DISPLAY_PATH, FONT_BOLD_PATH, load_font

# ── Surface Texture Cache ──────────────────────────────────────────────────────
_TEXTURE_CACHE = {}


def generate_wood_texture(width: int, height: int, is_dark_wood: bool = False) -> pygame.Surface:
    """Procedurally generate warm organic wood-grain texture with grain lines & vignette."""
    cache_key = (width, height, is_dark_wood)
    if cache_key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[cache_key]

    surf = pygame.Surface((width, height))
    palette = WOOD_THEMES['dark' if is_dark_wood else 'light']
    base_col = palette['bg_primary']
    grain_col = palette['bg_grain']
    highlight_col = palette['bg_highlight']

    surf.fill(base_col)

    # 1. Subtle horizontal tonal bands (wood growth layers)
    rng = random.Random(42)  # Deterministic seed for reproducible warm grain
    band_h = 32
    for y in range(0, height, band_h):
        variance = rng.randint(-12, 12)
        band_col = (
            max(0, min(255, base_col[0] + variance)),
            max(0, min(255, base_col[1] + variance // 2)),
            max(0, min(255, base_col[2] + variance // 3)),
        )
        band_surf = pygame.Surface((width, band_h), pygame.SRCALPHA)
        band_surf.fill((*band_col, 50))
        surf.blit(band_surf, (0, y))

    # 2. Organic wavy grain lines running horizontally
    grain_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    num_strands = int(height * 0.45)
    for _ in range(num_strands):
        gy = rng.randint(0, height)
        alpha = rng.randint(25, 60)
        c = grain_col if rng.random() > 0.3 else highlight_col
        # Sine-perturbed horizontal strand
        freq = rng.uniform(0.003, 0.008)
        phase = rng.uniform(0, math.pi * 2)
        amp = rng.uniform(3, 10)
        thickness = rng.choice([1, 1, 2])

        points = []
        for x in range(0, width + 20, 20):
            ny = gy + amp * math.sin(x * freq + phase)
            points.append((x, ny))

        if len(points) >= 2:
            pygame.draw.lines(grain_surf, (*c, alpha), False, points, thickness)

    # 3. Soft wooden plank grooves across width
    for sep_y in [height // 4, height // 2, 3 * height // 4]:
        pygame.draw.line(grain_surf, (30, 15, 5, 50), (0, sep_y), (width, sep_y), 2)
        pygame.draw.line(grain_surf, (255, 230, 190, 45), (0, sep_y + 1), (width, sep_y + 1), 1)

    surf.blit(grain_surf, (0, 0))

    # 4. Subtle Radial Vignette
    vignette = pygame.Surface((width, height), pygame.SRCALPHA)
    cx, cy = width / 2, height / 2
    max_dist = math.hypot(cx, cy)
    for r_step in range(8):
        fraction = (r_step + 1) / 8.0
        r = max_dist * fraction
        alpha = int(45 * (fraction ** 2))
        pygame.draw.rect(vignette, (15, 8, 2, alpha), (0, 0, width, height))

    surf.blit(vignette, (0, 0))

    try:
        final_surf = surf.convert()
    except Exception:
        final_surf = surf

    _TEXTURE_CACHE[cache_key] = final_surf
    return final_surf


# ── Gradient & Shadow Helpers ──────────────────────────────────────────────────

def draw_gradient_rect(surface: pygame.Surface, rect: pygame.Rect,
                       top_color: Tuple[int, int, int], bottom_color: Tuple[int, int, int],
                       border_radius: int = 0):
    """Draw smooth vertical gradient rectangle with optional rounded corners."""
    w, h = rect.width, rect.height
    if w <= 0 or h <= 0:
        return
    grad_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    r1, g1, b1 = top_color
    r2, g2, b2 = bottom_color
    for y in range(h):
        t = y / max(1, h - 1)
        c = (
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
            255
        )
        pygame.draw.line(grad_surf, c, (0, y), (w, y))

    if border_radius > 0:
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=border_radius)
        grad_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    surface.blit(grad_surf, rect.topleft)


def draw_shadow(surface: pygame.Surface, rect: pygame.Rect,
                blur_radius: int = 6, alpha: int = 80,
                offset: Tuple[int, int] = (0, 4), border_radius: int = 10):
    """Draw a soft drop shadow beneath UI elements."""
    w = rect.width + blur_radius * 2
    h = rect.height + blur_radius * 2
    if w <= 0 or h <= 0:
        return
    sh_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    sh_rect = pygame.Rect(blur_radius + offset[0], blur_radius + offset[1], rect.width, rect.height)
    pygame.draw.rect(sh_surf, (0, 0, 0, alpha), sh_rect, border_radius=border_radius)
    surface.blit(sh_surf, (rect.x - blur_radius, rect.y - blur_radius))


# ── Outlined Typography ────────────────────────────────────────────────────────

def draw_outlined_text(surface: pygame.Surface, text: str, font: pygame.font.Font,
                       fill_color: Tuple[int, int, int], outline_color: Tuple[int, int, int],
                       outline_width: int, center_or_pos: Tuple[int, int],
                       is_centered: bool = True, shadow_offset: Tuple[int, int] = (0, 3),
                       shadow_color: Optional[Tuple[int, int, int]] = (30, 15, 5)) -> pygame.Rect:
    """Render high-contrast text with crisp multi-pixel outline and soft shadow."""
    # 1. Text shadow
    if shadow_color and shadow_offset != (0, 0):
        sh_surf = font.render(text, True, shadow_color)
        if is_centered:
            sh_x = center_or_pos[0] - sh_surf.get_width() // 2 + shadow_offset[0]
            sh_y = center_or_pos[1] - sh_surf.get_height() // 2 + shadow_offset[1]
        else:
            sh_x = center_or_pos[0] + shadow_offset[0]
            sh_y = center_or_pos[1] + shadow_offset[1]
        surface.blit(sh_surf, (sh_x, sh_y))

    # 2. Outline ring
    if outline_width > 0:
        out_surf = font.render(text, True, outline_color)
        offsets = []
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx * dx + dy * dy <= outline_width * outline_width:
                    offsets.append((dx, dy))

        for dx, dy in offsets:
            if is_centered:
                ox = center_or_pos[0] - out_surf.get_width() // 2 + dx
                oy = center_or_pos[1] - out_surf.get_height() // 2 + dy
            else:
                ox = center_or_pos[0] + dx
                oy = center_or_pos[1] + dy
            surface.blit(out_surf, (ox, oy))

    # 3. Main face
    face_surf = font.render(text, True, fill_color)
    if is_centered:
        fx = center_or_pos[0] - face_surf.get_width() // 2
        fy = center_or_pos[1] - face_surf.get_height() // 2
    else:
        fx = center_or_pos[0]
        fy = center_or_pos[1]
    surface.blit(face_surf, (fx, fy))
    return pygame.Rect(fx, fy, face_surf.get_width(), face_surf.get_height())


# ── Wooden Plank & Button Helpers ──────────────────────────────────────────────

def draw_wood_plank(surface: pygame.Surface, rect: pygame.Rect,
                    is_dark: bool = False, border_radius: int = 12,
                    show_nail_rivets: bool = True):
    """Draw a carved wooden plank with beveled rims and subtle wood grain."""
    palette = WOOD_THEMES['dark' if is_dark else 'light']

    # Drop shadow
    draw_shadow(surface, rect, blur_radius=6, alpha=90, offset=(0, 5), border_radius=border_radius)

    # Main wooden body with vertical lighting gradient
    top_c = palette['btn_wood_top']
    bot_c = palette['btn_wood_bottom']
    draw_gradient_rect(surface, rect, top_c, bot_c, border_radius=border_radius)

    # Carved border rim
    border_col = palette['btn_wood_border']
    pygame.draw.rect(surface, border_col, rect, width=3, border_radius=border_radius)

    # Inner bevel highlight
    inner_rect = rect.inflate(-4, -4)
    if inner_rect.width > 0 and inner_rect.height > 0:
        pygame.draw.rect(surface, palette['btn_wood_inner_rim'], inner_rect, width=1, border_radius=max(0, border_radius - 2))

    # Optional decorative nail rivets at edges
    if show_nail_rivets and rect.width > 80 and rect.height > 24:
        for nx, ny in [(rect.left + 14, rect.centery), (rect.right - 14, rect.centery)]:
            pygame.draw.circle(surface, (50, 25, 8), (nx, ny + 1), 4)
            pygame.draw.circle(surface, (215, 175, 75), (nx, ny), 4)
            pygame.draw.circle(surface, (255, 245, 180), (nx - 1, ny - 1), 1)


def draw_wood_button(surface: pygame.Surface, rect: pygame.Rect, title: str,
                     font: pygame.font.Font, state: str = 'normal',
                     is_dark: bool = False, is_primary: bool = True) -> pygame.Rect:
    """Draw an interactive wooden plank button with hover lift and press displacement."""
    palette = WOOD_THEMES['dark' if is_dark else 'light']

    # Apply 2px down displacement when pressed
    y_offset = 2 if state == 'pressed' else (-2 if state == 'hover' else 0)
    btn_rect = rect.copy()
    btn_rect.y += y_offset

    # Determine gradient colors based on state
    if state == 'pressed':
        top_c = palette['btn_wood_pressed_top']
        bot_c = palette['btn_wood_pressed_bottom']
        sh_alpha = 40
        sh_offset = (0, 2)
    elif state == 'hover':
        top_c = palette['btn_wood_hover_top']
        bot_c = palette['btn_wood_hover_bottom']
        sh_alpha = 110
        sh_offset = (0, 6)
    else:
        top_c = palette['btn_wood_top']
        bot_c = palette['btn_wood_bottom']
        sh_alpha = 80
        sh_offset = (0, 4)

    # 1. Soft Drop Shadow
    draw_shadow(surface, btn_rect, blur_radius=6, alpha=sh_alpha, offset=sh_offset, border_radius=10)

    # 2. Main Wooden Body Gradient
    draw_gradient_rect(surface, btn_rect, top_c, bot_c, border_radius=10)

    # 3. Horizontal Wood Fiber Accents inside button
    mid_y = btn_rect.y + btn_rect.height // 2
    pygame.draw.line(surface, (*palette['btn_wood_border'], 60), (btn_rect.x + 8, mid_y), (btn_rect.right - 8, mid_y), 1)

    # 4. Carved Dark Wooden Border
    border_col = (255, 215, 45) if state == 'hover' else palette['btn_wood_border']
    border_w = 3 if state == 'hover' else 2
    pygame.draw.rect(surface, border_col, btn_rect, width=border_w, border_radius=10)

    # 5. Inner Highlight Bevel
    inner = btn_rect.inflate(-4, -4)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.rect(surface, palette['btn_wood_inner_rim'], inner, width=1, border_radius=8)

    # 6. Button Title (Clean bold white text with dark carved drop shadow; NO subtitles)
    draw_outlined_text(
        surface, text=title, font=font,
        fill_color=(255, 255, 255),
        outline_color=(55, 25, 8),
        outline_width=2,
        center_or_pos=(btn_rect.centerx, btn_rect.centery),
        is_centered=True,
        shadow_offset=(0, 2),
        shadow_color=(35, 15, 5)
    )

    return btn_rect


# ── Logo Banner ("Ludo Verse" on Carved Wooden Plank) ─────────────────────────

def draw_logo_plank(surface: pygame.Surface, cx: int, cy: int, is_dark: bool = False,
                    banner_w: int = 500, banner_h: int = 118):
    """Draw the brand logo: 'Ludo Verse' in chunky, rounded, glossy orange-yellow letters
    sitting on an enlarged carved wooden plank banner with 4-color gem accents.
    """
    banner_rect = pygame.Rect(cx - banner_w // 2, cy - banner_h // 2, banner_w, banner_h)

    # 1. Carved Wooden Plank Banner with nail rivets & bevel
    draw_wood_plank(surface, banner_rect, is_dark=is_dark, border_radius=16, show_nail_rivets=True)

    # Decorative inner gold border inlay
    inlay_rect = banner_rect.inflate(-12, -12)
    inlay_gold = (215, 160, 45, 120) if not is_dark else (175, 125, 35, 100)
    inlay_surf = pygame.Surface((inlay_rect.width, inlay_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(inlay_surf, inlay_gold, (0, 0, inlay_rect.width, inlay_rect.height), width=2, border_radius=12)
    surface.blit(inlay_surf, inlay_rect.topleft)

    # 2. Four Decorative Ludo Gem Dots (Yellow, Blue, Red, Green)
    dots_x = banner_rect.left + 32
    dot_colors = [
        PLAYER_THEMES['yellow']['pawn_main'],
        PLAYER_THEMES['blue']['pawn_main'],
        PLAYER_THEMES['red']['pawn_main'],
        PLAYER_THEMES['green']['pawn_main']
    ]
    for i, col in enumerate(dot_colors):
        dy = banner_rect.centery - 27 + i * 18
        pygame.draw.circle(surface, (40, 20, 5), (dots_x, dy + 2), 6)
        pygame.draw.circle(surface, (255, 215, 0), (dots_x, dy), 6)
        pygame.draw.circle(surface, col, (dots_x, dy), 5)
        pygame.draw.circle(surface, (255, 255, 255), (dots_x - 1, dy - 1), 2)

    dots_r_x = banner_rect.right - 32
    for i, col in enumerate(dot_colors[::-1]):
        dy = banner_rect.centery - 27 + i * 18
        pygame.draw.circle(surface, (40, 20, 5), (dots_r_x, dy + 2), 6)
        pygame.draw.circle(surface, (255, 215, 0), (dots_r_x, dy), 6)
        pygame.draw.circle(surface, col, (dots_r_x, dy), 5)
        pygame.draw.circle(surface, (255, 255, 255), (dots_r_x - 1, dy - 1), 2)

    # 3. Chunky Glossy "Ludo Verse" Lettering
    logo_font = load_font(FONT_DISPLAY_PATH, 54, ['Lilita One', 'Fredoka One', 'Arial Rounded MT Bold'], bold=True)
    text = "Ludo Verse"

    # Multi-layer outlined rendering:
    # Layer A: Dark Blue Shadow Outline
    dark_blue_outline = (12, 38, 92)
    draw_outlined_text(
        surface, text=text, font=logo_font,
        fill_color=(255, 215, 25),      # Golden Yellow Center
        outline_color=dark_blue_outline,
        outline_width=5,
        center_or_pos=(cx, cy - 3),
        is_centered=True,
        shadow_offset=(0, 5),
        shadow_color=(25, 12, 4)
    )

    # Layer B: Inner Orange-to-Yellow Gloss Reflection
    inner_font = load_font(FONT_DISPLAY_PATH, 52, ['Lilita One', 'Fredoka One', 'Arial Rounded MT Bold'], bold=True)
    draw_outlined_text(
        surface, text=text, font=inner_font,
        fill_color=(255, 240, 110),
        outline_color=(235, 110, 15),    # Vibrant Orange Inner Rim
        outline_width=1,
        center_or_pos=(cx, cy - 4),
        is_centered=True,
        shadow_offset=(0, 0),
        shadow_color=None
    )


# ── Glossy Cabochon Tokens (Pawns) ────────────────────────────────────────────

def draw_glossy_pawn(surface: pygame.Surface, cx: int, cy: int, radius: int,
                     color_key: str, scale: float = 1.0, is_active: bool = False,
                     pulse_offset: float = 0.0, hop_y: float = 0.0):
    """Draw a glossy oval/cabochon jewel token matching reference wooden board style."""
    ptheme = PLAYER_THEMES.get(color_key, PLAYER_THEMES['yellow'])
    r = int(radius * scale)
    cy_pos = int(cy + hop_y)

    # 1. Soft Oval Drop Shadow on the board
    sh_w = int(r * 2.2)
    sh_h = int(r * 1.1)
    sh_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
    # Higher alpha if near board, fading slightly if hopping high
    sh_alpha = max(20, int(90 * max(0.2, 1.0 - abs(hop_y) / 40.0)))
    pygame.draw.ellipse(sh_surf, (20, 10, 4, sh_alpha), (0, 0, sh_w, sh_h))
    surface.blit(sh_surf, (cx - sh_w // 2, cy + int(r * 0.4) - sh_h // 2))

    # 2. Active Pulsing Golden Halo
    if is_active:
        halo_r = int(r + 5 + pulse_offset)
        pygame.draw.circle(surface, (255, 215, 0), (cx, cy_pos), halo_r, 3)

    # 3. Outer Polished Gold / Bronze Metallic Rim
    rim_color = ptheme['pawn_rim']
    pygame.draw.circle(surface, (45, 22, 6), (cx, cy_pos + 2), r + 2)  # Rim bottom shadow
    pygame.draw.circle(surface, rim_color, (cx, cy_pos), r + 2)
    pygame.draw.circle(surface, (255, 235, 140), (cx, cy_pos), r + 2, 1)  # Rim bevel shine

    # 4. Glossy Jewel Token Body Gradient
    body_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    main_c = ptheme['pawn_main']
    top_c = ptheme['pawn_highlight']
    for row in range(r * 2):
        t = row / max(1, r * 2 - 1)
        c = (
            int(top_c[0] * (1 - t) + main_c[0] * t),
            int(top_c[1] * (1 - t) + main_c[1] * t),
            int(top_c[2] * (1 - t) + main_c[2] * t),
        )
        pygame.draw.line(body_surf, c, (0, row), (r * 2, row))

    # Circular mask for token body
    mask = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r)
    body_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(body_surf, (cx - r, cy_pos - r))

    # 5. Inner Crescent Highlight (3D Glass Reflection)
    hl_x = cx - r // 3
    hl_y = cy_pos - r // 3
    hl_r = max(2, r // 3)
    pygame.draw.circle(surface, (255, 255, 255, 220), (hl_x, hl_y), hl_r)
    pygame.draw.circle(surface, (255, 255, 255, 120), (hl_x + 1, hl_y + 1), hl_r + 1)


# ── Realistic 3D Dice Renderer ────────────────────────────────────────────────

def draw_dice_3d(surface: pygame.Surface, cx: int, cy: int, value: int,
                 is_rolling: bool, anim_start: float, anim_duration: float,
                 size: int = 64):
    """Draw a realistic 3D rounded ivory cube with dark pips, tumble physics & shadow."""
    d_size = size
    bounce_y = 0
    if is_rolling:
        import time
        elapsed = time.time() - anim_start
        t = min(1.0, elapsed / max(0.001, anim_duration))
        bounce_y = -int(abs(math.sin(t * 12)) * (1.0 - t) * 16)

    cur_cy = cy + bounce_y

    # Drop shadow
    shadow_rect = pygame.Rect(cx - d_size // 2 + 4, cy + d_size // 2 - 4, d_size - 8, 14)
    shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
    shadow_alpha = max(20, int(75 * (1.0 - abs(bounce_y) / 25)))
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, shadow_alpha), (0, 0, shadow_rect.width, shadow_rect.height))
    surface.blit(shadow_surf, shadow_rect)

    # Main cube body
    cube_rect = pygame.Rect(cx - d_size // 2, cur_cy - d_size // 2, d_size, d_size)
    draw_gradient_rect(surface, cube_rect, (255, 253, 245), (230, 222, 208), border_radius=12)

    # 3D Bevel lighting
    pygame.draw.line(surface, (255, 255, 255), (cube_rect.left + 4, cube_rect.top + 2), (cube_rect.right - 4, cube_rect.top + 2), 2)
    pygame.draw.line(surface, (255, 255, 255), (cube_rect.left + 2, cube_rect.top + 4), (cube_rect.left + 2, cube_rect.bottom - 4), 2)
    pygame.draw.line(surface, (170, 160, 145), (cube_rect.left + 4, cube_rect.bottom - 2), (cube_rect.right - 4, cube_rect.bottom - 2), 2)
    pygame.draw.line(surface, (170, 160, 145), (cube_rect.right - 2, cube_rect.top + 4), (cube_rect.right - 2, cube_rect.bottom - 4), 2)
    pygame.draw.rect(surface, (155, 142, 125), cube_rect, 2, border_radius=12)

    # Dark rounded pips
    pip_color = (40, 25, 12)
    pip_r = 5
    pip_map = {
        1: [(cx, cur_cy)],
        2: [(cx - 15, cur_cy - 15), (cx + 15, cur_cy + 15)],
        3: [(cx - 16, cur_cy - 16), (cx, cur_cy), (cx + 16, cur_cy + 16)],
        4: [(cx - 15, cur_cy - 15), (cx + 15, cur_cy - 15),
            (cx - 15, cur_cy + 15), (cx + 15, cur_cy + 15)],
        5: [(cx - 15, cur_cy - 15), (cx + 15, cur_cy - 15), (cx, cur_cy),
            (cx - 15, cur_cy + 15), (cx + 15, cur_cy + 15)],
        6: [(cx - 15, cur_cy - 16), (cx + 15, cur_cy - 16),
            (cx - 15, cur_cy),      (cx + 15, cur_cy),
            (cx - 15, cur_cy + 16), (cx + 15, cur_cy + 16)]
    }

    pips = pip_map.get(value, pip_map[1])
    for px, py in pips:
        # Indented pip shadow
        pygame.draw.circle(surface, (255, 255, 255), (px, py + 1), pip_r)
        pygame.draw.circle(surface, pip_color, (px, py), pip_r)
        if value == 1:
            # Special radiant red ace dot
            pygame.draw.circle(surface, (225, 45, 45), (px, py), pip_r + 2)
            pygame.draw.circle(surface, (255, 120, 120), (px - 1, py - 1), 2)
        else:
            pygame.draw.circle(surface, (10, 5, 2), (px, py), pip_r - 1)
