# LudoMax: Expectimax AI for Ludo under Dice Chance

A Ludo game where AI players choose which piece to move after the dice is rolled. The main AI uses Expectimax search to average over all six possible dice values and judge risk. We compare it with aggressive, defensive, and random agents over many seeded games.

## Team

- Saniya Asim (24K-3084) — Ludo engine, rules, unit tests, tournament runner
- Aamna (24K-3001) — Rule-based agents, Pygame interface, human player
- Aisha Shaikh (24K-3026) — Expectimax agent, evaluation function, charts and analysis

## Setup

```bash
pip install -r requirements.txt