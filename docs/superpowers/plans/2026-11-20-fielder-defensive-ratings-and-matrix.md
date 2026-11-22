# Fielder Defensive Ratings & Positional Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the granular (0–99) defensive ratings architecture across Tracking, Glove, Throwing, and Mental categories on the `Player` domain model, along with the positional weight matrix, minimum gate penalties, experience scaling, and database hydration, verified through a single consolidated test suite.

**Architecture:**
1. Equip the authoritative `Player` domain model with 10 granular defensive ratings (0–99) and kinematic conversion helpers that map rating values into physical simulation constants (seconds, ft/s, feet, mph).
2. Build the Positional Matrix & Gate Engine calculating composite and current positional ratings for all 7 standard non-battery positions (SS, 2B, 3B, 1B, CF, RF, LF) with gate failure penalties and a 200-game experience curve.
3. Integrate serialization (`to_dict`), universal hydration (`from_dict`), height parsing from vitals for the 1B gate, and pre-warmed database hydration in `roster_store.py`.
4. Consolidate all unit tests into a single comprehensive test module: `tests/engine/batting_engine/test_player_fielding.py`.

**Tech Stack:** Python 3.13, pytest, `Player` domain model in `backend/engine/models/player.py`, `backend/database/roster_store.py`.

**Spec:** Section 2 of [`docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md`](file:///home/swadaddy4life/Documents/dev-projects/baseball/docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md)

---

## Global Constraints

- Python standard library only (`math`, `typing`, `dataclasses`). No external dependencies.
- Defensive rating keys: `reaction`, `route_efficiency`, `range`, `fielding`, `transfer_speed`, `arm_strength`, `arm_accuracy`, `body_control`, `positioning`, `baseball_iq`.
- Ratings scale: 0.0 to 99.0, clamped.
- Default baseline rating for unseeded defensive attributes: 65.0.
- All new tests for this feature must reside in the single consolidated test file: `tests/engine/batting_engine/test_player_fielding.py`.

## Review Focus

1. **Vitals Height Parsing for 1B Gate:** Player vitals may store height as `"6'2\""`, `"6-2"`, or integer inches (`74`). Parsing must safely resolve height in inches without crashing on missing or malformed vitals.
2. **Clamping Output Bounds:** Ratings calculated through weights, penalties, and experience must be strictly clamped to `[1.0, 99.0]`.
3. **Missing Attribute Resilience:** `get_defensive_rating()` must safely return the default (65.0) for any rating key omitted from the player's ratings dict.
4. **Zero-Experience Floor:** A player with 0 games of experience must receive exactly $65\%$ of their post-penalty composite rating.
5. **Serialization Round-Trip Integrity:** `Player.from_dict(player.to_dict())` must preserve all 10 defensive ratings exactly.

---

### Task 1: Granular Defensive Ratings on `Player` & Kinematic Helpers

**Files:**
- Modify: `backend/engine/models/player.py:40-75, 360-400`
- Test: `tests/engine/batting_engine/test_player_fielding.py`

**Interfaces:**
- Consumes: `Player.__init__`, `self.ratings`.
- Produces:
  - `DEFAULT_DEFENSIVE_RATINGS: Dict[str, float]`
  - `DEFENSIVE_RATING_KEYS: Tuple[str, ...]`
  - `Player.get_defensive_rating(self, key: str) -> float`
  - `Player.get_reaction_time_s(self) -> float`
  - `Player.get_sprint_speed_fps(self) -> float`
  - `Player.get_route_efficiency(self) -> float`
  - `Player.get_glove_radius_ft(self) -> float`
  - `Player.get_transfer_time_s(self) -> float`
  - `Player.get_throw_speed_mph(self) -> float`

- [ ] **Step 1: Write failing tests in `tests/engine/batting_engine/test_player_fielding.py` for granular ratings and kinematic helpers**

```python
# tests/engine/batting_engine/test_player_fielding.py
import pytest
from backend.engine.models.player import (
    Player,
    DEFAULT_DEFENSIVE_RATINGS,
    DEFENSIVE_RATING_KEYS,
)

def test_defensive_keys_defined():
    expected_keys = {
        "reaction", "route_efficiency", "range",
        "fielding", "transfer_speed",
        "arm_strength", "arm_accuracy", "body_control",
        "positioning", "baseball_iq",
    }
    assert set(DEFENSIVE_RATING_KEYS) == expected_keys
    for k in expected_keys:
        assert k in DEFAULT_DEFENSIVE_RATINGS
        assert DEFAULT_DEFENSIVE_RATINGS[k] == 65.0

def test_get_defensive_rating_fallback():
    p = Player(name="Bare Player")
    assert p.get_defensive_rating("range") == 65.0
    assert p.get_defensive_rating("reaction") == 65.0

def test_get_defensive_rating_explicit():
    p = Player(name="Speedster", ratings={"range": 95.0, "reaction": 82.0})
    assert p.get_defensive_rating("range") == 95.0
    assert p.get_defensive_rating("reaction") == 82.0
    assert p.get_defensive_rating("arm_strength") == 65.0

def test_kinematic_conversion_helpers():
    # Elite defender (all 99)
    elite = Player(name="Elite", ratings={k: 99.0 for k in DEFENSIVE_RATING_KEYS})
    assert elite.get_reaction_time_s() == pytest.approx(0.45 - (99.0 / 100.0) * 0.25, abs=1e-3) # ~0.2025s
    assert elite.get_sprint_speed_fps() == pytest.approx(22.0 + (99.0 / 100.0) * 8.5, abs=1e-3) # ~30.415 ft/s
    assert elite.get_route_efficiency() == pytest.approx(0.85 + (99.0 / 100.0) * 0.15, abs=1e-3) # ~0.9985
    assert elite.get_glove_radius_ft() == pytest.approx(3.2 + (99.0 / 100.0) * 2.3, abs=1e-3)   # ~5.477 ft
    assert elite.get_transfer_time_s() == pytest.approx(0.85 - (99.0 / 100.0) * 0.40, abs=1e-3) # ~0.454s
    assert elite.get_throw_speed_mph() == pytest.approx(70.0 + (99.0 / 100.0) * 32.0, abs=1e-3) # ~101.68 mph

    # Poor defender (all 0)
    poor = Player(name="Poor", ratings={k: 0.0 for k in DEFENSIVE_RATING_KEYS})
    assert poor.get_reaction_time_s() == pytest.approx(0.45, abs=1e-3)
    assert poor.get_sprint_speed_fps() == pytest.approx(22.0, abs=1e-3)
    assert poor.get_route_efficiency() == pytest.approx(0.85, abs=1e-3)
    assert poor.get_glove_radius_ft() == pytest.approx(3.2, abs=1e-3)
    assert poor.get_transfer_time_s() == pytest.approx(0.85, abs=1e-3)
    assert poor.get_throw_speed_mph() == pytest.approx(70.0, abs=1e-3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/batting_engine/test_player_fielding.py -v`  
Expected: FAIL with `ImportError: cannot import name 'DEFAULT_DEFENSIVE_RATINGS'`

- [ ] **Step 3: Implement constants and kinematic helpers in `backend/engine/models/player.py`**

In `backend/engine/models/player.py`:
- Add `DEFENSIVE_RATING_KEYS` tuple and `DEFAULT_DEFENSIVE_RATINGS` dictionary.
- Add `get_defensive_rating(self, key: str) -> float` querying `self.ratings` with fallback to `DEFAULT_DEFENSIVE_RATINGS`.
- Add `get_reaction_time_s`, `get_sprint_speed_fps`, `get_route_efficiency`, `get_glove_radius_ft`, `get_transfer_time_s`, `get_throw_speed_mph` using the exact spec conversion formulas.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/batting_engine/test_player_fielding.py -v`  
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/models/player.py tests/engine/batting_engine/test_player_fielding.py
git commit -m "feat(player): add granular defensive ratings and kinematic physical helpers"
```

---

### Task 2: Positional Weight Matrix, Minimum Gates, & Experience Engine

**Files:**
- Modify: `backend/engine/models/player.py:400-470`
- Modify: `tests/engine/batting_engine/test_player_fielding.py`

**Interfaces:**
- Consumes: `Player.get_defensive_rating()`, `Player.vitals`.
- Produces:
  - `POSITION_WEIGHTS: Dict[str, Dict[str, float]]`
  - `POSITION_GATES: Dict[str, List[Dict[str, Any]]]`
  - `Player.get_height_inches(self) -> Optional[int]`
  - `Player.check_position_gates(self, position: str) -> Tuple[bool, float, List[str]]`
  - `Player.calculate_position_rating(self, position: str, games_at_position: int = 200) -> float`

- [ ] **Step 1: Append failing tests in `tests/engine/batting_engine/test_player_fielding.py` for weight matrix, gates, height parsing, and experience**

```python
# Append to tests/engine/batting_engine/test_player_fielding.py
from backend.engine.models.player import (
    POSITION_WEIGHTS,
    POSITION_GATES,
)

def test_position_weights_sum_to_one():
    for pos, weights in POSITION_WEIGHTS.items():
        assert sum(weights.values()) == pytest.approx(1.0, abs=1e-4), f"{pos} weights do not sum to 1.0"

def test_height_inches_parsing():
    assert Player(name="P1", vitals={"height": "6'2\""}).get_height_inches() == 74
    assert Player(name="P2", vitals={"height": "6-4"}).get_height_inches() == 76
    assert Player(name="P3", vitals={"height": 72}).get_height_inches() == 72
    assert Player(name="P4", vitals={"height": "75"}).get_height_inches() == 75
    assert Player(name="P5", vitals={}).get_height_inches() is None

def test_ss_gates():
    # SS requires Range >= 60 (-15) and Arm >= 55 (-15)
    ss = Player(name="Shortstop", ratings={"range": 55.0, "arm_strength": 50.0})
    passed, penalty, reasons = ss.check_position_gates("SS")
    assert passed is False
    assert penalty == 30.0
    assert len(reasons) == 2

def test_1b_height_or_fielding_gate():
    # 1B requires Height >= 74 inches OR Fielding >= 65 (-10)
    p1 = Player(name="Tall 1B", vitals={"height": "6'3\""}, ratings={"fielding": 50.0})
    passed, penalty, _ = p1.check_position_gates("1B")
    assert passed is True
    assert penalty == 0.0

    p2 = Player(name="Short 1B", vitals={"height": "5'10\""}, ratings={"fielding": 75.0})
    passed, penalty, _ = p2.check_position_gates("1B")
    assert passed is True
    assert penalty == 0.0

    p3 = Player(name="Unfit 1B", vitals={"height": "5'10\""}, ratings={"fielding": 50.0})
    passed, penalty, reasons = p3.check_position_gates("1B")
    assert passed is False
    assert penalty == 10.0

def test_cf_gate_and_full_score():
    # CF requires Range >= 65 (-20)
    cf = Player(
        name="Speedy CF",
        position="CF",
        ratings={
            "range": 80.0,
            "reaction": 75.0,
            "route_efficiency": 85.0,
            "arm_strength": 70.0,
            "arm_accuracy": 70.0,
            "fielding": 75.0,
        }
    )
    score = cf.calculate_position_rating("CF", games_at_position=200)
    assert score == pytest.approx(78.4, abs=0.1)

    rookie_score = cf.calculate_position_rating("CF", games_at_position=0)
    assert rookie_score == pytest.approx(78.35 * 0.65, abs=0.1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/batting_engine/test_player_fielding.py::test_position_weights_sum_to_one -v`  
Expected: FAIL with `ImportError: cannot import name 'POSITION_WEIGHTS'`

- [ ] **Step 3: Implement matrix, gates, height parser, and position rating formula in `backend/engine/models/player.py`**

In `backend/engine/models/player.py`:
- Define `POSITION_WEIGHTS` matching the 7 positions verbatim from the spec.
- Define `POSITION_GATES`:
  - `SS`: `[("range", 60.0, 15.0), ("arm_strength", 55.0, 15.0)]`
  - `2B`: `[("range", 50.0, 10.0)]`
  - `3B`: `[("arm_strength", 60.0, 15.0)]`
  - `1B`: custom rule: height $\ge 74$ inches OR `fielding` $\ge 65.0$ (penalty: 10.0)
  - `CF`: `[("range", 65.0, 20.0)]`
  - `RF`: `[("arm_strength", 55.0, 10.0)]`
  - `LF`: `[]`
- Implement `get_height_inches(self) -> Optional[int]` parsing `vitals.get("height")` (`6'2"`, `6-2`, integer).
- Implement `check_position_gates(self, position: str) -> Tuple[bool, float, List[str]]`.
- Implement `calculate_position_rating(self, position: str, games_at_position: int = 200) -> float` with clamping to `[1.0, 99.0]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/batting_engine/test_player_fielding.py -v`  
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/models/player.py tests/engine/batting_engine/test_player_fielding.py
git commit -m "feat(player): implement position weight matrix, minimum gates, and experience multiplier"
```

---

### Task 3: Roster Hydration, Serialization, & Database Integration

**Files:**
- Modify: `backend/engine/models/player.py:180-230, 325-360`
- Modify: `backend/database/roster_store.py:205-235`
- Modify: `tests/engine/batting_engine/test_player_fielding.py`

**Interfaces:**
- Consumes: `Player.from_dict`, `Player.to_dict`, `roster_store.py`.
- Produces:
  - Clean serialization of defensive ratings in `Player.to_dict()`.
  - Position-tailored defensive defaults in `roster_store.py` during player hydration.

- [ ] **Step 1: Append failing tests in `tests/engine/batting_engine/test_player_fielding.py` for serialization round-trip and roster hydration**

```python
# Append to tests/engine/batting_engine/test_player_fielding.py
from backend.database.roster_store import RosterStore

def test_player_serialization_round_trip():
    initial = Player(
        name="Mookie Betts",
        position="RF",
        ratings={
            "range": 88.0,
            "reaction": 92.0,
            "route_efficiency": 90.0,
            "arm_strength": 85.0,
            "fielding": 95.0,
            "transfer_speed": 88.0,
            "arm_accuracy": 82.0,
            "body_control": 90.0,
            "positioning": 85.0,
            "baseball_iq": 94.0,
        }
    )
    d = initial.to_dict()
    hydrated = Player.from_dict(d)
    for k in DEFENSIVE_RATING_KEYS:
        assert hydrated.get_defensive_rating(k) == initial.get_defensive_rating(k)

def test_roster_store_hydrates_position_players_with_defensive_ratings():
    store = RosterStore()
    store.warmup(force=True)
    teams = store.get_all_teams()
    assert len(teams) > 0
    first_team = teams[0]
    roster = store.get_team_roster(first_team["abbr"])
    position_players = [p for p in roster.get("hitters", []) or roster.get("position_players", []) if not p.is_pitcher]
    if position_players:
        p = position_players[0]
        assert p.get_defensive_rating("range") > 0.0
        assert p.get_defensive_rating("reaction") > 0.0
        assert p.get_defensive_rating("fielding") > 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/batting_engine/test_player_fielding.py::test_player_serialization_round_trip -v`  
Expected: FAIL if serialization or hydration drops ratings keys

- [ ] **Step 3: Update `to_dict`, `from_dict`, and `roster_store.py`**

In `backend/engine/models/player.py`:
- In `to_dict()`, ensure `self.ratings` dict contains all hydrated defensive ratings.
- In `from_dict()`, normalize and preserve defensive rating keys from incoming `ratings` maps.
In `backend/database/roster_store.py`:
- In `_load_team_players()`, populate position players' ratings dictionary with baseline defensive ratings derived from their position archetype.

- [ ] **Step 4: Run consolidated test module to verify it passes**

Run: `pytest tests/engine/batting_engine/test_player_fielding.py -v`  
Expected: PASS (11 passed)

- [ ] **Step 5: Run full test suite to guarantee zero regressions**

Run: `pytest tests/engine/ -v`  
Expected: ALL PASS with 0 failures

- [ ] **Step 6: Commit**

```bash
git add backend/engine/models/player.py backend/database/roster_store.py tests/engine/batting_engine/test_player_fielding.py
git commit -m "feat(roster): support defensive ratings in Player serialization and database hydration"
```

---

## Execution Handoff

Plan complete and saved to [`docs/superpowers/plans/2026-11-20-fielder-defensive-ratings-and-matrix.md`](file:///home/swadaddy4life/Documents/dev-projects/baseball/docs/superpowers/plans/2026-11-20-fielder-defensive-ratings-and-matrix.md).

All tests are now consolidated into a single dedicated test file:
`tests/engine/batting_engine/test_player_fielding.py`.

Shall I begin executing Task 1?

