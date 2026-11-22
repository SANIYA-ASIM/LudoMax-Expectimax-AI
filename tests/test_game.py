"""
test_game.py — Phase 3: Game Mechanics and Turn Management Tests
=================================================================
Tests for game.py:
  - Game initialization and validation (requires exactly 4 agents)
  - Dice roll generation (range 1-6 and determinism with random seed)
  - Turn execution and player advancement
  - Extra turn on rolling 6
  - Consecutive sixes: 3 consecutive 6s triggers forfeit and advances player
  - Move validation: rogue/bad agents returning illegal moves are overridden
  - execute_move() for interactive GUI integration and illegal move prevention
  - Statistics updates (turns, captures made, captures suffered)
  - Full game simulation loop (play_game) with winner detection
"""
import pytest
from board import COLORS, PROGRESS_BASE, PROGRESS_FINISHED
from game import Game
from game_state import GameState
from move import Move


class MockAgent:
    """Mock agent for testing game mechanics."""
    def __init__(self, color: str, strategy: str = "first"):
        self.color = color
        self.strategy = strategy  # "first", "last", "illegal", "none"

    def choose_move(self, state, legal_moves, dice_value):
        if self.strategy == "first":
            return legal_moves[0]
        elif self.strategy == "last":
            return legal_moves[-1]
        elif self.strategy == "none":
            return None
        elif self.strategy == "illegal":
            # Return an invalid move not present in legal_moves
            return Move(piece_index=99, dice_value=dice_value, from_progress=99, to_progress=100)
        return legal_moves[0]


def create_mock_agents(strategy: str = "first"):
    return [MockAgent(color, strategy) for color in COLORS]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Initialization
# ─────────────────────────────────────────────────────────────────────────────

def test_game_init_requires_4_agents():
    """Game must reject agent lists that do not contain exactly 4 agents."""
    agents_3 = [MockAgent(c) for c in COLORS[:3]]
    with pytest.raises(ValueError, match="Exactly 4 agents are required"):
        Game(agents_3)

    agents_5 = [MockAgent(c) for c in COLORS] + [MockAgent("extra")]
    with pytest.raises(ValueError, match="Exactly 4 agents are required"):
        Game(agents_5)


def test_game_init_success():
    """Game initializes with 4 agents, initial GameState, and zero stats."""
    agents = create_mock_agents()
    game = Game(agents, seed=42)
    assert len(game.agents) == 4
    for c in COLORS:
        assert c in game.agents
        assert game.stats[c]['turns'] == 0
        assert game.stats[c]['captures_made'] == 0
        assert game.stats[c]['captures_suffered'] == 0
    assert game.turn_count == 0
    assert game.winner is None
    assert game.state.current_player == COLORS[0]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Dice Generation
# ─────────────────────────────────────────────────────────────────────────────

def test_roll_dice_range():
    """Dice rolls must strictly produce integers between 1 and 6."""
    game = Game(create_mock_agents(), seed=123)
    rolls = [game.roll_dice() for _ in range(300)]
    assert all(1 <= r <= 6 for r in rolls)
    assert set(rolls) == {1, 2, 3, 4, 5, 6}


def test_roll_dice_reproducibility():
    """Identical seeds must produce identical dice sequences."""
    game1 = Game(create_mock_agents(), seed=999)
    game2 = Game(create_mock_agents(), seed=999)
    rolls1 = [game1.roll_dice() for _ in range(50)]
    rolls2 = [game2.roll_dice() for _ in range(50)]
    assert rolls1 == rolls2


# ─────────────────────────────────────────────────────────────────────────────
# 3. Turn Progression and Extra Turns
# ─────────────────────────────────────────────────────────────────────────────

