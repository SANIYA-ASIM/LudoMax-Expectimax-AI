"""
board.py — LudoMax Board Data and Coordinate System
=====================================================
Defines the 15×15 Ludo board geometry:
  - 52-square shared outer track
  - Safe squares (8 total: 4 start squares + 4 star squares)
  - Home path for each player: exactly 6 positions:
      Positions 1–5: 5 square-shaped blocks (progress 51–55)
      Position  6:   1 triangular-shaped center goal block (progress 56 / FINISHED)
  - Base piece slot positions
  - Progress constants:
      -1    → piece is in base (not yet entered the board)
       0–50 → piece on shared outer track (51 squares; 50 is the home-entrance square)
      51–55 → piece in 5 square-shaped blocks of private home path (positions 1–5)
      56    → piece in triangular final home destination (position 6 / center goal)

Grid coordinates use (col, row) on a 15×15 grid where col=0 is the
left edge and row=0 is the top edge.  Call grid_to_screen() to convert
to pixel coordinates for Pygame rendering.
"""

from typing import Tuple, List, Dict, Set, FrozenSet

# ── Player colours (also dict keys throughout the project) ──────────────────
COLORS = ['yellow', 'blue', 'red', 'green']

# RGB display colours
COLOR_VALUES = {
    'yellow': (255, 215,   0),
    'blue':   ( 65, 105, 225),
    'red':    (220,  50,  60),
    'green':  ( 50, 200,  70),
}

# Darker shades used for outlines / home column tinting
COLOR_DARK = {
    'yellow': (180, 150,   0),
    'blue':   ( 40,  65, 155),
    'red':    (155,  30,  35),
    'green':  ( 30, 130,  45),
}

# Lighter/brighter tints used for home column cells
COLOR_LIGHT = {
    'yellow': (255, 240, 100),
    'blue':   (130, 170, 255),
    'red':    (255, 130, 130),
    'green':  (130, 255, 150),
}

# Dark base background colours
COLOR_BASE_BG = {
    'yellow': ( 55,  45,   5),
    'blue':   ( 10,  18,  70),
    'red':    ( 70,  12,  15),
    'green':  ( 10,  50,  15),
}

# ── Shared outer track (52 squares, clockwise from Yellow's entry) ──────────
# Each entry is (col, row) on a 15×15 grid (col = x-index, row = y-index).
TRACK = [
    # Yellow side: row 6, cols 1-5 (going right)
    (1, 6), (2, 6), (3, 6), (4, 6), (5, 6),          # 0-4   Yellow entry = 0
    # Up col 6: rows 5 → 0
    (6, 5), (6, 4), (6, 3), (6, 2), (6, 1), (6, 0),   # 5-10
    # Top of board: row 0, cols 7-8
    (7, 0), (8, 0),                                    # 11-12
    # Down col 8: rows 1 → 5
    (8, 1), (8, 2), (8, 3), (8, 4), (8, 5),            # 13-17  Blue entry = 13
    # Blue side: row 6, cols 9-13
    (9, 6), (10, 6), (11, 6), (12, 6), (13, 6),        # 18-22
    # Right edge col 14: rows 6-8
    (14, 6), (14, 7), (14, 8),                          # 23-25
    # Red side: row 8, cols 13 → 9
    (13, 8), (12, 8), (11, 8), (10, 8), (9, 8),        # 26-30  Red entry = 26
    # Down col 8: rows 9 → 13
    (8, 9), (8, 10), (8, 11), (8, 12), (8, 13),        # 31-35
    # Bottom of board: row 14
    (8, 14), (7, 14), (6, 14),                          # 36-38
    # Green side: col 6, rows 13 → 9
    (6, 13), (6, 12), (6, 11), (6, 10), (6, 9),        # 39-43  Green entry = 39
    # Row 8, left portion: cols 5 → 1
    (5, 8), (4, 8), (3, 8), (2, 8), (1, 8),            # 44-48
    # Left edge col 0: rows 8 → 6
    (0, 8), (0, 7), (0, 6),                             # 49-51
]

assert len(TRACK) == 52, "TRACK must have exactly 52 squares"

# Fast-lookup structures
TRACK_SET   = set(TRACK)
TRACK_INDEX = {pos: idx for idx, pos in enumerate(TRACK)}

# ── Player offsets on the outer track ───────────────────────────────────────
# The entry square for each player (their progress-0 position).
PLAYER_OFFSETS = {
    'yellow':  0,
    'blue':   13,
    'red':    26,
    'green':  39,
}

