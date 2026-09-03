# Baseball Simulation — Development Log

A record of each work session, split by what Claude assisted with vs. what was self-implemented.

**Purpose:** Document how Claude was used for efficiency on repetitive/data tasks, while keeping architecture and core logic as personal learning work.

---

## Session 2026-05-24 — Project Foundation

### Self-Implemented
- **Task:** Designed the class hierarchy in [roster.py](../roster.py) — `Player` base class with `Pitcher` and `PositionPlayer` subclasses using inheritance
- **Why self-implemented:** Core OOP architecture — the design decisions about how to model players, what attributes to store, and how inheritance should work were the learning objective
- **Result:** Reusable class structure that separates pitchers from position players while sharing common fields via `super()`

- **Task:** Built the full game shell in [baseball_practice.py](../baseball_practice.py) — `main()` loop, `print_option()` dispatcher, `display_lineups()`, `adjust_lineup_order()`
- **Why self-implemented:** Terminal interface design and game loop structure are fundamental architecture decisions
- **Result:** Working menu system with lineup position swapping via 1-indexed input

### Claude-Assisted
- None this session

### Notes
Initial commit established the full foundation. All 225 lines written from scratch. Future trajectory documented in [baseball_practice.py](../baseball_practice.py) header: text-based now, SQLite + Flask later.

---

## Session 2026-05-29 — 2026 Rosters + Rotation Switching

### Claude-Assisted
- **Task:** Populated 2026 MLB rosters in [roster.py](../roster.py) — Mets home team (position players + full bullpen with ratings) and Yankees away team (player names + pitching staff)
- **Why delegated:** Repetitive data entry of real player names, jersey numbers, positions, and ratings — not a design decision, just research and transcription
- **Result:** Full Mets roster with realistic 2026 ratings; Yankees roster with player names (ratings pending — see `TODO(human)` in [roster.py](../roster.py))

### Self-Implemented
- **Task:** Extended [baseball_practice.py](../baseball_practice.py) option 3 — starting rotation display and order-switching using the same `adjust_lineup_order()` pattern as batting lineup
- **Why self-implemented:** Applying an existing pattern to a new context (rotations) is a concrete learning exercise in code reuse
- **Result:** Option 3 now lets users reorder both teams' starting rotations interactively

### Notes
Yankees ratings are still 0 — left as `TODO(human)` intentionally so that filling in the ratings is a self-directed task (looking up stats, deciding on rating scale, making judgment calls on player value).

---
