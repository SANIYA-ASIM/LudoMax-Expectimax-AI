"""
tournament.py — Automated Tournament Runner for LudoMax
========================================================
Runs multiple headless games between configurable agents,
collects per-player statistics, and saves results to CSV.
"""
import csv
import os
import time
from typing import Dict, List, Optional

from board import COLORS
from game import Game
from agents import create_agent, AGENT_TYPES


class Tournament:
    """Run an automated round-robin or matchup tournament.

    Args:
        num_games:  How many games to play per matchup configuration.
        seed_base:  Base random seed; each game uses seed_base + game_index.
        max_turns:  Safety limit per game to prevent infinite loops.
        verbose:    Print progress to stdout.
    """

    def __init__(self, num_games: int = 20, seed_base: int = 42,
                 max_turns: int = 2000, verbose: bool = True):
        self.num_games = num_games
        self.seed_base = seed_base
        self.max_turns = max_turns
        self.verbose = verbose

    # ──────────────────────────────────────────────────────────────────────
    # Core: run a single matchup
    # ──────────────────────────────────────────────────────────────────────

    def run_matchup(self, agent_configs: List[Dict],
                    num_games: Optional[int] = None,
                    label: str = '') -> Dict:
        """Play *num_games* games with the given 4-agent configuration.

        agent_configs: list of 4 dicts, each with keys:
            'type'  : agent type string (e.g. 'expectimax')
            'depth' : (optional) search depth for Expectimax
            'seed'  : (optional) base seed increment

        Returns a dict mapping colour → stats dict.
        """
        if num_games is None:
            num_games = self.num_games

        # Accumulator
        acc: Dict[str, Dict] = {
            color: {'wins': 0, 'captures_made': 0,
                    'captures_suffered': 0, 'turns': 0, 'games': 0}
            for color in COLORS
        }
        type_map = {}

        for game_num in range(num_games):
            seed = self.seed_base + game_num * 7

            # Rotate starting player so no colour always goes first
            start_offset = game_num % 4
            start_color = COLORS[start_offset]

            # Build agents (one per colour)
            agents = []
            for i, color in enumerate(COLORS):
                cfg = agent_configs[i]
                atype = cfg.get('type', 'random')
                depth = cfg.get('depth', 2)
                a_seed = seed * 13 + i * 31
                agent = create_agent(atype, color,
                                     seed=a_seed, depth=depth)
                agents.append(agent)
                type_map[color] = atype

            game = Game(agents, seed=seed)
            game.state.current_player = start_color

            winner = game.play_game(max_turns=self.max_turns)

            # Accumulate stats
            for color in COLORS:
                s = acc[color]
                gs = game.stats[color]
                s['games'] += 1
                s['captures_made']     += gs['captures_made']
                s['captures_suffered'] += gs['captures_suffered']
                s['turns']             += gs['turns']
                if winner == color:
                    s['wins'] += 1

            if self.verbose:
                tag = f" [{label}]" if label else ""
                print(f"  Game {game_num+1:>3}/{num_games}{tag}: "
                      f"winner={winner or 'timeout'} "
                      f"turns={game.turn_count}")

        # Compute rates
        result: Dict[str, Dict] = {}
        for color in COLORS:
            s = acc[color]
            n = max(s['games'], 1)
            result[color] = {
                'type':                   type_map.get(color, '?'),
                'wins':                   s['wins'],
                'win_rate':               s['wins'] / n,
                'avg_captures_made':      s['captures_made'] / n,
                'avg_captures_suffered':  s['captures_suffered'] / n,
                'avg_turns':              s['turns'] / n,
                'games_played':           n,
            }
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Pre-built experiments
    # ──────────────────────────────────────────────────────────────────────

    def run_all_vs_all(self, num_games: Optional[int] = None) -> Dict:
        """One Expectimax + one Aggressive + one Defensive + one Random."""
        configs = [
            {'type': 'expectimax', 'depth': 2},
            {'type': 'aggressive'},
            {'type': 'defensive'},
            {'type': 'random'},
        ]
        if self.verbose:
            print("\n=== All-vs-All Tournament ===")
        return self.run_matchup(configs, num_games=num_games,
                                label='4-way')

    def run_expectimax_vs(self, opponent: str,
                           depth: int = 2,
                           num_games: Optional[int] = None) -> Dict:
        """Expectimax (yellow) vs three copies of *opponent*."""
        configs = [
            {'type': 'expectimax', 'depth': depth},
            {'type': opponent},
            {'type': opponent},
            {'type': opponent},
        ]
        label = f"Expectimax(d={depth}) vs 3×{opponent}"
        if self.verbose:
            print(f"\n=== {label} ===")
        return self.run_matchup(configs, num_games=num_games, label=label)

    def run_depth_comparison(self, num_games: Optional[int] = None,
                              depths=(1, 2, 3)) -> Dict[int, Dict]:
        """Compare Expectimax at different search depths vs 3 Random agents."""
        results = {}
        for d in depths:
            if self.verbose:
                print(f"\n=== Expectimax depth={d} vs 3×Random ===")
            configs = [
                {'type': 'expectimax', 'depth': d},
                {'type': 'random'},
                {'type': 'random'},
                {'type': 'random'},
            ]
            results[d] = self.run_matchup(
                configs, num_games=num_games,
                label=f"depth={d}"
            )
        return results

    def run_performance_benchmark(self,
                                   depths=(1, 2, 3),
                                   num_games: int = 5) -> Dict[int, Dict]:
        """Measure Expectimax nodes-expanded and decision time per depth."""
        from expectimax import ExpectimaxAgent
        from agents import RandomAgent

        perf: Dict[int, Dict] = {}
        for d in depths:
            if self.verbose:
                print(f"\n=== Performance benchmark depth={d} ===")

            all_nodes = []
            all_times = []

            for game_num in range(num_games):
                seed = self.seed_base + game_num * 17
                ex_agent = ExpectimaxAgent('yellow', depth=d)
                others = [RandomAgent(c, seed=seed + i)
                          for i, c in enumerate(['blue', 'red', 'green'])]
                agents = [ex_agent] + others

                game = Game(agents, seed=seed)
                while not game.state.is_game_over() and game.turn_count < self.max_turns:
                    prev_player = game.state.current_player
                    game.play_turn()
                    if prev_player == 'yellow':
                        all_nodes.append(ex_agent.nodes_expanded)
                        all_times.append(ex_agent.last_decision_time)
                        ex_agent.nodes_expanded = 0
                        ex_agent.last_decision_time = 0.0

                if self.verbose:
                    print(f"  Game {game_num+1}/{num_games}: "
                          f"turns={game.turn_count} winner={game.state.get_winner()}")

            perf[d] = {
                'avg_nodes':   sum(all_nodes) / max(len(all_nodes), 1),
                'avg_time_ms': sum(all_times) / max(len(all_times), 1) * 1000,
                'samples':     len(all_nodes),
            }

        return perf

    # ──────────────────────────────────────────────────────────────────────
    # CSV output
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def save_matchup_csv(result: Dict, filepath: str):
        """Save a matchup result dict to a CSV file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Color', 'Agent Type', 'Games Played',
                             'Wins', 'Win Rate',
                             'Avg Captures Made', 'Avg Captures Suffered',
                             'Avg Turns'])
            for color in COLORS:
                s = result[color]
                writer.writerow([
                    color, s['type'], s['games_played'],
                    s['wins'], f"{s['win_rate']:.4f}",
                    f"{s['avg_captures_made']:.2f}",
                    f"{s['avg_captures_suffered']:.2f}",
                    f"{s['avg_turns']:.1f}",
                ])
        print(f"  Saved → {filepath}")

    @staticmethod
    def save_depth_csv(depth_results: Dict[int, Dict], filepath: str):
        """Save depth-comparison results to CSV."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Depth', 'Win Rate (Expectimax)',
                             'Avg Captures Made', 'Avg Turns'])
            for depth, result in sorted(depth_results.items()):
                r = result['yellow']   # Expectimax always plays as yellow
                writer.writerow([
                    depth,
                    f"{r['win_rate']:.4f}",
                    f"{r['avg_captures_made']:.2f}",
                    f"{r['avg_turns']:.1f}",
                ])
        print(f"  Saved → {filepath}")

    @staticmethod
    def save_performance_csv(perf: Dict[int, Dict], filepath: str):
        """Save performance-benchmark results to CSV."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Depth', 'Avg Nodes Expanded',
                             'Avg Decision Time (ms)', 'Samples'])
            for depth, data in sorted(perf.items()):
                writer.writerow([
                    depth,
                    f"{data['avg_nodes']:.1f}",
                    f"{data['avg_time_ms']:.3f}",
                    data['samples'],
                ])
        print(f"  Saved → {filepath}")