# ── Safe squares (absolute track indices) ───────────────────────────────────
# The 4 player start squares + 4 starred squares = 8 safe squares total.
SAFE_SQUARES = frozenset({0, 8, 13, 21, 26, 34, 39, 47})

# ── Home columns: (col, row) for progress 51 → 55 (5 square-shaped blocks) ───
HOME_COLUMNS = {
    'yellow': [(1,7), (2,7), (3,7), (4,7), (5,7)],   # row 7, left → centre (5 squares)
    'blue':   [(7,1), (7,2), (7,3), (7,4), (7,5)],   # col 7, top → centre  (5 squares)
    'red':    [(13,7),(12,7),(11,7),(10,7),(9,7)],   # row 7, right → centre (5 squares)
    'green':  [(7,13),(7,12),(7,11),(7,10),(7,9)],   # col 7, bottom → centre (5 squares)
}
HOME_COLUMN_SETS = {c: set(map(tuple, lst)) for c, lst in HOME_COLUMNS.items()}

# ── Base piece-slot positions (col, row) for rendering ──────────────────────
# Symmetrically centered within each player's 6×6 corner base
BASE_POSITIONS = {
    'yellow': [(1, 1),  (4, 1),  (1, 4),  (4, 4)],
    'blue':   [(10, 1), (13, 1), (10, 4), (13, 4)],
    'red':    [(10, 10),(13, 10),(10, 13),(13, 13)],
    'green':  [(1, 10), (4, 10), (1, 13), (4, 13)],
}

# ── Progress constants ───────────────────────────────────────────────────────
PROGRESS_BASE       = -1   # piece in base (not yet out)
PROGRESS_TRACK_MIN  =  0   # first square on shared track
PROGRESS_TRACK_MAX  = 50   # last  square on shared track (home-entrance square)
PROGRESS_HOME_MIN   = 51   # first square-shaped block of home path (position 1)
PROGRESS_HOME_MAX   = 55   # fifth square-shaped block of home path (position 5)
PROGRESS_FINISHED   = 56   # triangular final home destination (position 6 / center goal)


# ── Helper functions ─────────────────────────────────────────────────────────

def get_absolute_track_pos(color: str, progress: int) -> int:
    """Return the absolute track index (0-51) for a piece at the given
    relative progress (0-51) for the specified player colour."""
    return (PLAYER_OFFSETS[color] + progress) % 52


def get_piece_grid_pos(color: str, progress: int, piece_slot: int = 0):
    """Return the (col, row) board cell for a piece.

    Args:
        color:      player colour string
        progress:   piece progress value
        piece_slot: slot index (0-3) used only when piece is in base (-1)

    Returns:
        (col, row) tuple, or (7, 7) for finished pieces.
    """
    if progress == PROGRESS_BASE:
        return BASE_POSITIONS[color][piece_slot]
    if PROGRESS_TRACK_MIN <= progress <= PROGRESS_TRACK_MAX:
        abs_idx = get_absolute_track_pos(color, progress)
        return TRACK[abs_idx]
    if PROGRESS_HOME_MIN <= progress <= PROGRESS_HOME_MAX:
        return HOME_COLUMNS[color][progress - PROGRESS_HOME_MIN]
    # PROGRESS_FINISHED or beyond
    return (7, 7)


def is_safe_absolute(abs_track_idx: int) -> bool:
    """Return True if the given absolute track index is a safe square."""
    return abs_track_idx in SAFE_SQUARES


def grid_to_screen(col: int, row: int, cell_size: int,
                   board_offset_x: int = 0,
                   board_offset_y: int = 0) -> tuple:
    """Convert a 15×15 grid cell to pixel centre coordinates.

    Args:
        col:            Grid column index (0–14, left → right).
        row:            Grid row index    (0–14, top  → bottom).
        cell_size:      Pixel size of each square grid cell.
        board_offset_x: Left margin in pixels (default 0).
        board_offset_y: Top  margin in pixels (default 0).

    Returns:
        (px, py) — pixel coordinates of the cell centre.
    """
    px = board_offset_x + col * cell_size + cell_size // 2
    py = board_offset_y + row * cell_size + cell_size // 2
    return px, py


# ── Board class encapsulating geometry, tracks, offsets & conversions ────────

