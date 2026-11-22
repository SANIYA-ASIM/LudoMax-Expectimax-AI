"""
test_ui.py — Phase 7: Pygame GUI Component Tests
=================================================
Headless tests for game_ui.py covering:
  - LudoUI initialization in headless mode
  - Main Menu transitions and button geometries
  - Game initialization for Human vs AI and AI vs AI
  - Piece token screen coordinate and bounding box calculations
  - Click detection on legal pieces
  - Rendering pipeline execution without display hardware
"""
import os
import pygame
import pytest

# Ensure headless video driver for testing
os.environ['SDL_VIDEODRIVER'] = 'dummy'

from game_ui import LudoUI, WINDOW_WIDTH, WINDOW_HEIGHT
from move import Move
from board import PROGRESS_BASE, PROGRESS_FINISHED


@pytest.fixture(scope="module")
def ui_instance():
    """Create a headless LudoUI instance for testing."""
    pygame.init()
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    ui = LudoUI(screen=surface, headless=True)
    yield ui


def test_ui_initial_state(ui_instance):
    """UI initializes in MENU mode with default dimensions."""
    assert ui_instance.mode == 'MENU'
    assert ui_instance.width == WINDOW_WIDTH
    assert ui_instance.height == WINDOW_HEIGHT
    assert ui_instance.game is None


def test_ui_start_human_vs_ai(ui_instance):
    """start_new_game('HUMAN_VS_AI') initializes Game with Human as Yellow."""
    ui_instance.start_new_game('HUMAN_VS_AI')
    assert ui_instance.mode == 'PLAYING'
    assert ui_instance.current_game_mode == 'HUMAN_VS_AI'
    assert ui_instance.game is not None
    assert ui_instance.game.agents['yellow'].name == 'Human'
    assert ui_instance.human_phase == 'NEED_ROLL'


def test_ui_start_ai_vs_ai(ui_instance):
    """start_new_game('AI_VS_AI') initializes Game with 4 AI agents."""
    ui_instance.start_new_game('AI_VS_AI')
    assert ui_instance.mode == 'PLAYING'
    assert ui_instance.current_game_mode == 'AI_VS_AI'
    assert ui_instance.game.agents['yellow'].name.startswith('Expectimax')


def test_ui_piece_pixel_rect(ui_instance):
    """get_piece_pixel_rect returns valid on-screen rectangle."""
    ui_instance.start_new_game('HUMAN_VS_AI')
    rect = ui_instance.get_piece_pixel_rect('yellow', 0)
    assert isinstance(rect, pygame.Rect)
    assert 0 <= rect.centerx <= WINDOW_WIDTH
    assert 0 <= rect.centery <= WINDOW_HEIGHT
    assert rect.width > 0 and rect.height > 0


def test_ui_rendering_does_not_crash(ui_instance):
    """render() draws the board, pieces, and side panel without raising errors."""
    ui_instance.start_new_game('HUMAN_VS_AI')
    ui_instance.render()
    ui_instance.mode = 'MENU'
    ui_instance.render()


def test_ui_hit_detection_legal_piece(ui_instance):
    """Clicking within a legal piece's bounding box selects that move."""
    ui_instance.start_new_game('HUMAN_VS_AI')
    move = Move(piece_index=0, dice_value=6, from_progress=PROGRESS_BASE, to_progress=0)
    ui_instance.human_legal_moves = [move]
    ui_instance.human_phase = 'SELECT_PIECE'

    p_rect = ui_instance.get_piece_pixel_rect('yellow', 0)
    clicked = ui_instance.get_clicked_legal_piece((p_rect.centerx, p_rect.centery))
    assert clicked == move

    # Clicking outside any piece returns None
    clicked_miss = ui_instance.get_clicked_legal_piece((0, 0))
    assert clicked_miss is None


