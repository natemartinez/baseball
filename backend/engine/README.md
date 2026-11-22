# Baseball Engine Architecture & Developer Triage Guide

This directory houses the authoritative backend simulation engines. All subpackages follow a modular, single-responsibility structure so developers can triage issues, adjust simulation parameters, or add features rapidly.

---

## Architecture Overview

```
backend/engine/
├── game_engine/          # Central simulation highway, game state, and field mechanics
│   ├── main.py           # Authoritative GameEngine coordinator (state mutator highway)
│   ├── game_logic/       # Pure rulebook logic: count, outs, base running, inning turnovers, stats
│   ├── orchestration/    # Pitch-by-pitch flow state machine, AI/human controllers, telemetry packets
│   ├── serialization/    # Payload builders for REST and WebSocket state diffs
│   ├── physics/          # Dr. Alan Nathan flight aerodynamics, ground bounce, friction, and trajectory trace
│   └── geometry/         # Strike zone 13-zone polygon, 2D plate cross-section coordinates, spray cloud dispersion
│
├── pitching_engine/      # Pitcher-side AI, ratings, confidence, and ball delivery execution
│   ├── engine.py         # Authoritative PitchingEngine coordinator
│   ├── pitcher_info/     # In-game pitcher state, stamina, arsenal metrics, pitch confidence, effectiveness
│   ├── pitch_selection/  # AI pitch selection, count leverage, intent target, batter matchup analysis
│   └── pitch_execution/  # Delivery physics, bivariate Gaussian command dispersion, pitch shape/break, timing tiers
│
└── batting_engine/       # Batter-side ratings, plate discipline, swing/take model, and contact resolution
    ├── engine.py         # Authoritative BattingEngine coordinator
    ├── batter_info/      # In-game batter ratings hydration, 13-zone hot/cold slugging profiles, trait normalization
    ├── swing_decision/   # Log-odds swing-or-take evaluator, count leverage, approach modes, swing_model_config.json
    └── contact/          # Batted-ball collision resolver (whiff/foul/in-play), launch velocity/angle, fielder reach radii
```

---

## Developer Triage Map

When fixing a bug or altering baseball behavior, use this quick-reference table to find the authoritative code:

