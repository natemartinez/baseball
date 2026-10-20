# Refactoring Recommendations

**Source:** Refactor Radar 0.1.0 scan, 2026-10-19  
**Scope:** 63 files / 427 functions across the Python backend and React Native client  
**Result:** 135 findings — 30 high, 62 medium, 43 low; 33 have safe fixes  
**Ranking inputs:** severity, cyclomatic complexity, function/file size, git churn in the last 180 days, and duplicate bodies

This document groups the scan into four tiers by importance. A single function can produce more than one raw finding (for example, both "long function" and "high complexity"); the tiers below combine those into one refactor item. These are recommendations, not required changes. No source files were modified.

| Tier | Focus | Why it ranks here |
| --- | --- | --- |
| 1 | Core simulation and persistence | Central game correctness, highest complexity, highest churn |
| 2 | Production client data, state, and UI | User-facing, high maintenance cost, mirrors backend logic |
| 3 | Debug surfaces and test harnesses | Large or complex, but lower production blast radius |
| 4 | Cleanup and quick wins | Low-risk, mechanical, or already implied by higher-tier splits |

### Finding inventory

| Category | Findings |
| --- | --- |
| Long functions | 39 |
| High complexity | 36 |
| Unused imports | 33 |
| Too many parameters | 10 |
| Large files | 7 |
| Duplicated functions | 4 |
| Broad exceptions | 3 |
| Explicit `any` | 3 |
| **Total** | **135** |

---

## Tier 1 — Core simulation and persistence

These are the highest-risk refactors. They sit on the game's critical path, combine large functions with high branching, and have the most recent churn in the repository.

| # | Location | Function | Metrics | Recommended refactor |
| --- | --- | --- | --- | --- |
| 1 | `backend/engine/game_engine.py:182` | `pitch` | 293 lines, complexity 38, churn 3 | Split the pitch pipeline into named stages and return a typed result object |
| 2 | `backend/engine/game_engine.py:507` | `calculate_strategy_and_intent` | 236 lines, complexity 88, churn 3 | Split by decision domain and replace branch chains with tables |
| 3 | `backend/engine/game_engine.py:744` | `get_game_state_payload` | 67 lines, complexity 21, churn 3 | Extract per-entity serializers |
| 4 | `backend/models/player.py:46` | `Player.from_dict` | 64 lines, complexity 30, churn 3 | Add typed field readers and a defaults map |
| 5 | `backend/engine/pitching_engine/strategy.py:36` | `choose_pitch` | 122 lines, complexity 39, 6 parameters | Introduce a pitch-choice context object and split selection from scoring |
| 6 | `backend/engine/batter_strategy.py:52` | `decide_swing` | 59 lines, complexity 20, 6 parameters, churn 2 | Share a swing context object with `resolve_contact` |
| 7 | `backend/engine/batter_strategy.py:112` | `resolve_contact` | 84 lines, complexity 20, churn 2 | Extract contact-outcome tables and keep decision separate from execution |
| 8 | `backend/engine/pitching_engine/engine.py:63` | `execute_pitch` | 112 lines, complexity 10, 11 parameters | Replace the parameter list with a `PitchRequest` object and extract rating/delivery steps |
| 9 | `backend/database/db.py:107` | `add_player` | 81 lines, complexity 5, 10 parameters, churn 4 | Introduce a typed player record and split insert/update paths |

### Why these first

- `pitch` is the largest function on the simulation path. Its responsibilities include intent/target selection, delivery execution, outcome classification, state updates, and telemetry. Extract those stages so each can be tested independently.
- `calculate_strategy_and_intent` has the highest complexity in the repository at 88. Every new strategy rule adds another branch. Split it into count leverage, situation, batter tendency, pitcher fatigue, and target selection, with a single public entry point.
- `Player.from_dict` and `add_player` sit at the persistence boundary. Typed request/record objects remove repeated field handling and make the 10–12 parameter signatures tractable.
- `execute_pitch` (11 parameters) and `choose_pitch` (6 parameters) are the best candidates for request objects. Keep existing public signatures stable with thin wrappers if other modules call them directly.

