"""
game_ui.py — Modern Wooden-Themed User Interface for Ludo Verse
==============================================================
Provides a rich, warm wooden graphical interface inspired by handcrafted
wooden board games. Features:
  - Procedural wood-grain backgrounds with horizontal fiber grain and vignette
  - Carved wooden plank logo banner with chunky glossy orange-yellow typography
  - Beveled wooden plank buttons with hover lift and press displacement
  - 15×15 wooden framed Ludo board with rounded-square bases & 2×2 circular wells
  - Cream/beige beveled track tiles with golden star safe squares
  - Glossy cabochon tokens with metallic rims, drop shadow, and hop movement arcs
  - 3D ivory/wood tumbling dice with indented pips
  - Light Wood and Dark Wood themes with small wooden top-right toggles
  - Partitioned Leaderboard and carved wooden confirmation modals
  - Pre-rendered surface caching for 60 FPS performance
"""
import sys
import os
import math
import time
from typing import Optional, List, Tuple, Dict, Any
import pygame

from board import (
    COLORS, COLOR_VALUES, COLOR_DARK, COLOR_LIGHT, COLOR_BASE_BG,
    TRACK, TRACK_INDEX, PLAYER_OFFSETS, SAFE_SQUARES, HOME_COLUMNS,
    BASE_POSITIONS, PROGRESS_BASE, PROGRESS_FINISHED,
    PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX, PROGRESS_HOME_MIN, PROGRESS_HOME_MAX,
    get_piece_grid_pos, grid_to_screen,
)
from game import Game
from game_state import GameState
from move import Move
from agents import create_agent, HumanAgent, AGENT_DISPLAY
from sound_effects import get_sound_manager
from leaderboard import LeaderboardManager

from theme import (
    GRID_CELL_SIZE, BOARD_GRID_DIM, BOARD_PIXEL_DIM, SIDE_PANEL_WIDTH,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    WOOD_THEMES, PLAYER_THEMES, PLAYER_ACCENTS,
    FONT_DISPLAY_PATH, FONT_BOLD_PATH, FONT_REGULAR_PATH, load_font,
    SPEED_PROFILES, DICE_THEME,
)
from dice import RealisticDice, render_last_roll_tile
from ui_utils import (
    generate_wood_texture, draw_gradient_rect, draw_shadow,
    draw_outlined_text, draw_wood_plank, draw_wood_button,
    draw_logo_plank, draw_glossy_pawn, draw_dice_3d,
)

# ── Dimensions & Backwards Compatibility Exports ───────────────────────────────
WINDOW_WIDTH = DEFAULT_WINDOW_WIDTH
WINDOW_HEIGHT = DEFAULT_WINDOW_HEIGHT
THEMES = WOOD_THEMES


