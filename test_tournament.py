"""
test_tournament.py — Phase 6: Automated Tournament and Benchmark Tests
=======================================================================
Tests for tournament.py and experiments.py covering:
  - Tournament runner initialization and configuration
  - Matchup execution and statistical metrics accumulation
  - CSV report serialization for matchups, depth comparisons, and performance
  - Chart generation without GUI display
"""
import os
import tempfile
import pytest
from tournament import Tournament
from board import COLORS


def test_tournament_init():
    t = Tournament(num_games=10, seed_base=100, max_turns=500, verbose=False)
    assert t.num_games == 10
    assert t.seed_base == 100
    assert t.max_turns == 500
    assert not t.verbose


def test_tournament_run_quick_matchup():
    """Run a tiny 2-game matchup to verify statistics accumulation."""
    t = Tournament(num_games=2, seed_base=42, max_turns=300, verbose=False)
    configs = [
        {'type': 'random'},
        {'type': 'random'},
        {'type': 'random'},
        {'type': 'random'},
    ]
    res = t.run_matchup(configs, num_games=2)
    assert len(res) == 4
    total_wins = sum(res[c]['wins'] for c in COLORS)
    assert total_wins <= 2
    for c in COLORS:
        assert res[c]['games_played'] == 2
        assert 0.0 <= res[c]['win_rate'] <= 1.0
        assert res[c]['avg_turns'] >= 0


def test_tournament_save_csv():
    """Verify CSV export formatting."""
    t = Tournament(num_games=1, verbose=False)
    configs = [{'type': 'random'}] * 4
    res = t.run_matchup(configs, num_games=1)

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test_matchup.csv')
        t.save_matchup_csv(res, csv_path)
        assert os.path.exists(csv_path)

        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        assert len(lines) == 5  # Header + 4 player rows
        assert 'Color,Agent Type,Games Played' in lines[0]


def test_experiments_chart_generation():
    """Verify matplotlib plot generation without opening display."""
    from experiments import plot_win_rates
    mock_results = {
        'yellow': {'type': 'expectimax', 'win_rate': 0.45},
        'blue':   {'type': 'aggressive', 'win_rate': 0.25},
        'red':    {'type': 'defensive',  'win_rate': 0.20},
        'green':  {'type': 'random',     'win_rate': 0.10},
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        chart_path = os.path.join(tmpdir, 'test_chart.png')
        plot_win_rates(mock_results, "Test Chart", chart_path)
        assert os.path.exists(chart_path)
        assert os.path.getsize(chart_path) > 1000