def test_non_six_advances_turn():
    """A non-six roll advances the turn to the next player in COLORS order."""
    game = Game(create_mock_agents())
    assert game.state.current_player == 'yellow'

    turn_res = game.play_turn(dice=4)
    assert turn_res['player'] == 'yellow'
    assert turn_res['dice'] == 4
    assert game.state.current_player == 'blue'
    assert game.turn_count == 1
    assert game.stats['yellow']['turns'] == 1


def test_six_awards_extra_turn():
    """Rolling a 6 keeps the current player for another turn."""
    game = Game(create_mock_agents())
    assert game.state.current_player == 'yellow'

    turn_res = game.play_turn(dice=6)
    assert turn_res['player'] == 'yellow'
    assert turn_res['dice'] == 6
    assert turn_res['forfeit'] is False
    assert game.state.current_player == 'yellow'  # Extra turn!
    assert game.state.consecutive_sixes == 1


def test_three_consecutive_sixes_forfeit():
    """Three consecutive sixes forfeits the 3rd roll and advances player."""
    game = Game(create_mock_agents())
    assert game.state.current_player == 'yellow'

    # Roll 1: six
    t1 = game.play_turn(dice=6)
    assert t1['forfeit'] is False
    assert game.state.current_player == 'yellow'
    assert game.state.consecutive_sixes == 1

    # Roll 2: six
    t2 = game.play_turn(dice=6)
    assert t2['forfeit'] is False
    assert game.state.current_player == 'yellow'
    assert game.state.consecutive_sixes == 2

    # Roll 3: six → FORFEIT!
    t3 = game.play_turn(dice=6)
    assert t3['forfeit'] is True
    assert t3['move'] is None
    assert game.state.consecutive_sixes == 0
    assert game.state.current_player == 'blue'  # Advanced to next player!


# ─────────────────────────────────────────────────────────────────────────────
# 4. Engine Validation of Agent Moves
# ─────────────────────────────────────────────────────────────────────────────

def test_engine_overrides_none_move_from_agent():
    """If an agent returns None when legal moves exist, the engine defaults to a legal move."""
    game = Game(create_mock_agents(strategy="none"))
    # With dice=6, yellow can move pieces out of base
    res = game.play_turn(dice=6)
    assert res['move'] is not None
    assert res['move'].from_progress == PROGRESS_BASE
    assert res['move'].to_progress == 0


def test_engine_overrides_illegal_move_from_agent():
    """If an agent returns an illegal move, the engine rejects it and selects a legal move."""
    game = Game(create_mock_agents(strategy="illegal"))
    res = game.play_turn(dice=6)
    assert res['move'] is not None
    assert res['move'].piece_index in [0, 1, 2, 3]
    assert res['move'].to_progress == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Interactive execute_move()
# ─────────────────────────────────────────────────────────────────────────────

def test_execute_move_valid():
    """execute_move successfully applies a valid move and updates turn state."""
    game = Game(create_mock_agents())
    legal_moves = game.state.get_legal_moves(6)
    chosen_move = legal_moves[0]

    res = game.execute_move(chosen_move, 6)
    assert res['player'] == 'yellow'
    assert res['move'] == chosen_move
    assert game.state.pieces['yellow'][chosen_move.piece_index] == 0


def test_execute_move_illegal_raises():
    """execute_move raises ValueError when an illegal move is provided."""
    game = Game(create_mock_agents())
    illegal = Move(piece_index=0, dice_value=5, from_progress=PROGRESS_BASE, to_progress=0)
    with pytest.raises(ValueError, match="Illegal move"):
        game.execute_move(illegal, 5)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Winner Detection and Full Game Loop
# ─────────────────────────────────────────────────────────────────────────────

def test_play_game_terminates_and_reports_winner():
    """Full game with random agents terminates and announces a valid winner."""
    game = Game(create_mock_agents(), seed=42)
    winner = game.play_game(max_turns=1000)
    assert winner in COLORS or winner is None
    if winner is not None:
        assert game.state.is_game_over()
        assert game.winner == winner
        assert all(p == PROGRESS_FINISHED for p in game.state.pieces[winner])
