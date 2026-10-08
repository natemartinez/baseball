# 06. Database Persistence & Live Statistics Engine

## Overview

The database layer runs concurrently with the simulation engine to record pitch events and at-bats, automatically updating player statistics without requiring full-page reloads or manual calculations.

```
                  ┌──────────────────────┐
                  │ Pitch / At-Bat Event │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   IDatabaseAdapter   │
                  │ (Mock / PostgreSQL)  │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌────────────────────────┐        ┌────────────────────────┐
│  Hitter Recalculation  │        │ Pitcher Recalculation  │
│  • Hits / At-Bats      │        │  • Pitch Count         │
│  • AVG, OBP, SLG, OPS  │        │  • IP, ERA, WHIP       │
└────────────────────────┘        └────────────────────────┘
            │                                 │
            └────────────────┬────────────────┘
                             ▼
                  ┌──────────────────────┐
                  │ JSON Snapshot / DB   │
                  │ + GameState Sync     │
                  └──────────────────────┘
```

---

## Atomic Statistical Formulas

### 1. Batting Metrics
- **Batting Average (AVG)**:
  $$\text{AVG} = \frac{\text{Hits}}{\text{At-Bats}}$$
- **On-Base Percentage (OBP)**:
  $$\text{OBP} = \frac{\text{Hits} + \text{Walks}}{\text{At-Bats} + \text{Walks}}$$
- **Slugging Percentage (SLG)**:
  $$\text{SLG} = \frac{\text{Singles} + 2 \times \text{Doubles} + 3 \times \text{Triples} + 4 \times \text{Home Runs}}{\text{At-Bats}}$$
- **On-Base Plus Slugging (OPS)**:
  $$\text{OPS} = \text{OBP} + \text{SLG}$$

### 2. Pitching Metrics
- **Earned Run Average (ERA)**:
  $$\text{ERA} = 9.0 \times \frac{\text{Earned Runs}}{\text{Innings Pitched}}$$
- **Walks Plus Hits per Inning Pitched (WHIP)**:
  $$\text{WHIP} = \frac{\text{Walks} + \text{Hits Allowed}}{\text{Innings Pitched}}$$

---

## Live Persistence Architecture

1. **In-Memory Speed + On-Disk Durability**:
   - Reads and writes execute in sub-millisecond in-memory structures ($< 0.5\text{ms}$ latency).
   - The seed dataset lives at `backend/mock/mock_baseball_db.json` and is loaded by the Python seeder (`backend/database/seed.py`) to populate SQLite.

2. **Pluggable Architecture (`IDatabaseAdapter`)**:
   - To swap to Cloud SQL or PostgreSQL, simply supply `DATABASE_TYPE=postgres` and `DATABASE_URL` in environment variables.
   - The entire front-end and pitching engine interact solely through the `IDatabaseAdapter` contract interface.
