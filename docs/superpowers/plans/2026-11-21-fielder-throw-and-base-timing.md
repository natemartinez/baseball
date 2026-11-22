# Fielder Throw Kinematics & Base Runner Timing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement physical glove-to-hand transfer delays, 3D aerodynamic throw flight trajectories to bases, batter-runner sprint kinematics, and authoritative out/safe clock comparisons to resolve infield groundouts vs. infield singles.

**Architecture:**
1. A throw kinematic solver (`fielder_throw.py`) models glove-to-hand transfer ($t_{\text{transfer}} \in [0.45\text{s}, 0.85\text{s}]$) with recovery penalties for diving/sliding stops, calculates throw flight trajectories ($v_{\text{throw}} \in [70, 102\text{ mph}]$) to base targets with angular dispersion, and handles 1B unassisted bag steps.
2. A runner sprint timing model (`runner_timing.py`) computes home-to-first sprint times ($t_{\text{home\_to\_first}} \in [3.95\text{s}, 4.85\text{s}]$) based on speed rating and batter handedness.
3. The contact outcome pipeline (`contact_outcome.py`) evaluates $t_{\text{ball\_at\_1B}}$ vs. $t_{\text{runner\_at\_1B}}$, turning beat-the-throw plays into authentic infield singles while populating rich `throw` telemetry samples `[x, y, z, t]`.

**Tech Stack:** Python 3.13, pytest, dataclasses, existing `ActiveDefense` and `Player` defensive rating models.

