"""
test_safe_squares.py — Phase 2: Safe Square Protection Tests
=============================================================
Tests for:
  - Pieces on safe squares cannot be captured
  - All 8 safe squares are protected (4 starts + 4 star squares)
  - Pieces on NON-safe squares ARE capturable
  - Start squares: yellow=0, blue=13, red=26, green=39 (absolute indices)
  - Star squares:  abs indices 8, 21, 34, 47

Safe square rule:
  A piece landing on a safe square cannot be captured by any opponent.
  A piece already on a safe square is immune to being captured.
"""
import pytest
from game_state import GameState
from board import (
    COLORS, PLAYER_OFFSETS, SAFE_SQUARES,
    PROGRESS_BASE, PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX,
    PROGRESS_FINISHED,
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


def relative_progress_for_abs(color: str, abs_idx: int) -> int:
    """Return the relative progress for *color* that maps to absolute *abs_idx*."""
    offset = PLAYER_OFFSETS[color]
    return (abs_idx - offset) % 52


# ─────────────────────────────────────────────────────────────────────────────
# 1. No capture when landing on a safe square
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("safe_abs", sorted(SAFE_SQUARES))
def test_no_capture_when_landing_on_safe_square(safe_abs):
    """Opponent on a safe square cannot be captured regardless of which square."""
    # Place blue piece 0 at safe_abs (compute blue's relative progress).
    blue_rel = relative_progress_for_abs('blue', safe_abs)

    # Yellow must land exactly at safe_abs.
    # yellow relative progress = safe_abs (since yellow offset=0).
    yellow_target_rel = safe_abs

    # Find a yellow piece position and dice that lands on yellow_target_rel.
    # Use dice=1, yellow piece at target-1, as long as target>=1 and not in home col.
    if yellow_target_rel == 0:
        # yellow at safe_abs=0: yellow piece starts at progress 0 (exits base).
        # Can't set up a landing scenario here simply — skip this sub-case.
        return
    yellow_start = yellow_target_rel - 1

    gs = state_with({
        'yellow': [-1, -1, -1, yellow_start],
        'blue':   [blue_rel, -1, -1, -1],
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(1)
    landing_moves = [m for m in moves
                     if m.piece_index == 3 and m.to_progress == yellow_target_rel]
    assert landing_moves, \
        f"No move found landing at abs={safe_abs} (yellow rel={yellow_target_rel})"
    assert landing_moves[0].captures == [], \
        f"Unexpected capture on safe square abs={safe_abs}: {landing_moves[0].captures}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pieces on start squares are protected
# ─────────────────────────────────────────────────────────────────────────────

def test_yellow_start_square_safe():
    """Yellow's start square (abs 0) protects pieces there from capture."""
    # Blue piece at relative progress that maps to abs 0: (13+r)%52=0 → r=39.
    # Yellow piece exits base with dice 6 → progress 0 (abs 0, yellow start, safe).
    gs = state_with({
        'yellow': [PROGRESS_FINISHED, PROGRESS_FINISHED, PROGRESS_FINISHED, -1],
        'blue':   [39, -1, -1, -1],  # blue at abs 0
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(6)
    landing = [m for m in moves if m.to_progress == 0]
    assert landing, "Expected a move to progress 0"
    assert landing[0].captures == [], \
        f"Blue should not be captured at safe abs=0: {landing[0].captures}"


def test_blue_start_square_safe():
    """Blue's start square (abs 13) is safe — opponent there cannot be captured."""
    # Yellow piece landing at absolute 13 = yellow relative progress 13.
    # Red piece at abs 13: (26+r)%52=13 → r=(13-26+52)%52=39.
    gs = state_with({
        'yellow': [-1, -1, -1, 12],   # 12+1=13
        'red':    [39, -1, -1, -1],   # red at abs 13
        'blue':   [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(1)
    landing = [m for m in moves if m.to_progress == 13]
    assert landing
    assert landing[0].captures == [], \
        f"Red should not be captured at safe abs=13: {landing[0].captures}"


def test_red_start_square_safe():
    """Red's start square (abs 26) is safe."""
    # Yellow at relative 25, dice 1 → 26 (abs 26, red's start, safe).
    # Green at abs 26: (39+r)%52=26 → r=(26-39+52)%52=39.
    gs = state_with({
        'yellow': [-1, -1, -1, 25],
        'green':  [39, -1, -1, -1],  # green at abs 26
        'blue':   [-1, -1, -1, -1],
        'red':    [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(1)
    landing = [m for m in moves if m.to_progress == 26]
    assert landing
    assert landing[0].captures == []


def test_green_start_square_safe():
    """Green's start square (abs 39) is safe."""
    # Yellow at relative 38, dice 1 → 39 (abs 39, green's start, safe).
    # Blue at abs 39: (13+r)%52=39 → r=26.
    gs = state_with({
        'yellow': [-1, -1, -1, 38],
        'blue':   [26, -1, -1, -1],  # blue at abs 39
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(1)
    landing = [m for m in moves if m.to_progress == 39]
    assert landing
    assert landing[0].captures == []


# ─────────────────────────────────────────────────────────────────────────────
# 3. Star squares are safe (abs 8, 21, 34, 47)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("star_abs", [8, 21, 34, 47])
def test_star_squares_protect_opponent(star_abs):
    """Pieces on star squares (abs 8, 21, 34, 47) cannot be captured."""
    # Place blue piece at star_abs, yellow lands there.
    blue_rel = relative_progress_for_abs('blue', star_abs)
    yellow_rel = star_abs  # yellow offset=0
    if yellow_rel == 0:
        return
    gs = state_with({
        'yellow': [-1, -1, -1, yellow_rel - 1],
        'blue':   [blue_rel, -1, -1, -1],
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(1)
    landing = [m for m in moves if m.to_progress == yellow_rel]
    assert landing, f"No move landing at abs={star_abs}"
    assert landing[0].captures == [], \
        f"Star square abs={star_abs} should protect: {landing[0].captures}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Non-safe squares ARE capturable
# ─────────────────────────────────────────────────────────────────────────────

def test_non_safe_square_is_capturable():
    """An opponent on a non-safe square CAN be captured."""
    # Yellow at 10, dice 1 → 11 (abs 11, not in SAFE_SQUARES).
    # Blue at relative 1 - (13-11+52)%52 → no wait, let's compute:
    # blue piece at abs 11: (13+r)%52=11 → r=(11-13+52)%52=50.
    assert 11 not in SAFE_SQUARES, "Test assumes abs 11 is not safe"
    gs = state_with({
        'yellow': [-1, -1, -1, 10],
        'blue':   [50, -1, -1, -1],  # blue at abs 11
        'red':    [-1, -1, -1, -1],
        'green':  [-1, -1, -1, -1],
    })
    moves = gs.get_legal_moves(1)
    landing = [m for m in moves if m.to_progress == 11]
    assert landing
    assert ('blue', 0) in landing[0].captures, \
        "Blue piece should be captured on non-safe square abs=11"


def test_exactly_8_safe_squares():
    """Sanity check: exactly 8 squares are safe on the entire track."""
    safe_count = sum(1 for i in range(52) if i in SAFE_SQUARES)
    assert safe_count == 8
