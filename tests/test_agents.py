"""
test_agents.py — Phase 4: Random, Aggressive, Defensive, and Human AI Tests
===========================================================================
Tests covering:
  - Agent base class interface
  - RandomAgent move selection and deterministic seed reproducibility
  - AggressiveAgent prioritization (captures > finish > base exit > advance)
  - DefensiveAgent prioritization (safe square > finish > minimum threat)
  - HumanAgent pending move buffer and consumption
  - create_agent factory function for all agent types
"""
import pytest
from agents import (
    Agent, RandomAgent, AggressiveAgent, DefensiveAgent, HumanAgent,
    create_agent, AGENT_TYPES,
)
from board import (
    COLORS, SAFE_SQUARES, PROGRESS_BASE, PROGRESS_FINISHED,
    PROGRESS_HOME_MIN, get_absolute_track_pos,
)
from game_state import GameState
from move import Move


def state_with(pieces: dict, current_player: str = 'yellow') -> GameState:
    gs = GameState()
    gs.current_player = current_player
    for color, positions in pieces.items():
        gs.pieces[color] = list(positions)
    return gs


# ─────────────────────────────────────────────────────────────────────────────
# 1. Base Agent Interface
# ─────────────────────────────────────────────────────────────────────────────

def test_agent_base_interface():
    agent = Agent('yellow')
    assert agent.color == 'yellow'
    assert agent.name == 'Agent'
    assert repr(agent) == 'Agent(yellow)'
    with pytest.raises(NotImplementedError):
        agent.choose_move(GameState(), [], 1)


# ─────────────────────────────────────────────────────────────────────────────
# 2. RandomAgent
# ─────────────────────────────────────────────────────────────────────────────

def test_random_agent_empty_moves():
    agent = RandomAgent('yellow', seed=42)
    assert agent.choose_move(GameState(), [], 3) is None


def test_random_agent_selects_legal_move():
    agent = RandomAgent('yellow', seed=42)
    gs = state_with({'yellow': [0, 5, 10, 15]})
    moves = gs.get_legal_moves(4)
    chosen = agent.choose_move(gs, moves, 4)
    assert chosen in moves


def test_random_agent_seed_reproducibility():
    agent1 = RandomAgent('yellow', seed=12345)
    agent2 = RandomAgent('yellow', seed=12345)
    gs = state_with({'yellow': [0, 5, 10, 15]})
    moves = gs.get_legal_moves(4)
    c1 = [agent1.choose_move(gs, moves, 4) for _ in range(20)]
    c2 = [agent2.choose_move(gs, moves, 4) for _ in range(20)]
    assert c1 == c2


# ─────────────────────────────────────────────────────────────────────────────
# 3. AggressiveAgent
# ─────────────────────────────────────────────────────────────────────────────

def test_aggressive_agent_empty_moves():
    agent = AggressiveAgent('yellow')
    assert agent.choose_move(GameState(), [], 2) is None


def test_aggressive_agent_prioritizes_captures():
    """AggressiveAgent must prioritize a capturing move over non-capturing moves."""
    agent = AggressiveAgent('yellow')
    # Move A: non-capturing
    move_a = Move(piece_index=0, dice_value=3, from_progress=10, to_progress=13, captures=[])
    # Move B: capturing an opponent
    move_b = Move(piece_index=1, dice_value=3, from_progress=5, to_progress=8, captures=[('blue', 0)])

    gs = state_with({'yellow': [10, 5, -1, -1], 'blue': [20, -1, -1, -1]})
    chosen = agent.choose_move(gs, [move_a, move_b], 3)
    assert chosen == move_b


def test_aggressive_agent_prioritizes_highest_value_capture():
    """When multiple captures exist, AggressiveAgent captures the most advanced piece."""
    agent = AggressiveAgent('yellow')
    # Victim 0 is at progress 5
    move_a = Move(piece_index=0, dice_value=2, from_progress=10, to_progress=12, captures=[('blue', 0)])
    # Victim 1 is at progress 40 (much further along)
    move_b = Move(piece_index=1, dice_value=2, from_progress=20, to_progress=22, captures=[('red', 1)])

    gs = state_with({
        'yellow': [10, 20, -1, -1],
        'blue':   [5, -1, -1, -1],
        'red':    [-1, 40, -1, -1],
    })
    chosen = agent.choose_move(gs, [move_a, move_b], 2)
    assert chosen == move_b


def test_aggressive_agent_prioritizes_finishing_over_base_exit():
    """Finishing a piece takes precedence over exiting base when both are available."""
    agent = AggressiveAgent('yellow')
    move_finish = Move(piece_index=0, dice_value=6, from_progress=51, to_progress=PROGRESS_FINISHED)
    move_exit = Move(piece_index=1, dice_value=6, from_progress=PROGRESS_BASE, to_progress=0)

    gs = state_with({'yellow': [51, -1, -1, -1]})
    chosen = agent.choose_move(gs, [move_exit, move_finish], 6)
    assert chosen == move_finish


