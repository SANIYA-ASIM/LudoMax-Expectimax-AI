"""
game_state.py — Immutable GameState for LudoMax
================================================
Stores all board information needed to represent the game at any point.
Used both by the live game and by the Expectimax search tree (via copy()).

Progress encoding (per player, per piece):
  -1    → piece is in base (not yet entered)
   0–50 → piece on the shared outer track (relative to that player; 50 is entrance)
  51–55 → piece in the 5 square-shaped blocks of private home path (positions 1–5)
  56    → piece in triangular final home destination (position 6 / FINISHED)
"""
import copy
from typing import Dict, List, Optional, Tuple

from board import (
    COLORS, PLAYER_OFFSETS, SAFE_SQUARES, HOME_COLUMNS,
    TRACK, get_absolute_track_pos,
    PROGRESS_BASE, PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX,
    PROGRESS_HOME_MIN, PROGRESS_HOME_MAX, PROGRESS_FINISHED,
)
from move import Move


class GameState:
    """Complete, copyable game state."""

    # ──────────────────────────────────────────────────────────────────────
    # Construction / Copying
    # ──────────────────────────────────────────────────────────────────────

    def __init__(self):
        # pieces[color][piece_idx] = progress value
        self.pieces: Dict[str, List[int]] = {
            color: [PROGRESS_BASE] * 4 for color in COLORS
        }
        # Turn order (can be rotated to change starting player)
        self.turn_order: List[str] = list(COLORS)
        self.current_player: str = COLORS[0]   # 'yellow' by default
        self.consecutive_sixes: int = 0

    def copy(self) -> 'GameState':
        """Deep copy – safe to modify without affecting the original."""
        ns = GameState.__new__(GameState)
        ns.pieces = {color: list(prog) for color, prog in self.pieces.items()}
        ns.turn_order = list(self.turn_order)
        ns.current_player = self.current_player
        ns.consecutive_sixes = self.consecutive_sixes
        return ns

    # ──────────────────────────────────────────────────────────────────────
    # Turn helpers
    # ──────────────────────────────────────────────────────────────────────

    def _next_player(self) -> str:
        idx = self.turn_order.index(self.current_player)
        return self.turn_order[(idx + 1) % len(self.turn_order)]

    # ──────────────────────────────────────────────────────────────────────
    # Legal move generation
    # ──────────────────────────────────────────────────────────────────────

    def get_legal_moves(self, dice_value: int) -> List[Move]:
        """Return all legal moves for the current player given dice_value."""
        player = self.current_player
        moves: List[Move] = []

        for piece_idx, progress in enumerate(self.pieces[player]):
            # ── Piece in base ──────────────────────────────────────────
            if progress == PROGRESS_BASE:
                if dice_value == 6:
                    captures = self._check_captures(player, 0)
                    moves.append(Move(piece_idx, dice_value,
                                      PROGRESS_BASE, 0, captures, player=player))
                continue

            # ── Piece already finished ────────────────────────────────
            if progress == PROGRESS_FINISHED:
                continue

            # ── Piece on track or home column ─────────────────────────
            new_progress = progress + dice_value

            # Overshoot check: cannot go beyond FINISHED
            if new_progress > PROGRESS_FINISHED:
                continue

            # Determine captures (only possible on shared track)
            if new_progress <= PROGRESS_TRACK_MAX:
                captures = self._check_captures(player, new_progress)
            else:
                captures = []   # home column and finish are always safe

            moves.append(Move(piece_idx, dice_value,
                              progress, new_progress, captures, player=player))

        return moves

    def _check_captures(self, player: str, new_progress: int) -> List[Tuple[str, int]]:
        """Return list of (color, piece_idx) for opponent pieces captured
        when this player's piece lands at new_progress (shared track only)."""
        captures: List[Tuple[str, int]] = []

        # Only shared-track landings can produce captures
        if new_progress < PROGRESS_TRACK_MIN or new_progress > PROGRESS_TRACK_MAX:
            return captures

        abs_pos = get_absolute_track_pos(player, new_progress)

        # Safe squares are immune to capture
        if abs_pos in SAFE_SQUARES:
            return captures

        opp_offset = PLAYER_OFFSETS
        for opp_color in COLORS:
            if opp_color == player:
                continue
            opp_off = opp_offset[opp_color]
            for opp_idx, opp_prog in enumerate(self.pieces[opp_color]):
                if PROGRESS_TRACK_MIN <= opp_prog <= PROGRESS_TRACK_MAX:
                    opp_abs = (opp_off + opp_prog) % 52
                    if opp_abs == abs_pos:
                        captures.append((opp_color, opp_idx))

        return captures

    # ──────────────────────────────────────────────────────────────────────
    # Move application (returns a NEW state; original is unchanged)
    # ──────────────────────────────────────────────────────────────────────

    def apply_move(self, move: Optional[Move], dice_value: int) -> 'GameState':
        """Apply *move* (may be None for a pass) and return the new state."""
        ns = self.copy()
        player = ns.current_player

        if move is not None:
            ns.pieces[player][move.piece_index] = move.to_progress
            for cap_color, cap_idx in move.captures:
                ns.pieces[cap_color][cap_idx] = PROGRESS_BASE

        # ── Update turn ───────────────────────────────────────────────
        has_captured = bool(move is not None and move.captures)

        if move is None:
            # No legal move → always pass to next player
            ns.consecutive_sixes = 0
            ns.current_player = ns._next_player()
        elif dice_value == 6:
            ns.consecutive_sixes = self.consecutive_sixes + 1
            if ns.consecutive_sixes >= 3:
                # Third consecutive 6: forfeit, next player
                ns.consecutive_sixes = 0
                ns.current_player = ns._next_player()
            # else: same player gets another turn (consecutive_sixes updated)
        elif has_captured:
            # Extra turn on capture! Player receives another dice roll
            ns.consecutive_sixes = 0
            # ns.current_player remains unchanged (same player continues)
        else:
            ns.consecutive_sixes = 0
            ns.current_player = ns._next_player()

        return ns

    # ──────────────────────────────────────────────────────────────────────
    # Win / game-over checks
    # ──────────────────────────────────────────────────────────────────────

    def is_game_over(self) -> bool:
        for color in COLORS:
            if all(p == PROGRESS_FINISHED for p in self.pieces[color]):
                return True
        return False

    def get_winner(self) -> Optional[str]:
        for color in COLORS:
            if all(p == PROGRESS_FINISHED for p in self.pieces[color]):
                return color
        return None

    # ──────────────────────────────────────────────────────────────────────
    # Convenience queries
    # ──────────────────────────────────────────────────────────────────────

    def pieces_in_base(self, color: str) -> int:
        return sum(1 for p in self.pieces[color] if p == PROGRESS_BASE)

    def pieces_finished(self, color: str) -> int:
        return sum(1 for p in self.pieces[color] if p == PROGRESS_FINISHED)

    def pieces_active(self, color: str) -> int:
        """Pieces on board (not in base and not finished)."""
        return sum(1 for p in self.pieces[color]
                   if PROGRESS_TRACK_MIN <= p <= PROGRESS_HOME_MAX)

    def __repr__(self) -> str:
        lines = [f"GameState(current={self.current_player}, "
                 f"consec6={self.consecutive_sixes})"]
        for color in COLORS:
            lines.append(f"  {color}: {self.pieces[color]}")
        return "\n".join(lines)