| Symptom / Subsystem | Subpackage | Authoritative File | Description |
| :--- | :--- | :--- | :--- |
| **Count, Outs, Innings** | `game_engine/game_logic/` | `count.py`, `inning.py` | 3 strikes = out, 4 balls = walk, 3 outs = half-inning turnover. |
| **Base Running / Runners** | `game_engine/game_logic/` | `base_running.py` | Runner advancement on hits, walks, sac flies, force outs. |
| **Game State Mutations** | `game_engine/game_logic/` | `state_mutator.py` | Applies batter activities to the central state snapshot. |
| **Turn Pipeline & Flow** | `game_engine/orchestration/` | `pitch_orchestrator.py` | Two-phase flow: THROWN -> RESOLVED, step coordination. |
| **AI / Human Batter Control** | `game_engine/orchestration/` | `controllers.py` | User swings/takes vs AI automated reactions. |
| **API / WebSocket State Payloads** | `game_engine/serialization/` | `state_payload.py` | Serialization for the frontend HUD, linescores, and player cards. |
| **Ball Flight & Kinematics** | `game_engine/physics/` | `ball_flight.py` | 3D trajectory calculation, ground rollout, bounce dampening. |
| **Strike Zone & Coordinates** | `game_engine/geometry/` | `strike_zone.py`, `gameday_math.py` | 13-zone boundaries, rulebook strike tests, nominal targets. |
| **Pitcher Dispersion / Command Error** | `game_engine/geometry/` | `gameday_math.py` | Bivariate truncated Gaussian spray cloud around target coordinates. |
| **Pitcher Confidence & Stamina** | `pitching_engine/pitcher_info/` | `pitch_confidence.py`, `active_pitcher.py` | In-game pitch confidence updates, fatigue, consecutive miss penalties. |
| **Pitcher Effectiveness** | `pitching_engine/pitcher_info/` | `pitch_effectiveness.py` | Whiff-rate and exit-velocity adjustments based on pitch usage & execution. |
| **Pitcher Arsenal & Ratings** | `pitching_engine/pitcher_info/` | `adjusted_ratings.py`, `pitch_objects.py` | Normalizes database pitcher attributes into in-game ratings. |
| **AI Pitch Selection** | `pitching_engine/pitch_selection/` | `selection.py`, `strategy.py` | AI pitch type & zone targeting choices by count and situation. |
| **Pitch Intent & Matchups** | `pitching_engine/pitch_selection/` | `intent.py`, `matchup.py` | Platoon splits, tunneling, and pitch intent generation. |
| **Pitch Break & Shape** | `pitching_engine/pitch_execution/` | `pitch_shape.py`, `calculations.py` | Vertical/horizontal movement, break profiles, and velocity. |
| **Command / Release Timing Tiers** | `pitching_engine/pitch_execution/` | `tiers.py` | Perfect / Good / Early / Late release timing distributions. |
| **Batter Ratings & Profiles** | `batting_engine/batter_info/` | `batters.py` | Normalizes player stats into in-game power, contact, discipline, and hot zones. |
| **Hot / Cold Zones** | `batting_engine/batter_info/` | `batters.py` | 13-zone slugging map normalization (`DEFAULT_BATTER_ZONES`). |
| **Swing Decision / Discipline** | `batting_engine/swing_decision/` | `strategy.py` | Log-odds swing-or-take evaluator, chase probabilities. |
| **Swing Decision Weights** | `batting_engine/swing_decision/` | `swing_model_config.json` | Configurable regression weights for counts, pitch types, leverage (authoritative source). |
| **Contact Resolution (Whiff / Foul)** | `batting_engine/contact/` | `contact.py` | Resolves swings into swing-and-miss, fouls, or balls in play. |
| **In-Play Batted-Ball Outcomes** | `batting_engine/contact/` | `contact_outcome.py` | Classifies hit vs out from landing point, fence distance, and fielder reach radii. |
| **Fielder Positions & Range** | `batting_engine/contact/` | `contact_outcome.py` | Defensive reach radii and fielder coordinates. |

---

## Architectural Principles

1. **State Mutation Boundary:** Only `GameEngine` mutates game state (`balls`, `strikes`, `outs`, `score`, `runners`).
2. **Pure Calculation Engines:** `PitchingEngine` and `BattingEngine` are pure functional coordinators; they accept pre-pitch context and return outcomes without modifying global game state.
3. **Backward Compatibility:** Root modules (`batters.py`, `batter_strategy.py`, `ball_flight.py`, `strike_zone.py`, `gameday_math.py`) maintain lightweight backward-compatibility shims using in-place module aliasing (`sys.modules[__name__] = _canonical`), while contact resolution and outcomes live cleanly under `batting_engine/contact/`.

---

## Test Suite Architecture & Directory Map

The test suite directly mirrors the functional backend layout:

```
tests/
├── conftest.py                      # Global test fixtures, sys.path configuration, _game() factory
├── test_reorg_smoke.py              # Root integration & directory organization smoke tests
├── api/                             # REST/WebSocket routes, state payloads, and RosterStore tests
├── database/                        # SQLite schema validation, O(1) retrieval, and performance tests
├── e2e_pitching_pipeline/           # Authoritative E2E contract test suites (Tiers 1-4)
└── engine/
    ├── pitching_engine/             # Pitcher ratings, confidence, effectiveness, selection, targeting
    ├── batting_engine/              # Batter info, plate discipline, swing decisions, contact outcomes
    ├── game_engine/                 # Ball flight, ground physics, turn orchestration, half-inning switch
    ├── game_logic/                  # Count, outs, base running, inning turnover, stats tracking
    ├── game_modes/                  # Practice mode and game mode controller
    └── serialization/               # State and arsenal payload formatting
```


