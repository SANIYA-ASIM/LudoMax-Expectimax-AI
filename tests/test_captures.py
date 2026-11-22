"""
test_captures.py — Phase 2: Capture Logic Tests
================================================
Tests for:
  - Landing on an opponent's piece sends it back to base
  - Multiple opponents on same square are all captured
  - Own pieces are never captured
  - Home column landings never trigger captures
  - Capture information is recorded correctly in the Move object
"""
import pytest
from game_state import GameState
from move import Move
from board import (
    COLORS, PLAYER_OFFSETS, SAFE_SQUARES,
    PROGRESS_BASE, PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX,
    PROGRESS_HOME_MIN, PROGRESS_FINISHED,
    get_absolute_track_pos,
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


def find_move(moves, piece_index: int) -> Move:
    for m in moves:
        if m.piece_index == piece_index:
            return m
    raise AssertionError(f"No move for piece_index={piece_index}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Basic capture
# ─────────────────────────────────────────────────────────────────────────────

def test_capture_sends_opponent_to_base():
    """Landing on an opponent's non-safe square sends that piece back to base."""
    # Yellow piece at progress 10 moves 3 → lands at 13.
    # Blue piece at relative progress 0 is at absolute position 13 (blue's start).
    # BUT blue's start (abs 13) IS a safe square → no capture there.
    # Instead: yellow at 7, dice 4 → lands at 11 (abs 11, not safe).
    # We need to find a non-safe square where blue sits.
    # Blue at relative progress 1 → absolute (13+1)%52=14 (not safe).
    # Yellow at progress p such that abs(yellow, p)=14: (0+p)%52=14 → p=14.
    # Yellow at 11, dice 3 → 14. Blue at 1 → abs 14.
    gs = state_with({
        'yellow': [-1, -1, -1, 11],
        'blue':   [1, -1, -1, -1],   # blue piece 0 at relative 1 → abs 14
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(3)
    m = find_move(moves, piece_index=3)
    assert m.to_progress == 14
    assert ('blue', 0) in m.captures, \
        f"Expected blue piece 0 captured, got captures={m.captures}"

    # Apply move and verify blue's piece is back in base
    new_gs = gs.apply_move(m, 3)
    assert new_gs.pieces['blue'][0] == PROGRESS_BASE


def test_capture_recorded_in_move():
    """The Move object lists all captured (color, piece_index) pairs."""
    # Yellow at 11, dice 3 → 14. Blue piece 0 at abs 14 (relative 1).
    gs = state_with({
        'yellow': [-1, -1, -1, 11],
        'blue':   [1, -1, -1, -1],
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(3)
    m = find_move(moves, piece_index=3)
    assert len(m.captures) == 1
    assert m.captures[0] == ('blue', 0)


def test_multiple_opponents_on_same_square_all_captured():
    """If two opponent pieces share a non-safe square, both are captured."""
    # Yellow at 11, dice 3 → abs 14.
    # Blue piece 0 and red piece 0 both at absolute 14.
    # Blue piece 0: relative 1 → abs (13+1)%52=14. ✓
    # Red piece 0: relative r such that (26+r)%52=14 → r=(14-26+52)%52=40.
    gs = state_with({
        'yellow': [-1, -1, -1, 11],
        'blue':   [1, -1, -1, -1],
        'red':    [40, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(3)
    m = find_move(moves, piece_index=3)
    assert len(m.captures) == 2
    captured_colors = {c for c, _ in m.captures}
    assert 'blue' in captured_colors
    assert 'red' in captured_colors

    new_gs = gs.apply_move(m, 3)
    assert new_gs.pieces['blue'][0] == PROGRESS_BASE
    assert new_gs.pieces['red'][0] == PROGRESS_BASE


def test_own_pieces_not_captured():
    """A player's own pieces are never in the captures list."""
    # Two yellow pieces on the same square — moving another piece there
    # should NOT capture the own piece.
    # Yellow piece 3 at progress 11, dice 3 → 14.
    # Yellow piece 2 also at progress 14 → same absolute square.
    gs = state_with({
        'yellow': [-1, -1, 14, 11],  # piece 2 already at 14
        'blue':   [-1, -1, -1, -1],
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(3)
    m = find_move(moves, piece_index=3)
    assert m.to_progress == 14
    assert m.captures == [], \
        f"Own pieces must not be captured, got {m.captures}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. No captures in home column or at finish
# ─────────────────────────────────────────────────────────────────────────────

def test_home_column_landing_no_capture():
    """Moving into the home column never triggers a capture."""
    # Yellow at progress 50, dice=1 → 51 (PROGRESS_HOME_MIN, first home-column square).
    # An opponent at any position should not be capturable here.
    gs = state_with({
        'yellow': [-1, -1, -1, 50],
        'blue':   [5, -1, -1, -1],
        'red':    [10, -1, -1, -1],
        'green':  [15, -1, -1, -1],
    })
    moves = gs.get_legal_moves(1)
    m = find_move(moves, piece_index=3)
    assert m.to_progress == PROGRESS_HOME_MIN
    assert m.captures == []


def test_finishing_no_capture():
    """Moving to PROGRESS_FINISHED never triggers a capture."""
    gs = state_with({
        'yellow': [-1, -1, -1, 53],
        'blue':   [5, -1, -1, -1],
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(3)
    m = find_move(moves, piece_index=3)
    assert m.to_progress == PROGRESS_FINISHED
    assert m.captures == []


# ─────────────────────────────────────────────────────────────────────────────
# 3. No self-capture on base exit
# ─────────────────────────────────────────────────────────────────────────────

def test_base_exit_no_self_capture():
    """When a piece exits base, its own pieces at the start square are not captured."""
    # Yellow piece 0 in base, yellow piece 1 already at progress 0 (start square).
    gs = state_with({
        'yellow': [-1, 0, -1, -1],
        'blue':   [-1, -1, -1, -1],
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(6)
    base_exit_moves = [m for m in moves if m.from_progress == PROGRESS_BASE]
    for m in base_exit_moves:
        assert m.captures == [], \
            f"Self-capture on base exit: {m.captures}"


def test_capture_does_not_affect_capturer_progress():
    """After a capture, the capturing piece's progress is correct."""
    gs = state_with({
        'yellow': [-1, -1, -1, 11],
        'blue':   [1, -1, -1, -1],
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(3)
    m = find_move(moves, piece_index=3)
    new_gs = gs.apply_move(m, 3)
    assert new_gs.pieces['yellow'][3] == 14   # capturer advances normally
    assert new_gs.pieces['blue'][0] == PROGRESS_BASE  # captured → back to base


def test_capture_grants_extra_turn():
    """Capturing an opponent piece grants an extra turn (same player continues)."""
    gs = state_with({
        'yellow': [-1, -1, -1, 11],
        'blue':   [1, -1, -1, -1],
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    }, current_player='yellow')
    moves = gs.get_legal_moves(3)
    m = find_move(moves, piece_index=3)
    assert len(m.captures) == 1
    new_gs = gs.apply_move(m, 3)
    # Yellow rolled a 3 (non-6) and captured blue -> Yellow gets an extra turn!
    assert new_gs.current_player == 'yellow'
    assert new_gs.consecutive_sixes == 0

