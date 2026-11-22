"""
test_moves.py — Phase 2: Move Generation and GameState Transition Tests
========================================================================
Tests for:
  - Piece exiting base (requires dice==6)
  - Normal track movement
  - Home column entry and traversal
  - Overshoot prevention (cannot exceed PROGRESS_FINISHED=58)
  - Exact finishing
  - Finished pieces excluded from legal moves
  - apply_move immutability (original state unchanged)
  - apply_move piece-progress update
  - Pass move (None) when no legal moves exist
  - Extra turn on rolling 6 (same player continues)
  - Third consecutive 6 → forfeit (next player's turn)
  - consecutive_sixes counter resets on non-6
"""
import pytest
from game_state import GameState
from move import Move
from board import (
    COLORS, PROGRESS_BASE, PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX,
    PROGRESS_HOME_MIN, PROGRESS_HOME_MAX, PROGRESS_FINISHED,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def fresh_state(current_player: str = 'yellow') -> GameState:
    """Return a fresh GameState with all pieces in base."""
    gs = GameState()
    gs.current_player = current_player
    return gs


def state_with(pieces: dict, current_player: str = 'yellow',
               consec: int = 0) -> GameState:
    """Return a GameState with custom piece positions."""
    gs = GameState()
    gs.current_player = current_player
    gs.consecutive_sixes = consec
    for color, positions in pieces.items():
        gs.pieces[color] = list(positions)
    return gs


# ─────────────────────────────────────────────────────────────────────────────
# 1. Base exit
# ─────────────────────────────────────────────────────────────────────────────

def test_base_piece_cannot_move_without_six():
    """Pieces in base must not generate moves for dice 1-5."""
    gs = fresh_state()
    for dice in range(1, 6):
        moves = gs.get_legal_moves(dice)
        assert moves == [], f"Expected no moves for dice={dice}, got {moves}"


def test_base_piece_exits_with_six():
    """A piece in base generates exactly one exit move when dice==6."""
    gs = fresh_state()
    moves = gs.get_legal_moves(6)
    # 4 pieces in base → up to 4 exit moves (but they are distinct pieces)
    assert len(moves) == 4
    for m in moves:
        assert m.from_progress == PROGRESS_BASE
        assert m.to_progress == 0
        assert m.dice_value == 6


def test_base_exit_single_piece_in_base():
    """With only one piece in base, only one exit move is generated."""
    gs = state_with({
        'yellow': [-1, 5, 10, 20],  # piece 0 in base, others on track
    })
    moves = gs.get_legal_moves(6)
    # piece 0 exits base + pieces 1,2,3 each advance 6
    exit_moves = [m for m in moves if m.from_progress == PROGRESS_BASE]
    assert len(exit_moves) == 1
    assert exit_moves[0].piece_index == 0


def test_no_exit_move_without_six_mixed():
    """No exit move for a piece in base when dice != 6, even with others on track."""
    gs = state_with({'yellow': [-1, 5, 10, 20]})
    for dice in range(1, 6):
        moves = gs.get_legal_moves(dice)
        for m in moves:
            assert m.from_progress != PROGRESS_BASE, \
                f"Unexpected base-exit move for dice={dice}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Normal track movement
# ─────────────────────────────────────────────────────────────────────────────

def test_normal_movement_progress():
    """Piece advances by exactly dice_value on the shared track."""
    gs = state_with({'yellow': [-1, -1, -1, 5]})
    moves = gs.get_legal_moves(3)
    assert len(moves) == 1
    assert moves[0].from_progress == 5
    assert moves[0].to_progress == 8
    assert moves[0].dice_value == 3


def test_movement_at_track_end():
    """Piece at progress 50 with dice=1 moves to 51 (HOME_MIN — first home-column square)."""
    gs = state_with({'yellow': [-1, -1, -1, 50]})
    moves = gs.get_legal_moves(1)
    assert len(moves) == 1
    assert moves[0].to_progress == PROGRESS_HOME_MIN  # 51


def test_track_to_home_column_entry():
    """Piece at progress 50 with dice=1 enters home column at progress 51 (PROGRESS_HOME_MIN)."""
    gs = state_with({'yellow': [-1, -1, -1, 50]})
    moves = gs.get_legal_moves(1)
    assert len(moves) == 1
    assert moves[0].to_progress == PROGRESS_HOME_MIN  # 51


def test_home_column_traversal():
    """Piece advances correctly within the home column."""
    gs = state_with({'yellow': [-1, -1, -1, 52]})  # second home-col square (51=first, 52=second)
    moves = gs.get_legal_moves(2)
    assert len(moves) == 1
    assert moves[0].to_progress == 54


# ─────────────────────────────────────────────────────────────────────────────
# 3. Overshoot prevention
# ─────────────────────────────────────────────────────────────────────────────

def test_overshoot_on_track_prevented():
    """Piece cannot move if it would overshoot progress 56 (PROGRESS_FINISHED)."""
    gs = state_with({'yellow': [-1, -1, -1, 54]})
    moves = gs.get_legal_moves(3)   # 54+3=57 > 56 → no move
    assert moves == [], f"Expected no moves, got {moves}"


def test_overshoot_in_home_column_prevented():
    """No move generated when home-column piece would overshoot finish."""
    gs = state_with({'yellow': [-1, -1, -1, 55]})  # last home square (position 5)
    moves = gs.get_legal_moves(2)   # 55+2=57 > 56 → no move
    assert moves == [], f"Expected no moves, got {moves}"


def test_exact_finish_allowed():
    """Piece lands exactly on PROGRESS_FINISHED=56 (triangle) when dice matches."""
    gs = state_with({'yellow': [-1, -1, -1, 53]})
    moves = gs.get_legal_moves(3)   # 53+3=56 → allowed
    assert len(moves) == 1
    assert moves[0].to_progress == PROGRESS_FINISHED


def test_exact_finish_from_last_home_square():
    """Piece at progress 55 (5th square block) enters triangular goal (position 6) with dice=1."""
    gs = state_with({'yellow': [-1, -1, -1, 55]})
    moves = gs.get_legal_moves(1)   # 55+1=56 → finish into triangle
    assert len(moves) == 1
    assert moves[0].to_progress == PROGRESS_FINISHED


# ─────────────────────────────────────────────────────────────────────────────
# 4. Finished pieces excluded
# ─────────────────────────────────────────────────────────────────────────────

def test_finished_piece_generates_no_moves():
    """A finished piece (progress=56) must never appear in legal moves."""
    gs = state_with({'yellow': [PROGRESS_FINISHED, -1, -1, -1]})
    for dice in range(1, 7):
        moves = gs.get_legal_moves(dice)
        for m in moves:
            assert m.piece_index != 0, \
                f"Finished piece generated a move for dice={dice}"


def test_all_finished_no_moves():
    """With all 4 pieces finished, no legal moves exist for any dice."""
    gs = state_with({'yellow': [PROGRESS_FINISHED] * 4})
    for dice in range(1, 7):
        assert gs.get_legal_moves(dice) == []


# ─────────────────────────────────────────────────────────────────────────────
# 5. apply_move immutability
# ─────────────────────────────────────────────────────────────────────────────

def test_apply_move_does_not_mutate_original():
    """apply_move must return a new state; the original must be unchanged."""
    gs = state_with({'yellow': [-1, -1, -1, 10]})
    original_progress = list(gs.pieces['yellow'])

    moves = gs.get_legal_moves(5)
    assert moves, "Need at least one legal move"
    new_gs = gs.apply_move(moves[0], 5)

    assert gs.pieces['yellow'] == original_progress, \
        "apply_move mutated the original state"
    assert new_gs is not gs


def test_apply_move_updates_piece_progress():
    """The moved piece's progress is updated correctly in the new state."""
    gs = state_with({'yellow': [-1, -1, -1, 10]})
    moves = gs.get_legal_moves(4)
    assert moves
    new_gs = gs.apply_move(moves[0], 4)
    assert new_gs.pieces['yellow'][3] == 14  # 10+4


def test_apply_move_base_exit():
    """Exiting base sets piece progress to 0 in the new state."""
    gs = state_with({'yellow': [-1, -1, -1, -1]})
    moves = gs.get_legal_moves(6)
    new_gs = gs.apply_move(moves[0], 6)
    piece_idx = moves[0].piece_index
    assert new_gs.pieces['yellow'][piece_idx] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Pass move (no legal moves)
# ─────────────────────────────────────────────────────────────────────────────

def test_pass_move_advances_turn():
    """apply_move(None, dice) always advances to the next player."""
    gs = fresh_state('yellow')
    new_gs = gs.apply_move(None, 3)
    assert new_gs.current_player == 'blue'


def test_pass_move_resets_consecutive_sixes():
    """A pass clears the consecutive_sixes counter."""
    gs = state_with({}, current_player='yellow', consec=1)
    new_gs = gs.apply_move(None, 3)
    assert new_gs.consecutive_sixes == 0


# ─────────────────────────────────────────────────────────────────────────────
# 7. Turn order and extra turns
# ─────────────────────────────────────────────────────────────────────────────

def test_non_six_advances_turn():
    """Rolling 1-5 passes the turn to the next player."""
    gs = state_with({'yellow': [-1, -1, -1, 10]})
    moves = gs.get_legal_moves(3)
    new_gs = gs.apply_move(moves[0], 3)
    assert new_gs.current_player == 'blue'


def test_six_keeps_same_player():
    """Rolling a 6 (first time) keeps the same player's turn."""
    gs = state_with({'yellow': [-1, -1, -1, -1]}, consec=0)
    moves = gs.get_legal_moves(6)
    new_gs = gs.apply_move(moves[0], 6)
    assert new_gs.current_player == 'yellow'
    assert new_gs.consecutive_sixes == 1


def test_second_six_keeps_same_player():
    """Rolling a second consecutive 6 keeps the same player's turn."""
    gs = state_with({'yellow': [0, -1, -1, -1]}, consec=1)
    moves = gs.get_legal_moves(6)
    new_gs = gs.apply_move(moves[0], 6)
    assert new_gs.current_player == 'yellow'
    assert new_gs.consecutive_sixes == 2


def test_third_consecutive_six_forfeits():
    """Rolling a third consecutive 6 forfeits the turn to next player."""
    gs = state_with({'yellow': [0, 5, -1, -1]}, consec=2)
    moves = gs.get_legal_moves(6)
    new_gs = gs.apply_move(moves[0], 6)
    assert new_gs.current_player == 'blue'
    assert new_gs.consecutive_sixes == 0


def test_non_six_resets_consecutive_counter():
    """consecutive_sixes resets to 0 on any non-6 roll."""
    gs = state_with({'yellow': [0, -1, -1, -1]}, consec=1)
    moves = gs.get_legal_moves(3)
    new_gs = gs.apply_move(moves[0], 3)
    assert new_gs.consecutive_sixes == 0


def test_turn_order_wraps_correctly():
    """Turn order cycles: yellow → blue → red → green → yellow."""
    gs = fresh_state('green')
    new_gs = gs.apply_move(None, 3)
    assert new_gs.current_player == 'yellow'


# ─────────────────────────────────────────────────────────────────────────────
# 8. Multiple pieces generating moves
# ─────────────────────────────────────────────────────────────────────────────

def test_multiple_pieces_generate_multiple_moves():
    """Each movable piece generates exactly one Move entry per dice roll."""
    gs = state_with({'yellow': [5, 10, 20, 30]})
    moves = gs.get_legal_moves(3)
    assert len(moves) == 4
    piece_indices = [m.piece_index for m in moves]
    assert sorted(piece_indices) == [0, 1, 2, 3]


def test_mixed_base_and_track_with_six():
    """With pieces in base and on track, dice=6 generates moves for all."""
    gs = state_with({'yellow': [-1, 10, -1, 25]})
    moves = gs.get_legal_moves(6)
    # piece 0 exits base, piece 1 advances, piece 2 exits base, piece 3 advances
    assert len(moves) == 4
    base_moves = [m for m in moves if m.from_progress == PROGRESS_BASE]
    track_moves = [m for m in moves if m.from_progress != PROGRESS_BASE]
    assert len(base_moves) == 2
    assert len(track_moves) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 9. Move dataclass attributes and aliases
# ─────────────────────────────────────────────────────────────────────────────

def test_move_attributes_and_aliases():
    """Verify Move class attributes and property aliases match specification."""
    m = Move(piece_index=2, dice_value=5, from_progress=10, to_progress=15,
             captures=[('blue', 1)], player='red')
    assert m.piece_index == 2
    assert m.piece_id == 2
    assert m.dice_value == 5
    assert m.from_progress == 10
    assert m.start_pos == 10
    assert m.to_progress == 15
    assert m.dest_pos == 15
    assert m.captures == [('blue', 1)]
    assert m.player == 'red'
    assert m.player_id == 'red'


def test_game_state_generates_moves_with_player_id():
    """Moves generated by GameState must carry the current player ID."""
    gs = fresh_state('blue')
    moves = gs.get_legal_moves(6)
    assert len(moves) == 4
    for m in moves:
        assert m.player == 'blue'
        assert m.player_id == 'blue'

