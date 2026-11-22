"""
main.py — Application Entry Point for Ludo Verse
==============================================
Starts the Ludo Verse application with Pygame GUI or headless execution.

Usage:
------
    python src/main.py                # Start GUI with Main Menu
    python src/main.py --mode human   # Start directly in Human vs AI mode
    python src/main.py --mode ai      # Start directly in AI vs AI matchup mode
    python src/main.py --headless     # Run automated tournament without display
"""
import os
import sys
import argparse

# Ensure src/ is on Python search path
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


def main():
    parser = argparse.ArgumentParser(description="Ludo Verse — Intelligent Ludo Game (Python + Pygame + Expectimax AI)")
    parser.add_argument('--mode', choices=['menu', 'human', 'ai'], default='menu',
                        help="Launch mode: 'menu' (default), 'human' (Human vs AI), or 'ai' (AI vs AI).")
    parser.add_argument('--headless', action='store_true',
                        help="Run in headless non-GUI mode (executes experiments suite).")
    args = parser.parse_args()

    if args.headless:
        from experiments import run_all_experiments
        run_all_experiments(quick=True)
        return

    # Initialize Pygame GUI
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    from game_ui import LudoUI

    ui = LudoUI()

    if args.mode == 'human':
        ui.start_new_game('HUMAN_VS_AI')
    elif args.mode == 'ai':
        ui.start_new_game('AI_VS_AI')

    ui.run_loop()


if __name__ == '__main__':
    main()