def test_aggressive_agent_prioritizes_base_exit_over_advance():
    """Bringing a piece out of base takes precedence over regular track advancement."""
    agent = AggressiveAgent('yellow')
    move_exit = Move(piece_index=0, dice_value=6, from_progress=PROGRESS_BASE, to_progress=0)
    move_advance = Move(piece_index=1, dice_value=6, from_progress=10, to_progress=16)

    gs = state_with({'yellow': [-1, 10, -1, -1]})
    chosen = agent.choose_move(gs, [move_advance, move_exit], 6)
    assert chosen == move_exit


def test_aggressive_agent_advances_furthest_piece():
    """When no captures or special conditions exist, advances the furthest piece."""
    agent = AggressiveAgent('yellow')
    move_lagging = Move(piece_index=0, dice_value=3, from_progress=5, to_progress=8)
    move_leading = Move(piece_index=1, dice_value=3, from_progress=30, to_progress=33)

    gs = state_with({'yellow': [5, 30, -1, -1]})
    chosen = agent.choose_move(gs, [move_lagging, move_leading], 3)
    assert chosen == move_leading


# ─────────────────────────────────────────────────────────────────────────────
# 4. DefensiveAgent
# ─────────────────────────────────────────────────────────────────────────────

def test_defensive_agent_empty_moves():
    agent = DefensiveAgent('yellow')
    assert agent.choose_move(GameState(), [], 1) is None


def test_defensive_agent_prioritizes_safe_square():
    """DefensiveAgent prioritizes moving to a safe square."""
    agent = DefensiveAgent('yellow')
    # Destination 8 is a star safe square for Yellow (abs 8 in SAFE_SQUARES)
    move_safe = Move(piece_index=0, dice_value=4, from_progress=4, to_progress=8)
    # Destination 9 is an unsafe square
    move_unsafe = Move(piece_index=1, dice_value=4, from_progress=5, to_progress=9)

    gs = state_with({'yellow': [4, 5, -1, -1]})
    chosen = agent.choose_move(gs, [move_unsafe, move_safe], 4)
    assert chosen == move_safe


def test_defensive_agent_prioritizes_home_column():
    """Moving into private home column is considered safe by DefensiveAgent."""
    agent = DefensiveAgent('yellow')
    move_home = Move(piece_index=0, dice_value=1, from_progress=50, to_progress=PROGRESS_HOME_MIN)
    move_track = Move(piece_index=1, dice_value=1, from_progress=10, to_progress=11)

    gs = state_with({'yellow': [50, 10, -1, -1]})
    chosen = agent.choose_move(gs, [move_track, move_home], 1)
    assert chosen == move_home


def test_defensive_agent_avoids_threats():
    """When safe squares are unavailable, DefensiveAgent selects the destination with fewest threats."""
    agent = DefensiveAgent('yellow')
    # Destination 10: threatened by Blue at blue rel 50 (abs 11-2 = 9? Blue offset 13: 13 + 36 = 49).
    # Specifically, set Red at abs 5, can roll 5 to land on abs 10.
    # Yellow move A lands at progress 10 (abs 10) -> threatened by Red!
    # Yellow move B lands at progress 25 (abs 25) -> no opponent near abs 25.
    move_threatened = Move(piece_index=0, dice_value=3, from_progress=7, to_progress=10)
    move_safe_track = Move(piece_index=1, dice_value=3, from_progress=22, to_progress=25)

    # Red piece at red rel 35 -> abs (26 + 35) % 52 = 9. With dice 1, Red can reach abs 10.
    gs = state_with({
        'yellow': [7, 22, -1, -1],
        'red':    [35, -1, -1, -1],
    })
    chosen = agent.choose_move(gs, [move_threatened, move_safe_track], 3)
    assert chosen == move_safe_track


# ─────────────────────────────────────────────────────────────────────────────
# 5. HumanAgent
# ─────────────────────────────────────────────────────────────────────────────

def test_human_agent_buffer_and_consumption():
    agent = HumanAgent('yellow')
    assert agent.name == 'Human'
    assert not agent.has_pending_move()

    move = Move(piece_index=0, dice_value=6, from_progress=PROGRESS_BASE, to_progress=0)
    agent.set_pending_move(move)
    assert agent.has_pending_move()

    chosen = agent.choose_move(GameState(), [move], 6)
    assert chosen == move
    # Once consumed, pending move is cleared
    assert not agent.has_pending_move()


def test_human_agent_clear_pending():
    agent = HumanAgent('blue')
    move = Move(piece_index=1, dice_value=3, from_progress=5, to_progress=8)
    agent.set_pending_move(move)
    agent.clear_pending_move()
    assert not agent.has_pending_move()
    assert agent.choose_move(GameState(), [move], 3) is None


# ─────────────────────────────────────────────────────────────────────────────
# 6. create_agent Factory
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("atype,expected_cls", [
    ('human', HumanAgent),
    ('random', RandomAgent),
    ('aggressive', AggressiveAgent),
    ('defensive', DefensiveAgent),
])
def test_create_agent_types(atype, expected_cls):
    agent = create_agent(atype, 'green')
    assert isinstance(agent, expected_cls)
    assert agent.color == 'green'


def test_create_agent_case_insensitive():
    agent = create_agent('AGGRESSIVE', 'red')
    assert isinstance(agent, AggressiveAgent)


def test_create_agent_invalid_raises():
    with pytest.raises(ValueError, match="Unknown agent type"):
        create_agent('quantum_ai', 'yellow')