### Suggested success criteria

- No Tier 1 function above 100 lines.
- `calculate_strategy_and_intent` complexity below 25; `pitch` below 20.
- `choose_pitch` below 80 lines and complexity below 15.
- Characterization tests for pitch outcomes, strategy intent, and player hydration added before the splits.

---

## Tier 2 — Production client data, state, and UI

These items are user-facing or directly mirror backend behavior. The client must stay in parity with the Python engine, so refactor backend and mock paths together.

### 2A — Client data, state, and services

| # | Location | Issue | Metrics | Recommended refactor |
| --- | --- | --- | --- | --- |
| 1 | `frontend/app/src/services/MockGameService.ts:462` | `_resolvePitch` | 266 lines, complexity 58 | Split by pitch outcome/result type and extract outcome tables |
| 2 | `frontend/app/src/services/MockGameService.ts:731` | `_applyOutcomeToGameState` | 118 lines, complexity 27 | Extract outcome-specific state reducers |
| 3 | `frontend/app/src/services/strategyEngine.ts:23` | `calculateStrategyAndIntent` | 225 lines, complexity 31 | Split by decision domain; name the callbacks at lines 114 and 177 |
| 4 | `frontend/app/src/services/HttpGameService.ts:149` | `ensureGamedayPacket` | 103 lines, complexity 23 | Extract validation and normalization helpers |
| 5 | `frontend/app/src/store/gameStore.ts:168` | Store creator callback | 380 lines, complexity 1 | Split the store into slices (game, UI, dev, calibration) and keep action names stable |
| 6 | `frontend/app/src/store/gameStore.ts:273` / `:303` | Duplicated `set()` callbacks in `pitch` and `simAtBat` | 12–14 lines each | Extract one `applyPitchResult` helper |
| 7 | `frontend/app/src/store/gameStore.ts:425` | `runFastCalibration` | 84 lines, complexity 12 | Extract the calibration loop and summary calculation |
| 8 | `backend/database/seed.py:47` | `run_seed` | 109 lines, complexity 19, churn 3 | Split by roster, lineup, and pitcher seeding; make helpers idempotent |
| 9 | `backend/api/routes.py:74` | `state` | 63 lines, complexity 12, churn 2 | Extract payload assembly from the route handler |
| 10 | `backend/engine/pitching_engine/pitch_objects.py:77` | `from_dict` | 34 lines, complexity 14 | Use the same typed parsing helpers as `Player.from_dict` |
| 11 | `backend/engine/pitching_engine/pitchers.py:64` | `get_adjusted_ratings` | 69 lines, complexity 10 | Extract fatigue/command adjustments into small pure functions |
| 12 | `backend/models/player.py:10` | `Player.__init__` | 12 parameters | Replace with a typed player record |
| 13 | `backend/engine/gameday_math.py:236` and `frontend/app/src/services/gamedayMath.ts:469` | `determine_situation_category` / `determineSituationCategory` | 6 parameters each, complexity 12 | Use a situation context object and keep backend/frontend formulas aligned |
| 14 | `backend/engine/pitching_engine/calculations.py:37` and `frontend/app/src/services/gamedayMath.ts:200` | `calculate_pitch_delivery` / `executeDelivery` | 6 parameters each | Introduce a delivery request object shared by both implementations |

### 2B — Production UI components

