"""
dice.py — Realistic 3D Tumbling Dice Engine for Ludo Verse
==========================================================
High-contrast, instantly readable 3D dice with:
- Crystal-clear resting pose: result face faces almost straight on (8-12° tilt)
  filling 85-90% of the dice visible area with zero clutter.
- Side slivers show thin 3D beveled edges with NO pips at rest.
- Large, high-contrast dimpled pips: vibrant red pip for 1, near-black #2A1A10 for 2-6.
- Pristine bright ivory faces (#FFFBF2 to #F2E8D0) with high ambient light (no grey faces).
- 3D tumble physics with smooth 0.2s ease-into-rest landing (no snapping).
- Small, soft, semi-transparent dark-brown contact shadow directly under dice.
- Non-obstructive "TAP TO ROLL" bubble placed above the center square.
- Floating result badge callout popping on landing for instant readability.
- Reusable ivory face renderer for sidebar "Last Roll" card.
"""
import math
import time
from typing import Dict, List, Optional, Tuple, Any
import pygame

from theme import DICE_THEME, PLAYER_THEMES


# ──────────────────────────────────────────────────────────────────────────────
# 3D Vector & Matrix Math
# ──────────────────────────────────────────────────────────────────────────────

def rot_mat_x(a: float) -> List[List[float]]:
    c, s = math.cos(a), math.sin(a)
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def rot_mat_y(a: float) -> List[List[float]]:
    c, s = math.cos(a), math.sin(a)
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def rot_mat_z(a: float) -> List[List[float]]:
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def mat_mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mat_vec(M: List[List[float]], v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (
        M[0][0] * v[0] + M[0][1] * v[1] + M[0][2] * v[2],
        M[1][0] * v[0] + M[1][1] * v[1] + M[1][2] * v[2],
        M[2][0] * v[0] + M[2][1] * v[1] + M[2][2] * v[2]
    )


def slerp_matrix(M1: List[List[float]], M2: List[List[float]], t: float) -> List[List[float]]:
    """Linear blend and re-orthonormalize rotation matrices."""
    t = max(0.0, min(1.0, t))
    R = [[M1[i][j] * (1.0 - t) + M2[i][j] * t for j in range(3)] for i in range(3)]
    # Gram-Schmidt orthonormalization
    # Row 0
    l0 = math.hypot(R[0][0], R[0][1], R[0][2]) or 1.0
    r0 = [R[0][0] / l0, R[0][1] / l0, R[0][2] / l0]
    # Row 1
    dot01 = r0[0] * R[1][0] + r0[1] * R[1][1] + r0[2] * R[1][2]
    r1_temp = [R[1][0] - dot01 * r0[0], R[1][1] - dot01 * r0[1], R[1][2] - dot01 * r0[2]]
    l1 = math.hypot(r1_temp[0], r1_temp[1], r1_temp[2]) or 1.0
    r1 = [r1_temp[0] / l1, r1_temp[1] / l1, r1_temp[2] / l1]
    # Row 2 (cross product r0 x r1)
    r2 = [
        r0[1] * r1[2] - r0[2] * r1[1],
        r0[2] * r1[0] - r0[0] * r1[2],
        r0[0] * r1[1] - r0[1] * r1[0]
    ]
    return [r0, r1, r2]


# ──────────────────────────────────────────────────────────────────────────────
# Cube Geometry & Rest Orientation Solver
# ──────────────────────────────────────────────────────────────────────────────

CUBE_VERTICES = [
    (-1.0, -1.0, -1.0),  # 0: back-top-left
    ( 1.0, -1.0, -1.0),  # 1: back-top-right
    ( 1.0,  1.0, -1.0),  # 2: back-bottom-right
    (-1.0,  1.0, -1.0),  # 3: back-bottom-left
    (-1.0, -1.0,  1.0),  # 4: front-top-left
    ( 1.0, -1.0,  1.0),  # 5: front-top-right
    ( 1.0,  1.0,  1.0),  # 6: front-bottom-right
    (-1.0,  1.0,  1.0),  # 7: front-bottom-left
]

# Standard die faces (face_value, vertex_indices, local_normal):
CUBE_FACES = [
    (1, [4, 5, 1, 0], (0.0, -1.0, 0.0)),  # Top face
    (6, [3, 2, 6, 7], (0.0,  1.0, 0.0)),  # Bottom face
    (2, [7, 6, 5, 4], (0.0,  0.0, 1.0)),  # Front face
    (5, [0, 1, 2, 3], (0.0,  0.0, -1.0)), # Back face
    (3, [5, 6, 2, 1], (1.0,  0.0, 0.0)),  # Right face
    (4, [0, 3, 7, 4], (-1.0, 0.0, 0.0)),  # Left face
]

# Base matrices mapping each face to FRONT (+Z)
BASE_ROT_MATS: Dict[int, List[List[float]]] = {
    1: rot_mat_x(-math.pi / 2),
    2: [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    3: rot_mat_y(-math.pi / 2),
    4: rot_mat_y(math.pi / 2),
    5: rot_mat_y(math.pi),
    6: rot_mat_x(math.pi / 2),
}

# Resting tilt: rx=-0.16 (~-9° tilt showing top sliver), ry=0.18 (~10° tilt showing right sliver)
# Result face faces directly at viewer with wz = 0.971, occupying 88% of visible area!
_tilt_x = -0.16
_tilt_y = 0.18
_R_REST_TILT = mat_mul(rot_mat_y(_tilt_y), rot_mat_x(_tilt_x))

REST_ROT_MATS: Dict[int, List[List[float]]] = {
    val: mat_mul(_R_REST_TILT, base_M)
    for val, base_M in BASE_ROT_MATS.items()
}


# ──────────────────────────────────────────────────────────────────────────────
# High-Resolution Dimpled Face Texture Cache
# ──────────────────────────────────────────────────────────────────────────────

class DicePipRenderer:
    """Pre-renders clean, crisp, high-contrast ivory faces with dimpled pips."""

    def __init__(self, resolution: int = 160):
        self.res = resolution
        self._cache: Dict[int, pygame.Surface] = {}
        self._generate_face_textures()

    def _draw_dimple_pip(self, surf: pygame.Surface, cx: float, cy: float, radius: float, is_red: bool = False):
        """Draw prominent dimple pip with radial shading and crisp specular reflection."""
        r = int(radius)
        ix, iy = int(cx), int(cy)

        # 1. Subtle top-left socket recess shadow
        if r >= 3:
            socket_shadow = (210, 198, 180)
            pygame.draw.circle(surf, socket_shadow, (ix - 1, iy - 1), r + 1, width=1)

        # 2. Main dimple fill (Red for 1, Near-black #2A1A10 for 2-6)
        main_color = (225, 42, 42) if is_red else (42, 26, 16)
        pygame.draw.circle(surf, main_color, (ix, iy), r)

        # 3. Inner radial depth rim
        if r >= 3:
            rim_color = (180, 25, 25) if is_red else (65, 42, 28)
            pygame.draw.circle(surf, rim_color, (ix, iy), r - 1, width=1)

        # 4. Specular lower-edge arc highlight
        if r >= 3:
            arc_box = pygame.Rect(ix - r + 1, iy - r + 1, (r - 1) * 2, (r - 1) * 2)
            pygame.draw.arc(surf, (255, 255, 255), arc_box, math.pi * 1.15, math.pi * 1.85, width=1)

    def _generate_face_textures(self):
        """Pre-compute the 6 face textures (1 to 6) at high resolution."""
        res = self.res
        pad = res * 0.22
        step = (res - pad * 2) / 2.0
        pip_r = res * 0.088  # ~17.6% of face width

        p_tl = (pad, pad)
        p_tr = (res - pad, pad)
        p_bl = (pad, res - pad)
        p_br = (res - pad, res - pad)
        p_ml = (pad, pad + step)
        p_mr = (res - pad, pad + step)
        p_c  = (res / 2.0, res / 2.0)

        pip_layouts = {
            1: [p_c],
            2: [p_tl, p_br],
            3: [p_tl, p_c, p_br],
            4: [p_tl, p_tr, p_bl, p_br],
            5: [p_tl, p_tr, p_c, p_bl, p_br],
            6: [p_tl, p_tr, p_ml, p_mr, p_bl, p_br],
        }

        for val, pips in pip_layouts.items():
            surf = pygame.Surface((res, res), pygame.SRCALPHA)
            r_box = pygame.Rect(0, 0, res, res)
            # Pristine ivory face (#FFFBF2)
            pygame.draw.rect(surf, (255, 251, 242), r_box, border_radius=int(res * 0.16))

            # Thin brown outline (#653B18)
            pygame.draw.rect(surf, (101, 59, 24), r_box, width=3, border_radius=int(res * 0.16))

            # Inner bevel highlight
            inner_box = r_box.inflate(-int(res * 0.05), -int(res * 0.05))
            pygame.draw.rect(surf, (255, 255, 255), inner_box, width=2, border_radius=int(res * 0.12))

            # Render pips: red for 1 (slightly larger), near-black for 2-6
            is_one = (val == 1)
            cur_r = pip_r * 1.25 if is_one else pip_r
            for px, py in pips:
                self._draw_dimple_pip(surf, px, py, cur_r, is_red=is_one)

            self._cache[val] = surf

    def get_face(self, value: int, target_size: int) -> pygame.Surface:
        """Return cached face surface scaled to target_size."""
        val = max(1, min(6, value))
        base = self._cache.get(val, self._cache[1])
        if base.get_width() == target_size:
            return base
        return pygame.transform.smoothscale(base, (target_size, target_size))


_PIP_RENDERER = DicePipRenderer(resolution=160)


# ──────────────────────────────────────────────────────────────────────────────
# Realistic 3D Dice Object & Physics Controller
# ──────────────────────────────────────────────────────────────────────────────

class RealisticDice:
    """Manages 3D tumble physics, readable resting pose, acoustics, and rendering."""

    def __init__(self):
        self.value: int = 1
        self.rolling: bool = False
        self.start_time: float = 0.0
        self.duration: float = 0.9
        self.tumble_seed_x: float = 0.0
        self.tumble_seed_y: float = 0.0
        self.tumble_seed_z: float = 0.0
        self.last_bounce_phase: int = 0
        self.landed_time: float = 0.0
        self.callout_hold: float = 0.6  # How long result callout badge stays visible

    def roll(self, target_value: int, duration: float = 0.9):
        """Initiate rolling animation with given duration and predetermined outcome."""
        self.value = max(1, min(6, target_value))
        self.rolling = True
        self.start_time = time.time()
        self.duration = max(0.1, duration)
        self.last_bounce_phase = 0
        self.landed_time = 0.0

        import random
        # Random multi-axis tumble speeds
        self.tumble_seed_x = random.choice([3, 4, 5]) * math.pi * 2
        self.tumble_seed_y = random.choice([3, 4, 5]) * math.pi * 2
        self.tumble_seed_z = random.choice([2, 3]) * math.pi * 2

    def get_current_transform(self) -> Tuple[List[List[float]], float, bool]:
        """Compute current (rotation_matrix, height_y, bounce_event)."""
        target_M = REST_ROT_MATS.get(self.value, REST_ROT_MATS[1])

        if not self.rolling:
            # Idle gentle breath
            idle_bob = math.sin(time.time() * 2.5) * 1.0
            return target_M, idle_bob, False

        now = time.time()
        elapsed = now - self.start_time
        t = min(1.0, elapsed / self.duration)

        # ── Physics-based height with 2 decaying bounces ──
        h = 0.0
        bounce_triggered = False

        if t < 0.60:
            sub_t = t / 0.60
            h = math.sin(sub_t * math.pi) * 70.0
            if self.last_bounce_phase == 0 and sub_t > 0.05:
                self.last_bounce_phase = 1
        elif t < 0.86:
            sub_t = (t - 0.60) / 0.26
            h = math.sin(sub_t * math.pi) * 18.0
            if self.last_bounce_phase == 1:
                bounce_triggered = True
                self.last_bounce_phase = 2
        else:
            sub_t = (t - 0.86) / 0.14
            h = math.sin(sub_t * math.pi) * 4.5 * (1.0 - sub_t)
            if self.last_bounce_phase == 2:
                bounce_triggered = True
                self.last_bounce_phase = 3

        # ── Rotation: full 3D tumble, ease into rest pose during last 0.2s ──
        # Tumble matrix based on decaying spin
        spin_decay = (1.0 - t) ** 1.8
        rx = self.tumble_seed_x * spin_decay
        ry = self.tumble_seed_y * spin_decay
        rz = self.tumble_seed_z * spin_decay
        R_tumble = mat_mul(rot_mat_z(rz), mat_mul(rot_mat_y(ry), rot_mat_x(rx)))

        # Settle ease-in window (last 0.2s of duration)
        settle_window = min(0.35, 0.20 / self.duration)
        if t < (1.0 - settle_window):
            cur_M = R_tumble
        else:
            # Smoothly blend from tumble into exact resting matrix
            blend_t = (t - (1.0 - settle_window)) / settle_window
            ease_t = blend_t * blend_t * (3.0 - 2.0 * blend_t)  # smoothstep
            cur_M = slerp_matrix(R_tumble, target_M, ease_t)

        if t >= 1.0:
            self.rolling = False
            cur_M = target_M
            h = 0.0
            self.landed_time = time.time()

        return cur_M, h, bounce_triggered

    def render(self, surface: pygame.Surface, cx: int, cy: int, size: int,
               current_player: str = 'yellow', is_human_turn: bool = False,
               sound_mgr: Any = None):
        """Render complete readable 3D dice at (cx, cy) with high ambient light and clear resting pose."""
        M, height_offset, bounce_hit = self.get_current_transform()

        if bounce_hit and sound_mgr is not None:
            sound_mgr.play('clack')

        die_y = cy - int(height_offset)

        # ── 1. Contact Shadow (small, soft, dark-brown semi-transparent ellipse) ──
        # ~60% of dice width, 20-25% opacity, subtle directly under dice at rest.
        sh_w = int(size * 0.60 * (1.0 + min(0.35, height_offset * 0.005)))
        sh_h = int(size * 0.22 * (1.0 - min(0.25, height_offset * 0.004)))
        sh_alpha = max(18, int(56 - height_offset * 0.7))

        if sh_w > 4 and sh_h > 2:
            shadow_surf = pygame.Surface((sh_w * 2, sh_h * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (45, 25, 10, sh_alpha), (0, 0, sh_w * 2, sh_h * 2))
            surface.blit(shadow_surf, (cx - sh_w, cy + int(size * 0.38) - sh_h // 2))

        # ── 2. Player Turn Glow (when resting on Human Turn) ──
        if is_human_turn and not self.rolling:
            glow_col = PLAYER_THEMES.get(current_player, PLAYER_THEMES['yellow'])['pawn_main']
            glow_pulse = (math.sin(time.time() * 3.5) + 1.0) * 0.5
            glow_r = int(size * 0.62 + glow_pulse * 4.0)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*glow_col, int(45 + glow_pulse * 40)), (glow_r, glow_r), glow_r)
            pygame.draw.circle(glow_surf, (255, 255, 255, int(75 + glow_pulse * 60)), (glow_r, glow_r), int(glow_r * 0.88), width=2)
            surface.blit(glow_surf, (cx - glow_r, die_y - glow_r))

        # ── 3. 3D Cube Vertex Transformation ──
        half_s = size * 0.50
        trans_v = []
        for vx, vy, vz in CUBE_VERTICES:
            lx, ly, lz = vx * half_s, vy * half_s, vz * half_s
            gx, gy, gz = mat_vec(M, (lx, ly, lz))
            # Perspective projection with subtle foreshortening
            proj_scale = 1.0 + (gz / (size * 8.0))
            sx = cx + gx * proj_scale
            sy = die_y + gy * proj_scale
            trans_v.append((sx, sy, gz))

        # ── 4. Face Lighting & Depth Sorting ──
        light_norm = (-0.35, -0.85, 0.40)
        l_len = math.hypot(light_norm[0], light_norm[1], light_norm[2])
        lx, ly, lz = light_norm[0] / l_len, light_norm[1] / l_len, light_norm[2] / l_len

        render_faces = []
        for val, idxs, local_norm in CUBE_FACES:
            wx, wy, wz = mat_vec(M, local_norm)

            # Back-face culling: face points away from camera if wz <= 0.04
            if wz <= 0.04:
                continue

            avg_z = sum(trans_v[i][2] for i in idxs) / 4.0
            pts_2d = [(trans_v[i][0], trans_v[i][1]) for i in idxs]

            # High ambient light: dot factor varies only 0.12, base is 0.88
            # Ensures NO face is darker than 85% of top face (bright pristine ivory, never grey!)
            dot = max(0.0, -(wx * lx + wy * ly + wz * lz))
            shade_factor = 0.88 + 0.12 * dot
            render_faces.append((avg_z, val, pts_2d, wz, wy, shade_factor))

        # Sort back-to-front (Painter's algorithm)
        render_faces.sort(key=lambda item: item[0])

        # ── 5. Draw Faces Back to Front ──
        for _, val, pts, wz, wy, shade in render_faces:
            # Bright ivory color (#FFFBF2 on front/top, #F2E8D0 on side slivers)
            r = min(255, int(DICE_THEME['face_top'][0] * shade))
            g = min(255, int(DICE_THEME['face_top'][1] * shade))
            b = min(255, int(DICE_THEME['face_top'][2] * shade))
            face_col = (r, g, b)

            # Solid ivory face polygon
            pygame.draw.polygon(surface, face_col, pts)

            # Edge bevel highlights on illuminated edges
            bevel_col = (min(255, r + 15), min(255, g + 15), min(255, b + 15))
            pygame.draw.polygon(surface, bevel_col, pts, width=2)

            # Thin brown outline (1-2px, #653B18)
            pygame.draw.polygon(surface, DICE_THEME['edge_dark'], pts, width=1)

            # Specular sheen on top edge catching light
            if wy < -0.25 and shade > 0.92:
                fcx = sum(p[0] for p in pts) / 4.0
                fcy = sum(p[1] for p in pts) / 4.0
                spec_r = max(3, int(size * 0.14))
                spec_surf = pygame.Surface((spec_r * 2, spec_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(spec_surf, (255, 255, 255, 75), (spec_r, spec_r), spec_r)
                surface.blit(spec_surf, (int(fcx - spec_r), int(fcy - spec_r)))

            # Pips rendering rule:
            # - When rolling: visible faces show their pips as normal.
            # - When at rest: ONLY the front result face (val == self.value) carries pips!
            #   The thin top and right side slivers carry NO pips, guaranteeing 100% readability!
            if self.rolling or (val == self.value):
                self._draw_face_pips(surface, val, pts)

        # ── 6. Result Callout Floating Badge (Pops on landing for result-hold duration) ──
        if not self.rolling and self.landed_time > 0:
            callout_elapsed = time.time() - self.landed_time
            if callout_elapsed < self.callout_hold:
                self._render_result_badge(surface, cx, die_y - int(size * 0.58), callout_elapsed)

        # ── 7. "TAP TO ROLL" Bubble (placed ABOVE center square, never covering dice) ──
        if is_human_turn and not self.rolling:
            # Position above center square: cy - 78 px
            self._render_tap_bubble(surface, cx, cy - 78)

    def _draw_face_pips(self, surface: pygame.Surface, val: int, pts: List[Tuple[float, float]]):
        """Draw prominent dimpled pips (16-18% of face width, red for 1, near-black for 2-6)."""
        fcx = sum(p[0] for p in pts) / 4.0
        fcy = sum(p[1] for p in pts) / 4.0

        p0, p1, p2, p3 = pts
        vx = ((p1[0] - p0[0]) + (p2[0] - p3[0])) * 0.25
        vy = ((p1[1] - p0[1]) + (p2[1] - p3[1])) * 0.25
        ux = ((p3[0] - p0[0]) + (p2[0] - p1[0])) * 0.25
        uy = ((p3[1] - p0[1]) + (p2[1] - p1[1])) * 0.25

        # Pip radius: ~17% of face width
        face_diag = math.hypot(p2[0] - p0[0], p2[1] - p0[1])
        pip_radius = max(3.0, min(6.5, face_diag * 0.082))
        pr = int(pip_radius)

        pips_map = {
            1: [(0.0, 0.0)],
            2: [(-0.52, -0.52), (0.52, 0.52)],
            3: [(-0.55, -0.55), (0.0, 0.0), (0.55, 0.55)],
            4: [(-0.52, -0.52), (0.52, -0.52), (-0.52, 0.52), (0.52, 0.52)],
            5: [(-0.54, -0.54), (0.54, -0.54), (0.0, 0.0), (-0.54, 0.54), (0.54, 0.54)],
            6: [(-0.52, -0.56), (0.52, -0.56), (-0.52, 0.0), (0.52, 0.0), (-0.52, 0.56), (0.52, 0.56)],
        }

        pips = pips_map.get(val, [(0.0, 0.0)])
        is_one = (val == 1)
        cur_pr = int(pr * 1.25) if is_one else pr
        main_col = DICE_THEME['pip_red'] if is_one else DICE_THEME['pip_dark']

        for nx, ny in pips:
            spx = fcx + nx * vx + ny * ux
            spy = fcy + nx * vy + ny * uy
            ipx, ipy = int(spx), int(spy)

            # 1. Socket indent shadow
            pygame.draw.circle(surface, (200, 185, 168), (ipx - 1, ipy - 1), cur_pr + 1, width=1)

            # 2. Main dimple fill
            pygame.draw.circle(surface, main_col, (ipx, ipy), cur_pr)

            # 3. Inner radial depth rim
            rim_col = (185, 28, 28) if is_one else DICE_THEME['pip_mid']
            pygame.draw.circle(surface, rim_col, (ipx, ipy), max(1, cur_pr - 1), width=1)

            # 4. Specular lower-edge arc highlight
            if cur_pr >= 3:
                arc_box = pygame.Rect(ipx - cur_pr + 1, ipy - cur_pr + 1, (cur_pr - 1) * 2, (cur_pr - 1) * 2)
                pygame.draw.arc(surface, (255, 255, 255), arc_box, math.pi * 1.15, math.pi * 1.85, width=1)

    def _render_result_badge(self, surface: pygame.Surface, cx: int, top_y: int, elapsed: float):
        """Floating wooden pill badge displaying the large bold result number on landing."""
        # Gentle spring pop scale: 0.0 to 1.0 with overshoot
        t_norm = min(1.0, elapsed / 0.15)
        scale = 1.0 + math.sin(t_norm * math.pi) * 0.20

        # Fade out near end of callout
        alpha = 255
        if elapsed > (self.callout_hold - 0.20):
            alpha = max(0, int(255 * (self.callout_hold - elapsed) / 0.20))

        bw, bh = int(36 * scale), int(32 * scale)
        badge_rect = pygame.Rect(cx - bw // 2, int(top_y - bh), bw, bh)

        badge_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        # Dark wooden carved background
        pygame.draw.rect(badge_surf, (55, 28, 10, alpha), (0, 0, bw, bh), border_radius=bh // 2)
        # Brilliant gold border
        pygame.draw.rect(badge_surf, (255, 215, 25, alpha), (0, 0, bw, bh), width=2, border_radius=bh // 2)

        # Large bold white number
        font = pygame.font.SysFont('segoeui', max(12, int(20 * scale)), bold=True)
        num_col = (255, 45, 45) if self.value == 1 else (255, 255, 255)
        txt = font.render(str(self.value), True, num_col)
        badge_surf.blit(txt, (bw // 2 - txt.get_width() // 2, bh // 2 - txt.get_height() // 2 - 1))

        surface.blit(badge_surf, badge_rect.topleft)

    def _render_tap_bubble(self, surface: pygame.Surface, cx: int, top_y: int):
        """Compact floating wooden 'TAP TO ROLL' speech bubble placed cleanly ABOVE center square."""
        float_y = int(math.sin(time.time() * 3.5) * 2.0)
        by = top_y + float_y

        bw, bh = 84, 22
        bx = cx - bw // 2
        bubble_rect = pygame.Rect(bx, by - bh, bw, bh)

        # Bubble body
        pygame.draw.rect(surface, (55, 28, 10), bubble_rect, border_radius=11)
        pygame.draw.rect(surface, (255, 215, 25), bubble_rect, width=1, border_radius=11)

        # Pointer arrow pointing down towards center square
        tri_pts = [(cx - 5, by), (cx + 5, by), (cx, by + 5)]
        pygame.draw.polygon(surface, (55, 28, 10), tri_pts)
        pygame.draw.polygon(surface, (255, 215, 25), tri_pts, width=1)

        # Text: high-contrast gold on dark wood
        font = pygame.font.SysFont('segoeui', 11, bold=True)
        txt = font.render("TAP TO ROLL", True, (255, 215, 25))
        surface.blit(txt, (bubble_rect.centerx - txt.get_width() // 2,
                           bubble_rect.centery - txt.get_height() // 2))


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar "Last Roll" Compact Tile
# ──────────────────────────────────────────────────────────────────────────────

def render_last_roll_tile(surface: pygame.Surface, rect: pygame.Rect,
                          value: int, player_color: str, is_dark: bool = False):
    """Render compact high-contrast wooden card in sidebar showing '<Player> Rolled' and dice face."""
    bg_col = (135, 75, 28) if not is_dark else (62, 32, 14)
    border_col = (88, 46, 16) if not is_dark else (35, 18, 6)
    pygame.draw.rect(surface, bg_col, rect, border_radius=8)
    pygame.draw.rect(surface, border_col, rect, 1, border_radius=8)

    # Dice thumbnail at left
    die_size = int(rect.height * 0.72)
    die_x = rect.x + 14
    die_y = rect.centery - die_size // 2
    face_surf = _PIP_RENDERER.get_face(value, die_size)
    surface.blit(face_surf, (die_x, die_y))

    # High-contrast text: Player name in pure white #FFFFFF, Result in cream #FFF3D6 with dark shadow
    plr_name = player_color.capitalize()
    font_main = pygame.font.SysFont('segoeui', 14, bold=True)
    font_sub = pygame.font.SysFont('segoeui', 13, bold=True)

    # Shadow
    sh_col = (42, 20, 8)
    sh_main = font_main.render(f"{plr_name} Rolled", True, sh_col)
    sh_sub = font_sub.render(f"Result: {value}", True, sh_col)
    surface.blit(sh_main, (die_x + die_size + 15, rect.centery - 15))
    surface.blit(sh_sub, (die_x + die_size + 15, rect.centery + 2))

    # Text fill
    txt_main = font_main.render(f"{plr_name} Rolled", True, (255, 255, 255))
    txt_sub = font_sub.render(f"Result: {value}", True, (255, 243, 214))  # #FFF3D6 High contrast cream
    surface.blit(txt_main, (die_x + die_size + 14, rect.centery - 16))
    surface.blit(txt_sub, (die_x + die_size + 14, rect.centery + 1))