class Board:
    """Board representation and coordinate conversion.

    Encapsulates 15×15 board geometry, track positions, starting offsets,
    safe squares, home columns, base positions, and coordinate conversions.
    """
    GRID_SIZE: int = 15
    TRACK: List[Tuple[int, int]] = TRACK
    TRACK_SET: Set[Tuple[int, int]] = TRACK_SET
    TRACK_INDEX: Dict[Tuple[int, int], int] = TRACK_INDEX
    PLAYER_OFFSETS: Dict[str, int] = PLAYER_OFFSETS
    SAFE_SQUARES: FrozenSet[int] = SAFE_SQUARES
    HOME_COLUMNS: Dict[str, List[Tuple[int, int]]] = HOME_COLUMNS
    HOME_COLUMN_SETS: Dict[str, Set[Tuple[int, int]]] = HOME_COLUMN_SETS
    BASE_POSITIONS: Dict[str, List[Tuple[int, int]]] = BASE_POSITIONS
    COLORS: List[str] = COLORS

    PROGRESS_BASE: int = PROGRESS_BASE
    PROGRESS_TRACK_MIN: int = PROGRESS_TRACK_MIN
    PROGRESS_TRACK_MAX: int = PROGRESS_TRACK_MAX
    PROGRESS_HOME_MIN: int = PROGRESS_HOME_MIN
    PROGRESS_HOME_MAX: int = PROGRESS_HOME_MAX
    PROGRESS_FINISHED: int = PROGRESS_FINISHED

    @staticmethod
    def get_absolute_track_pos(color: str, progress: int) -> int:
        """Return the absolute track index (0-51) for relative progress."""
        return get_absolute_track_pos(color, progress)

    @staticmethod
    def get_piece_grid_pos(color: str, progress: int, piece_slot: int = 0) -> Tuple[int, int]:
        """Return the (col, row) board cell for a piece."""
        return get_piece_grid_pos(color, progress, piece_slot)

    @staticmethod
    def is_safe_absolute(abs_track_idx: int) -> bool:
        """Return True if the absolute track index is a safe square."""
        return is_safe_absolute(abs_track_idx)

    @staticmethod
    def grid_to_screen(col: int, row: int, cell_size: int,
                       board_offset_x: int = 0,
                       board_offset_y: int = 0) -> Tuple[int, int]:
        """Convert a 15×15 grid cell to pixel centre coordinates."""
        return grid_to_screen(col, row, cell_size, board_offset_x, board_offset_y)


# ── Module self-test (run directly: python src/board.py) ─────────────────────

