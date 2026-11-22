"""
test_board.py — Phase 1: Board Representation & Coordinate Mapping Tests
========================================================================
Tests for board.py covering:
  - TRACK structure and integrity
  - SAFE_SQUARES validity
  - HOME_COLUMNS and BASE_POSITIONS counts
  - PLAYER_OFFSETS correctness
  - get_absolute_track_pos() arithmetic
  - get_piece_grid_pos() for base, track, home column, and finished states
  - grid_to_screen() pixel-coordinate conversion
  - is_safe_absolute() predicate
  - Progress constants match the specification
"""
import pytest

from board import (
    Board,
    COLORS, TRACK, TRACK_SET, TRACK_INDEX,
    PLAYER_OFFSETS, SAFE_SQUARES, HOME_COLUMNS, HOME_COLUMN_SETS,
    BASE_POSITIONS, COLOR_VALUES, COLOR_DARK, COLOR_LIGHT,
    PROGRESS_BASE, PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX,
    PROGRESS_HOME_MIN, PROGRESS_HOME_MAX, PROGRESS_FINISHED,
    get_absolute_track_pos, get_piece_grid_pos,
    is_safe_absolute, grid_to_screen,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. TRACK structure
# ─────────────────────────────────────────────────────────────────────────────

def test_track_length():
    """TRACK must contain exactly 52 squares."""
    assert len(TRACK) == 52, f"Expected 52 squares, got {len(TRACK)}"


def test_track_uniqueness():
    """Every square on TRACK must be a unique (col, row) pair."""
    assert len(set(TRACK)) == 52, "TRACK contains duplicate positions"


def test_track_entries_are_tuples():
    """Every TRACK entry must be a (col, row) tuple with values 0-14."""
    for idx, cell in enumerate(TRACK):
        col, row = cell
        assert 0 <= col <= 14, f"TRACK[{idx}] col={col} out of 0-14"
        assert 0 <= row <= 14, f"TRACK[{idx}] row={row} out of 0-14"


def test_track_index_lookup():
    """TRACK_INDEX must correctly map every (col,row) → its track index."""
    for idx, cell in enumerate(TRACK):
        assert TRACK_INDEX[cell] == idx


# ─────────────────────────────────────────────────────────────────────────────
# 2. Player offsets
# ─────────────────────────────────────────────────────────────────────────────

def test_player_offsets_all_colors_present():
    """Every player colour must have an entry in PLAYER_OFFSETS."""
    for color in COLORS:
        assert color in PLAYER_OFFSETS, f"Missing offset for {color}"


def test_player_offsets_in_range():
    """Each offset must be a valid TRACK index (0-51)."""
    for color, off in PLAYER_OFFSETS.items():
        assert 0 <= off <= 51, f"PLAYER_OFFSETS[{color}]={off} out of range"


def test_player_offset_known_values():
    """Verify specific offset values that drive all track arithmetic."""
    assert PLAYER_OFFSETS['yellow'] ==  0
    assert PLAYER_OFFSETS['blue']   == 13
    assert PLAYER_OFFSETS['red']    == 26
    assert PLAYER_OFFSETS['green']  == 39


# ─────────────────────────────────────────────────────────────────────────────
# 3. Safe squares
# ─────────────────────────────────────────────────────────────────────────────

def test_safe_squares_count():
    """Must have exactly 8 safe squares (4 starts + 4 star squares)."""
    assert len(SAFE_SQUARES) == 8, f"Expected 8 safe squares, got {len(SAFE_SQUARES)}"


def test_safe_squares_valid_indices():
    """All safe-square values must be valid absolute TRACK indices (0-51)."""
    for sq in SAFE_SQUARES:
        assert 0 <= sq <= 51, f"Safe square {sq} is out of TRACK range"


def test_start_squares_are_safe():
    """The 4 player start squares (at their offsets) must all be safe."""
    for color, off in PLAYER_OFFSETS.items():
        assert off in SAFE_SQUARES, f"Start square for {color} (abs={off}) is not safe"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Home columns
# ─────────────────────────────────────────────────────────────────────────────

def test_home_column_lengths():
    """Each player's home column must have exactly 5 square-shaped blocks (progress 51-55)."""
    for color in COLORS:
        assert len(HOME_COLUMNS[color]) == 5, \
            f"HOME_COLUMNS[{color}] has {len(HOME_COLUMNS[color])} entries, expected 5"


def test_home_column_no_overlap_with_track():
    """Home column squares must not collide with the shared TRACK."""
    for color, hc in HOME_COLUMNS.items():
        for cell in hc:
            assert cell not in TRACK_SET, \
                f"HOME_COLUMNS[{color}] cell {cell} is also on the shared track"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Base positions
# ─────────────────────────────────────────────────────────────────────────────

def test_base_positions_count():
    """Each player must have exactly 4 base slots (one per piece)."""
    for color in COLORS:
        assert len(BASE_POSITIONS[color]) == 4, \
            f"BASE_POSITIONS[{color}] has {len(BASE_POSITIONS[color])} entries, expected 4"


# ─────────────────────────────────────────────────────────────────────────────
# 6. get_absolute_track_pos
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("color,progress,expected_abs", [
    ('yellow',  0,  0),   # yellow starts at abs 0
    ('yellow', 13, 13),   # yellow at progress 13 → abs 13
    ('yellow', 50, 50),   # yellow at progress 50 → abs 50 (home-entrance square)
    ('blue',    0, 13),   # blue's first square is abs 13
    ('blue',   13, 26),   # blue at progress 13 → abs 26
    ('blue',   39,  0),   # blue at progress 39 → abs (13+39)%52=0
    ('red',     0, 26),
    ('red',    26,  0),   # red at progress 26 → abs (26+26)%52=0
    ('green',   0, 39),
    ('green',  13,  0),   # green at progress 13 → abs (39+13)%52=0
])
def test_get_absolute_track_pos(color, progress, expected_abs):
    result = get_absolute_track_pos(color, progress)
    assert result == expected_abs, \
        f"get_absolute_track_pos({color},{progress})={result}, expected {expected_abs}"


# ─────────────────────────────────────────────────────────────────────────────
# 7. get_piece_grid_pos
# ─────────────────────────────────────────────────────────────────────────────

def test_get_piece_grid_pos_base():
    """In-base pieces must map to their BASE_POSITIONS slot."""
    for color in COLORS:
        for slot in range(4):
            pos = get_piece_grid_pos(color, PROGRESS_BASE, slot)
            expected = BASE_POSITIONS[color][slot]
            assert pos == expected, \
                f"{color} slot {slot}: got {pos}, expected {expected}"


def test_get_piece_grid_pos_track():
    """Pieces on the shared track must map to the correct TRACK cell."""
    # Verify at progress 0, 1, 10 for yellow (simplest: no offset wrapping)
    # Progress 50 is the last valid track square (home-entrance square for yellow).
    for prog in [0, 1, 10, 50]:
        pos = get_piece_grid_pos('yellow', prog)
        abs_idx = get_absolute_track_pos('yellow', prog)
        expected = TRACK[abs_idx]
        assert pos == expected, \
            f"yellow progress {prog}: got {pos}, expected {expected}"


def test_get_piece_grid_pos_home_column():
    """Pieces in the home column must map to the correct HOME_COLUMNS cell."""
    for color in COLORS:
        for home_prog in range(PROGRESS_HOME_MIN, PROGRESS_HOME_MAX + 1):
            pos = get_piece_grid_pos(color, home_prog)
            expected = HOME_COLUMNS[color][home_prog - PROGRESS_HOME_MIN]
            assert pos == expected, \
                f"{color} home_prog={home_prog}: got {pos}, expected {expected}"


def test_get_piece_grid_pos_finished():
    """Finished pieces (progress=58) must map to the shared centre cell (7,7)."""
    for color in COLORS:
        pos = get_piece_grid_pos(color, PROGRESS_FINISHED)
        assert pos == (7, 7), \
            f"{color} finished: got {pos}, expected (7,7)"


# ─────────────────────────────────────────────────────────────────────────────
# 8. grid_to_screen
# ─────────────────────────────────────────────────────────────────────────────

def test_grid_to_screen_origin():
    """Cell (0,0) with cell_size=50 and no offset → centre at (25,25)."""
    px, py = grid_to_screen(0, 0, 50)
    assert (px, py) == (25, 25)


def test_grid_to_screen_nonzero_cell():
    """Cell (2,3) with cell_size=40 and no offset → (100,140) + half=20 → (100,140)."""
    px, py = grid_to_screen(2, 3, 40)
    # 2*40 + 20 = 100; 3*40 + 20 = 140
    assert (px, py) == (100, 140)


def test_grid_to_screen_with_offset():
    """Board offsets are added correctly."""
    px, py = grid_to_screen(2, 3, 40, board_offset_x=10, board_offset_y=20)
    # (10 + 2*40 + 20, 20 + 3*40 + 20) = (110, 160)
    assert (px, py) == (110, 160)


def test_grid_to_screen_last_cell():
    """Cell (14,14) with cell_size=50 → pixel centre at (725, 725)."""
    px, py = grid_to_screen(14, 14, 50)
    # 14*50 + 25 = 725
    assert (px, py) == (725, 725)


def test_grid_to_screen_integer_types():
    """grid_to_screen must return integer pixel values."""
    px, py = grid_to_screen(3, 7, 45)
    assert isinstance(px, int)
    assert isinstance(py, int)


# ─────────────────────────────────────────────────────────────────────────────
# 9. is_safe_absolute
# ─────────────────────────────────────────────────────────────────────────────

def test_is_safe_absolute_known_safe():
    """All 8 safe-square indices must return True."""
    for sq in SAFE_SQUARES:
        assert is_safe_absolute(sq), f"Square {sq} should be safe"


def test_is_safe_absolute_known_unsafe():
    """Non-safe squares must return False."""
    unsafe_examples = [1, 2, 3, 4, 5, 6, 7, 9, 10, 20, 30, 40, 50, 51]
    for sq in unsafe_examples:
        if sq not in SAFE_SQUARES:
            assert not is_safe_absolute(sq), f"Square {sq} should not be safe"


# ─────────────────────────────────────────────────────────────────────────────
# 10. Progress constants
# ─────────────────────────────────────────────────────────────────────────────

def test_progress_constants():
    """All progress constants must match the project specification exactly."""
    assert PROGRESS_BASE       == -1, "PROGRESS_BASE must be -1"
    assert PROGRESS_TRACK_MIN  ==  0, "PROGRESS_TRACK_MIN must be 0"
    assert PROGRESS_TRACK_MAX  == 50, "PROGRESS_TRACK_MAX must be 50"
    assert PROGRESS_HOME_MIN   == 51, "PROGRESS_HOME_MIN must be 51"
    assert PROGRESS_HOME_MAX   == 55, "PROGRESS_HOME_MAX must be 55"
    assert PROGRESS_FINISHED   == 56, "PROGRESS_FINISHED must be 56"


def test_progress_ordering():
    """Progress constants must follow the expected ordering."""
    assert PROGRESS_BASE < PROGRESS_TRACK_MIN
    assert PROGRESS_TRACK_MIN < PROGRESS_TRACK_MAX
    assert PROGRESS_TRACK_MAX < PROGRESS_HOME_MIN
    assert PROGRESS_HOME_MIN < PROGRESS_HOME_MAX
    assert PROGRESS_HOME_MAX < PROGRESS_FINISHED


# ─────────────────────────────────────────────────────────────────────────────
# 11. Colour lookup tables
# ─────────────────────────────────────────────────────────────────────────────

def test_color_values_all_players():
    """COLOR_VALUES, COLOR_DARK, COLOR_LIGHT must include all 4 players."""
    for color in COLORS:
        assert color in COLOR_VALUES
        assert color in COLOR_DARK
        assert color in COLOR_LIGHT


# ─────────────────────────────────────────────────────────────────────────────
# 12. Board class
# ─────────────────────────────────────────────────────────────────────────────

def test_board_class_attributes():
    """Board class must expose standard game constants and geometry."""
    b = Board()
    assert b.GRID_SIZE == 15
    assert len(b.TRACK) == 52
    assert len(b.SAFE_SQUARES) == 8
    assert len(b.PLAYER_OFFSETS) == 4
    assert len(b.HOME_COLUMNS) == 4
    assert len(b.BASE_POSITIONS) == 4


def test_board_class_methods():
    """Board class static and instance methods must match module functions."""
    b = Board()
    assert Board.get_absolute_track_pos('blue', 0) == 13
    assert b.get_absolute_track_pos('green', 0) == 39
    assert Board.is_safe_absolute(0) is True
    assert b.is_safe_absolute(1) is False
    assert b.get_piece_grid_pos('yellow', PROGRESS_FINISHED) == (7, 7)
    assert b.grid_to_screen(0, 0, 50) == (25, 25)


# ─────────────────────────────────────────────────────────────────────────────
# 13. Movement simulation: verify all 4 colors enter home column correctly
# ─────────────────────────────────────────────────────────────────────────────

def test_home_column_entry_simulation_all_colors():
    """
    Simulate a piece moving step-by-step from progress 0 to PROGRESS_FINISHED
    for every colour. Verify:
      - Progress 50 maps to the home-entrance track square (NOT behind start).
      - Progress 51 (HOME_MIN) maps to home-column square [0] (turns in correctly).
      - The 'just behind start' absolute square is NEVER visited during steps 0-50.
      - PROGRESS_FINISHED maps to (7, 7).
    """
    # The absolute track index of the square just behind each player's start:
    behind_start_abs = {
        'yellow': 51,   # TRACK[51] = (0, 6)
        'blue':   12,   # TRACK[12] = (8, 0)
        'red':    25,   # TRACK[25] = (14, 6)
        'green':  38,   # TRACK[38] = (6, 14)
    }

    for color in COLORS:
        visited_track_abs = []

        for prog in range(PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX + 1):
            pos = get_piece_grid_pos(color, prog)
            abs_idx = get_absolute_track_pos(color, prog)
            visited_track_abs.append(abs_idx)
            expected = TRACK[abs_idx]
            assert pos == expected, (
                f"{color}: progress {prog} -> pos {pos}, expected TRACK[{abs_idx}]={expected}"
            )

        # Home entrance (progress 50) must NOT be the 'behind-start' square.
        entrance_abs = get_absolute_track_pos(color, PROGRESS_TRACK_MAX)
        assert entrance_abs != behind_start_abs[color], (
            f"{color}: home entrance abs={entrance_abs} collides with "
            f"behind-start abs={behind_start_abs[color]}"
        )

        # 'Behind start' must never appear in the track phase.
        assert behind_start_abs[color] not in visited_track_abs, (
            f"{color}: behind-start abs={behind_start_abs[color]} was visited "
            f"during track phase"
        )

        # Verify home column entry at PROGRESS_HOME_MIN.
        home0 = get_piece_grid_pos(color, PROGRESS_HOME_MIN)
        assert home0 == HOME_COLUMNS[color][0], (
            f"{color}: progress {PROGRESS_HOME_MIN} -> {home0}, "
            f"expected HOME_COLUMNS[0]={HOME_COLUMNS[color][0]}"
        )

        # Verify all 5 home column square-shaped blocks.
        for step in range(5):
            prog = PROGRESS_HOME_MIN + step
            pos = get_piece_grid_pos(color, prog)
            assert pos == HOME_COLUMNS[color][step], (
                f"{color}: home-col progress {prog} -> {pos}, "
                f"expected HOME_COLUMNS[{step}]={HOME_COLUMNS[color][step]}"
            )

        # Finished piece maps to center.
        assert get_piece_grid_pos(color, PROGRESS_FINISHED) == (7, 7), (
            f"{color}: PROGRESS_FINISHED does not map to (7,7)"
        )

