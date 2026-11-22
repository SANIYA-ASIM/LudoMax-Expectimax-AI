"""
game.py — Game Controller and Turn Manager for LudoMax
======================================================
Orchestrates dice rolling, turn management, extra turns, rule enforcement,
and agent interaction. Operates independently of Pygame GUI and works for both
headless simulation (tournament) and interactive GUI gameplay.

Rules & Mechanics for Ambiguous Ludo Situations:
------------------------------------------------
1. Base Exit:
   - Rolling a 6 is strictly required to move a piece from Base (-1) to the
     player's starting track position (relative progress 0).
2. Extra Turn on Six:
   - Any roll of 6 awards the player an immediate extra roll.
3. Three Consecutive Sixes Penalty:
   - If a player rolls three sixes in succession (consecutive_sixes reaches 2 and
     rolls another 6), the third roll is forfeited: no piece moves, the counter
     resets to 0, and the turn immediately passes to the next player.
4. Captures & Safe Squares:
   - Landing on an opponent piece on any of the 44 non-safe shared-track squares
     captures that piece and sends it back to its Base (-1).
   - If multiple opponent pieces share a non-safe square, all of them are captured.
   - The 8 designated safe squares (4 player start squares + 4 star squares) protect
     any piece occupying them; pieces coexisting on safe squares are immune to capture.
5. Private Home Columns & Exact Finish:
   - Each player has a private home path of exactly 6 positions:
     5 square-shaped blocks (progress 51–55) + 1 triangular final home destination (progress 56 / FINISHED)
     where pieces cannot be entered or captured by opponents.
   - A piece enters the center goal (progress 56 / FINISHED) only on an EXACT dice roll.
   - Overshooting past progress 56 is strictly illegal; if no pieces can legally move,
     the turn is passed.
6. Engine Validation:
   - The engine validates every move against GameState.get_legal_moves() independently
     of the AI agent or GUI caller, ensuring no illegal moves can ever be executed.
"""
import random
from typing import Dict, List, Optional

from board import COLORS
from game_state import GameState
from move import Move


class Game:
    """Manages a complete Ludo game between 4 agents.

    Args:
        agents: List of 4 Agent objects in COLORS order
                [yellow_agent, blue_agent, red_agent, green_agent].
        seed:   Random seed for reproducible dice rolls (None = non-deterministic).
    """

    def __init__(self, agents: list, seed: Optional[int] = None):
        if len(agents) != 4:
            raise ValueError("Exactly 4 agents are required.")

        self.agents: Dict[str, object] = {
            color: agent for color, agent in zip(COLORS, agents)
        }
        self.rng = random.Random(seed)
        self.state = GameState()
        self.winner: Optional[str] = None
        self.turn_count: int = 0

        # Per-player statistics
        self.stats: Dict[str, Dict] = {
            color: {
                'captures_made': 0,
                'captures_suffered': 0,
                'turns': 0,
            }
            for color in COLORS
        }

    # ──────────────────────────────────────────────────────────────────────
    # Dice
    # ──────────────────────────────────────────────────────────────────────

    def roll_dice(self) -> int:
        """Return a random integer 1–6."""
        return self.rng.randint(1, 6)

    # ──────────────────────────────────────────────────────────────────────
    # Turn execution (supports headless tournament & testing)
    # ──────────────────────────────────────────────────────────────────────

    def play_turn(self, dice: Optional[int] = None) -> dict:
        """Execute one complete turn for the current player.

        Args:
            dice: Optional explicit dice roll (for testing/deterministic replay).
                  If None, self.roll_dice() is called.

        Returns a dict with keys:
            player, dice, move, forfeit, captures
        """
        player = self.state.current_player
        self.stats[player]['turns'] += 1

        if dice is None:
            dice = self.roll_dice()

        # ── Third consecutive 6: forfeit ─────────────────────────────
        if dice == 6 and self.state.consecutive_sixes >= 2:
            ns = self.state.copy()
            ns.consecutive_sixes = 0
            ns.current_player = ns._next_player()
            self.state = ns
            self.turn_count += 1
            return {
                'player': player,
                'dice': dice,
                'move': None,
                'forfeit': True,
                'captures': [],
            }

        # ── Get legal moves ───────────────────────────────────────────
        legal_moves = self.state.get_legal_moves(dice)

        # ── Ask agent to choose and strictly validate move ────────────
        agent = self.agents[player]
        if legal_moves:
            chosen = agent.choose_move(self.state, legal_moves, dice)
            # Ensure move is strictly within legal_moves (engine independence)
            if chosen in legal_moves:
                move = chosen
            else:
                move = legal_moves[0]
        else:
            move = None

        # ── Update statistics ─────────────────────────────────────────
        captures = []
        if move and move.captures:
            captures = list(move.captures)
            self.stats[player]['captures_made'] += len(captures)
            for cap_color, _ in captures:
                self.stats[cap_color]['captures_suffered'] += 1

        # ── Apply move ────────────────────────────────────────────────
        self.state = self.state.apply_move(move, dice)
        self.turn_count += 1

        if self.state.is_game_over() and self.winner is None:
            self.winner = self.state.get_winner()

        return {
            'player': player,
            'dice': dice,
            'move': move,
            'forfeit': False,
            'captures': captures,
        }

    def execute_move(self, move: Optional[Move], dice_value: int) -> dict:
        """Directly execute a specified move with a given dice roll.
        Used by the interactive GUI layer for human move selection.

        Args:
            move: The chosen legal Move (or None if no legal moves exist).
            dice_value: The dice value that generated the move.

        Returns a dict with turn execution details.
        """
        player = self.state.current_player
        self.stats[player]['turns'] += 1

        # Enforce move legality if a move is supplied
        if move is not None:
            legal_moves = self.state.get_legal_moves(dice_value)
            if move not in legal_moves:
                raise ValueError(f"Illegal move {move} for dice {dice_value}")

        captures = []
        if move and move.captures:
            captures = list(move.captures)
            self.stats[player]['captures_made'] += len(captures)
            for cap_color, _ in captures:
                self.stats[cap_color]['captures_suffered'] += 1

        self.state = self.state.apply_move(move, dice_value)
        self.turn_count += 1

        if self.state.is_game_over() and self.winner is None:
            self.winner = self.state.get_winner()

        return {
            'player': player,
            'dice': dice_value,
            'move': move,
            'forfeit': False,
            'captures': captures,
        }

    def is_game_over(self) -> bool:
        """Check if game has reached a terminal winning state."""
        return self.state.is_game_over() or self.winner is not None

    def get_winner(self) -> Optional[str]:
        """Return winning player color, or None."""
        if self.winner is not None:
            return self.winner
        return self.state.get_winner()

    # ──────────────────────────────────────────────────────────────────────
    # Full game loop (headless)
    # ──────────────────────────────────────────────────────────────────────

    def play_game(self, max_turns: int = 2000) -> Optional[str]:
        """Play until someone wins (or max_turns is reached).

        Returns the winner colour, or None if max_turns exceeded.
        """
        while not self.state.is_game_over() and self.turn_count < max_turns:
            self.play_turn()

        self.winner = self.state.get_winner()
        return self.winner
