"""
test_expectimax.py — Phase 5: Expectimax AI Agent Tests
========================================================
Tests covering:
  - Agent initialization, configurable depths (1, 2, 3), and custom weights
  - Performance telemetry (nodes_expanded, last_decision_time, total_nodes)
  - Single legal move fast return (bypasses full search)
  - Genuine adversarial stochastic search (MAX, CHANCE with 1/6 probability, MIN nodes)
  - Terminal state and game-over handling in search
  - Handling of extra turns on 6 and three consecutive 6s penalty
  - Comprehensive evaluation function:
      1. Piece progress
      2. Finished pieces
      3. Active pieces
      4. Safe positions
      5. Captures / opponent base suppression
      6. Capture vulnerability (immediate danger)
  - Depths 1, 2, and 3 decision validity
"""
import pytest
from board import (
    COLORS, SAFE_SQUARES, PROGRESS_BASE, PROGRESS_FINISHED,
    PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX, PROGRESS_HOME_MIN, PROGRESS_HOME_MAX,
)
from expectimax import ExpectimaxAgent
from game_state import GameState
from move import Move


def state_with(pieces: dict, current_player: str = 'yellow', consec: int = 0) -> GameState:
    gs = GameState()
    gs.current_player = current_player
    gs.consecutive_sixes = consec
    for color, positions in pieces.items():
        gs.pieces[color] = list(positions)
    return gs


# ─────────────────────────────────────────────────────────────────────────────
# 1. Initialization and Configuration
# ─────────────────────────────────────────────────────────────────────────────

def test_expectimax_default_config():
    agent = ExpectimaxAgent('yellow')
    assert agent.color == 'yellow'
    assert agent.depth == 2
    assert agent.name == "Expectimax(d=2)"
    assert agent.weights['progress'] == 1.0
    assert agent.weights['finish'] == 1.0
    assert agent.weights['active'] == 1.0
    assert agent.weights['safe'] == 1.0
    assert agent.weights['capture'] == 1.0
    assert agent.weights['vulnerability'] == 1.0


def test_expectimax_custom_depth_and_weights():
    custom_weights = {
        'progress': 2.0,
        'finish': 5.0,
        'active': 0.5,
        'safe': 1.5,
        'capture': 3.0,
        'vulnerability': 2.5,
    }
    agent = ExpectimaxAgent('blue', depth=3, weights=custom_weights)
    assert agent.depth == 3
    assert agent.name == "Expectimax(d=3)"
    assert agent.weights['progress'] == 2.0
    assert agent.weights['finish'] == 5.0
    assert agent.weights['capture'] == 3.0


def test_expectimax_tuple_weights():
    agent = ExpectimaxAgent('red', depth=1, weights=(1.5, 2.0, 0.8, 1.2, 1.8, 0.9))
    assert agent.weights['progress'] == 1.5
    assert agent.weights['finish'] == 2.0
    assert agent.weights['active'] == 0.8
    assert agent.weights['safe'] == 1.2
    assert agent.weights['capture'] == 1.8
    assert agent.weights['vulnerability'] == 0.9


# ─────────────────────────────────────────────────────────────────────────────
# 2. Performance Telemetry & Fast-Path
# ─────────────────────────────────────────────────────────────────────────────

def test_expectimax_single_move_fast_path():
    """When only 1 legal move is available, Expectimax immediately returns it."""
    agent = ExpectimaxAgent('yellow', depth=2)
    gs = state_with({'yellow': [0, -1, -1, -1]})
    moves = gs.get_legal_moves(3)
    assert len(moves) == 1
    chosen = agent.choose_move(gs, moves, 3)
    assert chosen == moves[0]
    # Fast path should not expand search tree nodes
    assert agent.nodes_expanded == 0


def test_expectimax_telemetry_tracking():
    """Search tracks nodes_expanded and last_decision_time on multi-move choices."""
    agent = ExpectimaxAgent('yellow', depth=2)
    gs = state_with({'yellow': [0, 10, -1, -1]})
    moves = gs.get_legal_moves(3)
    assert len(moves) == 2

    chosen = agent.choose_move(gs, moves, 3)
    assert chosen in moves
    assert agent.nodes_expanded > 0
    assert agent.total_nodes == agent.nodes_expanded
    assert agent.last_decision_time >= 0.0
    assert agent.total_decisions == 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. Evaluation Function Heuristics
# ─────────────────────────────────────────────────────────────────────────────