| # | Location | Issue | Metrics | Recommended refactor |
| --- | --- | --- | --- | --- |
| 1 | `frontend/app/src/components/ScorebugWidget.tsx:64` | `ScorebugWidget` | 241 lines, complexity 31 (file 623 lines) | Split into team, count, bases, and status subcomponents |
| 2 | `frontend/app/src/screens/BaseballSimScreen.tsx:33` | `BaseballSimScreen` | 154 lines, complexity 13 | Extract layout sections and move data preparation into hooks |
| 3 | `frontend/app/src/components/PitchSelectorWidget.tsx:213` | `ArsenalChip` | 111 lines, complexity 10 (file 522 lines) | Extract card primitives and pitch metadata formatting |
| 4 | `frontend/app/src/components/StrikeZoneGridWidget.tsx:49` / `:226` | `StrikeZoneGridWidget` / `InnerStrikeZone3x3` | 115/6 and 81/5 (file 581 lines) | Split rendering, gesture handling, and zone math |
| 5 | `frontend/app/src/components/PitchTrajectoryWidget.tsx:166` / `:76` / `:291` | Widget, `buildGeometry`, `PitcherFigure` | 122/3, 80/13, 92/1 | Separate geometry calculation from SVG rendering |
| 6 | `frontend/app/src/components/StrategyDeciderWidget.tsx:92` / `:21` | `PitchWeightCard`, parent widget | 69/12, 68/3 | Extract the weight controls and sliders |
| 7 | `frontend/app/src/components/ScoreboardControlsWidget.tsx:27` / `:100` | Widget and `pitchResultColor` | 72/10, 25/11 | Split controls from color mapping; share the color map with `PitchOutcomeFeedWidget` |
| 8 | `frontend/app/src/components/PitchOutcomeFeedWidget.tsx:89` | `resultBadgeColor` | 15 lines, duplicate | Reuse one shared `pitchResultColor` utility |
| 9 | `frontend/app/src/services/gamedayMath.ts:363` / `:433` | `getZoneNominalTarget`, `getPitchTypeColor` | 32/14, 19/13 | Replace lookup branches with tables |
| 10 | `frontend/app/src/components/SettingsMenuModal.tsx:32`, `LineupDialogWidget.tsx:27`, `RotationBullpenDialogWidget.tsx:25`, `StrategyMenuModal.tsx:16` | Dialog components | 146/5, 127/8, 141/10, 79/6 | Extract form sections and shared dialog primitives |

### Parity warning

`MockGameService` is a high-fidelity mirror of the Python engine. Refactor `_resolvePitch`, `_applyOutcomeToGameState`, and `strategyEngine` alongside the corresponding Python changes, and run parity tests at each step.

---

## Tier 3 — Debug surfaces and test harnesses

These are large or complex but have a much smaller production blast radius. Split them when the area is being changed, not before.

| # | Location | Issue | Metrics | Recommended refactor |
| --- | --- | --- | --- | --- |
| 1 | `frontend/app/src/components/debug/GamedayDevMenuModal.tsx:60` | `GamedayDevMenuModal` | 360 lines, complexity 33 (file 669 lines) | Split by dev tab/panel |
| 2 | `frontend/app/src/components/debug/GamedayVisualizerColumn.tsx:50` | `GamedayVisualizerColumn` | 268 lines, complexity 19 | Extract chart, controls, and payload formatting |
| 3 | `frontend/app/src/components/debug/CalibrationDiagnosticsColumn.tsx:28` | `CalibrationDiagnosticsColumn` | 204 lines, complexity 23 | Extract filters, metrics table, and baseline calculation |
| 4 | `frontend/app/src/components/debug/StrategyIngestColumn.tsx:16` | `StrategyIngestColumn` | 123 lines, complexity 12 | Extract payload parsing and rendering |
| 5 | `tests/test_at_bat.py:20`, `tests/test_statcast_engine.py:108` | `run_single_at_bat`, `run_all_tests` | 74/12, 72/6 | Use pytest fixtures and parameterization |

The debug menu is the largest UI component in the scan. It is still lower priority than the core engine because a regression there does not change game outcomes.

---

## Tier 4 — Cleanup and quick wins

### 4.1 Unused imports (33 findings, all safe-fixable)

These are mechanical and low risk. Use Refactor Radar's preview-first fix or "Apply All Safe Fixes in File", then run the tests.