**Spec:** [`docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md`](file:///home/swadaddy4life/Documents/dev-projects/baseball/docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md)

---

## Global Constraints

- Python standard library only (`math`, `typing`, `dataclasses`, `random`). No external physics engines.
- First base target coordinate is pinned to $(x_{\text{1B}}, y_{\text{1B}}, z_{\text{1B}}) = (63.64, 63.64, 3.0)\text{ ft}$.
- Transfer time must adhere to $t_{\text{transfer}} = 0.85 - (\text{transfer\_speed} / 100) \times 0.40\text{s}$ with off-balance recovery penalties for sliding/diving stops.
- Throw velocity must adhere to $v_{\text{throw}} = 70.0 + (\text{arm\_strength} / 100) \times 32.0\text{ mph}$.
- Home-to-first sprint time must adhere to $t = 4.85 - (\text{speed} / 100) \times 0.85\text{s}$ with a $-0.08\text{s}$ bonus for left-handed batters.
- Bounded throw trajectory `samples` must contain exactly 10 monotonic 4D points `[x, y, z, t]` spanning from throw release $(t_{\text{intercept}} + t_{\text{transfer}})$ to arrival at the target base bag.
- `resolve_contact_outcome` must remain 100% backward-compatible with all existing callers and default to `ActiveDefense.default()`.

---

## Review Focus

1. **1B Unassisted Step:** When 1B fields a ground ball within $12\text{ ft}$ of first base, 1B must step directly on the bag (`is_unassisted = True`) without throwing to themselves. (Tested in Task 1, Step 1).
2. **Diving/Sliding Catch Recovery Penalty:** Fielders making a `DIVING_CATCH` or `SLIDING_CATCH` must take an extra pop-up/recovery delay before releasing the throw, scaled by $(1.0 - \text{body\_control} / 150.0)$. (Tested in Task 1, Step 1).
3. **Elite Speed Beat-The-Throw Infield Single:** A slow roller fielded deep by 3B must produce an `IN_PLAY_OUT` for a slow runner (speed 25) but an infield `SINGLE` for an elite sprinter (speed 95). (Tested in Task 3, Step 1).
4. **Pitcher Comebacker Flip:** A 100-mph line drive or grounder deflected back to the pitcher at $(0.0, 55.0)$ must compute a stable throw across the $60\text{ ft}$ diagonal to 1B without numerical instability. (Tested in Task 2, Step 1).
5. **Strict Monotonic Space-Time Samples:** All 10 coordinates in `throw.samples` must have strictly non-decreasing timestamps starting at $t \ge t_{\text{intercept}} + t_{\text{transfer}}$. (Tested in Task 1, Step 1).

---

### Task 1: Fielder Throw Kinematics & 3D Flight Solver

**Files:**
- Create: `backend/engine/game_engine/physics/fielder_throw.py`
- Test: `tests/engine/game_engine/test_fielder_throw.py`

**Interfaces:**
- Consumes: `Player` from `backend.engine.models.player`, `ActiveDefense` from `backend.engine.game_engine.defense`.
- Produces:
  - `BASE_COORDINATES: Dict[str, Tuple[float, float, float]]`
  - `ThrowResult(thrower_id, target_base, start_pos, target_pos, transfer_time_s, throw_flight_time_s, throw_start_time_s, ball_arrival_time_s, throw_distance_ft, throw_velocity_mph, offline_distance_ft, is_unassisted, samples)`
  - `calculate_transfer_time(transfer_speed: float, fielding_type: str, body_control: float) -> float`
  - `solve_fielder_throw(fielder_id: str, intercept_x: float, intercept_y: float, intercept_z: float, t_intercept: float, arm_strength: float, arm_accuracy: float, transfer_speed: float, body_control: float, fielding_type: str = "GROUND_SCOOP", target_base: str = "1B", sprint_speed: float = 27.0) -> ThrowResult`

- [ ] **Step 1: Write failing tests for transfer time, throw kinematics, 1B unassisted, and throw trajectory samples**

```python
# tests/engine/game_engine/test_fielder_throw.py
import pytest
import math
from backend.engine.game_engine.physics.fielder_throw import (
    BASE_COORDINATES,
    ThrowResult,
    calculate_transfer_time,
    solve_fielder_throw,
)

def test_base_coordinates_match_standard_diamond():
    assert BASE_COORDINATES["HOME"] == (0.0, 0.0, 0.0)
    assert BASE_COORDINATES["1B"] == (63.64, 63.64, 3.0)
    assert BASE_COORDINATES["2B"] == (0.0, 127.28, 3.0)
    assert BASE_COORDINATES["3B"] == (-63.64, 63.64, 3.0)

def test_transfer_time_with_fielding_type_and_body_control():
    # Routine ground scoop with 50 transfer speed: 0.85 - 0.50 * 0.40 = 0.65s
    t_routine = calculate_transfer_time(50.0, fielding_type="GROUND_SCOOP", body_control=65.0)
    assert pytest.approx(t_routine, abs=1e-3) == 0.650

    # Elite transfer speed (100) -> 0.45s
    t_elite = calculate_transfer_time(100.0, fielding_type="GROUND_SCOOP", body_control=80.0)
    assert pytest.approx(t_elite, abs=1e-3) == 0.450

    # Diving stop has recovery penalty
    t_dive = calculate_transfer_time(50.0, fielding_type="DIVING_CATCH", body_control=50.0)
    assert t_dive > t_routine

def test_1b_unassisted_step_when_within_12_ft():
    # 1B fields ball at (60.0, 60.0), which is ~5.1 ft from 1B bag (63.64, 63.64)
    res = solve_fielder_throw(
        fielder_id="1B",
        intercept_x=60.0,
        intercept_y=60.0,
        intercept_z=0.0,
        t_intercept=1.80,
        arm_strength=65.0,
        arm_accuracy=65.0,
        transfer_speed=65.0,
        body_control=65.0,
        fielding_type="GROUND_SCOOP",
        target_base="1B",
        sprint_speed=26.0,
    )
    assert res.is_unassisted is True
    assert res.throw_distance_ft < 12.0
    assert res.ball_arrival_time_s > 1.80
    assert len(res.samples) == 10
    assert res.samples[-1][0] == pytest.approx(63.64, abs=0.1)

def test_ss_deep_throw_to_1b_kinematics_and_monotonic_samples():
    # SS fields deep in hole at (-55.0, 125.0) at t=2.1s
    res = solve_fielder_throw(
        fielder_id="SS",
        intercept_x=-55.0,
        intercept_y=125.0,
        intercept_z=0.0,
        t_intercept=2.10,
        arm_strength=90.0,  # ~98.8 mph throw
        arm_accuracy=85.0,
        transfer_speed=80.0,
        body_control=80.0,
        fielding_type="GROUND_SCOOP",
        target_base="1B",
    )
    assert res.is_unassisted is False
    assert res.throw_distance_ft > 130.0
    assert res.throw_velocity_mph >= 95.0
    assert res.ball_arrival_time_s > res.throw_start_time_s
    assert len(res.samples) == 10

    # Verify strict monotonic timestamps
    timestamps = [s[3] for s in res.samples]
    for i in range(len(timestamps) - 1):
        assert timestamps[i + 1] >= timestamps[i]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/game_engine/test_fielder_throw.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.engine.game_engine.physics.fielder_throw'`

- [ ] **Step 3: Implement `fielder_throw.py`**

In `backend/engine/game_engine/physics/fielder_throw.py`:
- Define `BASE_COORDINATES` with 3D tuples for `HOME`, `1B`, `2B`, `3B`.
- Implement dataclass `ThrowResult`.
- Implement `calculate_transfer_time(transfer_speed, fielding_type, body_control)` applying base $0.85 - (\text{transfer\_speed} / 100) \times 0.40$ and extra recovery delays for `DIVING_CATCH` ($+0.50 \times (1.0 - \text{body\_control} / 150.0)$), `SLIDING_CATCH`, and `BACKHAND_PICK` ($+0.20 \times (1.0 - \text{body\_control} / 150.0)$).
- Implement `solve_fielder_throw`:
  - Calculate distance to target base $d = \operatorname{hypot}(x_{\text{target}} - x, y_{\text{target}} - y)$.
  - If `fielder_id == "1B"` and $d \le 12.0\text{ ft}$: set `is_unassisted = True`, sprint to bag $t_{\text{step}} = d / v_{\text{sprint}}$, $t_{\text{ball\_at\_base}} = t_{\text{intercept}} + t_{\text{step}}$.
  - Otherwise: $v_{\text{throw}} = 70.0 + (\text{arm\_strength} / 100) \times 32.0\text{ mph}$, $t_{\text{flight}} = d / (v_{\text{throw}} \times 1.46667 \times 0.95)$, $t_{\text{throw\_start}} = t_{\text{intercept}} + t_{\text{transfer}}$, $t_{\text{ball\_at\_base}} = t_{\text{throw\_start}} + t_{\text{flight}}$.
  - Calculate offline dispersion distance $\Delta r = d \times \tan(\operatorname{radians}(\sigma_\theta))$.
  - Generate 10 evenly spaced 4D samples $[x, y, z, t]$ with parabolic arc height $z(t)$ peaking at $+1.5\text{ ft}$ midpoint.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/game_engine/test_fielder_throw.py -v`  
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/game_engine/physics/fielder_throw.py tests/engine/game_engine/test_fielder_throw.py
git commit -m "feat(physics): implement fielder transfer delays and 3D throw flight kinematics"
```

---

### Task 2: Batter-Runner Sprint Kinematics & Out/Safe Resolution

**Files:**
- Create: `backend/engine/game_engine/physics/runner_timing.py`
- Test: `tests/engine/game_engine/test_runner_timing.py`

**Interfaces:**
- Consumes: `ThrowResult` from `backend.engine.game_engine.physics.fielder_throw`.
- Produces:
  - `BasePlayResult(is_out, is_close_play, margin_s, ball_arrival_time_s, runner_arrival_time_s, call, description)`
  - `calculate_home_to_first_time(speed_rating: float, is_left_handed: bool = False, exit_velocity_mph: float = 95.0) -> float`
  - `resolve_play_at_base(throw: ThrowResult, runner_arrival_time_s: float) -> BasePlayResult`

- [ ] **Step 1: Write failing tests for runner sprint times, pitcher comebacker, and base clock comparison**

```python
# tests/engine/game_engine/test_runner_timing.py
import pytest
from backend.engine.game_engine.physics.fielder_throw import solve_fielder_throw
from backend.engine.game_engine.physics.runner_timing import (
    BasePlayResult,
    calculate_home_to_first_time,
    resolve_play_at_base,
)

def test_home_to_first_sprint_timing_scaling():
    # Elite speed (100) right-handed: ~4.00s
    t_elite_rhb = calculate_home_to_first_time(100.0, is_left_handed=False)
    assert pytest.approx(t_elite_rhb, abs=0.05) == 4.00

    # Elite speed (100) left-handed (-0.08s box advantage): ~3.92s
    t_elite_lhb = calculate_home_to_first_time(100.0, is_left_handed=True)
    assert t_elite_lhb < t_elite_rhb

    # Average speed (65): ~4.30s
    t_avg = calculate_home_to_first_time(65.0, is_left_handed=False)
    assert 4.25 <= t_avg <= 4.35

    # Slow speed (20): ~4.68s
    t_slow = calculate_home_to_first_time(20.0, is_left_handed=False)
    assert t_slow > 4.60

def test_resolve_play_at_base_out_vs_safe():
    # Ball arrives at 3.90s, Runner arrives at 4.20s -> OUT by 0.30s
    throw = solve_fielder_throw("SS", -45.0, 115.0, 0.0, 2.0, 80.0, 80.0, 75.0, 75.0)
    res_out = resolve_play_at_base(throw, runner_arrival_time_s=throw.ball_arrival_time_s + 0.30)
    assert res_out.is_out is True
    assert res_out.call == "OUT"
    assert res_out.margin_s == pytest.approx(-0.30, abs=0.01)

    # Ball arrives at 4.20s, Runner arrives at 4.05s -> SAFE by 0.15s
    res_safe = resolve_play_at_base(throw, runner_arrival_time_s=throw.ball_arrival_time_s - 0.15)
    assert res_safe.is_out is False
    assert res_safe.call == "SAFE"
    assert res_safe.margin_s == pytest.approx(0.15, abs=0.01)
    assert res_safe.is_close_play is True

def test_pitcher_comebacker_timing():
    # Pitcher fields comebacker at (0.0, 55.0) at t=0.55s
    throw = solve_fielder_throw("P", 0.0, 55.0, 1.5, 0.55, 75.0, 75.0, 75.0, 75.0)
    runner_t = calculate_home_to_first_time(60.0)
    play = resolve_play_at_base(throw, runner_t)
    assert throw.throw_distance_ft > 60.0
    assert play.is_out is True
    assert play.margin_s < -0.80  # Out by a wide margin on routine comebacker
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/game_engine/test_runner_timing.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.engine.game_engine.physics.runner_timing'`

- [ ] **Step 3: Implement `runner_timing.py`**

In `backend/engine/game_engine/physics/runner_timing.py`:
- Define `BasePlayResult` dataclass.
- Implement `calculate_home_to_first_time(speed_rating: float, is_left_handed: bool = False, exit_velocity_mph: float = 95.0) -> float`:
  - Calculate $t = 4.85 - (\text{speed\_rating} / 100.0) \times 0.85$.
  - If `is_left_handed`, subtract $0.08\text{s}$.
  - If $v_{\text{ev}} \ge 100.0\text{ mph}$, add $+0.04\text{s}$ (hard swing delay); if $v_{\text{ev}} \le 75.0\text{ mph}$, subtract $-0.04\text{s}$ (bunt/tap momentum).
  - Return `round(t, 3)`.
- Implement `resolve_play_at_base(throw: ThrowResult, runner_arrival_time_s: float) -> BasePlayResult`:
  - $\text{margin} = \text{round}(\text{throw.ball\_arrival\_time\_s} - \text{runner\_arrival\_time\_s}, 3)$.
  - If $\text{margin} \le 0.0$: `is_out = True`, `call = "OUT"`.
  - Else: `is_out = False`, `call = "SAFE"`.
  - `is_close_play = abs(margin) <= 0.15`.
  - Build natural description detailing out/safe margin and close play indicator.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/game_engine/test_runner_timing.py -v`  
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/game_engine/physics/runner_timing.py tests/engine/game_engine/test_runner_timing.py
git commit -m "feat(physics): implement batter-runner sprint model and out-safe base play clock"
```

---

### Task 3: Integration with Contact Outcome, Engine Pipeline, and Telemetry

**Files:**
- Modify: `backend/engine/batting_engine/contact/contact_outcome.py:340-410`
- Modify: `backend/engine/batting_engine/engine.py:240-270`
- Test: `tests/engine/batting_engine/test_contact_outcome.py`
- Test: `tests/engine/game_engine/test_infield_throws_integration.py`

**Interfaces:**
- Consumes: `solve_fielder_throw` from `fielder_throw`, `calculate_home_to_first_time` & `resolve_play_at_base` from `runner_timing`.
- Produces:
  - Enriched `batted_ball` dictionary containing top-level `throw` dictionary when an infield ground ball triggers a throw or unassisted play.
  - Dynamically resolved `call` (`IN_PLAY_OUT` vs. `SINGLE`) based on authoritative base arrival times.

- [ ] **Step 1: Write failing integration tests for infield groundout vs. infield single and throw telemetry packet**

```python
# tests/engine/game_engine/test_infield_throws_integration.py
import pytest
from backend.engine.batting_engine.contact.contact_outcome import resolve_contact_outcome
from backend.engine.game_engine.defense import ActiveDefense

def test_routine_groundout_to_ss_has_throw_telemetry():
    # 90 mph grounder at 0 deg launch, -15 spray to SS
    res = resolve_contact_outcome(90.0, 0.0, -15.0, batter_speed=65.0)
    assert res["call"] == "IN_PLAY_OUT"
    batted = res["batted_ball"]
    assert "throw" in batted
    throw_data = batted["throw"]
    assert throw_data is not None
    assert throw_data["thrower_id"] == "SS"
    assert throw_data["target_base"] == "1B"
    assert throw_data["is_out"] is True
    assert len(throw_data["samples"]) == 10

def test_deep_chopper_with_elite_runner_becomes_infield_single():
    # Slow chopper: 68 mph, 8 deg launch, -35 spray (deep towards 3B line)
    # With elite batter speed 98, runner beats throw
    res = resolve_contact_outcome(68.0, 8.0, -35.0, batter_speed=98.0)
    assert res["call"] == "SINGLE"
    assert "Infield single" in res["description"] or "beats the throw" in res["description"]
    batted = res["batted_ball"]
    assert "throw" in batted
    assert batted["throw"]["is_out"] is False

def test_airborne_flyout_does_not_generate_infield_throw():
    # 95 mph fly ball caught airborne by CF
    res = resolve_contact_outcome(95.0, 30.0, 0.0, batter_speed=70.0)
    assert res["call"] == "IN_PLAY_OUT"
    assert res["batted_ball"]["throw"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/game_engine/test_infield_throws_integration.py -v`  
Expected: FAIL with `AssertionError: assert 'throw' in batted`

- [ ] **Step 3: Wire throw kinematics and base play resolution in `contact_outcome.py` and `BattingEngine`**

In `backend/engine/batting_engine/contact/contact_outcome.py`:
- Import `solve_fielder_throw` and `BASE_COORDINATES` from `backend.engine.game_engine.physics.fielder_throw`.
- Import `calculate_home_to_first_time` and `resolve_play_at_base` from `backend.engine.game_engine.physics.runner_timing`.
- In `resolve_contact_outcome`:
  - When `not is_airborne_catch and intercept.fielded and intercept.s_intercept <= 165.0`:
    - Lookup fielder attributes:
      ```python
      fielder_state = active_defense.get_fielder(intercept.fielder_id)
      fielder_p = fielder_state.player if fielder_state else None
      arm_str = fielder_p.get_defensive_rating("arm_strength") if fielder_p else 65.0
      arm_acc = fielder_p.get_defensive_rating("arm_accuracy") if fielder_p else 65.0
      trans_spd = fielder_p.get_defensive_rating("transfer_speed") if fielder_p else 65.0
      body_ctrl = fielder_p.get_defensive_rating("body_control") if fielder_p else 65.0
      sprint_spd = fielder_p.get_sprint_speed_fps() if fielder_p else 26.5
      ```
    - Compute `throw_result = solve_fielder_throw(...)`.
    - Compute `runner_time = calculate_home_to_first_time(speed, is_left_handed=False, exit_velocity_mph=ev)`.
    - Compute `base_play = resolve_play_at_base(throw_result, runner_time)`.
    - If `base_play.is_out`:
      - `call = 'IN_PLAY_OUT'`
      - `description = base_play.description`
    - Else:
      - `call = 'SINGLE'`
      - `description = f"Infield single to {intercept.fielder_id}. {base_play.description}"`
    - Convert `throw_result` into JSON-serializable dictionary for `batted_ball_trace['throw']`.
  - For non-throw plays (`is_airborne_catch`, hits to outfield, foul, home run): set `batted_ball_trace['throw'] = None`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/game_engine/test_infield_throws_integration.py tests/engine/batting_engine/test_contact_outcome.py -v`  
Expected: PASS with 0 failures

- [ ] **Step 5: Commit**

```bash
git add backend/engine/batting_engine/contact/contact_outcome.py tests/engine/game_engine/test_infield_throws_integration.py
git commit -m "feat(engine): wire throw kinematics and base play resolution into contact outcome and gameday telemetry"
```

---

### Task 4: Full Suite Regression Verification & Documentation Update

**Files:**
- Modify: `docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md`
- Test: Full backend test suite `tests/`
- Test: Full frontend test suite `frontend/app/`

- [ ] **Step 1: Run full backend test suite to guarantee zero regressions across all 430+ tests**

Run: `pytest tests/ -q`  
Expected: ALL PASS (430+ passed, 0 failed)

- [ ] **Step 2: Run full frontend test suite to ensure client contract integrity**

Run: `cd frontend/app && npm test`  
Expected: ALL PASS (201 passed, 0 failed)

- [ ] **Step 3: Update System Design Specification with Phase 4 status**

In `docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md`:
- Mark Phase 4 (Glove-to-Hand Transfer, Throw Kinematics, and 1B Base Timing) as Implemented.
- Document the `throw` packet schema and base clock resolution formula.

- [ ] **Step 4: Commit**

```bash
git add -f docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md
git commit -m "docs(spec): document throw kinematics, base play clock, and telemetry schema"
```

---

## Execution Handoff

Plan complete and saved to [`docs/superpowers/plans/2026-11-21-fielder-throw-and-base-timing.md`](file:///home/swadaddy4life/Documents/dev-projects/baseball/docs/superpowers/plans/2026-11-21-fielder-throw-and-base-timing.md).

Which execution approach would you prefer?

- **Subagent-driven** - A fresh subagent implements each task and a fresh reviewer checks it before the next one starts, then a whole-branch review at the end. Most thorough; costs a fresh context per task and per review.
- **Native** - I implement every task myself in this session, the way this harness runs work, then one fresh reviewer on the most capable model checks the whole branch. Cheapest and fastest; no independent review until the end.

For this plan I recommend **Subagent-driven**, because the tasks span across kinematic physics (`fielder_throw.py`), runner sprint models (`runner_timing.py`), and gameday packet schemas (`contact_outcome.py`), making independent per-task test verification and reviewer gates valuable to avoid subtle timing regressions. Does the plan capture what you want, and which approach should we use?