class LudoUI:
    """Manages Pygame rendering, user interaction, animations, and game screens."""

    def __init__(self, screen: Optional[pygame.Surface] = None, headless: bool = False):
        self.headless = headless
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        self.width = WINDOW_WIDTH
        self.height = WINDOW_HEIGHT
        self.theme_name: str = 'light'  # 'light' (Light Wood) or 'dark' (Dark Wood)
        self.sound = get_sound_manager()

        if screen is not None:
            self.screen = screen
        elif not headless:
            self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption("Ludo Verse")
        else:
            self.screen = pygame.Surface((self.width, self.height))

        self.clock = pygame.time.Clock()

        # Typography hierarchy (Lilita One for display, Poppins for UI/body)
        self._init_fonts()

        # Game state & mode
        self.game: Optional[Game] = None
        self.mode: str = 'MENU'  # 'MENU', 'PLAYING', 'GAME_OVER', 'LEADERBOARD'
        self.current_game_mode: str = 'AI_VS_AI'  # 'HUMAN_VS_AI', 'AI_VS_AI'
        self.message: str = "Welcome to Ludo Verse!"
        self.last_dice: Optional[int] = None
        self.last_forfeit: bool = False

        # Activity log (timeline items)
        self.activity_log: List[dict] = []
        self._add_log_entry('system', "Welcome to Ludo Verse!", 'info')

        # Human turn flow
        self.human_phase: str = 'NEED_ROLL'
        self.human_legal_moves: List[Move] = []
        self.hovered_piece_idx: Optional[int] = None

        # Turn Timer (15s countdown for Human turns)
        self.turn_start_time: float = time.time()
        self.turn_time_limit: float = 15.0

        # 3D Center Dice Engine & Last Roll Tracker
        self.dice_3d = RealisticDice()
        self.last_dice_player: Optional[str] = None
        self.center_dice_hitbox: pygame.Rect = pygame.Rect(0, 0, 80, 80)

        # Centralized SPEED_PROFILES and speed control
        self.speed_modes = ['slow', 'normal', 'fast']
        self.speed_labels = ["Speed: Slow", "Speed: Normal", "Speed: Fast"]
        self.current_speed_idx = 1  # Default to 'normal'
        self.speed_mode = self.speed_modes[self.current_speed_idx]
        self.speed_levels = [
            int(SPEED_PROFILES['slow']['ai_think'] * 1000),
            int(SPEED_PROFILES['normal']['ai_think'] * 1000),
            int(SPEED_PROFILES['fast']['ai_think'] * 1000),
        ]
        self.ai_delay_ms = self.speed_levels[self.current_speed_idx]
        self.last_ai_step_time = 0.0

        # Timing State Machine ('WAIT_ROLL', 'DICE_ROLLING', 'DICE_HOLDING', 'PIECE_MOVING', 'PAUSE_TURN')
        self.turn_state: str = 'WAIT_ROLL'
        self.state_start_time: float = time.time()
        self.pause_duration: float = 0.5
        self._staged_ai_turn_info: Optional[dict] = None
        self._human_staged_caps: list = []

        # Confirmation modal state ('restart', 'menu', or None)
        self.confirm_dialog: Optional[str] = None
        self.pressed_button_name: Optional[str] = None

        # Visual Animation Controllers
        self.animating_move: Optional[dict] = None  # {color, piece_idx, start_px, end_px, start_time, duration}
        self.pulse_phase: float = 0.0

        # Screen transition fade
        self.screen_fade_alpha: float = 0.0

        # Particle Systems (Captures & Victory Confetti)
        self.particles: List[dict] = []
        self.confetti: List[dict] = []
        self._init_confetti()

        # Leaderboard state
        self.leaderboard_mgr = LeaderboardManager()
        self.leaderboard_tab: str = 'human'  # 'human' or 'ai'

        # Cached pre-rendered static surfaces
        self.cached_board: Optional[pygame.Surface] = None
        self.cached_board_theme: Optional[str] = None

        # UI Button rectangles
        self._init_buttons()

    @property
    def confirm_restart_modal(self) -> bool:
        """Backwards compatibility property for restart confirmation modal."""
        return self.confirm_dialog == 'restart'

    @confirm_restart_modal.setter
    def confirm_restart_modal(self, val: bool):
        self.confirm_dialog = 'restart' if val else None

    def _init_fonts(self):
        """Initialize high-quality typography with bundled fonts and system fallbacks."""
        self.font_hero = load_font(FONT_DISPLAY_PATH, 42, ['arialrounded', 'segoeui', 'arial'], bold=True)
        self.font_title = load_font(FONT_DISPLAY_PATH, 32, ['arialrounded', 'segoeui', 'arial'], bold=True)
        self.font_heading = load_font(FONT_BOLD_PATH, 24, ['arialrounded', 'segoeui', 'arial'], bold=True)
        self.font_subheading = load_font(FONT_BOLD_PATH, 19, ['arialrounded', 'segoeui', 'arial'], bold=True)
        self.font_body = load_font(FONT_REGULAR_PATH, 15, ['segoeui', 'arial'], bold=False)
        self.font_body_bold = load_font(FONT_BOLD_PATH, 15, ['segoeui', 'arial'], bold=True)
        self.font_small = load_font(FONT_REGULAR_PATH, 13, ['segoeui', 'arial'], bold=False)
        self.font_btn = load_font(FONT_BOLD_PATH, 16, ['arialrounded', 'segoeui', 'arial'], bold=True)
        self.font_dice = load_font(FONT_DISPLAY_PATH, 38, ['arialrounded', 'segoeui', 'arial'], bold=True)
        self.font_logo = load_font(FONT_DISPLAY_PATH, 28, ['arialrounded', 'segoeui', 'arial'], bold=True)
        self.font_logo_verse = load_font(FONT_DISPLAY_PATH, 22, ['arialrounded', 'segoeui', 'arial'], bold=True)

    @property
    def theme(self) -> dict:
        return WOOD_THEMES[self.theme_name]

    def toggle_theme(self):
        """Toggle between Light Wood and Dark Wood themes."""
        self.theme_name = 'dark' if self.theme_name == 'light' else 'light'
        self.cached_board = None  # Invalidate cached board surface
        self.sound.play('click')

    def toggle_sound(self):
        """Toggle mute / unmute state."""
        self.sound.toggle_mute()
        if not self.sound.muted:
            self.sound.play('click')

    def _add_log_entry(self, player: str, text: str, entry_type: str = 'normal'):
        """Append an event to the timeline activity log."""
        t_str = time.strftime("%H:%M:%S")
        self.activity_log.append({
            'time': t_str,
            'player': player,
            'text': text,
            'type': entry_type
        })
        if len(self.activity_log) > 50:
            self.activity_log.pop(0)

    def _init_confetti(self):
        """Pre-populate victory celebration confetti particles."""
        import random
        self.confetti = []
        cols = [
            (255, 215, 0), (235, 55, 65), (45, 125, 245), (50, 195, 75),
            (255, 255, 255), (255, 165, 0), (180, 75, 255)
        ]
        for _ in range(90):
            self.confetti.append({
                'x': random.uniform(20, self.width - 20),
                'y': random.uniform(-self.height, 0),
                'vx': random.uniform(-2.0, 2.0),
                'vy': random.uniform(2.5, 6.0),
                'size': random.randint(5, 11),
                'color': random.choice(cols),
                'rot': random.uniform(0, 360),
                'rot_v': random.uniform(-6, 6)
            })

    def _trigger_capture_burst(self, px: int, py: int, color: str):
        """Spawn particle explosion at captured coordinate."""
        import random
        ptheme = PLAYER_THEMES.get(color, PLAYER_THEMES['red'])
        base_c = ptheme['pawn_main']
        for _ in range(24):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2.5, 8.5)
            self.particles.append({
                'x': px,
                'y': py,
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd,
                'life': 1.0,
                'decay': random.uniform(0.035, 0.065),
                'color': base_c,
                'size': random.randint(4, 8)
            })

    def _init_buttons(self):
        """Calculate layout coordinates for all interactive buttons."""
        panel_x = BOARD_PIXEL_DIM + 20

        # 1. Main Menu buttons (nicely spaced below enlarged title banner)
        btn_w, btn_h = 390, 54
        cx = self.width // 2 - btn_w // 2
        self.btn_menu_human = pygame.Rect(cx, 245, btn_w, btn_h)
        self.btn_menu_ai = pygame.Rect(cx, 318, btn_w, btn_h)
        self.btn_menu_leaderboard = pygame.Rect(cx, 391, btn_w, btn_h)
        self.btn_menu_exit = pygame.Rect(cx, 464, btn_w, btn_h)
        self.btn_menu_theme = pygame.Rect(self.width - 110, 16, 28, 28)

        # 2. Top-right small wooden buttons (Sun/Light Wood, Moon/Dark Wood, Sound)
        self.btn_sun = pygame.Rect(self.width - 110, 16, 28, 28)
        self.btn_moon = pygame.Rect(self.width - 76, 16, 28, 28)
        self.btn_sound = pygame.Rect(self.width - 42, 16, 28, 28)

        # 3. In-game side panel buttons
        self.btn_roll = pygame.Rect(panel_x, 348, 300, 48)
        self.btn_restart = pygame.Rect(panel_x, 558, 145, 38)
        self.btn_main_menu = pygame.Rect(panel_x + 155, 558, 145, 38)
        self.btn_speed = pygame.Rect(panel_x, 604, 300, 38)

        # 4. Confirmation Modal Buttons
        modal_w, modal_h = 460, 190
        mx = self.width // 2 - modal_w // 2
        my = self.height // 2 - modal_h // 2
        self.modal_rect = pygame.Rect(mx, my, modal_w, modal_h)
        m_btn_w, m_btn_h = 190, 44
        self.btn_modal_yes = pygame.Rect(mx + 30, my + 124, m_btn_w, m_btn_h)
        self.btn_modal_cancel = pygame.Rect(mx + 240, my + 124, m_btn_w, m_btn_h)
        self.btn_confirm_restart_yes = self.btn_modal_yes
        self.btn_confirm_restart_cancel = self.btn_modal_cancel

        # 5. Game-over screen action buttons
        go_btn_w, go_btn_h = 240, 52
        self.btn_play_again = pygame.Rect(self.width // 2 - go_btn_w - 20, 550, go_btn_w, go_btn_h)
        self.btn_game_over_exit = pygame.Rect(self.width // 2 + 20, 550, go_btn_w, go_btn_h)

        # 6. Leaderboard buttons
        self.btn_lead_back = pygame.Rect(32, 18, 150, 36)
        self.btn_lead_tab_human = pygame.Rect(310, 66, 185, 40)
        self.btn_lead_tab_ai = pygame.Rect(505, 66, 185, 40)

    # ──────────────────────────────────────────────────────────────────────────
    # Game Initialization & Reset
    # ──────────────────────────────────────────────────────────────────────────

    def start_new_game(self, game_mode: str, ai_types: Optional[List[str]] = None):
        """Start a new game session with chosen player/AI configuration."""
        self.current_game_mode = game_mode
        self.mode = 'PLAYING'
        self.confirm_dialog = None
        self.animating_move = None
        self.last_dice = None
        self.last_dice_player = None
        self.last_forfeit = False
        self.activity_log.clear()
        self.dice_3d = RealisticDice()

        if game_mode == 'HUMAN_VS_AI':
            opponents = ai_types or ['expectimax', 'aggressive', 'defensive']
            agents = [
                HumanAgent('yellow'),
                create_agent(opponents[0], 'blue', depth=2),
                create_agent(opponents[1], 'red'),
                create_agent(opponents[2], 'green'),
            ]
        else:  # 'AI_VS_AI'
            models = ai_types or ['expectimax', 'aggressive', 'defensive', 'random']
            agents = [
                create_agent(models[0], 'yellow', depth=2),
                create_agent(models[1], 'blue', depth=2 if models[1] == 'expectimax' else None),
                create_agent(models[2], 'red'),
                create_agent(models[3], 'green'),
            ]

        self.game = Game(agents=agents)
        self.human_phase = 'NEED_ROLL'
        self.human_legal_moves = []
        self.turn_start_time = time.time()
        self.last_ai_step_time = time.time()
        self.turn_state = 'WAIT_ROLL'
        self.state_start_time = time.time()
        self.pause_duration = 0.5
        self._staged_ai_turn_info = None
        self._human_staged_caps = []

        m_name = "HUMAN VS AI" if game_mode == 'HUMAN_VS_AI' else "AI VS AI SHOWDOWN"
        self._add_log_entry('system', f"LudoVerse match started: {m_name}", 'info')
        self.message = f"Game started! {self.game.state.current_player.capitalize()}'s turn."
        self.sound.play('game_start')

    # ──────────────────────────────────────────────────────────────────────────
    # Pixel Math & Hit Detection
    # ──────────────────────────────────────────────────────────────────────────

    def get_piece_pixel_rect(self, color: str, piece_idx: int) -> pygame.Rect:
        """Calculate on-screen pixel rectangle for a piece."""
        prog = self.game.state.pieces[color][piece_idx]
        col, row = get_piece_grid_pos(color, prog, piece_idx)
        px, py = grid_to_screen(col, row, GRID_CELL_SIZE)

        if prog == PROGRESS_BASE:
            radius = int(GRID_CELL_SIZE * 0.36)
            return pygame.Rect(px - radius, py - radius, radius * 2, radius * 2)

        # Detect pieces sharing the same cell
        sharing = []
        my_slot = 0
        for c in COLORS:
            for idx, p in enumerate(self.game.state.pieces[c]):
                if p != PROGRESS_BASE and get_piece_grid_pos(c, p, idx) == (col, row):
                    if (c, idx) == (color, piece_idx):
                        my_slot = len(sharing)
                    sharing.append((c, idx))

        total_sharing = len(sharing)
        radius = int(GRID_CELL_SIZE * 0.36)

        if total_sharing <= 1:
            return pygame.Rect(px - radius, py - radius, radius * 2, radius * 2)
        elif total_sharing == 2:
            radius = int(GRID_CELL_SIZE * 0.28)
            offset = 8
            ox = -offset if my_slot == 0 else offset
            return pygame.Rect(px + ox - radius, py - radius, radius * 2, radius * 2)
        else:
            radius = int(GRID_CELL_SIZE * 0.24)
            offsets = [(-8, -8), (8, -8), (-8, 8), (8, 8)]
            ox, oy = offsets[my_slot % 4]
            return pygame.Rect(px + ox - radius, py + oy - radius, radius * 2, radius * 2)

    def get_clicked_legal_piece(self, mouse_pos: Tuple[int, int]) -> Optional[Move]:
        """Return the Move corresponding to the piece clicked by the user."""
        curr_player = self.game.state.current_player
        for move in self.human_legal_moves:
            p_rect = self.get_piece_pixel_rect(curr_player, move.piece_index)
            hitbox = p_rect.inflate(14, 14)
            if hitbox.collidepoint(mouse_pos):
                return move
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Frame Update Loop
    # ──────────────────────────────────────────────────────────────────────────

    def update(self):
        """Update game state, AI steps, animations, and particle physics."""
        self.pulse_phase += 0.08

        # Update move animation
        if self.animating_move:
            elapsed = time.time() - self.animating_move['start_time']
            if elapsed >= self.animating_move['duration']:
                self.animating_move = None

        # Update particles
        for p in self.particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.2  # Gravity
            p['life'] -= p['decay']
            if p['life'] <= 0:
                self.particles.remove(p)

        # Update game-over victory confetti
        if self.mode == 'GAME_OVER':
            for c in self.confetti:
                c['y'] += c['vy']
                c['x'] += c['vx'] + math.sin(c['rot'] * 0.05) * 0.5
                c['rot'] += c['rot_v']
                if c['y'] > self.height:
                    c['y'] = -10
                    import random
                    c['x'] = random.uniform(20, self.width - 20)

        # Handle Turn Execution & SPEED_PROFILES State Machine
        if self.mode == 'PLAYING' and self.game:
            if self.confirm_dialog is not None:
                return  # Paused while confirmation modal is open

            if self.game.is_game_over():
                self.mode = 'GAME_OVER'
                winner = self.game.get_winner()
                self._record_game_over(winner)
                self.sound.play('victory')
                return

            curr_player = self.game.state.current_player
            agent = self.game.agents[curr_player]
            is_human = isinstance(agent, HumanAgent)
            prof = SPEED_PROFILES.get(self.speed_mode, SPEED_PROFILES['normal'])
            now = time.time()

            # Headless fast-path (tournaments & unit tests)
            if self.headless:
                if not is_human:
                    dice = self.game.roll_dice()
                    self.last_dice = dice
                    self.last_dice_player = curr_player
                    self._add_log_entry(curr_player, f"Rolled a {dice}", 'roll')
                    if dice == 6 and self.game.state.consecutive_sixes >= 2:
                        self.message = f"{curr_player.capitalize()} rolled 3rd six! Turn forfeited."
                        self._add_log_entry(curr_player, "Rolled 6 (3rd consecutive). Forfeited.", 'forfeit')
                        self.last_forfeit = True
                        self.game.play_turn(dice=dice)
                        return
                    self.last_forfeit = False
                    turn_info = self.game.play_turn(dice=dice)
                    self._apply_ai_turn_result(turn_info, trigger_anim=False)
                return

            # GUI State Machine with SPEED_PROFILES
            if self.turn_state == 'WAIT_ROLL':
                if not is_human:
                    if (now - self.state_start_time) >= prof['ai_think']:
                        dice = self.game.roll_dice()
                        self.last_dice = dice
                        self.last_dice_player = curr_player
                        self.dice_3d.roll(dice, duration=prof['dice_roll'])
                        self.sound.play('dice')
                        self._add_log_entry(curr_player, f"Rolled a {dice}", 'roll')
                        self.turn_state = 'DICE_ROLLING'
                        self.state_start_time = now

            elif self.turn_state == 'DICE_ROLLING':
                if (now - self.state_start_time) >= prof['dice_roll']:
                    self.turn_state = 'DICE_HOLDING'
                    self.state_start_time = now

            elif self.turn_state == 'DICE_HOLDING':
                if (now - self.state_start_time) >= prof['result_hold']:
                    dice = self.last_dice
                    # Consecutive sixes check
                    if dice == 6 and self.game.state.consecutive_sixes >= 2:
                        self.message = f"{curr_player.capitalize()} rolled 3rd six! Turn forfeited."
                        self._add_log_entry(curr_player, "Rolled 6 (3rd consecutive). Forfeited.", 'forfeit')
                        self.last_forfeit = True
                        self.game.play_turn(dice=dice)
                        self.turn_state = 'PAUSE_TURN'
                        self.pause_duration = prof['pause_turn']
                        self.state_start_time = now
                        return

                    self.last_forfeit = False

                    if is_human:
                        self.human_legal_moves = self.game.state.get_legal_moves(dice)
                        if not self.human_legal_moves:
                            self.message = f"You rolled a {dice}. No legal moves. Turn passed."
                            self._add_log_entry('yellow', f"No legal moves for roll {dice}. Turn passed.", 'pass')
                            self.game.execute_move(None, dice)
                            self.turn_state = 'PAUSE_TURN'
                            self.pause_duration = prof['pause_turn']
                            self.state_start_time = now
                        elif len(self.human_legal_moves) == 1:
                            self._human_execute_move(self.human_legal_moves[0])
                        else:
                            self.message = f"You rolled a {dice}. Click a highlighted piece to move."
                            self.human_phase = 'SELECT_PIECE'
                            self.turn_state = 'SELECT_PIECE'
                    else:
                        legal_moves = self.game.state.get_legal_moves(dice)
                        turn_info = self.game.play_turn(dice=dice)
                        m = turn_info['move']
                        if m is not None:
                            tiles = max(1, m.to_progress - m.from_progress) if m.from_progress != PROGRESS_BASE else 1
                            hop_dur = tiles * prof['hop_per_tile']
                            self._start_piece_animation(curr_player, m.piece_index, m.from_progress, m.to_progress, duration=hop_dur)
                            self._staged_ai_turn_info = turn_info
                            self.turn_state = 'PIECE_MOVING'
                            self.state_start_time = now
                        else:
                            self._apply_ai_turn_result(turn_info, trigger_anim=False)
                            self.turn_state = 'PAUSE_TURN'
                            self.pause_duration = prof['pause_turn']
                            self.state_start_time = now

            elif self.turn_state == 'PIECE_MOVING':
                if not self.animating_move:
                    if is_human:
                        caps = getattr(self, '_human_staged_caps', [])
                        pause_time = prof['capture_anim'] if caps else prof['pause_turn']
                        self.turn_state = 'PAUSE_TURN'
                        self.pause_duration = pause_time
                        self.state_start_time = now
                    else:
                        turn_info = self._staged_ai_turn_info
                        self._staged_ai_turn_info = None
                        if turn_info:
                            self._apply_ai_turn_result(turn_info, trigger_anim=False)
                            caps = turn_info.get('captures', [])
                            pause_time = prof['capture_anim'] if caps else prof['pause_turn']
                        else:
                            pause_time = prof['pause_turn']
                        self.turn_state = 'PAUSE_TURN'
                        self.pause_duration = pause_time
                        self.state_start_time = now

            elif self.turn_state == 'PAUSE_TURN':
                if (now - self.state_start_time) >= getattr(self, 'pause_duration', prof['pause_turn']):
                    if self.game.is_game_over():
                        self.mode = 'GAME_OVER'
                        winner = self.game.get_winner()
                        self._record_game_over(winner)
                        self.sound.play('victory')
                        return
                    self.turn_state = 'WAIT_ROLL'
                    self.human_phase = 'NEED_ROLL'
                    self.state_start_time = now

    def _start_dice_animation(self):
        """Initiate 3D dice tumbling animation and play dice roll audio."""
        if self.headless:
            return
        self.anim_dice_rolling = True
        self.anim_dice_start = time.time()
        self.sound.play('dice')

    def _start_piece_animation(self, color: str, piece_idx: int, from_prog: int, to_prog: int, duration: float = 0.22):
        """Trigger animated token movement along the track."""
        if self.headless:
            return
        fc, fr = get_piece_grid_pos(color, from_prog, piece_idx)
        tc, tr = get_piece_grid_pos(color, to_prog, piece_idx)
        spx, spy = grid_to_screen(fc, fr, GRID_CELL_SIZE)
        epx, epy = grid_to_screen(tc, tr, GRID_CELL_SIZE)

        self.animating_move = {
            'color': color,
            'piece_idx': piece_idx,
            'start_px': (spx, spy),
            'end_px': (epx, epy),
            'start_time': time.time(),
            'duration': duration,
        }
        if to_prog == PROGRESS_FINISHED:
            self.sound.play('home')
        else:
            self.sound.play('move')

    def _apply_ai_turn_result(self, turn_info: dict, trigger_anim: bool = True):
        """Process AI move outcome, logging events and triggering animations."""
        player_col = turn_info['player']
        plr = player_col.capitalize()
        m: Optional[Move] = turn_info['move']
        caps = turn_info['captures']
        prof = SPEED_PROFILES.get(self.speed_mode, SPEED_PROFILES['normal'])

        if m is not None:
            if trigger_anim and not self.headless:
                tiles = max(1, m.to_progress - m.from_progress) if m.from_progress != PROGRESS_BASE else 1
                hop_dur = tiles * prof['hop_per_tile']
                self._start_piece_animation(player_col, m.piece_index, m.from_progress, m.to_progress, duration=hop_dur)

            if caps:
                for cap_col, cap_idx in caps:
                    col, row = get_piece_grid_pos(player_col, m.to_progress, m.piece_index)
                    px, py = grid_to_screen(col, row, GRID_CELL_SIZE)
                    self._trigger_capture_burst(px, py, cap_col)
                    self._add_log_entry(player_col, f"CAPTURED {cap_col.upper()}'s piece!", 'capture')
                self._add_log_entry(player_col, "EXTRA TURN granted for capture!", 'extra_turn')

            cap_text = f" Captured {len(caps)} piece(s)!" if caps else ""
            fin_text = " Reached Center Goal!" if m.to_progress == PROGRESS_FINISHED else ""
            self.message = f"{plr} moved piece {m.piece_index + 1} ({m.from_progress}→{m.to_progress}).{cap_text}{fin_text}"
            self._add_log_entry(player_col, f"Moved piece {m.piece_index + 1} ({m.from_progress}→{m.to_progress})", 'move')
        else:
            if not self.last_forfeit:
                self.message = f"{plr} rolled {turn_info['dice']}. No legal moves. Turn passed."
                self._add_log_entry(player_col, f"No legal moves for roll {turn_info['dice']}. Passed.", 'pass')

    # ──────────────────────────────────────────────────────────────────────────
    # User Input & Event Handling
    # ──────────────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event):
        """Process Pygame user input events."""
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Top Header Controls: Light Wood (Sun), Dark Wood (Moon), and Sound
            if self.btn_sun.collidepoint(mx, my):
                self.theme_name = 'light'
                self.cached_board = None
                self.sound.play('click')
                return
            elif self.btn_moon.collidepoint(mx, my):
                self.theme_name = 'dark'
                self.cached_board = None
                self.sound.play('click')
                return
            elif self.btn_sound.collidepoint(mx, my):
                self.toggle_sound()
                return

            # Confirmation Modal Handling
            if self.confirm_dialog is not None:
                if self.btn_modal_yes.collidepoint(mx, my):
                    self.sound.play('click')
                    target_action = self.confirm_dialog
                    self.confirm_dialog = None
                    if target_action == 'restart':
                        self.start_new_game(self.current_game_mode)
                    elif target_action == 'menu':
                        self.mode = 'MENU'
                elif self.btn_modal_cancel.collidepoint(mx, my) or not self.modal_rect.collidepoint(mx, my):
                    self.sound.play('click')
                    self.confirm_dialog = None
                return

            if self.mode == 'MENU':
                if self.btn_menu_human.collidepoint(mx, my):
                    self.sound.play('click')
                    self.start_new_game('HUMAN_VS_AI')
                elif self.btn_menu_ai.collidepoint(mx, my):
                    self.sound.play('click')
                    self.start_new_game('AI_VS_AI')
                elif self.btn_menu_leaderboard.collidepoint(mx, my):
                    self.sound.play('click')
                    self.mode = 'LEADERBOARD'
                elif self.btn_menu_theme.collidepoint(mx, my):
                    self.toggle_theme()
                elif self.btn_menu_exit.collidepoint(mx, my):
                    pygame.quit()
                    sys.exit()

            elif self.mode == 'LEADERBOARD':
                if self.btn_lead_back.collidepoint(mx, my):
                    self.sound.play('click')
                    self.mode = 'MENU'
                elif self.btn_lead_tab_human.collidepoint(mx, my):
                    self.sound.play('click')
                    self.leaderboard_tab = 'human'
                elif self.btn_lead_tab_ai.collidepoint(mx, my):
                    self.sound.play('click')
                    self.leaderboard_tab = 'ai'

            elif self.mode == 'GAME_OVER':
                if self.btn_play_again.collidepoint(mx, my):
                    self.sound.play('click')
                    self.start_new_game(self.current_game_mode)
                elif self.btn_game_over_exit.collidepoint(mx, my):
                    self.sound.play('click')
                    self.mode = 'MENU'

            elif self.mode == 'PLAYING':
                if self.btn_restart.collidepoint(mx, my):
                    self.sound.play('click')
                    self.confirm_dialog = 'restart'
                    return
                elif self.btn_main_menu.collidepoint(mx, my):
                    self.sound.play('click')
                    self.confirm_dialog = 'menu'
                    return
                elif self.btn_speed.collidepoint(mx, my):
                    self.sound.play('click')
                    self.current_speed_idx = (self.current_speed_idx + 1) % len(self.speed_modes)
                    self.speed_mode = self.speed_modes[self.current_speed_idx]
                    self.ai_delay_ms = self.speed_levels[self.current_speed_idx]
                    return

                # Human player actions
                curr_player = self.game.state.current_player
                curr_agent = self.game.agents[curr_player]
                if isinstance(curr_agent, HumanAgent):
                    is_dice_click = self.btn_roll.collidepoint(mx, my) or self.center_dice_hitbox.collidepoint(mx, my)
                    if is_dice_click and (self.turn_state == 'WAIT_ROLL' or self.human_phase == 'NEED_ROLL'):
                        self._human_roll_dice()
                    elif self.turn_state == 'SELECT_PIECE' or self.human_phase == 'SELECT_PIECE':
                        clicked_move = self.get_clicked_legal_piece((mx, my))
                        if clicked_move is not None:
                            self._human_execute_move(clicked_move)

        elif event.type == pygame.KEYDOWN:
            if self.confirm_dialog is not None:
                if event.key == pygame.K_ESCAPE:
                    self.confirm_dialog = None
            elif self.mode == 'MENU':
                if event.key == pygame.K_1:
                    self.sound.play('click')
                    self.start_new_game('HUMAN_VS_AI')
                elif event.key == pygame.K_2:
                    self.sound.play('click')
                    self.start_new_game('AI_VS_AI')
                elif event.key == pygame.K_3:
                    self.sound.play('click')
                    self.mode = 'LEADERBOARD'
                elif event.key in (pygame.K_4, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
            elif self.mode == 'PLAYING':
                if event.key == pygame.K_SPACE:
                    curr_player = self.game.state.current_player
                    if isinstance(self.game.agents[curr_player], HumanAgent) and (self.turn_state == 'WAIT_ROLL' or self.human_phase == 'NEED_ROLL'):
                        self._human_roll_dice()

    def _human_roll_dice(self):
        """Roll dice for Human player with 3D tumble animation."""
        curr_player = self.game.state.current_player
        if not isinstance(self.game.agents[curr_player], HumanAgent):
            return
        if self.turn_state != 'WAIT_ROLL' and self.human_phase != 'NEED_ROLL':
            return

        prof = SPEED_PROFILES.get(self.speed_mode, SPEED_PROFILES['normal'])
        dice = self.game.roll_dice()
        self.last_dice = dice
        self.last_dice_player = 'yellow'

        if not self.headless:
            self.dice_3d.roll(dice, duration=prof['dice_roll'])
            self.sound.play('dice')

        self._add_log_entry('yellow', f"Rolled a {dice}", 'roll')
        self.turn_state = 'DICE_ROLLING'
        self.human_phase = 'WAIT_ANIM'
        self.state_start_time = time.time()

    def _human_execute_move(self, move: Move):
        """Execute selected move for human with tile-hop animation."""
        prof = SPEED_PROFILES.get(self.speed_mode, SPEED_PROFILES['normal'])
        tiles = max(1, move.to_progress - move.from_progress) if move.from_progress != PROGRESS_BASE else 1
        hop_dur = (tiles * prof['hop_per_tile']) if not self.headless else 0.001
        self._start_piece_animation('yellow', move.piece_index, move.from_progress, move.to_progress, duration=hop_dur)

        turn_res = self.game.execute_move(move, self.last_dice)
        caps = turn_res['captures']
        self._human_staged_caps = caps

        if caps:
            for cap_col, cap_idx in caps:
                col, row = get_piece_grid_pos('yellow', move.to_progress, move.piece_index)
                px, py = grid_to_screen(col, row, GRID_CELL_SIZE)
                self._trigger_capture_burst(px, py, cap_col)
                self._add_log_entry('yellow', f"CAPTURED {cap_col.upper()}'s piece!", 'capture')
            self._add_log_entry('yellow', "EXTRA TURN granted for capture!", 'extra_turn')

        cap_text = f" Captured {len(caps)} opponent piece!" if caps else ""
        fin_text = " Reached Center Goal!" if move.to_progress == PROGRESS_FINISHED else ""
        self.message = f"Moved piece {move.piece_index + 1} ({move.from_progress}→{move.to_progress}).{cap_text}{fin_text}"
        self._add_log_entry('yellow', f"Moved piece {move.piece_index + 1} ({move.from_progress}→{move.to_progress})", 'move')

        self.human_phase = 'NEED_ROLL'
        self.human_legal_moves = []
        self.turn_state = 'PIECE_MOVING'
        self.state_start_time = time.time()

    # ──────────────────────────────────────────────────────────────────────────
    # Rendering Pipeline
    # ──────────────────────────────────────────────────────────────────────────

    def render(self):
        """Render active scene."""
        if self.mode == 'MENU':
            self._render_menu()
        elif self.mode == 'LEADERBOARD':
            self._render_leaderboard()
        elif self.mode in ('PLAYING', 'GAME_OVER'):
            self._render_board()
            self._render_pieces()
            self._render_center_dice()
            self._render_side_panel()
            if self.mode == 'GAME_OVER':
                self._render_game_over_screen()

        # Confirmation modal overlay
        if self.confirm_dialog is not None:
            self._render_confirmation_modal()

        if not self.headless:
            pygame.display.flip()

    # ──────────────────────────────────────────────────────────────────────────
    # Main Menu Screen (Wooden Reskin matching Reference Style)
    # ──────────────────────────────────────────────────────────────────────────

    def _render_menu(self):
        """Render warm wooden main menu with enlarged plank logo and 4 wooden buttons."""
        is_dark = (self.theme_name == 'dark')
        cx = self.width // 2

        # 1. Procedural Warm Wood-Grain Background
        bg_surf = generate_wood_texture(self.width, self.height, is_dark_wood=is_dark)
        self.screen.blit(bg_surf, (0, 0))

        # 2. Top-right small wooden controls (Sun, Moon, Sound)
        self._render_header_icons()

        # 3. Brand Logo Plank Banner (enlarged and brought down)
        draw_logo_plank(self.screen, cx, cy=135, is_dark=is_dark, banner_w=500, banner_h=118)

        # 4. Four Wooden Plank Buttons (Titles in white bold, NO subtitles)
        mouse_pos = pygame.mouse.get_pos()
        is_mouse_down = pygame.mouse.get_pressed()[0]

        buttons_info = [
            (self.btn_menu_human,       "1. Human vs AI"),
            (self.btn_menu_ai,          "2. AI vs AI Showdown"),
            (self.btn_menu_leaderboard, "3. Leaderboard"),
            (self.btn_menu_exit,        "4. Exit Game"),
        ]

        for btn, label in buttons_info:
            hovered = btn.collidepoint(mouse_pos)
            state = 'pressed' if (hovered and is_mouse_down) else ('hover' if hovered else 'normal')
            draw_wood_button(self.screen, btn, title=label, font=self.font_btn, state=state, is_dark=is_dark)

    def _render_menu_centerpiece(self, cx: int, cy: int):
        """Draw 3D perspective wooden board, pawns, and tumbling dice."""
        # Isometric Board Diamond
        top = (cx, cy - 36)
        right = (cx + 120, cy)
        bottom = (cx, cy + 36)
        left = (cx - 120, cy)

        # 3D skirt / thickness extrusion (rich dark mahogany)
        skirt_pts = [left, bottom, right, (right[0], right[1] + 14), (bottom[0], bottom[1] + 14), (left[0], left[1] + 14)]
        pygame.draw.polygon(self.screen, (55, 26, 8), skirt_pts)
        pygame.draw.line(self.screen, (180, 120, 45), (left[0], left[1] + 14), (bottom[0], bottom[1] + 14), 2)
        pygame.draw.line(self.screen, (180, 120, 45), (bottom[0], bottom[1] + 14), (right[0], right[1] + 14), 2)

        # Board main diamond face (warm cream/wood canvas)
        board_face = [top, right, bottom, left]
        pygame.draw.polygon(self.screen, (246, 238, 222), board_face)
        pygame.draw.polygon(self.screen, (115, 68, 28), board_face, 3)

        # 4 Quadrants matching Ludo colors
        quads = [
            ([top, (cx + 60, cy - 18), (cx, cy), (cx - 60, cy - 18)], PLAYER_THEMES['yellow']['pawn_main']),
            ([(cx + 60, cy - 18), right, (cx + 60, cy + 18), (cx, cy)], PLAYER_THEMES['blue']['pawn_main']),
            ([(cx - 60, cy + 18), (cx, cy), (cx + 60, cy + 18), bottom], PLAYER_THEMES['red']['pawn_main']),
            ([left, (cx - 60, cy - 18), (cx, cy), (cx - 60, cy + 18)], PLAYER_THEMES['green']['pawn_main']),
        ]
        for q_pts, q_col in quads:
            pygame.draw.polygon(self.screen, q_col, q_pts)
            # Quadrant inner dots
            q_cx = sum(p[0] for p in q_pts) // 4
            q_cy = sum(p[1] for p in q_pts) // 4
            for bx, by in [(-5, -2), (5, -2), (-5, 2), (5, 2)]:
                pygame.draw.circle(self.screen, (30, 15, 5), (q_cx + bx, q_cy + by), 3)

        # Center goal
        cross_pts = [(cx, cy - 12), (cx + 22, cy), (cx, cy + 12), (cx - 22, cy)]
        pygame.draw.polygon(self.screen, (255, 250, 240), cross_pts)
        pygame.draw.polygon(self.screen, (215, 160, 25), cross_pts, 2)

        # 3D Tumbling Center Dice
        draw_dice_3d(self.screen, cx, cy - 8, value=1, is_rolling=False, anim_start=0.0, anim_duration=0.45, size=32)

        # 4 Glossy Cabochon Pawns around board
        draw_glossy_pawn(self.screen, cx - 70, cy - 36, radius=12, color_key='yellow', scale=0.9)
        draw_glossy_pawn(self.screen, cx + 70, cy - 36, radius=12, color_key='blue', scale=0.9)
        draw_glossy_pawn(self.screen, cx + 138, cy + 12, radius=12, color_key='red', scale=1.1)
        draw_glossy_pawn(self.screen, cx - 138, cy + 12, radius=12, color_key='green', scale=1.1)

    # ──────────────────────────────────────────────────────────────────────────
    # Wooden Board Rendering (Pre-rendered for 60 FPS Performance)
    # ──────────────────────────────────────────────────────────────────────────

    def _render_board(self):
        """Draw 15×15 wooden framed Ludo board with rounded bases, cream tiles, and stars."""
        # 1. Draw pre-rendered cached board if available
        if self.cached_board is not None and self.cached_board_theme == self.theme_name:
            self.screen.blit(self.cached_board, (0, 0))
            self._render_active_base_glow()
            return

        # Pre-render static board surface
        th = self.theme
        b_surf = pygame.Surface((BOARD_PIXEL_DIM, BOARD_PIXEL_DIM))
        is_dark = (self.theme_name == 'dark')

        # Outer thick brown wooden frame with bevel and shadow
        frame_rect = pygame.Rect(0, 0, BOARD_PIXEL_DIM, BOARD_PIXEL_DIM)
        draw_gradient_rect(b_surf, frame_rect, th['board_frame_outer'], th['board_frame_mid'])

        # Inner carved wooden canvas bed
        canvas_margin = 8
        canvas_rect = frame_rect.inflate(-canvas_margin * 2, -canvas_margin * 2)
        pygame.draw.rect(b_surf, th['board_frame_inner'], canvas_rect, width=2)
        pygame.draw.rect(b_surf, th['board_canvas'], canvas_rect)

        # 2. Draw 4 Rounded-Square Corner Bases with Vertical Gradients & 2x2 Slots
        base_squares = {
            'yellow': pygame.Rect(0, 0, 6 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE),
            'blue':   pygame.Rect(9 * GRID_CELL_SIZE, 0, 6 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE),
            'red':    pygame.Rect(9 * GRID_CELL_SIZE, 9 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE),
            'green':  pygame.Rect(0, 9 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE),
        }

        for color, rect in base_squares.items():
            ptheme = PLAYER_THEMES[color]
            # Rounded-square base with vertical gradient
            draw_gradient_rect(b_surf, rect, ptheme['base_top'], ptheme['base_bottom'], border_radius=18)
            # Base dark outline
            pygame.draw.rect(b_surf, ptheme['base_border'], rect, width=3, border_radius=18)
            # Inner highlight outline
            inner_rect = rect.inflate(-8, -8)
            pygame.draw.rect(b_surf, ptheme['base_inner_rim'], inner_rect, width=2, border_radius=14)

            # 4 dark circular token wells/slots in 2x2 layout
            for slot_col, slot_row in BASE_POSITIONS[color]:
                px, py = grid_to_screen(slot_col, slot_row, GRID_CELL_SIZE)
                slot_r = int(GRID_CELL_SIZE * 0.38)
                # Outer shadow ring
                pygame.draw.circle(b_surf, ptheme['slot_shadow'], (px, py + 2), slot_r)
                # Recessed dark well
                pygame.draw.circle(b_surf, ptheme['slot_fill'], (px, py), slot_r)
                # Inner rim shadow
                pygame.draw.circle(b_surf, (0, 0, 0, 75), (px, py), slot_r, 2)

        # 3. Draw Track Grid: Cream / Beige rounded tiles with subtle bevels
        for col in range(BOARD_GRID_DIM):
            for row in range(BOARD_GRID_DIM):
                if (col < 6 and row < 6) or (col > 8 and row < 6) or \
                   (col > 8 and row > 8) or (col < 6 and row > 8) or \
                   (6 <= col <= 8 and 6 <= row <= 8):
                    continue

                cell_rect = pygame.Rect(col * GRID_CELL_SIZE + 1, row * GRID_CELL_SIZE + 1,
                                        GRID_CELL_SIZE - 2, GRID_CELL_SIZE - 2)
                # Tile bevel shadow
                pygame.draw.rect(b_surf, th['tile_shadow'], cell_rect.move(0, 1), border_radius=6)
                # Tile face
                pygame.draw.rect(b_surf, th['tile_cream'], cell_rect, border_radius=6)
                pygame.draw.rect(b_surf, th['tile_border'], cell_rect, 1, border_radius=6)

        # 4. Colorize Home-Stretch Lanes (5 square blocks per color)
        for color, cells in HOME_COLUMNS.items():
            ptheme = PLAYER_THEMES[color]
            for c_col, c_row in cells:
                cell_rect = pygame.Rect(c_col * GRID_CELL_SIZE + 1, c_row * GRID_CELL_SIZE + 1,
                                        GRID_CELL_SIZE - 2, GRID_CELL_SIZE - 2)
                pygame.draw.rect(b_surf, ptheme['home_lane'], cell_rect, border_radius=6)
                pygame.draw.rect(b_surf, ptheme['base_border'], cell_rect, 1, border_radius=6)

        # 5. Starting Entry Squares with Directional Chevrons
        for color, off in PLAYER_OFFSETS.items():
            scol, srow = TRACK[off]
            s_rect = pygame.Rect(scol * GRID_CELL_SIZE + 1, srow * GRID_CELL_SIZE + 1,
                                 GRID_CELL_SIZE - 2, GRID_CELL_SIZE - 2)
            pygame.draw.rect(b_surf, PLAYER_THEMES[color]['home_lane'], s_rect, border_radius=6)
            pygame.draw.rect(b_surf, PLAYER_THEMES[color]['base_border'], s_rect, 2, border_radius=6)
            self._draw_directional_arrow_on(b_surf, scol, srow, color)

        # 6. Star Safe Squares (8, 21, 34, 47) — Golden 5-Pointed Stars
        star_indices = [8, 21, 34, 47]
        for star_idx in star_indices:
            scol, srow = TRACK[star_idx]
            px, py = grid_to_screen(scol, srow, GRID_CELL_SIZE)
            self._draw_vector_star_on(b_surf, px, py, radius=12, color=th['star_gold'], outline=th['star_outline'])

        # 7. Directional chevrons pointing into home columns
        entrances = [('yellow', 0, 7, 'right'), ('blue', 7, 0, 'down'),
                     ('red', 14, 7, 'left'), ('green', 7, 14, 'up')]
        for c, ec, er, direction in entrances:
            self._draw_home_entrance_chevron_on(b_surf, ec, er, c, direction)

        # 8. Center Home Triangles (Goal at 7, 7)
        cx, cy = grid_to_screen(7, 7, GRID_CELL_SIZE)
        half_dim = int(1.5 * GRID_CELL_SIZE)
        left, right = cx - half_dim, cx + half_dim
        top, bottom = cy - half_dim, cy + half_dim

        pygame.draw.polygon(b_surf, PLAYER_THEMES['yellow']['triangle'], [(left, top), (left, bottom), (cx, cy)])
        pygame.draw.polygon(b_surf, PLAYER_THEMES['blue']['triangle'],   [(left, top), (right, top), (cx, cy)])
        pygame.draw.polygon(b_surf, PLAYER_THEMES['red']['triangle'],    [(right, top), (right, bottom), (cx, cy)])
        pygame.draw.polygon(b_surf, PLAYER_THEMES['green']['triangle'],  [(left, bottom), (right, bottom), (cx, cy)])
        pygame.draw.polygon(b_surf, th['board_frame_outer'], [(left, top), (right, top), (right, bottom), (left, bottom)], 3)

        # Golden Center Medallion
        pygame.draw.circle(b_surf, (255, 255, 255), (cx, cy), 13)
        pygame.draw.circle(b_surf, (215, 160, 25), (cx, cy), 13, 2)
        self._draw_vector_star_on(b_surf, cx, cy, radius=6, color=(255, 215, 25), outline=(180, 130, 15))

        try:
            self.cached_board = b_surf.convert()
        except Exception:
            self.cached_board = b_surf

        self.cached_board_theme = self.theme_name
        self.screen.blit(self.cached_board, (0, 0))
        self._render_active_base_glow()

    def _render_active_base_glow(self):
        """Draw pulsing golden border around the currently active player's home base."""
        if not self.game:
            return
        curr_player = self.game.state.current_player
        base_squares = {
            'yellow': pygame.Rect(0, 0, 6 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE),
            'blue':   pygame.Rect(9 * GRID_CELL_SIZE, 0, 6 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE),
            'red':    pygame.Rect(9 * GRID_CELL_SIZE, 9 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE),
            'green':  pygame.Rect(0, 9 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE, 6 * GRID_CELL_SIZE),
        }
        active_rect = base_squares.get(curr_player)
        if active_rect:
            pulse = math.sin(self.pulse_phase) * 2
            glow_rect = active_rect.inflate(int(4 + pulse), int(4 + pulse))
            pygame.draw.rect(self.screen, (255, 215, 25), glow_rect, width=3, border_radius=20)

    def _draw_vector_star_on(self, surface: pygame.Surface, cx: int, cy: int, radius: float, color: tuple, outline: tuple):
        """Draw an anti-aliased 5-pointed star."""
        points = []
        for i in range(10):
            r = radius if i % 2 == 0 else radius * 0.45
            angle = i * math.pi / 5 - math.pi / 2
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, outline, points, 1)

    def _draw_directional_arrow_on(self, surface: pygame.Surface, col: int, row: int, color: str):
        """Draw directional chevron on player start squares."""
        px, py = grid_to_screen(col, row, GRID_CELL_SIZE)
        d = 7
        pts_map = {
            'yellow': [(px - d, py - d), (px + d, py), (px - d, py + d)],   # right
            'blue':   [(px - d, py - d), (px, py + d), (px + d, py - d)],   # down
            'red':    [(px + d, py - d), (px - d, py), (px + d, py + d)],   # left
            'green':  [(px - d, py + d), (px, py - d), (px + d, py + d)],   # up
        }
        pts = pts_map.get(color, [])
        if pts:
            pygame.draw.polygon(surface, PLAYER_THEMES[color]['base_border'], pts)

    def _draw_home_entrance_chevron_on(self, surface: pygame.Surface, col: int, row: int, color: str, direction: str):
        """Draw chevron pointing into each home lane."""
        px, py = grid_to_screen(col, row, GRID_CELL_SIZE)
        d = 6
        pts = [(px - d, py), (px + d, py), (px, py + d)]
        if direction == 'right':
            pts = [(px - d, py - d), (px + 2, py), (px - d, py + d)]
        elif direction == 'left':
            pts = [(px + d, py - d), (px - 2, py), (px + d, py + d)]
        elif direction == 'up':
            pts = [(px - d, py + d), (px, py - 2), (px + d, py + d)]
        pygame.draw.polygon(surface, PLAYER_THEMES[color]['base_border'], pts)

    # ──────────────────────────────────────────────────────────────────────────
    # Piece Rendering (Glossy Cabochon Tokens & Hop Movement Animation)
    # ──────────────────────────────────────────────────────────────────────────

    def _render_pieces(self):
        """Draw glossy cabochon player tokens with shadows, numbers, and hop arcs."""
        if not self.game:
            return

        curr_player = self.game.state.current_player
        is_human = isinstance(self.game.agents[curr_player], HumanAgent)
        legal_piece_indices = {m.piece_index for m in self.human_legal_moves} if is_human else set()
        pulse = math.sin(self.pulse_phase) * 3

        for color in COLORS:
            for idx in range(4):
                prog = self.game.state.pieces[color][idx]

                # Check if this piece is animating move
                is_anim = (self.animating_move and
                           self.animating_move['color'] == color and
                           self.animating_move['piece_idx'] == idx)
                if is_anim:
                    elapsed = time.time() - self.animating_move['start_time']
                    t = min(1.0, elapsed / self.animating_move['duration'])
                    t_eased = 1 - (1 - t) * (1 - t)
                    sx, sy = self.animating_move['start_px']
                    ex, ey = self.animating_move['end_px']
                    center_x = int(sx + (ex - sx) * t_eased)
                    center_y = int(sy + (ey - sy) * t_eased)
                    # Parabolic hop arc
                    hop_y = -36.0 * math.sin(math.pi * t)
                    radius = int(GRID_CELL_SIZE * 0.36)
                else:
                    p_rect = self.get_piece_pixel_rect(color, idx)
                    center_x, center_y = p_rect.centerx, p_rect.centery
                    hop_y = 0.0
                    radius = p_rect.width // 2

                is_selectable = (color == curr_player and is_human and
                                 idx in legal_piece_indices and self.human_phase == 'SELECT_PIECE')

                draw_glossy_pawn(
                    self.screen, cx=center_x, cy=center_y, radius=radius,
                    color_key=color, scale=1.0, is_active=is_selectable,
                    pulse_offset=pulse, hop_y=hop_y
                )

                # Piece number on jewel token
                num_col = (45, 25, 8) if color == 'yellow' else (255, 255, 255)
                num_surf = self.font_small.render(str(idx + 1), True, num_col)
                self.screen.blit(num_surf, (center_x - num_surf.get_width() // 2,
                                            int(center_y + hop_y) - num_surf.get_height() // 2))

    def _render_center_dice(self):
        """Render 3D physical dice sitting on the star in the middle of the four triangles."""
        if not self.game:
            return
        cx, cy = grid_to_screen(7, 7, GRID_CELL_SIZE)
        center_sq_w = 3 * GRID_CELL_SIZE
        dice_size = int(center_sq_w * 0.50)  # 50% of center square (~66px)
        self.center_dice_hitbox = pygame.Rect(cx - dice_size // 2, cy - dice_size // 2, dice_size, dice_size)

        curr_player = self.game.state.current_player
        is_human_player = isinstance(self.game.agents[curr_player], HumanAgent)
        is_human_turn = is_human_player and (self.turn_state == 'WAIT_ROLL' or self.human_phase == 'NEED_ROLL')

        self.dice_3d.render(
            self.screen, cx=cx, cy=cy, size=dice_size,
            current_player=curr_player, is_human_turn=is_human_turn,
            sound_mgr=self.sound
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Side Control Panel (Carved Wooden Style)
    # ──────────────────────────────────────────────────────────────────────────

    def _render_side_panel(self):
        """Render carved wooden side HUD with player cards, tumbling dice, and logs."""
        th = self.theme
        is_dark = (self.theme_name == 'dark')
        panel_rect = pygame.Rect(BOARD_PIXEL_DIM, 0, SIDE_PANEL_WIDTH, WINDOW_HEIGHT)

        # Carved Wooden Panel Background
        draw_gradient_rect(self.screen, panel_rect, th['panel_bg'], th['panel_card_bg'])
        pygame.draw.line(self.screen, th['board_frame_outer'], (BOARD_PIXEL_DIM, 0), (BOARD_PIXEL_DIM, WINDOW_HEIGHT), 3)

        x_margin = BOARD_PIXEL_DIM + 20
        mouse_pos = pygame.mouse.get_pos()
        is_mouse_down = pygame.mouse.get_pressed()[0]

        # Brand Header: "Ludo Verse"
        draw_outlined_text(
            self.screen, text="Ludo Verse", font=self.font_title,
            fill_color=(255, 215, 25), outline_color=(50, 24, 6), outline_width=2,
            center_or_pos=(x_margin, 12), is_centered=False, shadow_offset=(0, 2), shadow_color=(25, 12, 4)
        )

        # Top-Right Small Wooden Icons
        self._render_header_icons()

        # Turn / Mode Subtitle
        mode_str = self.current_game_mode.replace('_', ' ')
        turn_lbl = self.font_small.render(f"Turn {self.game.turn_count}  |  {mode_str}", True, th['text_muted'])
        self.screen.blit(turn_lbl, (x_margin, 46))

        # 4 Player Status Cards
        curr_player = self.game.state.current_player
        card_y = 70
        card_w = 300
        card_h = 44

        for color in COLORS:
            c_rect = pygame.Rect(x_margin, card_y, card_w, card_h)
            is_active = (color == curr_player)
            ptheme = PLAYER_THEMES[color]

            # Inset wooden card slot
            bg = th['panel_card_active'] if is_active else th['panel_card_bg']
            pygame.draw.rect(self.screen, bg, c_rect, border_radius=8)
            border_c = (255, 215, 25) if is_active else th['panel_border']
            border_w = 2 if is_active else 1
            pygame.draw.rect(self.screen, border_c, c_rect, border_w, border_radius=8)

            # Player Glossy Gem Pip
            draw_glossy_pawn(self.screen, cx=x_margin + 18, cy=card_y + 22, radius=8, color_key=color, scale=1.0)

            raw_agent_name = self.game.agents[color].name
            disp_agent = "Expectimax" if raw_agent_name.startswith("Expectimax") else raw_agent_name
            fin_count = self.game.state.pieces_finished(color)
            p_text = f"{color.capitalize()} ({disp_agent})"
            fin_text = f"{fin_count}/4 Pieces Home"

            name_surf = self.font_body_bold.render(p_text, True, th['text_white'])
            fin_color = (255, 215, 45) if fin_count == 4 else th['text_cream']
            fin_surf = self.font_small.render(fin_text, True, fin_color)

            self.screen.blit(name_surf, (x_margin + 36, card_y + 4))
            self.screen.blit(fin_surf, (x_margin + 36, card_y + 24))

            if is_active:
                badge_w, badge_h = 76, 22
                badge_rect = pygame.Rect(x_margin + card_w - badge_w - 6, card_y + 11, badge_w, badge_h)
                pygame.draw.rect(self.screen, (60, 32, 10), badge_rect, border_radius=11)
                pygame.draw.rect(self.screen, (255, 215, 25), badge_rect, 1, border_radius=11)
                turn_mark = self.font_small.render("ACTIVE", True, (255, 215, 25))
                self.screen.blit(turn_mark, (badge_rect.centerx - turn_mark.get_width() // 2,
                                            badge_rect.centery - turn_mark.get_height() // 2))

            card_y += 48

        # Last Roll Compact Tile
        last_roll_box = pygame.Rect(x_margin, 268, 300, 68)
        disp_dice = self.last_dice if self.last_dice is not None else 1
        disp_player = self.last_dice_player or curr_player
        render_last_roll_tile(self.screen, last_roll_box, value=disp_dice, player_color=disp_player, is_dark=is_dark)

        # Roll Dice Button (Wooden Plank Button)
        is_human_player = isinstance(self.game.agents[curr_player], HumanAgent)
        is_human_turn = is_human_player and (self.turn_state == 'WAIT_ROLL' or self.human_phase == 'NEED_ROLL')
        roll_hov = self.btn_roll.collidepoint(mouse_pos) and is_human_turn
        roll_state = 'pressed' if (roll_hov and is_mouse_down) else ('hover' if roll_hov else 'normal')
        if not is_human_player:
            roll_state = 'disabled'
            roll_title = "Waiting for turn..."
        elif is_human_turn:
            roll_title = "Roll Dice (Click or Space)"
        elif self.turn_state in ('DICE_ROLLING', 'DICE_HOLDING'):
            roll_state = 'disabled'
            roll_title = "Rolling..."
        elif self.turn_state == 'SELECT_PIECE' or self.human_phase == 'SELECT_PIECE':
            roll_state = 'disabled'
            roll_title = "Select Piece to Move"
        else:
            roll_state = 'disabled'
            roll_title = "Moving..."

        draw_wood_button(self.screen, self.btn_roll, title=roll_title, font=self.font_subheading, state=roll_state, is_dark=is_dark)

        # Activity Log (Recessed Wooden Niche)
        self._render_activity_log(x_margin, 404, 300, 144)

        # Action Buttons: Restart & Menu
        btns = [
            (self.btn_restart, "Restart"),
            (self.btn_main_menu, "Main Menu"),
        ]
        for btn, lbl_txt in btns:
            b_hov = btn.collidepoint(mouse_pos)
            b_state = 'pressed' if (b_hov and is_mouse_down) else ('hover' if b_hov else 'normal')
            draw_wood_button(self.screen, btn, title=lbl_txt, font=self.font_btn, state=b_state, is_dark=is_dark)

        # Speed / Pause Toggle Button
        spd_lbl = f"Speed: {self.speed_mode.capitalize()}"
        s_hov = self.btn_speed.collidepoint(mouse_pos)
        s_state = 'pressed' if (s_hov and is_mouse_down) else ('hover' if s_hov else 'normal')
        draw_wood_button(self.screen, self.btn_speed, title=spd_lbl, font=self.font_btn, state=s_state, is_dark=is_dark)

    def _render_header_icons(self):
        """Draw small wooden square buttons for Sun, Moon, and Sound toggles at top right."""
        th = self.theme
        mouse_pos = pygame.mouse.get_pos()
        is_mouse_down = pygame.mouse.get_pressed()[0]
        is_dark = (self.theme_name == 'dark')

        icons = [
            (self.btn_sun, 'sun', self.theme_name == 'light'),
            (self.btn_moon, 'moon', self.theme_name == 'dark'),
            (self.btn_sound, 'sound', not self.sound.muted)
        ]

        for btn, icon_type, is_active in icons:
            hov = btn.collidepoint(mouse_pos)
            state = 'pressed' if (hov and is_mouse_down) else ('hover' if hov else 'normal')

            # Small wooden button frame
            btn_r = btn.copy()
            if state == 'pressed':
                btn_r.y += 2

            top_c = th['btn_wood_hover_top'] if (hov or is_active) else th['btn_wood_top']
            bot_c = th['btn_wood_hover_bottom'] if (hov or is_active) else th['btn_wood_bottom']
            draw_gradient_rect(self.screen, btn_r, top_c, bot_c, border_radius=6)
            border_c = (255, 215, 25) if is_active else th['btn_wood_border']
            pygame.draw.rect(self.screen, border_c, btn_r, width=2 if is_active else 1, border_radius=6)

            # Icon graphics
            cx, cy = btn_r.centerx, btn_r.centery
            icon_c = (255, 245, 180) if is_active else (255, 255, 255)

            if icon_type == 'sun':
                pygame.draw.circle(self.screen, icon_c, (cx, cy), 4)
                for i in range(8):
                    a = i * math.pi / 4
                    x1 = cx + 6 * math.cos(a)
                    y1 = cy + 6 * math.sin(a)
                    x2 = cx + 8 * math.cos(a)
                    y2 = cy + 8 * math.sin(a)
                    pygame.draw.line(self.screen, icon_c, (x1, y1), (x2, y2), 1)

            elif icon_type == 'moon':
                pygame.draw.circle(self.screen, icon_c, (cx, cy), 6)
                pygame.draw.circle(self.screen, top_c, (cx + 3, cy - 2), 5)

            elif icon_type == 'sound':
                pygame.draw.polygon(self.screen, icon_c, [(cx - 5, cy - 3), (cx - 2, cy - 3), (cx + 3, cy - 6), (cx + 3, cy + 6), (cx - 2, cy + 3), (cx - 5, cy + 3)])
                if not self.sound.muted:
                    pygame.draw.arc(self.screen, icon_c, (cx + 1, cy - 5, 6, 10), -math.pi / 2, math.pi / 2, 2)
                else:
                    pygame.draw.line(self.screen, (225, 45, 45), (cx - 5, cy - 5), (cx + 5, cy + 5), 2)

    def _render_activity_log(self, x: int, y: int, w: int, h: int):
        """Draw timeline activity log in a carved recessed wooden niche."""
        th = self.theme
        log_rect = pygame.Rect(x, y, w, h)
        draw_gradient_rect(self.screen, log_rect, th['panel_subcard'], th['panel_card_bg'], border_radius=8)
        pygame.draw.rect(self.screen, th['panel_border'], log_rect, 1, border_radius=8)

        # Title
        title_surf = self.font_small.render("ACTIVITY LOG", True, (255, 215, 25))
        self.screen.blit(title_surf, (x + 12, y + 8))
        pygame.draw.line(self.screen, th['panel_border'], (x + 10, y + 26), (x + w - 10, y + 26), 1)

        # Display last 5 entries
        visible_entries = self.activity_log[-5:]
        line_y = y + 32
        for entry in visible_entries:
            p_col = entry['player']
            dot_color = PLAYER_ACCENTS.get(p_col, (255, 215, 25))
            pygame.draw.circle(self.screen, dot_color, (x + 16, line_y + 8), 3)

            txt = self.font_small.render(entry['text'], True, th['text_cream'])
            self.screen.blit(txt, (x + 26, line_y))
            line_y += 21

    # ──────────────────────────────────────────────────────────────────────────
    # Leaderboard Screen (Wooden Styling)
    # ──────────────────────────────────────────────────────────────────────────

    def _render_leaderboard(self):
        """Render complete partitioned Leaderboard (Human vs AI & AI vs AI)."""
        is_dark = (self.theme_name == 'dark')
        th = self.theme
        cx = self.width // 2

        # 1. Wood Background
        bg_surf = generate_wood_texture(self.width, self.height, is_dark_wood=is_dark)
        self.screen.blit(bg_surf, (0, 0))

        # 2. Wooden Back Button
        mouse_pos = pygame.mouse.get_pos()
        is_mouse_down = pygame.mouse.get_pressed()[0]
        back_hov = self.btn_lead_back.collidepoint(mouse_pos)
        back_state = 'pressed' if (back_hov and is_mouse_down) else ('hover' if back_hov else 'normal')
        draw_wood_button(self.screen, self.btn_lead_back, title="< Back to Menu", font=self.font_btn, state=back_state, is_dark=is_dark)

        # 3. Screen Title
        draw_outlined_text(
            self.screen, text="LUDO VERSE LEADERBOARD", font=self.font_title,
            fill_color=(255, 215, 25), outline_color=(45, 22, 6), outline_width=2,
            center_or_pos=(cx, 32), is_centered=True, shadow_offset=(0, 2), shadow_color=(25, 12, 4)
        )

        self._render_header_icons()

        # 4. Mode Selection Wooden Tabs
        tabs = [
            (self.btn_lead_tab_human, "Human vs AI", self.leaderboard_tab == 'human'),
            (self.btn_lead_tab_ai,    "AI vs AI Championship", self.leaderboard_tab == 'ai'),
        ]
        for t_btn, t_label, is_sel in tabs:
            t_hov = t_btn.collidepoint(mouse_pos)
            t_state = 'pressed' if (t_hov and is_mouse_down) else ('hover' if (t_hov or is_sel) else 'normal')
            draw_wood_button(self.screen, t_btn, title=t_label, font=self.font_btn, state=t_state, is_dark=is_dark)
            if is_sel:
                pygame.draw.line(self.screen, (255, 215, 25), (t_btn.left + 8, t_btn.bottom - 2), (t_btn.right - 8, t_btn.bottom - 2), 3)

        # 5. Tab Content
        if self.leaderboard_tab == 'human':
            self._render_leaderboard_human(self.leaderboard_mgr.get_human_stats())
        else:
            self._render_leaderboard_ai(self.leaderboard_mgr.get_ai_stats())

    def _draw_shadow_text(self, text: str, font: pygame.font.Font, color: Tuple[int, int, int],
                          pos: Tuple[int, int], shadow_color: Tuple[int, int, int] = (58, 31, 10),
                          offset: Tuple[int, int] = (1, 1)):
        """Blit text with a high-contrast 1-2px shadow outline for readability on wood."""
        sh_surf = font.render(text, True, shadow_color)
        self.screen.blit(sh_surf, (pos[0] + offset[0], pos[1] + offset[1]))
        txt_surf = font.render(text, True, color)
        self.screen.blit(txt_surf, pos)

    def _render_leaderboard_human(self, h_data: dict):
        """Render Human vs AI career stats and match history with high-contrast text."""
        th = self.theme
        is_dark = (self.theme_name == 'dark')

        # 4 Summary KPI Cards
        cards = [
            ("MATCHES PLAYED", str(h_data.get('games_played', 0)), "Career Matches"),
            ("HUMAN WINS", str(h_data.get('human_wins', 0)), f"{round((h_data.get('human_wins', 0) / max(1, h_data.get('games_played', 1))) * 100, 1)}% Win Rate"),
            ("PIECES CAPTURED", str(h_data.get('total_captures', 0)), "Tokens Sent to Base"),
            ("PIECES FINISHED", str(h_data.get('pieces_finished', 0)), "Reached Center Goal"),
        ]
        card_w, card_h = 210, 72
        start_x = 55
        for i, (title, val, sub) in enumerate(cards):
            c_rect = pygame.Rect(start_x + i * 230, 116, card_w, card_h)
            draw_wood_plank(self.screen, c_rect, is_dark=is_dark, border_radius=8, show_nail_rivets=False)

            self._draw_shadow_text(title, self.font_small, th['text_cream'], (c_rect.x + 12, c_rect.y + 8), shadow_color=th['text_shadow'])
            val_col = (255, 215, 25) if i == 1 else th['text_white']
            self._draw_shadow_text(val, self.font_heading, val_col, (c_rect.x + 12, c_rect.y + 26), shadow_color=th['text_shadow'])
            self._draw_shadow_text(sub, self.font_small, th['text_cream'], (c_rect.x + 12, c_rect.y + 50), shadow_color=th['text_shadow'])

        # Head-to-Head Table against AI Opponents
        table_box = pygame.Rect(55, 202, 890, 185)
        draw_wood_plank(self.screen, table_box, is_dark=is_dark, border_radius=8, show_nail_rivets=False)

        # Header Row
        pygame.draw.rect(self.screen, th['panel_subcard'], pygame.Rect(55, 202, 890, 32), border_top_left_radius=8, border_top_right_radius=8)
        cols = [("AI Opponent", 75), ("Encounters", 255), ("Human Wins", 380), ("AI Wins", 505), ("Win Rate", 630), ("Threat Level / Strategy Profile", 735)]
        for col_name, cx in cols:
            self._draw_shadow_text(col_name, self.font_small, th['text_cream'], (cx, 209), shadow_color=th['text_shadow'])

        opponents = h_data.get('opponents', {})
        row_y = 242
        for opp_key, opp_info in opponents.items():
            opp_name = "Expectimax AI" if opp_key == 'expectimax' else f"{opp_key.capitalize()} AI"
            enc = opp_info.get('encounters', 0)
            h_wins = opp_info.get('human_wins', 0)
            a_wins = opp_info.get('ai_wins', 0)
            w_rate = f"{round((h_wins / max(1, enc)) * 100, 1)}%"
            threat = opp_info.get('threat', 'Standard')

            # Semi-transparent dark overlay behind row for high contrast (4.5:1+)
            row_overlay = pygame.Surface((882, 38), pygame.SRCALPHA)
            row_overlay.fill(th['table_row_bg'])
            self.screen.blit(row_overlay, (59, row_y - 2))

            dot_col = (255, 205, 0) if opp_key == 'expectimax' else ((40, 120, 245) if opp_key == 'aggressive' else (230, 50, 65))
            pygame.draw.circle(self.screen, dot_col, (75, row_y + 10), 5)
            self._draw_shadow_text(opp_name, self.font_body_bold, th['text_white'], (90, row_y + 2), shadow_color=th['text_shadow'])

            # Encounters: pure white with dark shadow
            self._draw_shadow_text(str(enc), self.font_body, th['text_white'], (265, row_y + 2), shadow_color=th['text_shadow'])

            # Human Wins: pure white bold with green indicator dot beside it
            pygame.draw.circle(self.screen, (70, 205, 90), (385, row_y + 11), 3.5)
            self._draw_shadow_text(str(h_wins), self.font_body_bold, th['text_white'], (395, row_y + 2), shadow_color=th['text_shadow'])

            # AI Wins: pure white bold with red indicator dot beside it (remove faded red)
            pygame.draw.circle(self.screen, (235, 65, 65), (510, row_y + 11), 3.5)
            self._draw_shadow_text(str(a_wins), self.font_body_bold, th['text_white'], (520, row_y + 2), shadow_color=th['text_shadow'])

            # Win Rate: Gold
            self._draw_shadow_text(w_rate, self.font_body_bold, (255, 215, 25), (640, row_y + 2), shadow_color=th['text_shadow'])

            # Threat Level: Cream (#FFF3D6), font_body (larger and readable!)
            self._draw_shadow_text(threat, self.font_body, th['text_cream'], (735, row_y + 2), shadow_color=th['text_shadow'])

            pygame.draw.line(self.screen, th['panel_border'], (70, row_y + 34), (930, row_y + 34), 1)
            row_y += 42

        # Recent Match History
        hist_box = pygame.Rect(55, 400, 890, 225)
        draw_wood_plank(self.screen, hist_box, is_dark=is_dark, border_radius=8, show_nail_rivets=False)

        pygame.draw.rect(self.screen, th['panel_subcard'], pygame.Rect(55, 400, 890, 32), border_top_left_radius=8, border_top_right_radius=8)
        self._draw_shadow_text("RECENT MATCH HISTORY (HUMAN VS AI)", self.font_small, (255, 215, 25), (75, 407), shadow_color=th['text_shadow'])

        recents = h_data.get('recent_history', [])[:4]
        h_y = 440
        for m in recents:
            res = m.get('result', 'VICTORY')
            res_bg = (35, 130, 55) if res == 'VICTORY' else (165, 45, 52)
            res_pill = pygame.Rect(75, h_y + 2, 85, 24)
            pygame.draw.rect(self.screen, res_bg, res_pill, border_radius=6)
            res_txt = self.font_small.render(res, True, (255, 255, 255))
            self.screen.blit(res_txt, (res_pill.centerx - res_txt.get_width() // 2, res_pill.centery - res_txt.get_height() // 2))

            detail_str = f"Human (Yellow) vs 3×AI Showdown  •  Turns Taken: {m.get('turns', 0)}  •  Captures: {m.get('captures', 0)}  •  {m.get('date', 'Today')}"
            self._draw_shadow_text(detail_str, self.font_body, th['text_cream'], (175, h_y + 4), shadow_color=th['text_shadow'])
            pygame.draw.line(self.screen, th['panel_border'], (75, h_y + 34), (930, h_y + 34), 1)
            h_y += 42

    def _render_leaderboard_ai(self, ai_data: dict):
        """Render AI vs AI Championship Table with high-contrast text."""
        th = self.theme
        is_dark = (self.theme_name == 'dark')
        models = ai_data.get('models', {})
        total_m = ai_data.get('total_matches', 0)
        exp_m = models.get('Expectimax', {})
        exp_wins = exp_m.get('wins', 0)
        exp_rate = exp_m.get('win_rate', 0.0)
        total_caps = sum(m.get('total_captures', 0) for m in models.values())
        fastest_win = min((m.get('fastest_win', 999) for m in models.values() if m.get('fastest_win', 0) > 0), default=312)

        # 4 Summary KPI Cards
        cards = [
            ("SHOWDOWNS PLAYED", str(total_m), "4-Way AI Tournaments"),
            ("EXPECTIMAX 1st", str(exp_wins), f"{exp_rate}% Win Rate (Champion)"),
            ("TOTAL AI CAPTURES", str(total_caps), "Tokens Sent to Base"),
            ("RECORD FASTEST WIN", f"{fastest_win} turns", "Best Tournament Run"),
        ]
        card_w, card_h = 210, 72
        start_x = 55
        for i, (title, val, sub) in enumerate(cards):
            c_rect = pygame.Rect(start_x + i * 230, 116, card_w, card_h)
            draw_wood_plank(self.screen, c_rect, is_dark=is_dark, border_radius=8, show_nail_rivets=False)

            self._draw_shadow_text(title, self.font_small, th['text_cream'], (c_rect.x + 12, c_rect.y + 8), shadow_color=th['text_shadow'])
            val_col = (255, 215, 25) if i == 1 else th['text_white']
            self._draw_shadow_text(val, self.font_heading, val_col, (c_rect.x + 12, c_rect.y + 26), shadow_color=th['text_shadow'])
            self._draw_shadow_text(sub, self.font_small, th['text_cream'], (c_rect.x + 12, c_rect.y + 50), shadow_color=th['text_shadow'])

        # 4-Way Model Championship Table
        table_box = pygame.Rect(55, 208, 890, 260)
        draw_wood_plank(self.screen, table_box, is_dark=is_dark, border_radius=8, show_nail_rivets=False)

        # Header Row
        pygame.draw.rect(self.screen, th['panel_subcard'], pygame.Rect(55, 208, 890, 34), border_top_left_radius=8, border_top_right_radius=8)
        cols = [("Rank", 75), ("AI Architecture", 155), ("Matches", 380), ("Wins (1st)", 480), ("Win Rate %", 590), ("Avg Goal /4", 705), ("Captures", 805), ("Fastest", 885)]
        for col_name, cx in cols:
            self._draw_shadow_text(col_name, self.font_small, th['text_cream'], (cx, 216), shadow_color=th['text_shadow'])

        row_y = 252
        medals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
        for name, m in models.items():
            rank = m.get('rank', 1)
            m_col = m.get('color', (255, 215, 0))

            # Semi-transparent dark overlay behind row for high contrast (4.5:1+)
            row_overlay = pygame.Surface((882, 42), pygame.SRCALPHA)
            row_overlay.fill(th['table_row_bg'])
            self.screen.blit(row_overlay, (59, row_y - 2))

            # Rank & Medal
            rank_col = (255, 215, 25) if rank == 1 else th['text_white']
            self._draw_shadow_text(medals.get(rank, f"{rank}th"), self.font_body_bold, rank_col, (75, row_y + 4), shadow_color=th['text_shadow'])

            # Dot & Architecture name
            pygame.draw.circle(self.screen, m_col, (165, row_y + 12), 6)
            self._draw_shadow_text(f"{name} AI", self.font_body_bold, th['text_white'], (180, row_y + 4), shadow_color=th['text_shadow'])

            # Metrics (pure white and gold with shadow)
            self._draw_shadow_text(str(m.get('games', 0)), self.font_body, th['text_white'], (390, row_y + 4), shadow_color=th['text_shadow'])
            win_col = (255, 215, 25) if rank == 1 else th['text_white']
            self._draw_shadow_text(str(m.get('wins', 0)), self.font_body_bold, win_col, (495, row_y + 4), shadow_color=th['text_shadow'])
            self._draw_shadow_text(f"{m.get('win_rate', 0)}%", self.font_body_bold, win_col, (600, row_y + 4), shadow_color=th['text_shadow'])
            self._draw_shadow_text(str(m.get('avg_goal', 0)), self.font_body, th['text_white'], (715, row_y + 4), shadow_color=th['text_shadow'])
            self._draw_shadow_text(str(m.get('total_captures', 0)), self.font_body, th['text_white'], (815, row_y + 4), shadow_color=th['text_shadow'])
            self._draw_shadow_text(f"{m.get('fastest_win', 0)} turns", self.font_body, th['text_cream'], (885, row_y + 4), shadow_color=th['text_shadow'])

            pygame.draw.line(self.screen, th['panel_border'], (75, row_y + 44), (930, row_y + 44), 1)
            row_y += 50

    # ──────────────────────────────────────────────────────────────────────────
    # Carved Wooden Confirmation Modals
    # ──────────────────────────────────────────────────────────────────────────

    def _render_confirmation_modal(self):
        """Draw carved wooden modal dialog for Restart or Main Menu confirmation."""
        # Darkened backdrop overlay
        backdrop = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 160))
        self.screen.blit(backdrop, (0, 0))

        is_dark = (self.theme_name == 'dark')
        th = self.theme
        mouse_pos = pygame.mouse.get_pos()
        is_mouse_down = pygame.mouse.get_pressed()[0]

        # Carved Wooden Modal Window
        draw_wood_plank(self.screen, self.modal_rect, is_dark=is_dark, border_radius=16, show_nail_rivets=True)

        is_menu_action = (self.confirm_dialog == 'menu')
        title_txt = "Return to Main Menu?" if is_menu_action else "Restart Match?"
        msg_txt = "Your current match progress will be lost."

        draw_outlined_text(
            self.screen, text=title_txt, font=self.font_title,
            fill_color=(255, 215, 25), outline_color=(45, 22, 6), outline_width=2,
            center_or_pos=(self.modal_rect.centerx, self.modal_rect.y + 40), is_centered=True
        )

        msg_surf = self.font_body_bold.render(msg_txt, True, th['text_cream'])
        self.screen.blit(msg_surf, (self.modal_rect.centerx - msg_surf.get_width() // 2, self.modal_rect.y + 78))

        # Confirm & Cancel Wooden Buttons
        y_hov = self.btn_modal_yes.collidepoint(mouse_pos)
        y_state = 'pressed' if (y_hov and is_mouse_down) else ('hover' if y_hov else 'normal')
        c_hov = self.btn_modal_cancel.collidepoint(mouse_pos)
        c_state = 'pressed' if (c_hov and is_mouse_down) else ('hover' if c_hov else 'normal')

        yes_label = "Yes, Go to Menu" if is_menu_action else "Yes, Restart"
        draw_wood_button(self.screen, self.btn_modal_yes, title=yes_label, font=self.font_btn, state=y_state, is_dark=is_dark)
        draw_wood_button(self.screen, self.btn_modal_cancel, title="Cancel", font=self.font_btn, state=c_state, is_dark=is_dark)

    def _render_game_over_screen(self):
        """Render victory celebration screen with winner standings."""
        winner = self.game.get_winner()
        is_dark = (self.theme_name == 'dark')
        th = self.theme
        cx = self.width // 2

        # Draw falling victory confetti particles
        for c in self.confetti:
            pygame.draw.rect(self.screen, c['color'], (c['x'], c['y'], c['size'], c['size']))

        # Main Wooden Podium Plaque
        modal_w, modal_h = 560, 480
        mx = cx - modal_w // 2
        my = self.height // 2 - modal_h // 2
        plaque_rect = pygame.Rect(mx, my, modal_w, modal_h)
        draw_wood_plank(self.screen, plaque_rect, is_dark=is_dark, border_radius=18, show_nail_rivets=True)

        w_col = winner.capitalize() if winner else "Match"
        draw_outlined_text(
            self.screen, text=f"{w_col} Wins The Match!", font=self.font_hero,
            fill_color=(255, 215, 25), outline_color=(45, 22, 6), outline_width=3,
            center_or_pos=(cx, my + 50), is_centered=True
        )

        sub_msg = self.font_heading.render(f"Completed in {self.game.turn_count} turns", True, th['text_cream'])
        self.screen.blit(sub_msg, (cx - sub_msg.get_width() // 2, my + 98))

        # Standings table
        rankings = []
        for color in COLORS:
            agent_name = self.game.agents[color].name
            fin = self.game.state.pieces_finished(color)
            is_win = (color == winner)
            rankings.append({
                'color': color,
                'name': agent_name,
                'finished': fin,
                'is_winner': is_win
            })

        rankings.sort(key=lambda r: (1 if r['is_winner'] else 0, r['finished']), reverse=True)
        medals = ["1st [WINNER]", "2nd Place", "3rd Place", "4th Place"]
        row_y = my + 148

        for rank_idx, r in enumerate(rankings):
            row_rect = pygame.Rect(mx + 30, row_y, modal_w - 60, 48)
            ptheme = PLAYER_THEMES[r['color']]
            pygame.draw.rect(self.screen, th['panel_card_bg'], row_rect, border_radius=8)
            pygame.draw.rect(self.screen, (255, 215, 25) if r['is_winner'] else th['panel_border'], row_rect, 1, border_radius=8)

            draw_glossy_pawn(self.screen, cx=mx + 56, cy=row_y + 24, radius=9, color_key=r['color'], scale=1.0)
            medal_lbl = medals[rank_idx]
            self.screen.blit(self.font_body_bold.render(medal_lbl, True, (255, 215, 25) if r['is_winner'] else th['text_white']), (mx + 80, row_y + 14))

            c_name = r['color'].capitalize()
            disp_a = "Expectimax" if r['name'].startswith("Expectimax") else r['name']
            self.screen.blit(self.font_body.render(f"{c_name} ({disp_a})", True, th['text_cream']), (mx + 220, row_y + 14))
            self.screen.blit(self.font_body_bold.render(f"{r['finished']}/4 Finished", True, (255, 215, 25) if r['finished'] == 4 else th['text_white']), (mx + 410, row_y + 14))

            row_y += 56

        # Action Buttons: Play Again & Return to Menu
        mouse_pos = pygame.mouse.get_pos()
        is_mouse_down = pygame.mouse.get_pressed()[0]

        p_hov = self.btn_play_again.collidepoint(mouse_pos)
        p_state = 'pressed' if (p_hov and is_mouse_down) else ('hover' if p_hov else 'normal')
        e_hov = self.btn_game_over_exit.collidepoint(mouse_pos)
        e_state = 'pressed' if (e_hov and is_mouse_down) else ('hover' if e_hov else 'normal')

        draw_wood_button(self.screen, self.btn_play_again, title="Play Again", font=self.font_btn, state=p_state, is_dark=is_dark)
        draw_wood_button(self.screen, self.btn_game_over_exit, title="Return to Menu", font=self.font_btn, state=e_state, is_dark=is_dark)

    def _record_game_over(self, winner: Optional[str]):
        """Record completed game results into persistent leaderboard database."""
        if not self.game:
            return
        turns = self.game.turn_count
        if self.current_game_mode == 'HUMAN_VS_AI':
            is_win = (winner == 'yellow')
            caps = sum(1 for entry in self.activity_log if entry['player'] == 'yellow' and entry['type'] == 'capture')
            fin = self.game.state.pieces_finished('yellow')
            self.leaderboard_mgr.record_human_match(winner_color=winner, is_human_win=is_win, turns=turns, captures=caps, pieces_finished=fin)
        else:
            stats = {}
            for c in COLORS:
                agent_name = self.game.agents[c].name
                caps = sum(1 for entry in self.activity_log if entry['player'] == c and entry['type'] == 'capture')
                stats[agent_name] = {'captures': caps, 'finished': self.game.state.pieces_finished(c)}
            win_agent = self.game.agents[winner].name if winner else 'Expectimax'
            self.leaderboard_mgr.record_ai_match(winner_model=win_agent, turns=turns, stats_by_model=stats)

    # ──────────────────────────────────────────────────────────────────────────
    # Main Event Loop (60 FPS Execution)
    # ──────────────────────────────────────────────────────────────────────────

    def run_loop(self):
        """Run interactive 60 FPS Pygame loop."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)

            self.update()
            self.render()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()
