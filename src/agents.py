"""
agents.py — AI and Human Agents for LudoMax
============================================
Provides:
  Agent          — base class (abstract interface)
  RandomAgent    — picks a random legal move
  AggressiveAgent — prioritises captures, then leaving base, then advancing
  DefensiveAgent  — prioritises safe squares and low-danger destinations
  HumanAgent      — stores a pending move set by the UI
  create_agent()  — factory function
"""
import random
from typing import List, Optional

from board import (
    COLORS, PLAYER_OFFSETS, SAFE_SQUARES,
    PROGRESS_BASE, PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX,
    PROGRESS_HOME_MIN, PROGRESS_FINISHED,
    get_absolute_track_pos,
)
from move import Move


# ─────────────────────────────────────────────────────────────────────────────
# Base class
# ─────────────────────────────────────────────────────────────────────────────

class Agent:
    """Abstract base agent."""

    def __init__(self, color: str):
        self.color = color

    def choose_move(self, game_state, legal_moves: List[Move],
                    dice_value: int) -> Optional[Move]:
        """Select and return one move from *legal_moves*.

        Return None only when *legal_moves* is empty.
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.name}({self.color})"


# ─────────────────────────────────────────────────────────────────────────────
# Random Agent
# ─────────────────────────────────────────────────────────────────────────────

class RandomAgent(Agent):
    """Chooses a uniformly random legal move. Baseline for comparison."""

    def __init__(self, color: str, seed: Optional[int] = None, **kwargs):
        super().__init__(color)
        self.rng = random.Random(seed)

    def choose_move(self, game_state, legal_moves: List[Move],
                    dice_value: int) -> Optional[Move]:
        if not legal_moves:
            return None
        return self.rng.choice(legal_moves)

    @property
    def name(self) -> str:
        return "Random"


# ─────────────────────────────────────────────────────────────────────────────
# Aggressive Agent
# ─────────────────────────────────────────────────────────────────────────────

class AggressiveAgent(Agent):
    """Heuristic agent that prioritises:
    1. Capturing opponents (most-advanced victim first).
    2. Bringing a piece out of base (when dice==6).
    3. Finishing a piece (reaching progress 58).
    4. Advancing the furthest active piece.
    5. Any remaining legal move.
    """

    @property
    def name(self) -> str:
        return "Aggressive"

    def choose_move(self, game_state, legal_moves: List[Move],
                    dice_value: int) -> Optional[Move]:
        if not legal_moves:
            return None

        # Priority 1: captures
        capturing = [m for m in legal_moves if m.captures]
        if capturing:
            # Pick the move that captures the most-advanced opponent piece
            def capture_value(m):
                return max(
                    game_state.pieces[c][i] for c, i in m.captures
                )
            return max(capturing, key=capture_value)

        # Priority 2: finish a piece
        finishing = [m for m in legal_moves if m.to_progress == PROGRESS_FINISHED]
        if finishing:
            return finishing[0]

        # Priority 3: bring out a piece from base
        from_base = [m for m in legal_moves if m.from_progress == PROGRESS_BASE]
        if from_base:
            return from_base[0]

        # Priority 4: advance furthest piece
        return max(legal_moves, key=lambda m: m.from_progress)


# ─────────────────────────────────────────────────────────────────────────────
# Defensive Agent
# ─────────────────────────────────────────────────────────────────────────────

class DefensiveAgent(Agent):
    """Heuristic agent that prioritises:
    1. Moving to a safe square.
    2. Finishing a piece (progress 58).
    3. Moving to the destination with the fewest threats.
    4. Keeping pieces in home column (progress >= 52).
    """

    @property
    def name(self) -> str:
        return "Defensive"

    def _is_safe_dest(self, move: Move) -> bool:
        if move.to_progress >= PROGRESS_HOME_MIN:
            return True  # home column always safe
        abs_pos = get_absolute_track_pos(self.color, move.to_progress)
        return abs_pos in SAFE_SQUARES

    def _threat_count(self, game_state, move: Move) -> int:
        """Count how many opponent pieces could reach this square next turn."""
        if move.to_progress >= PROGRESS_HOME_MIN:
            return 0
        abs_dest = get_absolute_track_pos(self.color, move.to_progress)
        if abs_dest in SAFE_SQUARES:
            return 0

        count = 0
        for d in range(1, 7):
            for opp in COLORS:
                if opp == self.color:
                    continue
                opp_off = PLAYER_OFFSETS[opp]
                for prog in game_state.pieces[opp]:
                    if PROGRESS_TRACK_MIN <= prog <= PROGRESS_TRACK_MAX:
                        # Opponents only stay on shared track if prog + d <= PROGRESS_TRACK_MAX
                        if prog + d <= PROGRESS_TRACK_MAX:
                            opp_abs = (opp_off + prog + d) % 52
                            if opp_abs == abs_dest:
                                count += 1
        return count

    def choose_move(self, game_state, legal_moves: List[Move],
                    dice_value: int) -> Optional[Move]:
        if not legal_moves:
            return None

        # Priority 1: move to safe square (tie-break by advancing further)
        safe_moves = [m for m in legal_moves if self._is_safe_dest(m)]
        if safe_moves:
            return min(safe_moves, key=lambda m: (self._threat_count(game_state, m), -m.to_progress))

        # Priority 2: finish a piece
        finishing = [m for m in legal_moves if m.to_progress == PROGRESS_FINISHED]
        if finishing:
            return finishing[0]

        # Priority 3: least dangerous destination (tie-break by advancing further)
        return min(legal_moves, key=lambda m: (self._threat_count(game_state, m), -m.to_progress))


# ─────────────────────────────────────────────────────────────────────────────
# Human Agent
# ─────────────────────────────────────────────────────────────────────────────

class HumanAgent(Agent):
    """Receives its move choice from the UI via set_pending_move()."""

    def __init__(self, color: str, **kwargs):
        super().__init__(color)
        self._pending: Optional[Move] = None

    @property
    def name(self) -> str:
        return "Human"

    def set_pending_move(self, move: Move):
        self._pending = move

    def clear_pending_move(self):
        self._pending = None

    def has_pending_move(self) -> bool:
        return self._pending is not None

    def choose_move(self, game_state, legal_moves: List[Move],
                    dice_value: int) -> Optional[Move]:
        move = self._pending
        self._pending = None   # consume
        return move


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

def create_agent(agent_type: str, color: str,
                 seed: Optional[int] = None,
                 depth: int = 2,
                 **kwargs) -> Agent:
    """Return an Agent instance given a type string.

    agent_type must be one of:
        'human', 'random', 'aggressive', 'defensive', 'expectimax'
    """
    t = agent_type.lower()
    if t == 'human':
        return HumanAgent(color)
    if t == 'random':
        return RandomAgent(color, seed=seed)
    if t == 'aggressive':
        return AggressiveAgent(color)
    if t == 'defensive':
        return DefensiveAgent(color)
    if t == 'expectimax':
        from expectimax import ExpectimaxAgent
        return ExpectimaxAgent(color, depth=depth)
    raise ValueError(f"Unknown agent type: '{agent_type}'. "
                     "Choose from: human, random, aggressive, defensive, expectimax")


AGENT_TYPES = ['human', 'random', 'aggressive', 'defensive', 'expectimax']
AGENT_DISPLAY = {
    'human': 'Human',
    'random': 'Random AI',
    'aggressive': 'Aggressive AI',
    'defensive': 'Defensive AI',
    'expectimax': 'Expectimax AI',
}