| File | Lines | Unused names | Findings |
| --- | --- | --- | --- |
| `backend/engine/game_engine.py` | 7, 8, 9, 10, 11, 14, 25, 29, 40 | `os`, `sys`, `math`, `random`, `Tuple`; six `gameday_math` names in both import branches; `PitchStrategy` in both branches | 9 |
| `backend/engine/strike_zone.py` | 7, 9, 17 | `Dict`, `Optional`; `ZONE_X_MIN`, `ZONE_X_MAX`, `ZONE_Z_BOT`, `ZONE_Z_TOP` in both branches | 3 |
| `backend/engine/pitching_engine/calculations.py` | 7, 8, 9, 12, 24 | `math`, `random`, `Tuple`; `get_zone_nominal_target`, `determine_situation_category`, `ZONE_CENTERS` in both branches | 5 |
| `backend/engine/pitching_engine/engine.py` | 8, 12 | `dataclass`, `InGamePitcherRatings` | 2 |
| `backend/engine/pitching_engine/pitchers.py` | 8, 9 | `List`, `Optional`, `field` | 2 |
| `backend/engine/pitching_engine/strategy.py` | 8 | `Tuple` | 1 |
| `backend/engine/batter_strategy.py` | 8 | `Optional` | 1 |
| `backend/api/routes.py` | 7 | `Dict`, `Any` | 1 |
| `frontend/app/src/services/MockGameService.ts` | 9 | `BatterGameStats`, `PitchArsenalItem`, `PitchOptionWeight`, `Score`, `StatcastMetrics`, `TeamLineup`, `TeamRotation`, `ZoneOptionWeight` | 1 |
| `frontend/app/src/services/HttpGameService.ts` | 12 | `Gameday2DPitchPacket` | 1 |
| `frontend/app/src/store/gameStore.ts` | 11 | `SituationCategory` | 1 |
| `frontend/app/src/components/debug/CalibrationDiagnosticsColumn.tsx` | 3 | `SituationCategory` | 1 |
| `frontend/app/src/components/debug/GamedayDevMenuModal.tsx` | 14 | `DevTab` | 1 |
| `frontend/app/src/components/ErrorEnvelopeBanner.tsx` | 4 | `Colors` | 1 |
| `frontend/app/src/components/LineupDialogWidget.tsx` | 2 | `ScrollView` | 1 |
| `frontend/app/src/components/MatchupCardWidget.tsx` | 2 | `TouchableOpacity`, `ScrollView` | 1 |
| `frontend/app/src/components/PitchOutcomeFeedWidget.tsx` | 2 | `FlatList` | 1 |

The duplicate-looking backend entries are separate imports inside `try` / `except ImportError` fallback branches. Preview the file before applying, because both branches are rewritten.

### 4.2 Duplicated logic (4 findings, 2 pairs)

| Pair | Locations | Recommendation |
| --- | --- | --- |
| 1 | `PitchOutcomeFeedWidget.tsx:89` (`resultBadgeColor`) and `ScoreboardControlsWidget.tsx:100` (`pitchResultColor`) | Extract one shared result-color utility |
| 2 | `gameStore.ts:273` and `gameStore.ts:303` (the `set()` callbacks in `pitch` and `simAtBat`) | Extract one `applyPitchResult` helper |

### 4.3 Parameter-heavy functions (10 findings)

| Function | Location | Parameters | Suggested shape |
| --- | --- | --- | --- |
| `Player.__init__` | `backend/models/player.py:10` | 12 | `PlayerRecord` |
| `execute_pitch` | `backend/engine/pitching_engine/engine.py:63` | 11 | `PitchRequest` |
| `add_player` | `backend/database/db.py:107` | 10 | `PlayerRecord` |
| `choose_pitch` | `backend/engine/pitching_engine/strategy.py:36` | 6 | `PitchChoiceContext` |
| `decide_swing` | `backend/engine/batter_strategy.py:52` | 6 | `SwingContext` |
| `determine_situation_category` | `backend/engine/gameday_math.py:236` | 6 | `SituationContext` |
| `determineSituationCategory` | `frontend/app/src/services/gamedayMath.ts:469` | 6 | `SituationContext` |
| `calculate_pitch_delivery` | `backend/engine/pitching_engine/calculations.py:37` | 6 | `DeliveryRequest` |
| `executeDelivery` | `frontend/app/src/services/gamedayMath.ts:200` | 6 | `DeliveryRequest` |
| `calculatePitchPoint` | `frontend/app/src/services/pitchTrajectory.ts:67` | 6 | `TrajectoryRequest` |

