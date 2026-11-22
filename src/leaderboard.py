"""
leaderboard.py — Career & Tournament Statistics Manager for LudoVerse
====================================================================
Manages persistent records for both:
  1. Human vs AI Matchups (Career stats, win rates, head-to-head vs AI models, recent matches)
  2. AI vs AI Championship (Model benchmarks, win distributions, capture stats, best runs)
"""
import json
import os
import time
from typing import Dict, Any, List

LEADERBOARD_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'outputs', 'leaderboard_stats.json')


def get_default_stats() -> Dict[str, Any]:
    """Return default seeded statistics for career records."""
    return {
        'human_vs_ai': {
            'games_played': 12,
            'human_wins': 7,
            'human_losses': 5,
            'total_captures': 41,
            'pieces_finished': 39,
            'opponents': {
                'expectimax': {'encounters': 12, 'human_wins': 7, 'ai_wins': 3, 'threat': 'Extreme (Depth 2-3 Search)'},
                'aggressive': {'encounters': 12, 'human_wins': 8, 'ai_wins': 1, 'threat': 'High (Capture Hunter)'},
                'defensive':  {'encounters': 12, 'human_wins': 9, 'ai_wins': 1, 'threat': 'Moderate (Safe Square Camper)'},
            },
            'recent_history': [
                {'result': 'VICTORY', 'turns': 84, 'captures': 4, 'date': 'Today', 'mode': 'Human vs AI'},
                {'result': 'VICTORY', 'turns': 92, 'captures': 5, 'date': 'Today', 'mode': 'Human vs AI'},
                {'result': 'DEFEAT',  'turns': 108, 'captures': 2, 'date': 'Yesterday', 'mode': 'Human vs AI'},
                {'result': 'VICTORY', 'turns': 76, 'captures': 6, 'date': 'Yesterday', 'mode': 'Human vs AI'},
                {'result': 'DEFEAT',  'turns': 114, 'captures': 3, 'date': 'Nov 16', 'mode': 'Human vs AI'},
            ]
        },
        'ai_vs_ai': {
            'total_matches': 25,
            'models': {
                'Expectimax': {
                    'rank': 1,
                    'color': (255, 205, 0),
                    'games': 25,
                    'wins': 14,
                    'win_rate': 56.0,
                    'avg_goal': 3.6,
                    'total_captures': 82,
                    'fastest_win': 72,
                    'description': 'Adversarial tree search with stochastic dice evaluation and risk weighting.'
                },
                'Aggressive': {
                    'rank': 2,
                    'color': (40, 120, 245),
                    'games': 25,
                    'wins': 7,
                    'win_rate': 28.0,
                    'avg_goal': 2.8,
                    'total_captures': 58,
                    'fastest_win': 81,
                    'description': 'Heuristic greedily prioritizing opponent captures and fast base release.'
                },
                'Defensive': {
                    'rank': 3,
                    'color': (230, 50, 65),
                    'games': 25,
                    'wins': 3,
                    'win_rate': 12.0,
                    'avg_goal': 2.2,
                    'total_captures': 36,
                    'fastest_win': 94,
                    'description': 'Heuristic prioritizing safe star squares and home column shelter.'
                },
                'Random': {
                    'rank': 4,
                    'color': (40, 195, 80),
                    'games': 25,
                    'wins': 1,
                    'win_rate': 4.0,
                    'avg_goal': 1.1,
                    'total_captures': 18,
                    'fastest_win': 118,
                    'description': 'Uniform random selection across all currently legal moves.'
                }
            }
        }
    }


class LeaderboardManager:
    """Loads, saves, and updates persistent LudoVerse leaderboard statistics."""

    def __init__(self, filepath: str = LEADERBOARD_FILE):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load stats from JSON or populate default stats."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        stats = get_default_stats()
        self._save(stats)
        return stats

    def _save(self, data: Dict[str, Any]):
        """Persist data to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_human_stats(self) -> Dict[str, Any]:
        """Return Human vs AI statistics dictionary."""
        return self.data.get('human_vs_ai', {})

    def get_ai_stats(self) -> Dict[str, Any]:
        """Return AI vs AI Championship statistics dictionary."""
        return self.data.get('ai_vs_ai', {})

    def record_human_match(self, human_won: bool, winner: str, turns: int, captures: int, pieces_home: int):
        """Record the outcome of a Human vs AI match."""
        h_stats = self.data['human_vs_ai']
        h_stats['games_played'] += 1
        if human_won:
            h_stats['human_wins'] += 1
        else:
            h_stats['human_losses'] += 1
        h_stats['total_captures'] += captures
        h_stats['pieces_finished'] += pieces_home

        record = {
            'result': 'VICTORY' if human_won else 'DEFEAT',
            'turns': turns,
            'captures': captures,
            'date': time.strftime("%b %d %H:%M"),
            'mode': 'Human vs AI'
        }
        h_stats['recent_history'].insert(0, record)
        if len(h_stats['recent_history']) > 15:
            h_stats['recent_history'].pop()

        self._save(self.data)

    def record_ai_match(self, winner_model: str, turns: int, stats_by_model: Dict[str, dict]):
        """Record the outcome of an AI vs AI showdown."""
        ai_data = self.data['ai_vs_ai']
        ai_data['total_matches'] += 1

        for model_name, info in stats_by_model.items():
            clean_name = 'Expectimax' if model_name.startswith('Expectimax') else model_name.capitalize()
            if clean_name in ai_data['models']:
                m = ai_data['models'][clean_name]
                m['games'] += 1
                if clean_name == ('Expectimax' if winner_model.startswith('Expectimax') else winner_model.capitalize()):
                    m['wins'] += 1
                    if m.get('fastest_win', 999) > turns:
                        m['fastest_win'] = turns
                m['win_rate'] = round((m['wins'] / m['games']) * 100, 1)
                m['total_captures'] += info.get('captures', 0)

        # Re-sort ranks
        sorted_models = sorted(ai_data['models'].items(), key=lambda kv: (kv[1]['wins'], kv[1]['win_rate']), reverse=True)
        for idx, (k, v) in enumerate(sorted_models):
            v['rank'] = idx + 1

        self._save(self.data)
