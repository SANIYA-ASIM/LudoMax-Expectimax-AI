"""
expectimax.py — Adversarial Expectimax AI Agent for LudoMax
===========================================================
Implements genuine adversarial stochastic tree search for strategic decision-making
under uncertain dice outcomes:

Tree Structure:
---------------
  MAX node  — Expectimax player chooses the move maximizing expected utility.
  CHANCE    — Stochastic node averaging over all 6 dice outcomes (probability 1/6 each).
  MIN node  — Combined opponent adversary choosing the response least favorable
              to the Expectimax player.

Evaluation Components (Configurable Weights):
---------------------------------------------
  1. Piece Progress       — Sum of forward progress along shared track and home path.
  2. Finished Pieces      — Significant reward for pieces safely reaching the center goal.
  3. Active Pieces        — Reward for pieces active on the board vs. stuck in base.
  4. Safe Positions       — Reward for occupying safe squares and private home columns.
  5. Captures             — Reward for capturing opponents and keeping them in base.
  6. Capture Vulnerability — Penalty proportional to immediate opponent threat.
"""
import time
from typing import Dict, List, Optional, Tuple, Union

from board import (
    COLORS, PLAYER_OFFSETS, SAFE_SQUARES,
    PROGRESS_BASE, PROGRESS_TRACK_MIN, PROGRESS_TRACK_MAX,
    PROGRESS_HOME_MIN, PROGRESS_HOME_MAX, PROGRESS_FINISHED,
    get_absolute_track_pos,
)
from agents import Agent
from game_state import GameState
from move import Move


