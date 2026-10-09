# Baseball Simulation — Expo Client

The Expo (React Native) client for the MLB Baseball Simulation, vendored into the
backend repo at `frontend/`. It renders the scoreboard, strike zone, pitch
selection, strategy decider, at-bat outcome feed, and the Gameday Dev Menu.

The authoritative simulation engine and REST API live in the repository root
(Python Flask, port `5000`). This directory contains only the client.

## Layout

```text
frontend/
├── app/                        # Expo app root (TypeScript)
│   ├── App.tsx / index.ts
│   ├── assets/                 # static resources (images, fonts, app icon)
│   └── src/
│       ├── components/         # Scorebug, Diamond, MatchupCard, StrikeZoneGrid,
│       │                       # PitchSelector, PitchOutcomeFeed, LineupDialog, ...
│       │   └── debug/          # Gameday Dev Menu, visualizer, calibration, strategy ingest
│       ├── screens/            # BaseballSimScreen
│       ├── services/           # GameRepository, HttpGameService, MockGameService, engines
│       ├── store/              # Zustand game store
│       ├── theme/              # Design tokens
│       └── types/              # API + gameday telemetry schemas
├── docs/pitching-logic/        # 6-part physics / strategy specification
├── pitching_logic.md           # Statcast physics spec & rules_config
└── dev.sh                      # Boots the Python backend + Expo web together
```

### Static resources

All static resources (images, fonts, the future app icon/splash) live under
`frontend/app/assets/`. In `app.json`, reference them project-root-relative as
`./assets/…` (for example `"icon": "./assets/icon.png"`).

## Run

```bash
# From the repo root (recommended): boots Flask + Expo web
./dev.sh            # or: npm run dev

# Or just this client:
cd frontend/app
npm install
npx expo start --web     # http://localhost:8081
```

In the app header, open the **Gameday Dev Menu** (`Shift+D` / tap **DEV**) and use
the **Backend Switcher** to toggle between the live **Python Flask (5000)** backend
and the in-client **Mock Engine**. On web the HTTP client defaults to
`http://localhost:5000` (see `app/.env.example`).

## Physics & Documentation

The `docs/pitching-logic/` suite documents the simulation:

1. [`01_HIGH_LEVEL_OVERVIEW.md`](docs/pitching-logic/01_HIGH_LEVEL_OVERVIEW.md)
2. [`02_STATCAST_PHYSICS_AND_ARSENAL.md`](docs/pitching-logic/02_STATCAST_PHYSICS_AND_ARSENAL.md)
3. [`03_INTENT_AND_STRATEGY_MATRIX.md`](docs/pitching-logic/03_INTENT_AND_STRATEGY_MATRIX.md)
4. [`04_STRIKE_ZONE_COMMAND_AND_TARGETING.md`](docs/pitching-logic/04_STRIKE_ZONE_COMMAND_AND_TARGETING.md)
5. [`05_REACT_JS_FRONTEND_INTEGRATION.md`](docs/pitching-logic/05_REACT_JS_FRONTEND_INTEGRATION.md)
6. [`06_DATABASE_PERSISTENCE_INTEGRATION.md`](docs/pitching-logic/06_DATABASE_PERSISTENCE_INTEGRATION.md)

## Notes

- The former standalone Node prototype (`server.js` / `db.js`) and the native
  Android app (`app/`) were removed. The Python backend is authoritative and the
  Expo client is the interactive frontend.
- The mock seed data moved to `backend/mock/mock_baseball_db.json`; the Python
  seeder (`backend/database/seed.py`) loads it to populate SQLite.