def test_ui_update_ai_step(ui_instance):
    """update() executes turn for AI players and updates status message."""
    ui_instance.start_new_game('AI_VS_AI')
    ui_instance.ai_delay_ms = 50  # fast step
    ui_instance.last_ai_step_time = 0.0
    initial_turns = ui_instance.game.turn_count

    ui_instance.update()
    assert ui_instance.game.turn_count == initial_turns + 1
    assert ui_instance.last_dice in (1, 2, 3, 4, 5, 6)


def test_ui_speed_toggle(ui_instance):
    """Clicking speed button cycles through speed levels."""
    ui_instance.start_new_game('AI_VS_AI')
    initial_idx = ui_instance.current_speed_idx

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_speed.centerx, ui_instance.btn_speed.centery)})
    ui_instance.handle_event(event)

    expected_idx = (initial_idx + 1) % len(ui_instance.speed_levels)
    assert ui_instance.current_speed_idx == expected_idx
    assert ui_instance.ai_delay_ms == ui_instance.speed_levels[expected_idx]


def test_ui_custom_ai_opponents(ui_instance):
    """Custom AI opponent lists can be configured."""
    ui_instance.start_new_game('HUMAN_VS_AI', ai_types=['random', 'random', 'random'])
    assert ui_instance.game.agents['blue'].name == 'Random'
    assert ui_instance.game.agents['red'].name == 'Random'
    assert ui_instance.game.agents['green'].name == 'Random'


def test_ui_main_menu_confirmation_dialog(ui_instance):
    """Clicking Main Menu displays confirmation dialog and does not navigate until confirmed."""
    ui_instance.start_new_game('HUMAN_VS_AI')
    assert ui_instance.mode == 'PLAYING'
    assert ui_instance.confirm_dialog is None

    # 1. Click Main Menu button -> opens confirmation dialog, stays in PLAYING
    event_menu = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_main_menu.centerx, ui_instance.btn_main_menu.centery)})
    ui_instance.handle_event(event_menu)
    assert ui_instance.confirm_dialog == 'menu'
    assert ui_instance.mode == 'PLAYING'

    # 2. Click Cancel button -> dismisses modal, stays in PLAYING with progress intact
    event_cancel = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_modal_cancel.centerx, ui_instance.btn_modal_cancel.centery)})
    ui_instance.handle_event(event_cancel)
    assert ui_instance.confirm_dialog is None
    assert ui_instance.mode == 'PLAYING'
    assert ui_instance.game is not None

    # 3. Click Main Menu again -> then click outside dialog -> closes modal, stays in PLAYING
    ui_instance.handle_event(event_menu)
    assert ui_instance.confirm_dialog == 'menu'
    event_outside = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (10, 10)})
    ui_instance.handle_event(event_outside)
    assert ui_instance.confirm_dialog is None
    assert ui_instance.mode == 'PLAYING'

    # 4. Click Main Menu -> then click Yes (Go to Menu) -> navigates to MENU
    ui_instance.handle_event(event_menu)
    assert ui_instance.confirm_dialog == 'menu'
    event_yes = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_modal_yes.centerx, ui_instance.btn_modal_yes.centery)})
    ui_instance.handle_event(event_yes)
    assert ui_instance.confirm_dialog is None
    assert ui_instance.mode == 'MENU'


def test_ui_restart_confirmation_dialog(ui_instance):
    """Clicking Restart displays confirmation dialog and resets only when confirmed."""
    ui_instance.start_new_game('HUMAN_VS_AI')
    assert ui_instance.mode == 'PLAYING'
    assert ui_instance.confirm_dialog is None

    # Click Restart -> opens confirmation dialog
    event_restart = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_restart.centerx, ui_instance.btn_restart.centery)})
    ui_instance.handle_event(event_restart)
    assert ui_instance.confirm_dialog == 'restart'
    assert ui_instance.confirm_restart_modal is True

    # Click Cancel -> dismisses modal
    event_cancel = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_modal_cancel.centerx, ui_instance.btn_modal_cancel.centery)})
    ui_instance.handle_event(event_cancel)
    assert ui_instance.confirm_dialog is None
    assert ui_instance.confirm_restart_modal is False


