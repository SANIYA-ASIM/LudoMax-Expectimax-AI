"""
test_gameplay_modes.py — Phase 9: Human vs AI and AI vs AI Integration Tests
=============================================================================
Comprehensive gameplay tests covering:
  - Human vs AI turn interleaving, move execution, and state consistency
  - Human vs AI complete game playout and winner announcement
  - AI vs AI 4-way matchups (Expectimax vs Aggressive vs Defensive vs Random)
  - Engine integrity validation across full games:
      * Every move played is strictly legal
      * Safe squares never suffer captures
      * Base exits require roll of 6
      * Home paths require exact finish rolls
      * Consecutive sixes rule enforced
  - Pygame GUI simulation in both Human vs AI and AI vs AI modes
"""
import os
import pygame
import pytest

os.environ['SDL_VIDEODRIVER'] = 'dummy'

from board import (
    COLORS, SAFE_SQUARES, PROGRESS_BASE, PROGRESS_FINISHED,
    PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX, PROGRESS_HOME_MIN,
    get_absolute_track_pos,
)
from game import Game
from game_state import GameState
from move import Move
from agents import create_agent, HumanAgent
from game_ui import LudoUI, WINDOW_WIDTH, WINDOW_HEIGHT


# ─────────────────────────────────────────────────────────────────────────────
# 1. Human vs AI Integration
# ─────────────────────────────────────────────────────────────────────────────

def test_human_vs_ai_turn_cycling():
    """Verify clean turn transitions between a Human player and 3 AI opponents."""
    human = create_agent('human', 'yellow')
    ai_blue = create_agent('expectimax', 'blue', depth=1)
    ai_red = create_agent('aggressive', 'red')
    ai_green = create_agent('defensive', 'green')

    game = Game([human, ai_blue, ai_red, ai_green], seed=101)

    # Turn 1: Yellow (Human) rolls 6
    legal_moves = game.state.get_legal_moves(6)
    assert len(legal_moves) == 4
    # Human selects piece 0 to exit base
    chosen = legal_moves[0]
    human.set_pending_move(chosen)
    t1 = game.play_turn(dice=6)
    assert t1['player'] == 'yellow'
    assert t1['move'] == chosen
    assert game.state.pieces['yellow'][0] == 0
    # Rolling 6 grants human an extra turn!
    assert game.state.current_player == 'yellow'

    # Turn 2: Yellow (Human) rolls 4 -> advances piece 0 from 0 to 4
    legal_moves = game.state.get_legal_moves(4)
    assert len(legal_moves) == 1
    chosen = legal_moves[0]
    human.set_pending_move(chosen)
    t2 = game.play_turn(dice=4)
    assert t2['player'] == 'yellow'
    assert game.state.pieces['yellow'][0] == 4
    # Non-six roll advances turn to Blue (AI)!
    assert game.state.current_player == 'blue'

    # Turn 3: Blue (AI) automatically rolls and plays
    t3 = game.play_turn()
    assert t3['player'] == 'blue'
    assert game.turn_count == 3


def test_human_vs_ai_full_game_playout():
    """Simulate complete Human vs AI game where Human plays first legal move."""
    class AutomatedHuman(HumanAgent):
        def choose_move(self, state, legal_moves, dice):
            return legal_moves[0] if legal_moves else None

    human = AutomatedHuman('yellow')
    agents = [
        human,
        create_agent('expectimax', 'blue', depth=1),
        create_agent('aggressive', 'red'),
        create_agent('defensive', 'green'),
    ]
    game = Game(agents, seed=202)
    winner = game.play_game(max_turns=600)
    assert winner in COLORS or winner is None
    if winner is not None:
        assert game.state.is_game_over()
        assert game.winner == winner
        assert all(p == PROGRESS_FINISHED for p in game.state.pieces[winner])


# ─────────────────────────────────────────────────────────────────────────────
# 2. AI vs AI Tournament & Rule Invariant Testing
# ─────────────────────────────────────────────────────────────────────────────

