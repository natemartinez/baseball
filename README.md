# Baseball Simulation

A text-based baseball game simulation I'm building in Python as a side project while learning software design. The goal is to eventually simulate a full nine-inning game — pitching outcomes, at-bats, hits, outs, and a box score — all driven from the terminal.

Right now the foundation is there: player rosters, a working menu loop, and lineup/rotation management. The actual game logic (pitching, hitting, in-play events) is still being built out.

---

## What it does right now

- Launch a terminal menu with 5 options
- View and reorder batting lineups for both teams
- View and reorder starting rotations for both teams
- Quit cleanly

## What's coming

- Pitch simulation (stuff/movement/control ratings vs. hit zones)
- At-bat loop with ball/strike/contact outcomes
- Full nine-inning game with score tracking and box score
- Substitutions and bullpen management
- SQLite backend to persist rosters and game state
- Flask server + frontend (eventually)

---

## Project Structure

```
baseball/
├── baseball_practice.py   # Main game loop, menu, lineup/rotation logic
├── roster.py              # Player classes and team rosters
└── logs/
    └── development_log.md # Session notes tracking what I built vs. what I used AI for
```

---

## How to run it

Requires Python 3.

```bash
python baseball_practice.py
```

You'll get a menu. Options 2 and 3 let you swap batting order positions and rotation slots interactively. Option 1 will eventually start the game simulation — for now it just prints "Play Ball!"

---

## Design notes

The player model uses class inheritance: a `Player` base class holds shared attributes (name, number, fielding rating), and `Pitcher` / `PositionPlayer` extend it with position-specific stats. Rosters are structured as nested dicts so it's easy to pull out starters, bench, bullpen, etc. independently.

The Mets roster has full ratings. The Yankees roster has names and positions but ratings are still 0 — filling those in is an intentional self-directed exercise (see `TODO(human)` in `roster.py`).

---

## Teams

- **Home:** New York Mets
- **Away:** New York Yankees

Both rosters reflect 2026 player data.

---

*Built as a learning project — tracking what I implement myself vs. what I delegate in `logs/development_log.md`.*