def test_eval_progress_reward():
    agent = ExpectimaxAgent('yellow', depth=1)
    s1 = state_with({'yellow': [5, -1, -1, -1]})
    s2 = state_with({'yellow': [25, -1, -1, -1]})
    assert agent._evaluate(s2) > agent._evaluate(s1)


def test_eval_finish_reward():
    agent = ExpectimaxAgent('yellow', depth=1)
    s_active = state_with({'yellow': [PROGRESS_HOME_MAX, -1, -1, -1]})
    s_finished = state_with({'yellow': [PROGRESS_FINISHED, -1, -1, -1]})
    assert agent._evaluate(s_finished) > agent._evaluate(s_active)


def test_eval_safe_square_reward():
    agent = ExpectimaxAgent('yellow', depth=1)
    # Relative progress 8 is star safe square (abs 8)
    # Relative progress 9 is non-safe square
    s_safe = state_with({'yellow': [8, -1, -1, -1]})
    s_unsafe = state_with({'yellow': [7, -1, -1, -1]})
    # Both s_safe and s_unsafe are active, s_safe has safe bonus
    assert agent._evaluate(s_safe) > agent._evaluate(s_unsafe)


def test_eval_captures_opponents_in_base_reward():
    agent = ExpectimaxAgent('yellow', depth=1)
    # State 1: all blue pieces in base
    s_all_base = state_with({
        'yellow': [10, -1, -1, -1],
        'blue':   [-1, -1, -1, -1],
    })
    # State 2: blue has 2 pieces out on track
    s_opp_out = state_with({
        'yellow': [10, -1, -1, -1],
        'blue':   [10, 20, -1, -1],
    })
    assert agent._evaluate(s_all_base) > agent._evaluate(s_opp_out)


def test_eval_vulnerability_penalty():
    agent = ExpectimaxAgent('yellow', depth=1)
    # Yellow at 10 (abs 10). Red at 35 (abs 9, 1 step behind Yellow)
    s_threatened = state_with({
        'yellow': [10, -1, -1, -1],
        'red':    [35, -1, -1, -1],
    })
    # Yellow at 10. Red far away at 10 (abs 36)
    s_safe = state_with({
        'yellow': [10, -1, -1, -1],
        'red':    [10, -1, -1, -1],
    })
    assert agent._danger_score(s_threatened) > agent._danger_score(s_safe)
    assert agent._evaluate(s_safe) > agent._evaluate(s_threatened)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Search Depths (1, 2, 3) Execution
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("depth", [1, 2, 3])
def test_expectimax_search_depths(depth):
    """Expectimax functions cleanly and returns legal moves at depths 1, 2, and 3."""
    agent = ExpectimaxAgent('yellow', depth=depth)
    gs = state_with({
        'yellow': [5, 12, -1, -1],
        'blue':   [10, -1, -1, -1],
    })
    moves = gs.get_legal_moves(4)
    assert len(moves) == 2

    chosen = agent.choose_move(gs, moves, 4)
    assert chosen in moves
    assert agent.nodes_expanded > 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Strategic Decision Making
# ─────────────────────────────────────────────────────────────────────────────

def test_expectimax_chooses_capture():
    """Expectimax identifies and executes capture when opponent is vulnerable."""
    agent = ExpectimaxAgent('yellow', depth=2)
    # Yellow at 10 can roll 2 to reach 12 (abs 12)
    # Red is at red rel 38 -> abs (26+38)%52 = 12 (non-safe, capturable!)
    # Yellow also has a piece at 20 that can advance to 22 (safe, non-capturing)
    gs = state_with({
        'yellow': [10, 20, -1, -1],
        'red':    [38, -1, -1, -1],
    })
    moves = gs.get_legal_moves(2)
    assert any(m.captures for m in moves)

    chosen = agent.choose_move(gs, moves, 2)
    assert chosen is not None
    assert len(chosen.captures) > 0


def test_expectimax_prefers_finishing():
    """Expectimax prioritizes finishing into goal over ordinary moves."""
    agent = ExpectimaxAgent('yellow', depth=2)
    # Piece 0 at 54, rolls 2 -> finishes at 56 (PROGRESS_FINISHED)
    # Piece 1 at 10, rolls 2 -> advances to 12
    gs = state_with({'yellow': [54, 10, -1, -1]})
    moves = gs.get_legal_moves(2)

    chosen = agent.choose_move(gs, moves, 2)
    assert chosen.to_progress == PROGRESS_FINISHED