### 4.4 Broad exceptions (3 findings)

| Location | Recommendation |
| --- | --- |
| `backend/database/seed.py:32` | Catch the specific database/file exceptions that can be recovered from |
| `tests/test_pitching_engine.py:209` | Narrow the expected exception or use `pytest.raises` |
| `tests/test_player_hydration.py:156` | Narrow the expected exception |

### 4.5 Large files (7 findings)

| File | Lines | Resolution |
| --- | --- | --- |
| `frontend/app/src/services/MockGameService.ts` | 870 | Resolved by the Tier 2A splits |
| `backend/engine/game_engine.py` | 811 | Resolved by the Tier 1 splits |
| `frontend/app/src/components/debug/GamedayDevMenuModal.tsx` | 669 | Resolved by the Tier 3 split |
| `frontend/app/src/components/ScorebugWidget.tsx` | 623 | Resolved by the Tier 2B split |
| `frontend/app/src/components/StrikeZoneGridWidget.tsx` | 581 | Resolved by the Tier 2B split |
| `frontend/app/src/store/gameStore.ts` | 563 | Resolved by store slices |
| `frontend/app/src/components/PitchSelectorWidget.tsx` | 522 | Resolved by the Tier 2B split |

### 4.6 Explicit `any` usage (3 findings)

| Location | Count | Recommendation |
| --- | --- | --- |
| `frontend/app/src/services/HttpGameService.ts:158` | 1 | Replace with `unknown` plus a narrowing guard |
| `frontend/app/src/services/MockGameService.ts:586` | 2 | Use the domain types already imported/declared nearby |
| `frontend/app/src/services/strategyEngine.ts:208` | 2 | Use a generic or a discriminated union for the strategy payload |

---

## Recommended execution order

1. **Baseline:** run the test suite and keep the current Refactor Radar report. Add characterization tests around `pitch`, `calculate_strategy_and_intent`, `choose_pitch`, and `Player.from_dict` before changing them.
2. **Tier 1:** refactor `pitch` and `calculate_strategy_and_intent` first, then `Player.from_dict`, `choose_pitch`, the batter strategy pair, `execute_pitch`, and `add_player`.
3. **Tier 2A:** update `MockGameService` and `strategyEngine` in parity with the Tier 1 changes; then split the game store slices and the HTTP normalization path.
4. **Tier 2B:** split the large production UI components, sharing the result-color utility and other duplicated presentation helpers.
5. **Tier 3:** split debug surfaces and test harnesses when those files are next touched.
6. **Tier 4:** batch the unused imports, then address duplicates, parameter objects, broad exceptions, and `any` usage opportunistically.
7. **Re-scan:** compare high-severity findings, function lengths, and complexity against this baseline.

## Verification and targets

Run the existing suites after each item:

```bash
./run_tests.sh
# or
pytest -n auto tests/
```

Suggested Refactor Radar targets after Tier 1 and Tier 2A:

- High-severity findings reduced from 30 to fewer than 10.
- No high-severity findings in `game_engine.py`, `player.py`, `strategy.py`, `batter_strategy.py`, or `MockGameService.ts`.
- `pitch` below 100 lines and complexity below 20.
- `calculate_strategy_and_intent` complexity below 25.
- `_resolvePitch` complexity below 20.
- Zero unused imports.
- No regression in backend/mock parity tests.

## Caveats

- Complexity is a proxy, not a goal by itself. Split functions only where the responsibilities are genuinely separable.
- Keep public APIs stable. If a signature must change, add a thin wrapper and migrate call sites separately.
- Debug and test code is deliberately lower priority; a regression there is easier to contain than one in the pitch or strategy engines.
- The scan is a snapshot. Run Refactor Radar again after each tier and update this document rather than treating the current numbers as fixed.
