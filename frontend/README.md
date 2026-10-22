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
│       │   ├── GameField.tsx           # Web R3F canvas shell
│       │   ├── GameField.native.tsx    # Native R3F canvas shell
│       │   ├── gamefield/              # 3D scene, geometry, projection, pitch visualizer
│       │   └── debug/          # Gameday Dev Menu, visualizer, calibration, strategy ingest
│       ├── screens/            # BaseballSimScreen
│       ├── services/           # GameRepository, HttpGameService, MockGameService, engines
│       ├── store/              # Zustand game store
│       ├── theme/              # Design tokens
│       └── types/              # API + gameday telemetry schemas
└── ../scripts/dev.sh           # Boots the Python backend + Expo web together
```

### Static resources

All static resources (images, fonts, the future app icon/splash) live under
`frontend/app/assets/`. In `app.json`, reference them project-root-relative as
`./assets/…` (for example `"icon": "./assets/icon.png"`).

## Run

```bash
# From the repo root (recommended): boots Flask + Expo web
./scripts/dev.sh    # or: npm run dev

# Or just this client:
cd frontend/app
npm install
npx expo start --web     # http://localhost:8081
```

In the app header, open the **Gameday Dev Menu** (`Shift+D` / tap **DEV**) and use
the **Backend Switcher** to toggle between the live **Python Flask (5000)** backend
and the in-client **Mock Engine**. On web the HTTP client defaults to
`http://localhost:5000` (see `app/.env.example`).

## 3D Field & Documentation

The tracked system-design docs live in the repository root [`docs/`](../docs/):

- [Documentation index](../docs/README.md)
- [3D Field, Pitch Visualization & HUD](../docs/08_3D_FIELD_PITCH_AND_HUD.md) — coordinate systems, camera calibration, projected strike-zone HUD, mock pitch flow, and IVB kinematics

Additional backend, API-contract, data-schema, and state-machine documents are planned; see the documentation index.

## Notes

- The former standalone Node prototype (`server.js` / `db.js`) and the native
  Android app (`app/`) were removed. The Python backend is authoritative and the
  Expo client is the interactive frontend.
- The mock seed data moved to `backend/mock/mock_baseball_db.json`; the Python
  seeder (`backend/database/seed.py`) loads it to populate SQLite.