class ExpectimaxAgent(Agent):
    """Expectimax search agent with configurable search depth and evaluation weights.

    Args:
        color:   Player colour this agent controls ('yellow', 'blue', 'red', 'green').
        depth:   Search depth (1 = greedy, 2 = default, 3 = deep).
        weights: Evaluation weight tuple (progress, finish, active, safe, capture, danger)
                 or dict mapping weight names to floats.
    """

    DEFAULT_WEIGHTS = {
        'progress': 1.0,
        'finish': 1.0,
        'active': 1.0,
        'safe': 1.0,
        'capture': 1.0,
        'vulnerability': 1.0,
    }

    def __init__(self, color: str,
                 depth: int = 2,
                 weights: Optional[Union[tuple, list, dict]] = None,
                 **kwargs):
        super().__init__(color)
        self.depth = max(1, min(3, depth))

        # Parse and configure evaluation weights
        self.weights = dict(self.DEFAULT_WEIGHTS)
        if isinstance(weights, dict):
            self.weights.update(weights)
        elif isinstance(weights, (tuple, list)):
            if len(weights) == 5:
                w_prog, w_fin, w_act, w_safe, w_dan = weights
                self.weights.update({
                    'progress': float(w_prog),
                    'finish': float(w_fin),
                    'active': float(w_act),
                    'safe': float(w_safe),
                    'capture': 1.0,
                    'vulnerability': float(w_dan),
                })
            elif len(weights) >= 6:
                w_prog, w_fin, w_act, w_safe, w_cap, w_dan = weights[:6]
                self.weights.update({
                    'progress': float(w_prog),
                    'finish': float(w_fin),
                    'active': float(w_act),
                    'safe': float(w_safe),
                    'capture': float(w_cap),
                    'vulnerability': float(w_dan),
                })

        # Performance counters
        self.nodes_expanded: int = 0          # nodes expanded in latest decision
        self.total_nodes: int = 0             # cumulative nodes expanded
        self.total_decisions: int = 0         # cumulative decisions made
        self.last_decision_time: float = 0.0  # seconds taken for latest decision
        self.total_decision_time: float = 0.0 # cumulative decision time in seconds

    @property
    def name(self) -> str:
        return f"Expectimax(d={self.depth})"

    # ──────────────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────────────

    def choose_move(self, game_state: GameState,
                    legal_moves: List[Move],
                    dice_value: int) -> Optional[Move]:
        """Return the optimal legal move determined by Expectimax search."""
        if not legal_moves:
            return None
        if len(legal_moves) == 1:
            return legal_moves[0]

        t0 = time.perf_counter()
        self.nodes_expanded = 0

        # Filter equivalent duplicate moves (e.g. identical pieces in base)
        candidate_moves = self._deduplicate_moves(legal_moves)

        _, best_move = self._root_max(game_state, candidate_moves,
                                      dice_value, self.depth)

        self.last_decision_time = time.perf_counter() - t0
        self.total_decision_time += self.last_decision_time
        self.total_nodes += self.nodes_expanded
        self.total_decisions += 1

        return best_move if best_move is not None else legal_moves[0]

    def _deduplicate_moves(self, moves: List[Move]) -> List[Move]:
        """Filter symmetric moves (such as multiple identical pieces in base)."""
        seen = set()
        unique = []
        for m in moves:
            key = (m.from_progress, m.to_progress, tuple(sorted(m.captures)))
            if key not in seen:
                seen.add(key)
                unique.append(m)
        return unique

    # ──────────────────────────────────────────────────────────────────────
    # Search tree: MAX, CHANCE, and MIN
    # ──────────────────────────────────────────────────────────────────────

    def _root_max(self, state: GameState, legal_moves: List[Move],
                  dice_value: int, depth: int) -> Tuple[float, Optional[Move]]:
        """Root MAX node: selects move with highest expected value given current roll."""
        best_score = float('-inf')
        best_move: Optional[Move] = None

        for move in legal_moves:
            self.nodes_expanded += 1
            new_state = state.apply_move(move, dice_value)

            if new_state.is_game_over() or depth <= 1:
                score = self._evaluate(new_state)
            else:
                is_my_turn_next = (new_state.current_player == self.color)
                score = self._chance_node(new_state, depth - 1, is_my_turn_next)

            if score > best_score:
                best_score = score
                best_move = move

        return best_score, best_move

    def _chance_node(self, state: GameState, depth: int,
                     is_my_turn: bool) -> float:
        """Stochastic Chance node: averages over all 6 dice outcomes with probability 1/6."""
        total = 0.0
        for d in range(1, 7):
            self.nodes_expanded += 1

            # Handle 3 consecutive 6s penalty
            if d == 6 and state.consecutive_sixes >= 2:
                ns = state.copy()
                ns.consecutive_sixes = 0
                ns.current_player = ns._next_player()
                is_next = (ns.current_player == self.color)
                if depth <= 1 or ns.is_game_over():
                    total += self._evaluate(ns)
                else:
                    total += self._chance_node(ns, depth - 1, is_next)
                continue

            if is_my_turn:
                total += self._max_node(state, d, depth)
            else:
                total += self._min_node(state, d, depth)

        return total / 6.0

    def _max_node(self, state: GameState, dice: int, depth: int) -> float:
        """MAX node: Expectimax player chooses highest scoring move."""
        if state.is_game_over():
            return self._evaluate(state)

        legal = state.get_legal_moves(dice)
        if not legal:
            # Pass turn to next player
            ns = state.apply_move(None, dice)
            if depth <= 1 or ns.is_game_over():
                return self._evaluate(ns)
            is_next = (ns.current_player == self.color)
            return self._chance_node(ns, depth - 1, is_next)

        candidates = self._deduplicate_moves(legal)
        best = float('-inf')
        for move in candidates:
            self.nodes_expanded += 1
            ns = state.apply_move(move, dice)
            if depth <= 1 or ns.is_game_over():
                score = self._evaluate(ns)
            else:
                is_next = (ns.current_player == self.color)
                score = self._chance_node(ns, depth - 1, is_next)
            if score > best:
                best = score
        return best

    def _min_node(self, state: GameState, dice: int, depth: int) -> float:
        """MIN node: Combined opponent adversary chooses move minimizing our score."""
        if state.is_game_over():
            return self._evaluate(state)

        legal = state.get_legal_moves(dice)
        if not legal:
            ns = state.apply_move(None, dice)
            if depth <= 1 or ns.is_game_over():
                return self._evaluate(ns)
            is_next = (ns.current_player == self.color)
            return self._chance_node(ns, depth - 1, is_next)

        candidates = self._deduplicate_moves(legal)
        worst = float('inf')
        for move in candidates:
            self.nodes_expanded += 1
            ns = state.apply_move(move, dice)
            if depth <= 1 or ns.is_game_over():
                score = self._evaluate(ns)
            else:
                is_next = (ns.current_player == self.color)
                score = self._chance_node(ns, depth - 1, is_next)
            if score < worst:
                worst = score
        return worst

    # ──────────────────────────────────────────────────────────────────────
    # Evaluation function
    # ──────────────────────────────────────────────────────────────────────

    def _evaluate(self, state: GameState) -> float:
        """Comprehensive evaluation function considering:
        1. Piece progress.
        2. Finished pieces.
        3. Active pieces.
        4. Safe positions.
        5. Captures made / opponents kept in base.
        6. Capture vulnerability (immediate danger).
        """
        w_prog = self.weights['progress']
        w_fin  = self.weights['finish']
        w_act  = self.weights['active']
        w_safe = self.weights['safe']
        w_cap  = self.weights['capture']
        w_dan  = self.weights['vulnerability']

        # ── 1. Our Pieces Evaluation ──────────────────────────────────
        my_pieces = state.pieces[self.color]
        progress_sum = 0.0
        finished_count = 0
        active_count = 0
        safe_count = 0

        for p in my_pieces:
            if p == PROGRESS_FINISHED:
                finished_count += 1
                progress_sum += PROGRESS_HOME_MAX + 1
            elif p == PROGRESS_BASE:
                pass  # in base: 0 progress
            elif PROGRESS_TRACK_MIN <= p <= PROGRESS_TRACK_MAX:
                progress_sum += p
                active_count += 1
                abs_pos = get_absolute_track_pos(self.color, p)
                if abs_pos in SAFE_SQUARES:
                    safe_count += 1
            else:  # Home column squares (51-55)
                progress_sum += p
                active_count += 1
                safe_count += 1  # home column squares are immune to capture

        # ── 2. Capture Advantage ──────────────────────────────────────
        # Opponent pieces remaining in base represent captured / delayed pieces
        opponents_in_base = 0
        opp_progress = 0.0
        for color in COLORS:
            if color == self.color:
                continue
            for p in state.pieces[color]:
                if p == PROGRESS_BASE:
                    opponents_in_base += 1
                elif p == PROGRESS_FINISHED:
                    opp_progress += PROGRESS_HOME_MAX + 1
                else:
                    opp_progress += max(p, 0)

        # ── 3. Capture Vulnerability ──────────────────────────────────
        danger = self._danger_score(state)

        # ── Composite Score ───────────────────────────────────────────
        score = (
            w_prog * progress_sum
            + w_fin  * (finished_count * 1000.0)
            + w_act  * (active_count   *   50.0)
            + w_safe * (safe_count     *   30.0)
            + w_cap  * (opponents_in_base * 40.0)
            - w_dan  * danger
            - 0.3    * opp_progress
        )

        return score

    def _danger_score(self, state: GameState) -> float:
        """Calculate total threat to our pieces from nearby opponents."""
        danger = 0.0
        my_off = PLAYER_OFFSETS[self.color]
        my_pieces = state.pieces[self.color]

        for p in my_pieces:
            if p < PROGRESS_TRACK_MIN or p > PROGRESS_TRACK_MAX:
                continue   # Base, home column, and finished pieces are immune
            abs_pos = (my_off + p) % 52
            if abs_pos in SAFE_SQUARES:
                continue   # Safe squares protect against any threat

            # Check all dice distances 1–6 from each opponent
            for d in range(1, 7):
                for opp in COLORS:
                    if opp == self.color:
                        continue
                    opp_off = PLAYER_OFFSETS[opp]
                    for opp_prog in state.pieces[opp]:
                        if PROGRESS_TRACK_MIN <= opp_prog <= PROGRESS_TRACK_MAX:
                            # Only threaten if opponent remains on the shared track
                            if opp_prog + d <= PROGRESS_TRACK_MAX:
                                opp_dest_abs = (opp_off + opp_prog + d) % 52
                                if opp_dest_abs == abs_pos:
                                    danger += 10.0

        return danger