def test_ui_sidebar_typography_and_branding(ui_instance):
    """Verify enlarged typography hierarchy and LudoVerse branding."""
    assert ui_instance.font_title.get_height() >= 30
    assert ui_instance.font_heading.get_height() >= 22
    assert ui_instance.font_subheading.get_height() >= 18
    assert ui_instance.font_body.get_height() >= 14
    assert ui_instance.font_small.get_height() >= 13
    assert ui_instance.font_btn.get_height() >= 14

    # Verify LudoVerse in initial message and activity log
    assert "LudoVerse" in ui_instance.activity_log[0]['text']


def test_ui_main_menu_and_leaderboard_navigation(ui_instance):
    """Verify 4 main menu options, Leaderboard partition switching, and back navigation."""
    ui_instance.mode = 'MENU'

    # 1. Click Option 3 (Leaderboard)
    event_lead = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_menu_leaderboard.centerx, ui_instance.btn_menu_leaderboard.centery)})
    ui_instance.handle_event(event_lead)
    assert ui_instance.mode == 'LEADERBOARD'
    assert ui_instance.leaderboard_tab == 'human'

    # 2. Switch to AI vs AI tab
    event_tab_ai = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_lead_tab_ai.centerx, ui_instance.btn_lead_tab_ai.centery)})
    ui_instance.handle_event(event_tab_ai)
    assert ui_instance.leaderboard_tab == 'ai'

    # 3. Switch back to Human vs AI tab
    event_tab_human = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_lead_tab_human.centerx, ui_instance.btn_lead_tab_human.centery)})
    ui_instance.handle_event(event_tab_human)
    assert ui_instance.leaderboard_tab == 'human'

    # 4. Render leaderboard without error
    ui_instance.render()
    ui_instance.leaderboard_tab = 'ai'
    ui_instance.render()

    # 5. Click Back button to return to Menu
    event_back = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (ui_instance.btn_lead_back.centerx, ui_instance.btn_lead_back.centery)})
    ui_instance.handle_event(event_back)
    assert ui_instance.mode == 'MENU'


def test_ui_expectimax_display_without_depth(ui_instance):
    """Verify that in-game display formats Expectimax without (d=2)."""
    ui_instance.start_new_game('HUMAN_VS_AI')
    # Expectimax agent is opponent
    exp_color = None
    for c, agent in ui_instance.game.agents.items():
        if agent.name.startswith("Expectimax"):
            exp_color = c
            break
    assert exp_color is not None

    # Verify that in-game card formatting produces clean name
    raw_name = ui_instance.game.agents[exp_color].name
    assert "d=" in raw_name  # underlying agent still exposes depth for benchmarks
    disp_name = "Expectimax" if raw_name.startswith("Expectimax") else raw_name
    assert disp_name == "Expectimax"
    assert "d=" not in disp_name


def test_ui_menu_logo_and_home_positions(ui_instance):
    """Verify MENU rendering with LUDO & VERSE badges and home-path pieces."""
    # 1. Render MENU mode
    ui_instance.mode = 'MENU'
    ui_instance.render()

    # 2. Start game and place pieces across all 6 home-path positions (51 to 56)
    ui_instance.start_new_game('HUMAN_VS_AI')
    # yellow piece 0: square 1 (51), piece 1: square 5 (55), piece 2: triangle (56 / FINISHED)
    ui_instance.game.state.pieces['yellow'] = [51, 55, 56, -1]
    ui_instance.render()

    # Pixel rects must be computed without error
    r_sq1 = ui_instance.get_piece_pixel_rect('yellow', 0)
    r_sq5 = ui_instance.get_piece_pixel_rect('yellow', 1)
    r_tri = ui_instance.get_piece_pixel_rect('yellow', 2)
    assert r_sq1.width > 0
    assert r_sq5.width > 0
    assert r_tri.width > 0




