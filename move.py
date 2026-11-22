"""
move.py — Move Dataclass
========================
Represents a single piece movement in LudoMax.
"""
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Move:
    """Encodes one legal move.

    Attributes:
        piece_index:   Index of the piece being moved (0–3).
        dice_value:    The dice roll that enables this move.
        from_progress: Piece's progress before the move.
        to_progress:   Piece's progress after the move.
        captures:      List of (color, piece_index) tuples of captured pieces.
        player:        Player color/ID string (e.g. 'yellow', 'blue').
    """
    piece_index:   int
    dice_value:    int
    from_progress: int
    to_progress:   int
    captures:      List[Tuple[str, int]] = field(default_factory=list)
    player:        str = ""

    @property
    def player_id(self) -> str:
        """Alias for player."""
        return self.player

    @property
    def piece_id(self) -> int:
        """Alias for piece_index."""
        return self.piece_index

    @property
    def start_pos(self) -> int:
        """Alias for from_progress."""
        return self.from_progress

    @property
    def dest_pos(self) -> int:
        """Alias for to_progress."""
        return self.to_progress

    def __repr__(self) -> str:
        cap = f", captures={self.captures}" if self.captures else ""
        plr = f", player='{self.player}'" if self.player else ""
        return (f"Move(piece={self.piece_index}, dice={self.dice_value}, "
                f"{self.from_progress}→{self.to_progress}{cap}{plr})")
