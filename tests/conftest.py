"""
conftest.py — Pytest configuration for LudoMax
===============================================
Adds the src/ directory to sys.path so that all test files can import
game modules (board, move, game_state, etc.) without installing the package.
"""
import sys
import os

# Insert src/ at the front of the module search path
_SRC = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, os.path.abspath(_SRC))
