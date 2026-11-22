"""
experiments.py — Automated Experiments and Matplotlib Visualization for LudoMax
================================================================================
Executes benchmarking tournaments between AI agents, saves CSV datasets to
outputs/results/, and generates analytical plots to outputs/charts/.
"""
import os
import sys
import tempfile
import argparse
from typing import Dict

os.environ.setdefault('MPLCONFIGDIR', os.path.join(tempfile.gettempdir(), 'matplotlib_ludomax'))

# Ensure matplotlib runs in headless mode
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Ensure src/ is on module search path
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from tournament import Tournament
from board import COLORS


RESULTS_DIR = os.path.join(_SRC_DIR, '..', 'outputs', 'results')
CHARTS_DIR  = os.path.join(_SRC_DIR, '..', 'outputs', 'charts')


def plot_win_rates(results: Dict[str, Dict], title: str, output_path: str):
    """Generate a bar chart of win rates across player agent types."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    colors = list(results.keys())
    agent_names = [f"{c.capitalize()}\n({results[c]['type']})" for c in colors]
    win_rates = [results[c]['win_rate'] * 100 for c in colors]
    bar_colors = ['gold', 'royalblue', 'crimson', 'forestgreen']

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(agent_names, win_rates, color=bar_colors, edgecolor='black', width=0.55)

    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}%",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"  Chart saved → {output_path}")


def plot_depth_comparison(depth_results: Dict[int, Dict], output_path: str):
    """Plot Expectimax win rate vs search depth."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    depths = sorted(depth_results.keys())
    win_rates = [depth_results[d]['yellow']['win_rate'] * 100 for d in depths]
    avg_captures = [depth_results[d]['yellow']['avg_captures_made'] for d in depths]

    fig, ax1 = plt.subplots(figsize=(8, 5))

    color = 'tab:blue'
    ax1.set_xlabel('Expectimax Search Depth', fontsize=12)
    ax1.set_ylabel('Win Rate (%)', color=color, fontsize=12)
    line1 = ax1.plot(depths, win_rates, marker='o', linewidth=2.5, markersize=8, color=color, label='Win Rate')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_xticks(depths)
    ax1.set_ylim(0, 100)
    ax1.grid(True, linestyle='--', alpha=0.6)

    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Avg Captures Made', color=color, fontsize=12)
    line2 = ax2.plot(depths, avg_captures, marker='s', linewidth=2, linestyle='--', markersize=8, color=color, label='Captures')
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title('Expectimax Search Depth vs Performance', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"  Chart saved → {output_path}")


def plot_performance_metrics(perf: Dict[int, Dict], output_path: str):
    """Plot search nodes expanded and decision latency across depths."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    depths = sorted(perf.keys())
    nodes = [perf[d]['avg_nodes'] for d in depths]
    times_ms = [perf[d]['avg_time_ms'] for d in depths]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax1.bar([str(d) for d in depths], nodes, color='mediumpurple', edgecolor='black', width=0.5)
    ax1.set_xlabel('Search Depth', fontsize=12)
    ax1.set_ylabel('Avg Nodes Expanded / Move', fontsize=12)
    ax1.set_title('Computational Complexity', fontsize=13, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.6)
    for i, v in enumerate(nodes):
        ax1.text(i, v + max(nodes)*0.02, f"{v:.1f}", ha='center', fontweight='bold')

    ax2.bar([str(d) for d in depths], times_ms, color='teal', edgecolor='black', width=0.5)
    ax2.set_xlabel('Search Depth', fontsize=12)
    ax2.set_ylabel('Avg Decision Time (ms)', fontsize=12)
    ax2.set_title('Search Latency', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', linestyle='--', alpha=0.6)
    for i, v in enumerate(times_ms):
        ax2.text(i, v + max(times_ms)*0.02, f"{v:.2f} ms", ha='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"  Chart saved → {output_path}")


def run_all_experiments(quick: bool = False):
    """Execute complete tournament suite and generate analytical outputs."""
    print("==================================================")
    print("          LudoVerse Automated Experiments         ")
    print("==================================================")
    num_games = 5 if quick else 20
    benchmark_games = 3 if quick else 6

    tourney = Tournament(num_games=num_games, verbose=True)

    # 1. All-vs-All 4-way matchup
    all_vs_all = tourney.run_all_vs_all()
    tourney.save_matchup_csv(all_vs_all, os.path.join(RESULTS_DIR, 'all_vs_all_matchup.csv'))
    plot_win_rates(all_vs_all, 'LudoVerse 4-Way Matchup: Expectimax vs Heuristic AI',
                   os.path.join(CHARTS_DIR, 'all_vs_all_win_rates.png'))

    # 2. Depth comparison
    depth_res = tourney.run_depth_comparison(num_games=num_games, depths=(1, 2, 3))
    tourney.save_depth_csv(depth_res, os.path.join(RESULTS_DIR, 'depth_comparison.csv'))
    plot_depth_comparison(depth_res, os.path.join(CHARTS_DIR, 'depth_comparison.png'))

    # 3. Performance benchmark
    perf_res = tourney.run_performance_benchmark(depths=(1, 2, 3), num_games=benchmark_games)
    tourney.save_performance_csv(perf_res, os.path.join(RESULTS_DIR, 'performance_metrics.csv'))
    plot_performance_metrics(perf_res, os.path.join(CHARTS_DIR, 'performance_metrics.png'))

    print("\n[OK] All experiments completed successfully!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run LudoVerse AI experiments.")
    parser.add_argument('--quick', action='store_true', help="Run small sample games for fast verification.")
    args = parser.parse_args()
    run_all_experiments(quick=args.quick)
