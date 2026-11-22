"""
test_winning.py — Phase 2: Winning Condition Tests
===================================================
Tests for:
  - Fresh game has no winner
  - All 4 pieces at PROGRESS_FINISHED (58) declares a winner
  - Partial completion is not a win
  - get_winner() returns the correct colour
  - is_game_over() corresponds to get_winner()
  - Exact finishing: overshoot is NOT allowed
  - Finishing last piece: apply_move correctly sets final piece to 58
  - pieces_finished() convenience counter
  - pieces_in_base() convenience counter
  - pieces_active() convenience counter
"""
import pytest
from game_state import GameState
from board import (
    COLORS, PROGRESS_BASE, PROGRESS_FINISHED,
    PROGRESS_HOME_MIN, PROGRESS_HOME_MAX,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def state_with(pieces: dict, current_player: str = 'yellow') -> GameState:
    gs = GameState()
    gs.current_player = current_player
    for color, positions in pieces.items():
        gs.pieces[color] = list(positions)
    return gs


# ─────────────────────────────────────────────────────────────────────────────
# 1. Fresh state has no winner
# ─────────────────────────────────────────────────────────────────────────────

def test_fresh_state_not_game_over():
    gs = GameState()
    assert not gs.is_game_over()


def test_fresh_state_no_winner():
    gs = GameState()
    assert gs.get_winner() is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Winning conditions
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("winner_color", COLORS)
def test_all_pieces_finished_wins(winner_color):
    """When all 4 pieces of a colour are at PROGRESS_FINISHED, that player wins."""
    pieces = {c: [-1, -1, -1, -1] for c in COLORS}
    pieces[winner_color] = [PROGRESS_FINISHED] * 4
    gs = state_with(pieces)
    assert gs.is_game_over()
    assert gs.get_winner() == winner_color


def test_partial_finish_not_winning():
    """3 finished pieces and 1 not → game is not over."""
    gs = state_with({'yellow': [PROGRESS_FINISHED, PROGRESS_FINISHED,
                                PROGRESS_FINISHED, 50]})
    assert not gs.is_game_over()
    assert gs.get_winner() is None


def test_three_finished_pieces_not_winning():
    """Having 3 finished pieces is not enough to win."""
    gs = state_with({'yellow': [PROGRESS_FINISHED, PROGRESS_FINISHED, PROGRESS_FINISHED, 0]})
    assert not gs.is_game_over()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Exact finishing
# ─────────────────────────────────────────────────────────────────────────────

def test_exact_finish_generates_move():
    """Progress 53 + dice 3 = 56 (PROGRESS_FINISHED) → a legal finishing move is generated."""
    gs = state_with({'yellow': [-1, -1, -1, 53]})
    moves = gs.get_legal_moves(3)
    finishing = [m for m in moves if m.to_progress == PROGRESS_FINISHED]
    assert len(finishing) == 1


def test_overshoot_no_move_generated():
    """Progress 54 + dice 3 = 57 > 56 → NO legal move generated."""
    gs = state_with({'yellow': [-1, -1, -1, 54]})
    moves = gs.get_legal_moves(3)
    assert moves == [], f"Expected no moves for overshoot, got {moves}"


@pytest.mark.parametrize("progress,dice", [
    (55, 2),   # 55+2=57 > 56
    (54, 3),   # 54+3=57 > 56
    (53, 4),   # 53+4=57 > 56
    (52, 5),   # 52+5=57 > 56
    (51, 6),   # 51+6=57 > 56
])
def test_various_overshoots_blocked(progress, dice):
    """All overshoot scenarios generate no legal moves."""
    gs = state_with({'yellow': [PROGRESS_FINISHED, PROGRESS_FINISHED, PROGRESS_FINISHED, progress]})
    moves = gs.get_legal_moves(dice)
    assert moves == [], \
        f"Expected no moves for progress={progress}+dice={dice}, got {moves}"


@pytest.mark.parametrize("progress,dice", [
    (55, 1),   # 55+1=56 (position 5 square to position 6 triangle)
    (54, 2),   # 54+2=56
    (53, 3),   # 53+3=56
    (52, 4),   # 52+4=56
    (51, 5),   # 51+5=56
    (50, 6),   # 50+6=56 (entrance to triangle)
])
def test_exact_finish_always_allowed(progress, dice):
    """All exact-finish combinations generate exactly one move."""
    gs = state_with({'yellow': [PROGRESS_FINISHED, PROGRESS_FINISHED, PROGRESS_FINISHED, progress]})
    moves = gs.get_legal_moves(dice)
    assert len(moves) == 1
    assert moves[0].to_progress == PROGRESS_FINISHED


def test_home_path_six_positions_structure():
    """
    Verify exact 6-position home path structure:
    Positions 1-5: 5 square-shaped blocks (progress 51-55).
    Position 6: 1 triangular-shaped block (progress 56 = PROGRESS_FINISHED).
    """
    assert PROGRESS_HOME_MAX - PROGRESS_HOME_MIN + 1 == 5  # exactly 5 square blocks
    assert PROGRESS_FINISHED == PROGRESS_HOME_MAX + 1     # position 6 is triangle

    for color in COLORS:
        # A piece at position 5 (progress 55) with roll 1 enters triangle (position 6)
        gs = state_with({color: [-1, -1, -1, 55]}, current_player=color)
        moves = [m for m in gs.get_legal_moves(1) if m.piece_index == 3]
        assert len(moves) == 1
        assert moves[0].to_progress == PROGRESS_FINISHED  # Position 6

        # Rolling 2-6 from position 5 is blocked (overshoot)
        for d in range(2, 7):
            p3_moves = [m for m in gs.get_legal_moves(d) if m.piece_index == 3]
            assert p3_moves == [], f"Roll {d} for piece at position 5 must be blocked"


def test_home_stretch_exact_vs_excessive_vs_insufficient():
    """
    Detailed test verifying exact winning logic:
    Suppose piece needs exactly 3 steps to finish (progress=53, needs 56 - 53 = 3).
    - Rolling 4 (excessive / too high): NO legal moves, piece must NOT enter final position, NO win.
    - Rolling 2 (insufficient / too low): advances to 55 (square 5), does NOT enter final position, NO win.
    - Rolling 3 (exact): reaches 56 (PROGRESS_FINISHED, triangle), finishes, triggers WIN.
    """
    for color in COLORS:
        # 3 pieces already finished, 1 piece in home stretch at 53 (needs exactly 3 to reach 56)
        initial_pieces = {c: [-1, -1, -1, -1] for c in COLORS}
        initial_pieces[color] = [PROGRESS_FINISHED, PROGRESS_FINISHED, PROGRESS_FINISHED, 53]

        # Case 1: Roll 4 (too high / excessive)
        gs_high = state_with(initial_pieces, current_player=color)
        moves_high = gs_high.get_legal_moves(4)
        assert moves_high == [], f"{color}: excessive roll 4 should yield NO moves, got {moves_high}"
        # When no moves, turn is skipped
        new_gs_high = gs_high.apply_move(None, 4)
        assert new_gs_high.pieces[color][3] == 53  # piece did NOT move
        assert not new_gs_high.is_game_over()
        assert new_gs_high.get_winner() is None

        # Case 2: Roll 2 (too low / insufficient)
        gs_low = state_with(initial_pieces, current_player=color)
        moves_low = gs_low.get_legal_moves(2)
        assert len(moves_low) == 1
        assert moves_low[0].to_progress == 55  # advances within home stretch to square 5
        new_gs_low = gs_low.apply_move(moves_low[0], 2)
        assert new_gs_low.pieces[color][3] == 55  # moved to 55, NOT finished
        assert not new_gs_low.is_game_over(), f"{color}: rolling 2 when 3 needed must NOT win"
        assert new_gs_low.get_winner() is None

        # Case 3: Roll 3 (EXACT)
        gs_exact = state_with(initial_pieces, current_player=color)
        moves_exact = gs_exact.get_legal_moves(3)
        assert len(moves_exact) == 1
        assert moves_exact[0].to_progress == PROGRESS_FINISHED
        new_gs_exact = gs_exact.apply_move(moves_exact[0], 3)
        assert new_gs_exact.pieces[color][3] == PROGRESS_FINISHED
        assert new_gs_exact.is_game_over()
        assert new_gs_exact.get_winner() == color


def test_skipped_turn_when_only_remaining_piece_cannot_move():
    """
    If the player has no other movable pieces and their only remaining piece
    cannot move because an exact dice roll is required, their turn should
    automatically be skipped, and the game proceeds to the next player.
    """
    from game import Game
    from agents import create_agent

    for color_idx, color in enumerate(COLORS):
        agents = [create_agent('defensive', c) for c in COLORS]
        game = Game(agents)
        game.state.current_player = color
        # 3 pieces in base, 1 piece in home stretch at 55 (needs exactly 1 to finish)
        game.state.pieces[color] = [-1, -1, -1, 55]
        next_color = COLORS[(color_idx + 1) % len(COLORS)]

        # Roll 5: cannot move in-base pieces (requires 6) and cannot move home piece (55+5=60 > 56)
        turn_info = game.play_turn(dice=5)
        assert turn_info['move'] is None, f"{color}: expected move=None when roll 5 is invalid"
        assert game.state.pieces[color][3] == 55, "Piece at 55 should remain unmoved"
        assert game.state.current_player == next_color, f"Turn should pass to {next_color}"
        assert not game.state.is_game_over()



# ─────────────────────────────────────────────────────────────────────────────
# 4. Finishing via apply_move
# ─────────────────────────────────────────────────────────────────────────────

def test_apply_move_finishes_piece():
    """After applying a finishing move, the piece is at PROGRESS_FINISHED."""
    gs = state_with({'yellow': [-1, -1, -1, 53]})
    moves = gs.get_legal_moves(3)
    new_gs = gs.apply_move(moves[0], 3)
    assert new_gs.pieces['yellow'][3] == PROGRESS_FINISHED


def test_last_piece_finish_wins_game():
    """Applying a finishing move to the last piece triggers game over."""
    gs = state_with({'yellow': [PROGRESS_FINISHED, PROGRESS_FINISHED, PROGRESS_FINISHED, 53]})
    moves = gs.get_legal_moves(3)
    assert moves, "Should have one legal finishing move"
    new_gs = gs.apply_move(moves[0], 3)
    assert new_gs.is_game_over()
    assert new_gs.get_winner() == 'yellow'


# ─────────────────────────────────────────────────────────────────────────────
# 5. Convenience counters
# ─────────────────────────────────────────────────────────────────────────────

def test_pieces_in_base_counter():
    """pieces_in_base() correctly counts pieces at PROGRESS_BASE."""
    gs = state_with({'yellow': [-1, -1, 10, 20]})
    assert gs.pieces_in_base('yellow') == 2


def test_pieces_finished_counter():
    """pieces_finished() correctly counts pieces at PROGRESS_FINISHED."""
    gs = state_with({'yellow': [PROGRESS_FINISHED, PROGRESS_FINISHED, -1, 10]})
    assert gs.pieces_finished('yellow') == 2


def test_pieces_active_counter():
    """pieces_active() correctly counts pieces on track or in home column."""
    gs = state_with({'yellow': [PROGRESS_FINISHED, -1, 10, 53]})
    # piece 0: finished (not active), piece 1: base (not active)
    # piece 2: track (active), piece 3: home column (active)
    assert gs.pieces_active('yellow') == 2


def test_all_in_base_counters():
    gs = GameState()
    for color in COLORS:
        assert gs.pieces_in_base(color) == 4
        assert gs.pieces_finished(color) == 0
        assert gs.pieces_active(color) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. is_game_over and get_winner consistency
# ─────────────────────────────────────────────────────────────────────────────

def test_game_over_and_winner_consistent():
    """is_game_over() == True iff get_winner() is not None."""
    for color in COLORS:
        pieces = {c: [-1, -1, -1, -1] for c in COLORS}
        pieces[color] = [PROGRESS_FINISHED] * 4
        gs = state_with(pieces)
        assert gs.is_game_over() == (gs.get_winner() is not None)
        assert gs.get_winner() == color


def test_no_winner_in_fresh_game_consistent():
    gs = GameState()
    assert gs.is_game_over() == False
    assert gs.get_winner() is None


# ─────────────────────────────────────────────────────────────────────────────
# 7. copy() integrity
# ─────────────────────────────────────────────────────────────────────────────

def test_copy_is_independent():
    """Modifying the copy does not affect the original."""
    gs = state_with({'yellow': [5, 10, 15, 20]})
    gs_copy = gs.copy()
    gs_copy.pieces['yellow'][0] = 99
    assert gs.pieces['yellow'][0] == 5, "Original mutated by copy modification"


def test_copy_has_same_state():
    """copy() produces an identical state."""
    gs = state_with({'yellow': [5, 10, 15, 20],
                     'blue': [3, -1, -1, -1]},
                    current_player='blue')
    gs.consecutive_sixes = 1
    gs_copy = gs.copy()
    assert gs_copy.pieces == gs.pieces
    assert gs_copy.current_player == gs.current_player
    assert gs_copy.consecutive_sixes == gs.consecutive_sixes
    assert gs_copy.turn_order == gs.turn_order