def test_ai_vs_ai_four_way_rules_invariant():
    """Run an entire AI vs AI game while validating engine rules at every move:
    - Every executed move is strictly in legal_moves
    - No capture ever occurs on any of the 8 safe squares
    - Pieces only exit base on a roll of 6
    - Pieces never overshoot past PROGRESS_FINISHED
    """
    agents = [
        create_agent('expectimax', 'yellow', depth=1),
        create_agent('aggressive', 'blue'),
        create_agent('defensive', 'red'),
        create_agent('random', 'green', seed=555),
    ]
    game = Game(agents, seed=303)

    moves_played = 0
    while not game.state.is_game_over() and game.turn_count < 500:
        player = game.state.current_player
        dice = game.roll_dice()

        # Engine rule check: Third consecutive six
        if dice == 6 and game.state.consecutive_sixes >= 2:
            res = game.play_turn(dice=dice)
            assert res['forfeit'] is True
            assert res['move'] is None
            continue

        legal = game.state.get_legal_moves(dice)
        res = game.play_turn(dice=dice)
        m = res['move']

        if m is not None:
            moves_played += 1
            # 1. Move was legal
            assert m in legal, f"Illegal move {m} played by {player} with dice {dice}"

            # 2. Base exit check
            if m.from_progress == PROGRESS_BASE:
                assert dice == 6
                assert m.to_progress == 0

            # 3. No overshoot past 58
            assert m.to_progress <= PROGRESS_FINISHED

            # 4. Safe square capture immunity
            if m.captures:
                dest_abs = get_absolute_track_pos(player, m.to_progress)
                assert dest_abs not in SAFE_SQUARES, \
                    f"Capture occurred on safe square {dest_abs} by {player}!"

    assert moves_played > 50, "Expected a substantial number of moves to be executed."
    assert game.winner in COLORS or game.winner is None


def test_ai_vs_ai_various_matchups():
    """Test Expectimax against homogeneous AI opponent configurations."""
    for opp_type in ['random', 'defensive', 'aggressive']:
        agents = [
            create_agent('expectimax', 'yellow', depth=1),
            create_agent(opp_type, 'blue'),
            create_agent(opp_type, 'red'),
            create_agent(opp_type, 'green'),
        ]
        game = Game(agents, seed=404)
        winner = game.play_game(max_turns=300)
        assert winner in COLORS or winner is None


# ─────────────────────────────────────────────────────────────────────────────
# 3. GUI Simulation in Both Modes
# ─────────────────────────────────────────────────────────────────────────────

def test_gui_human_vs_ai_interaction_flow():
    """Simulate human UI flow: Roll Dice button -> piece selection -> turn update."""
    pygame.init()
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    ui = LudoUI(screen=surface, headless=True)

    ui.start_new_game('HUMAN_VS_AI')
    assert ui.mode == 'PLAYING'
    assert ui.human_phase == 'NEED_ROLL'

    # 1. Click "Roll Dice" button
    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {
        'button': 1,
        'pos': (ui.btn_roll.centerx, ui.btn_roll.centery),
    })
    ui.handle_event(click_event)
    assert ui.last_dice in (1, 2, 3, 4, 5, 6)

    # 2. If human had choices, selecting piece executes move
    if ui.human_phase == 'SELECT_PIECE' and ui.human_legal_moves:
        chosen_move = ui.human_legal_moves[0]
        p_rect = ui.get_piece_pixel_rect('yellow', chosen_move.piece_index)
        piece_click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {
            'button': 1,
            'pos': (p_rect.centerx, p_rect.centery),
        })
        ui.handle_event(piece_click)
        assert ui.human_phase == 'NEED_ROLL'


def test_gui_ai_vs_ai_simulation_loop():
    """Simulate automated AI vs AI loop running in GUI without errors."""
    pygame.init()
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    ui = LudoUI(screen=surface, headless=True)

    ui.start_new_game('AI_VS_AI')
    ui.ai_delay_ms = 50  # fast headless steps
    ui.last_ai_step_time = 0.0

    # Step through 20 AI turns
    for _ in range(20):
        ui.last_ai_step_time = 0.0
        ui.update()
        ui.render()

    assert ui.game.turn_count >= 10
    assert ui.mode in ('PLAYING', 'GAME_OVER')
