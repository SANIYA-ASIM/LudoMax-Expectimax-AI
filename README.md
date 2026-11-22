# LudoMax — Expectimax AI for Ludo under Dice Chance

**Python 3.11+ | Pygame-CE | Expectimax Adversarial AI**

LudoMax is a complete, modular implementation of the classic four-player Ludo board game featuring an intelligent AI player powered by **Expectimax**, a search algorithm designed for environments involving uncertainty and chance.

The project combines a fully functional Ludo game engine, a graphical interface built using Pygame-CE, multiple AI playing strategies, and tournament experiments to evaluate agent performance.

Unlike traditional adversarial search algorithms that assume opponents always make the worst possible move, Expectimax also considers random events such as dice rolls. It evaluates possible future outcomes and selects moves based on their expected value.

## Table of Contents

- [Project Overview](#project-overview)
- [Team Members](#team-members)
- [Key Features](#key-features)
- [Technologies Used](#technologies-used)
- [Installation and Setup](#installation-and-setup)
- [Running the Game](#running-the-game)
- [AI Agent Strategies](#ai-agent-strategies)
- [How Expectimax Works](#how-expectimax-works)
- [Game Rules and Mechanics](#game-rules-and-mechanics)
- [Project Architecture](#project-architecture)
- [Experiments and Performance Analysis](#experiments-and-performance-analysis)
- [Testing](#testing)

---

## Project Overview

LudoMax aims to demonstrate how Artificial Intelligence can make strategic decisions in a game that combines player competition with random events.

The game supports human players and multiple AI strategies. Players move their tokens around the board according to dice rolls, capture opponent tokens, use safe squares, and attempt to move all four tokens into their home area.

The main AI strategy is **Expectimax**, which searches through possible future game states while considering the probability of different dice outcomes.

The project also includes rule-based agents that provide different playing styles. Their performance can be compared against the Expectimax agent through simulated tournaments.

## Team Members

| Team Member | Roll Number | Contributions |
|---|---|---|
| Saniya Asim | 24K-3084 | Ludo game engine, game rules, unit testing, and tournament runner |
| Aamna | 24K-3001 | Rule-based agents, Pygame interface, and human player |
| Aisha Shaikh | 24K-3026 | Expectimax agent, evaluation function, charts, and performance analysis |

## Key Features

- **Complete Ludo Game Engine:** Implements the core rules, token movement, captures, safe squares, and winning conditions.
- **Graphical User Interface:** Provides an interactive game board using Pygame-CE.
- **Human vs AI Gameplay:** Allows a human player to compete against computer-controlled opponents.
- **Multiple AI Agents:** Includes Random, Aggressive, Defensive, and Expectimax strategies.
- **Expectimax Search:** Evaluates possible future outcomes while accounting for the uncertainty of dice rolls.
- **Adjustable Search Depth:** Supports different search depths to study the relationship between decision quality and computational cost.
- **Tournament System:** Runs simulated matches between different AI agents.
- **Performance Evaluation:** Collects statistics and generates charts to compare agent performance.
- **Leaderboard:** Maintains game performance statistics.
- **Unit Testing:** Includes automated tests for important game mechanics and AI functionality.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.11+ | Main programming language |
| Pygame-CE | Graphical interface and game rendering |
| NumPy | Numerical operations |
| Matplotlib | Generating performance charts |
| CSV | Storing experimental results |
| JSON | Storing leaderboard statistics |
| Pytest | Automated testing |

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/SANIYA-ASIM/LudoMax-Expectimax-AI.git
```

### 2. Navigate to the Project Folder

```bash
cd LudoMax-Expectimax-AI
```

### 3. Install Dependencies

Make sure Python 3.11 or later is installed.

Install the required packages using:

```bash
pip install -r requirements.txt
```

## Running the Game

The main entry point of the application is `src/main.py`.

### Launch the Graphical Game

```bash
python src/main.py
```

### Human Player Mode

```bash
python src/main.py --mode human
```

### AI Player Mode

```bash
python src/main.py --mode ai
```

The game starts through the graphical interface, allowing players to interact with the Ludo board and play against the available computer-controlled agents.

## AI Agent Strategies

LudoMax includes four different AI strategies. Each strategy makes decisions using a different approach.

### 1. Random Agent

The Random Agent selects a legal move randomly from the available moves.

It does not consider future consequences or attempt to develop a long-term strategy. It provides a baseline for evaluating the performance of more advanced agents.

### 2. Aggressive Agent

The Aggressive Agent prioritizes moves that allow it to capture opponent tokens.

Its main objective is to put pressure on other players by selecting offensive opportunities whenever possible.

### 3. Defensive Agent

The Defensive Agent focuses on protecting its own tokens.

It considers safer positions and attempts to reduce the chances of its tokens being captured by opponents.

### 4. Expectimax Agent

The Expectimax Agent uses a search algorithm to evaluate possible future game states.

Instead of selecting a move based only on the current board, it considers possible future dice rolls and the moves that may become available afterward.

It calculates the expected value of possible outcomes and selects the move with the most promising expected result.

The Expectimax Agent supports different search depths, allowing its performance and computational cost to be compared.

## How Expectimax Works

Expectimax is an adversarial search algorithm used in environments where decisions involve both strategic choices and random events.

Unlike Minimax, which assumes that an opponent always selects the least favorable outcome, Expectimax handles uncertainty by calculating expected values.

In LudoMax, the search involves three important types of nodes:

**1. MAX Nodes**

These represent decisions made by the Expectimax-controlled player. The agent selects the move with the highest expected value.

**2. CHANCE Nodes**

These represent dice rolls. Since a six-sided die has six possible outcomes, the algorithm considers the possible dice values and calculates their expected contribution.

**3. MIN Nodes**

These represent opponent decision points. The search accounts for the possible moves of competing players when evaluating future states.

### Expected Value Calculation

At a chance node, the expected value is calculated using:

\[
EV(s)=\sum_{i=1}^{n}P(i)\times V(i)
\]

Where:

- \(EV(s)\) is the expected value of the current state.
- \(P(i)\) is the probability of an outcome.
- \(V(i)\) is the value of that outcome.
- \(n\) represents the number of possible outcomes.

For a fair six-sided die, each dice outcome has a probability of:

\[
P(i)=\frac{1}{6}
\]

The algorithm combines the values of possible future outcomes to make a decision.

### Search Depth

Search depth determines how far into the future the algorithm explores.

- **Depth 1:** Evaluates a smaller number of future possibilities.
- **Depth 2:** Explores additional future decisions and dice outcomes.
- **Depth 3:** Looks further ahead, potentially improving decision quality but requiring more computation.

Increasing search depth can improve decision-making, but it also increases the number of states that must be evaluated.

## Game Rules and Mechanics

LudoMax implements the main mechanics of the traditional Ludo game.

### Players and Tokens

- The game supports two to four players.
- Each player controls four tokens.
- Every token starts in its respective base.
- The objective is to move all four tokens into the home area before the other players.

### Dice Rolls

- Players roll a six-sided die.
- A token generally needs a six to leave its base.
- The dice value determines how many steps a token can move.
- Rolling a six provides an additional turn, subject to the implemented turn rules.

### Token Movement

The game uses progress values to represent token positions:

| Progress Value | Meaning |
|---|---|
| -1 | Token is in its base |
| 0–51 | Token is on the main board loop |
| 52–57 | Token is in its home column or finishing path |
| 58 | Token has completed its journey |

A token must follow the movement rules, and it cannot move beyond the finishing position.

### Capturing

When a token lands on an opponent's token on a capturable square, the opponent's token is sent back to its base.

### Safe Squares

Certain board positions are designated as safe squares. Tokens occupying these positions are protected from capture.

### Winning Condition

A player wins when all four of their tokens successfully reach the final home position.

## Project Architecture

The project is organized into separate directories to keep the game engine, interface, tests, and experimental results organized.

```text
LudoMax-Expectimax-AI/
│
├── src/
│   ├── agents.py
│   ├── board.py
│   ├── dice.py
│   ├── expectimax.py
│   ├── experiments.py
│   ├── game.py
│   ├── game_state.py
│   ├── game_ui.py
│   ├── leaderboard.py
│   ├── main.py
│   ├── move.py
│   ├── sound_effects.py
│   ├── theme.py
│   ├── tournament.py
│   └── ui_utils.py
│
├── tests/
│   ├── conftest.py
│   ├── test_agents.py
│   ├── test_board.py
│   ├── test_captures.py
│   ├── test_expectimax.py
│   ├── test_game.py
│   ├── test_gameplay_modes.py
│   ├── test_moves.py
│   ├── test_safe_squares.py
│   ├── test_tournament.py
│   ├── test_ui.py
│   └── test_winning.py
│
├── assets/
│   └── fonts/
│       ├── LilitaOne-Regular.ttf
│       ├── Poppins-Bold.ttf
│       └── Poppins-Regular.ttf
│
├── outputs/
│   ├── charts/
│   │   ├── all_vs_all_win_rates.png
│   │   ├── depth_comparison.png
│   │   └── performance_metrics.png
│   │
│   ├── results/
│   │   ├── all_vs_all_matchup.csv
│   │   ├── depth_comparison.csv
│   │   └── performance_metrics.csv
│   │
│   ├── screens/
│   └── leaderboard_stats.json
│
├── docs/
├── data/
├── README.md
└── requirements.txt
```

### Main Source Files

| File | Responsibility |
|---|---|
| `agents.py` | Defines the available AI player strategies |
| `board.py` | Handles the Ludo board structure and positions |
| `dice.py` | Implements dice rolling |
| `expectimax.py` | Implements the Expectimax search algorithm |
| `experiments.py` | Runs performance experiments |
| `game.py` | Controls the main game flow |
| `game_state.py` | Represents the current game state |
| `game_ui.py` | Implements the graphical game interface |
| `leaderboard.py` | Maintains leaderboard statistics |
| `main.py` | Entry point of the application |
| `move.py` | Represents and handles token moves |
| `sound_effects.py` | Handles game sound effects |
| `theme.py` | Defines visual theme settings |
| `tournament.py` | Runs matches between AI agents |
| `ui_utils.py` | Provides graphical interface utilities |

### Tests Directory

The `tests/` directory contains automated tests for different parts of the application, including:

- AI agent behavior
- Board functionality
- Token captures
- Expectimax decisions
- Game logic
- Gameplay modes
- Token movement
- Safe squares
- Tournament functionality
- User interface
- Winning conditions

### Assets Directory

The `assets/fonts/` directory contains the font files used to customize the graphical interface.

### Outputs Directory

The `outputs/` directory stores the results generated by the project.

- `charts/` contains performance visualization images.
- `results/` contains CSV files with experimental data.
- `screens/` contains screenshots of the application and its results.
- `leaderboard_stats.json` stores leaderboard statistics.

## Experiments and Performance Analysis

LudoMax includes an experimental framework to compare the performance of different AI strategies.

The experiments evaluate:

- Expectimax against Random, Aggressive, and Defensive agents.
- The effect of different Expectimax search depths.
- Agent win rates.
- Game performance and computational cost.

### Performance Metrics

The project uses several metrics to evaluate the agents:

| Metric | Purpose |
|---|---|
| Win Rate | Measures how often an agent wins |
| Captures Made | Counts opponent tokens captured |
| Captures Suffered | Counts the agent's tokens captured |
| Average Game Length | Measures the number of turns taken |
| Nodes Expanded | Measures the number of search states explored |
| Decision Time | Measures the time required to select a move |

### Generated Charts

The project includes the following performance charts:

1. `all_vs_all_win_rates.png` — Compares the win rates of different agents.
2. `depth_comparison.png` — Shows the effect of Expectimax search depth.
3. `performance_metrics.png` — Visualizes important performance measurements.

The corresponding CSV files are stored in `outputs/results/`.

## Testing

The project includes an automated test suite to verify the correctness of the game engine, AI agents, and other components.

Tests cover important functionality such as:

- Legal and illegal token movements.
- Capturing opponent tokens.
- Safe-square protection.
- Winning conditions.
- AI agent decisions.
- Expectimax functionality.
- Tournament execution.
- Graphical interface behavior.

### Running Tests

Install the required dependencies, including the testing framework, and run:

```bash
pytest
```

The project documentation reports **193 unit tests passed**.

---

## Project Goal

LudoMax demonstrates how Artificial Intelligence can be applied to a stochastic, multi-agent game environment.

By combining game-state representation, rule-based decision-making, Expectimax search, probability calculations, and performance experiments, the project provides a practical demonstration of AI concepts in game development.

**LudoMax — Making strategic decisions in a game of chance.**