if __name__ == '__main__':
    import sys
    # Reconfigure stdout to UTF-8 so Unicode symbols work on all terminals.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    errors: list = []

    # 1. Track length
    if len(TRACK) != 52:
        errors.append(f'TRACK length {len(TRACK)} != 52')

    # 2. Track uniqueness
    if len(set(TRACK)) != 52:
        errors.append('TRACK contains duplicate positions')

    # 3. Player offsets in range
    for c, off in PLAYER_OFFSETS.items():
        if not (0 <= off < 52):
            errors.append(f'PLAYER_OFFSETS[{c}]={off} out of range')

    # 4. Safe squares
    if len(SAFE_SQUARES) != 8:
        errors.append(f'SAFE_SQUARES count {len(SAFE_SQUARES)} != 8')
    for sq in SAFE_SQUARES:
        if not (0 <= sq < 52):
            errors.append(f'Safe square {sq} out of range')

    # 5. Home columns
    for c, hc in HOME_COLUMNS.items():
        if len(hc) != 5:
            errors.append(f'HOME_COLUMNS[{c}] length {len(hc)} != 5')

    # 6. Base positions
    for c, bp in BASE_POSITIONS.items():
        if len(bp) != 4:
            errors.append(f'BASE_POSITIONS[{c}] length {len(bp)} != 4')

    # 7. get_absolute_track_pos known values
    expected = [('yellow', 0, 0), ('blue', 0, 13),
                ('red', 0, 26), ('green', 0, 39),
                ('yellow', 13, 13), ('blue', 13, 26)]
    for color, prog, exp_abs in expected:
        got = get_absolute_track_pos(color, prog)
        if got != exp_abs:
            errors.append(
                f'get_absolute_track_pos({color},{prog})={got}, expected {exp_abs}')

    # 8. get_piece_grid_pos — base
    for c in COLORS:
        for slot in range(4):
            pos = get_piece_grid_pos(c, PROGRESS_BASE, slot)
            if pos != BASE_POSITIONS[c][slot]:
                errors.append(f'get_piece_grid_pos base mismatch {c} slot {slot}')

    # 9. get_piece_grid_pos — finished
    for c in COLORS:
        pos = get_piece_grid_pos(c, PROGRESS_FINISHED)
        if pos != (7, 7):
            errors.append(f'get_piece_grid_pos finished {c} -> {pos}, expected (7,7)')

    # 10. grid_to_screen
    px, py = grid_to_screen(0, 0, 50)
    if (px, py) != (25, 25):
        errors.append(f'grid_to_screen(0,0,50)=({px},{py}), expected (25,25)')
    px, py = grid_to_screen(2, 3, 40, board_offset_x=10, board_offset_y=20)
    if (px, py) != (110, 160):
        errors.append(f'grid_to_screen offset=({px},{py}), expected (110,160)')

    # 11. Progress constants
    assert PROGRESS_BASE      == -1
    assert PROGRESS_TRACK_MIN ==  0
    assert PROGRESS_TRACK_MAX == 50
    assert PROGRESS_HOME_MIN  == 51
    assert PROGRESS_HOME_MAX  == 55
    assert PROGRESS_FINISHED  == 56

    # 12. Board class methods and attributes
    b = Board()
    if b.GRID_SIZE != 15:
        errors.append(f'Board.GRID_SIZE {b.GRID_SIZE} != 15')
    if b.get_absolute_track_pos('blue', 0) != 13:
        errors.append('Board.get_absolute_track_pos mismatch')
    if not b.is_safe_absolute(0):
        errors.append('Board.is_safe_absolute mismatch')
    if b.grid_to_screen(0, 0, 50) != (25, 25):
        errors.append('Board.grid_to_screen mismatch')

    # 13. Movement simulation check for all 4 colors
    behind_start_abs = {
        'yellow': 51,   # TRACK[51] = (0, 6)
        'blue':   12,   # TRACK[12] = (8, 0)
        'red':    25,   # TRACK[25] = (14, 6)
        'green':  38,   # TRACK[38] = (6, 14)
    }
    for c in COLORS:
        visited = []
        for p in range(PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX + 1):
            abs_idx = get_absolute_track_pos(c, p)
            visited.append(abs_idx)
            grid_pos = get_piece_grid_pos(c, p)
            if grid_pos != TRACK[abs_idx]:
                errors.append(f'{c} step {p} grid mismatch {grid_pos} != TRACK[{abs_idx}]')
        
        # Verify entrance square (progress 50) is NOT behind start
        entrance_abs = get_absolute_track_pos(c, PROGRESS_TRACK_MAX)
        if entrance_abs == behind_start_abs[c]:
            errors.append(f'{c} entrance collides with behind-start {behind_start_abs[c]}')
        if behind_start_abs[c] in visited:
            errors.append(f'{c} visited behind-start {behind_start_abs[c]} on track')
        
        # Verify home column turns in correctly at PROGRESS_HOME_MIN
        if get_piece_grid_pos(c, PROGRESS_HOME_MIN) != HOME_COLUMNS[c][0]:
            errors.append(f'{c} did not enter home column at {PROGRESS_HOME_MIN}')

    if errors:
        print('SELF-TEST FAILED:')
        for e in errors:
            print(f'  [FAIL] {e}')
    else:
        print('board.py self-test: ALL CHECKS PASSED [OK]')
        print('\n--- Simulation Check: Steps for All 4 Colors ---')
        for c in COLORS:
            print(f'\nPlayer {c.upper()}:')
            print(f'  Start square (progress 0):  {get_piece_grid_pos(c, 0)} (TRACK index {PLAYER_OFFSETS[c]})')
            print(f'  Entrance sq (progress 50): {get_piece_grid_pos(c, 50)} (TRACK index {get_absolute_track_pos(c, 50)})')
            print(f'  Home sq 1  (progress 51):  {get_piece_grid_pos(c, 51)} (HOME_COLUMNS[0])')
            print(f'  Home sq 5  (progress 55):  {get_piece_grid_pos(c, 55)} (HOME_COLUMNS[4])')
            print(f'  Finish     (progress 56):  {get_piece_grid_pos(c, 56)} (Center Goal)')
            print(f'  Square behind start ({behind_start_abs[c]}: {TRACK[behind_start_abs[c]]}) visited? False [VERIFIED]')
