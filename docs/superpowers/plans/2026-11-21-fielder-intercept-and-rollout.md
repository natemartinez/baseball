# Fielder Intercept, Rollout Physics & Dynamic Fielding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the dynamic spatial defense resolver, continuous flight-to-turf rollout physics, 3D fielder pursuit intercept solver, and enriched gameday packet telemetry.

**Architecture:** Connect calibrated projectile ball flight with Dr. Alan Nathan's hop and grass rollout equations into a continuous trajectory $[x(t), y(t), z(t)]$. Model an 8-man `ActiveDefense` with pre-pitch spatial shading and player-specific kinematics ($t_{\text{react}}, v_{\text{sprint}}, \eta, r_{\text{glove}}$) to solve the earliest valid 3D intercept, classify catches (`ROUTINE_FLY_CATCH`, `RUNNING_CATCH`, `GROUND_SCOOP`, `WALL_LEAP`, etc.), and package bounded 20-sample $[x, y, z, t]$ telemetry into gameday events.

**Tech Stack:** Python 3.13, `dataclasses`, `math`, pytest.

**Spec:** [`docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md`](file:///home/swadaddy4life/Documents/dev-projects/baseball/docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md)

## Global Constraints

- **Field Coordinates:** Statcast standard feet ($+Y$ towards CF, $+X$ towards 1B/RF, $-X$ towards 3B/LF, $Z=0$ at ground level).
- **Physical Reach Ceiling:** Catch window height is strictly $z \le 8.5\text{ ft}$, extended to $9.5\text{ ft}$ within $5.0\text{ ft}$ of the outfield fence for `WALL_LEAP`. Fielder pursuit cannot intercept airborne balls higher than $z_{\text{max}}$.
- **Bounded Samples:** `samples` must contain exactly 20 monotonic $[x, y, z, t]$ points starting at $[0.0, 0.0, z_0, 0.0]$ and terminating exactly at $[x_{\text{int}}, y_{\text{int}}, z_{\text{int}}, t_{\text{int}}]$. Trajectories are never truncated post-generation.
- **Backward Compatibility:** All existing signatures (`resolve_contact_outcome`, `BattingEngine.resolve_pitch_outcome`) must accept `defense: Optional[ActiveDefense] = None` and seamlessly fall back to `ActiveDefense.default()` with zero regressions.
- **Home Run Pre-Screening:** Balls clearing the outfield fence distance on the fly at $z \ge \text{fence\_height}$ (8.0 ft) bypass ground rollout and fielder pursuit.

## Review Focus

1. **Unfielded Ball Fence Collision:** An uncaught ball rolling into the gap ($s \ge s_{\text{fence}}(\text{spray})$) must clamp to rest at the fence wall and score as `DOUBLE` (or `TRIPLE`) with `fielded=False`, `fielding_type='UNFIELDED'`, without infinite loops.
2. **Sky-ball Altitude Rejection:** A 105 mph fly ball at 35° launch angle that passes directly over SS at $(x=-45, y=115)$ at an altitude of $z = 45\text{ ft}$ must NOT be caught by SS; it must remain airborne until $z \le 8.5\text{ ft}$.
3. **Pre-pitch Depth Shading:** Fielders with higher `positioning` ratings must adjust starting depth according to spray/depth tendencies, and outfielders must position symmetrically around standard depths.
4. **Fielder Start & Intercept Correlation:** The returned telemetry `batted_ball` must contain `fielder_start: [x_0, y_0]`, `intercept_point: [x, y, z, t]`, and `samples[-1]` matching the intercept point within 0.02 ft.
5. **Zero Breaking Changes to Engine Calls:** Calling `resolve_contact_outcome` without `defense` must produce identical outcome taxonomy (`call`, `is_in_play`, `description`, `batted_ball`) and pass all existing test suites.

---

### Task 1: `ActiveDefense` Spatial Resolver & Positioning Depth Shading

**Files:**
- Create: `backend/engine/game_engine/defense.py`
- Test: `tests/engine/game_engine/test_active_defense.py`

**Interfaces:**
- Consumes: `Player`, `DEFAULT_DEFENSIVE_RATINGS` from `backend.engine.models.player`.
- Produces:
  - `STANDARD_FIELDER_COORDINATES: Dict[str, Tuple[float, float]]`
  - `@dataclass FielderState`: attributes `player: Player`, `position_id: str`, `x: float`, `y: float`, `depth_ft: float`
  - `@dataclass ActiveDefense`: container with `fielders: Dict[str, FielderState]`
  - `ActiveDefense.default() -> ActiveDefense`
  - `ActiveDefense.from_lineup(defending_lineup: List[Player], pitcher: Player) -> ActiveDefense`
  - `ActiveDefense.get_fielder(position_id: str) -> Optional[FielderState]`

- [ ] **Step 1: Write failing tests for ActiveDefense alignment and positioning shading**

```python
# tests/engine/game_engine/test_active_defense.py
import pytest
from backend.engine.models.player import Player
from backend.engine.game_engine.defense import (
    ActiveDefense,
    FielderState,
    STANDARD_FIELDER_COORDINATES,
)


def test_default_active_defense_has_all_8_positions():
    defense = ActiveDefense.default()
    assert len(defense.fielders) == 8
    expected_positions = ('P', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF')
    for pos in expected_positions:
        assert pos in defense.fielders
        fielder = defense.fielders[pos]
        assert isinstance(fielder, FielderState)
        assert isinstance(fielder.player, Player)
        assert fielder.position_id == pos
        # Default positioning (65.0) sits exactly at standard coordinates
        std_x, std_y = STANDARD_FIELDER_COORDINATES[pos]
        assert fielder.x == pytest.approx(std_x, abs=0.1)
        assert fielder.y == pytest.approx(std_y, abs=0.1)


def test_active_defense_from_lineup_maps_players():
    rf = Player(name="Aaron Judge", position="RF", ratings={"range": 85.0})
    ss = Player(name="Anthony Volpe", position="SS", ratings={"range": 82.0})
    pitcher = Player(name="Gerrit Cole", position="SP")
    lineup = [rf, ss]

    defense = ActiveDefense.from_lineup(lineup, pitcher)
    assert defense.get_fielder("RF").player.name == "Aaron Judge"
    assert defense.get_fielder("SS").player.name == "Anthony Volpe"
    assert defense.get_fielder("P").player.name == "Gerrit Cole"
    # Unfilled positions populate standard defaults
    cf = defense.get_fielder("CF")
    assert cf is not None
    assert cf.player.position == "CF"


def test_positioning_rating_applies_depth_shading():
    # CF with 95 positioning shades 10 ft deeper than default for power protection
    deep_cf = Player(
        name="Deep CF",
        position="CF",
        ratings={"positioning": 95.0, "range": 80.0},
    )
    # CF with 35 positioning plays shallower
    shallow_cf = Player(
        name="Shallow CF",
        position="CF",
        ratings={"positioning": 35.0, "range": 80.0},
    )
    p = Player(name="Pitcher", position="P")

    defense_deep = ActiveDefense.from_lineup([deep_cf], p)
    defense_shallow = ActiveDefense.from_lineup([shallow_cf], p)

    cf_deep_state = defense_deep.get_fielder("CF")
    cf_shallow_state = defense_shallow.get_fielder("CF")

    assert cf_deep_state.y > STANDARD_FIELDER_COORDINATES["CF"][1]
    assert cf_shallow_state.y < STANDARD_FIELDER_COORDINATES["CF"][1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/game_engine/test_active_defense.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.engine.game_engine.defense'`

- [ ] **Step 3: Implement `backend/engine/game_engine/defense.py`**

- Define `STANDARD_FIELDER_COORDINATES`:
  - `'P'`: `(0.0, 60.5)`
  - `'1B'`: `(63.6, 63.6)`
  - `'2B'`: `(45.0, 115.0)`
  - `'3B'`: `(-63.6, 63.6)`
  - `'SS'`: `(-45.0, 115.0)`
  - `'LF'`: `(-115.0, 255.0)`
  - `'CF'`: `(0.0, 330.0)`
  - `'RF'`: `(115.0, 255.0)`
- Define `@dataclass class FielderState`:
  - `player: Player`
  - `position_id: str`
  - `x: float`
  - `y: float`
  - `depth_ft: float`
- Define `@dataclass class ActiveDefense`:
  - `fielders: Dict[str, FielderState]`
  - `get_fielder(self, position_id: str) -> Optional[FielderState]`
  - `classmethod default() -> ActiveDefense`
  - `classmethod from_lineup(defending_lineup: List[Player], pitcher: Player) -> ActiveDefense`:
    - For each standard position, assign the matching player from `defending_lineup` (or `pitcher` for `'P'`). If none, create a default `Player(name=f"Default {pos}", position=pos)`.
    - Apply positioning offset: for OF (`LF`, `CF`, `RF`), offset $y$ by $(\text{positioning} - 65.0) \times 0.35\text{ ft}$. For IF (`1B`, `2B`, `3B`, `SS`), offset $y$ by $(\text{positioning} - 65.0) \times 0.15\text{ ft}$.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/game_engine/test_active_defense.py -v`  
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/game_engine/defense.py tests/engine/game_engine/test_active_defense.py
git commit -m "feat(defense): implement ActiveDefense spatial resolver and positioning shading"
```

---

### Task 2: Continuous Ball Flight Rollout & 3D Fielder Intercept Solver

**Files:**
- Create: `backend/engine/game_engine/physics/fielder_intercept.py`
- Modify: `backend/engine/game_engine/physics/ball_flight.py`
- Test: `tests/engine/game_engine/test_fielder_intercept.py`

**Interfaces:**
- Consumes: `ActiveDefense`, `FielderState` from `backend.engine.game_engine.defense`, `solve_ground_motion`, `ground_transit_time` from `backend.engine.game_engine.physics.ball_flight`.
- Produces:
  - `@dataclass class InterceptResult`:
    - `fielded: bool`
    - `fielder_id: Optional[str]`
    - `fielder_name: Optional[str]`
    - `fielding_type: str`
    - `s_intercept: float`
    - `t_intercept: float`
    - `intercept_x: float`
    - `intercept_y: float`
    - `intercept_z: float`
    - `fielder_start: Optional[Tuple[float, float]]`
    - `samples: List[List[float]]`
  - `solve_continuous_ball_flight(exit_velocity_mph: float, launch_angle_deg: float, spray_angle_deg: float, contact_height_ft: float = 3.0) -> Dict[str, Any]`
  - `solve_defense_intercept(ball_flight: Dict[str, Any], spray_deg: float, defense: ActiveDefense) -> InterceptResult`
  - `generate_bounded_samples(ball_flight: Dict[str, Any], spray_deg: float, t_end: float, sample_count: int = 20) -> List[List[float]]`

- [ ] **Step 1: Write failing tests for continuous flight rollout and fielder intercept**

```python
# tests/engine/game_engine/test_fielder_intercept.py
import pytest
from backend.engine.game_engine.defense import ActiveDefense
from backend.engine.game_engine.physics.fielder_intercept import (
    solve_continuous_ball_flight,
    solve_defense_intercept,
    generate_bounded_samples,
)


def test_continuous_ball_flight_connects_air_flight_to_ground_roll():
    # 95 mph at 15 deg launch: in-air flight hits grass and continues rolling
    motion = solve_continuous_ball_flight(95.0, 15.0, 0.0)
    assert motion["t_hang"] > 0.0
    assert motion["landing_distance_ft"] > 0.0
    assert motion["total_distance_ft"] > motion["landing_distance_ft"]
    assert motion["v_impact_xy"] > 0.0
    # Position at t=0 is at home plate contact height
    pos_0 = motion["position_at_t"](0.0)
    assert pos_0 == (0.0, 3.0)  # (s, z)
    # Position at t_hang is at landing distance at ground z=0
    pos_land = motion["position_at_t"](motion["t_hang"])
    assert pos_land[0] == pytest.approx(motion["landing_distance_ft"], abs=0.5)
    assert pos_land[1] == pytest.approx(0.0, abs=0.1)


def test_routine_fly_ball_intercepted_by_cf():
    # 95 mph, 30 deg launch, 0 spray: routine fly ball to CF
    motion = solve_continuous_ball_flight(95.0, 30.0, 0.0)
    defense = ActiveDefense.default()
    res = solve_defense_intercept(motion, spray_deg=0.0, defense=defense)
    assert res.fielded is True
    assert res.fielder_id == "CF"
    assert res.fielding_type in ("ROUTINE_FLY_CATCH", "RUNNING_CATCH")
    assert res.intercept_z >= 2.5
    assert len(res.samples) == 20
    assert res.samples[-1][3] == pytest.approx(res.t_intercept, abs=0.01)


def test_line_drive_in_gap_fielded_on_ground():
    # 102 mph, 14 deg launch, -35 spray: shoots left-field gap and rolls into outfield
    motion = solve_continuous_ball_flight(102.0, 14.0, -35.0)
    defense = ActiveDefense.default()
    res = solve_defense_intercept(motion, spray_deg=-35.0, defense=defense)
    assert res.fielded is True
    assert res.fielder_id == "LF"
    assert res.fielding_type in ("GROUND_SCOOP", "SLIDING_CATCH", "RUNNING_CATCH")
    assert len(res.samples) == 20
    assert res.samples[-1][3] == pytest.approx(res.t_intercept, abs=0.01)


def test_vertical_ceiling_prevents_unphysical_sky_catches():
    # 108 mph, 28 deg launch: passes over SS at z = 35 ft. SS must not catch it.
    motion = solve_continuous_ball_flight(108.0, 28.0, -18.0)
    defense = ActiveDefense.default()
    res = solve_defense_intercept(motion, spray_deg=-18.0, defense=defense)
    if res.fielded and res.fielder_id == "SS":
        assert res.intercept_z <= 8.5
    # Catch must be at z <= 8.5 ft
    assert res.intercept_z <= 8.5


def test_unfielded_ball_at_wall_clamps_to_fence():
    # Scorcher 112 mph line drive at 12 deg into deep corner gap
    motion = solve_continuous_ball_flight(112.0, 12.0, 38.0)
    # Slow defense that cannot reach the ball
    defense = ActiveDefense.default()
    for f in defense.fielders.values():
        f.player.ratings["range"] = 10.0
        f.player.ratings["reaction"] = 10.0

    res = solve_defense_intercept(motion, spray_deg=38.0, defense=defense)
    assert res.fielded is False
    assert res.fielding_type == "UNFIELDED"
    assert len(res.samples) == 20
    assert res.samples[-1][3] == pytest.approx(res.t_intercept, abs=0.05)


def test_bounded_samples_are_strictly_monotonic():
    motion = solve_continuous_ball_flight(98.0, 22.0, 10.0)
    samples = generate_bounded_samples(motion, spray_deg=10.0, t_end=3.5, sample_count=20)
    assert len(samples) == 20
    for i in range(1, len(samples)):
        # t must be strictly increasing
        assert samples[i][3] > samples[i - 1][3]
        # x and y distance from origin must be non-decreasing
        dist_prev = samples[i - 1][0] ** 2 + samples[i - 1][1] ** 2
        dist_curr = samples[i][0] ** 2 + samples[i][1] ** 2
        assert dist_curr >= dist_prev - 1e-3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/game_engine/test_fielder_intercept.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.engine.game_engine.physics.fielder_intercept'`

- [ ] **Step 3: Implement `backend/engine/game_engine/physics/fielder_intercept.py`**

- In `ball_flight.py`: export helper `_fence_distance(spray_angle_deg)` and ensure `solve_ground_motion` accepts optional initial velocity vector $(v_{xy}, v_z)$.
- In `fielder_intercept.py`:
  - Implement `solve_continuous_ball_flight`:
    - For $t \le t_{\text{hang}}$: uses air flight equations:
      $$v_{xy}(t) = v_{0xy} e^{-k \cdot t}, \quad s(t) = \frac{v_{0xy}}{k} (1 - e^{-k \cdot t}), \quad z(t) = z_0 + v_{0z} t - \frac{1}{2} g_{\text{eff}} t^2$$
    - Terminal velocity at impact ($z=0$): $v_{xy,\text{impact}} = v_{0xy} e^{-k \cdot t_{\text{hang}}}$, $v_{z,\text{impact}} = -(v_{0z} - g_{\text{eff}} t_{\text{hang}})$.
    - For $t > t_{\text{hang}}$: uses Nathan hops and grass deceleration:
      $$s(t) = s_{\text{landing}} + s_{\text{ground}}(t - t_{\text{hang}})$$
    - Returns a dict with `t_hang`, `landing_distance_ft`, `total_distance_ft`, `v_impact_xy`, `t_total`, and a callable `position_at_t(t) -> Tuple[float, float]` producing $(s, z)$.
  - Implement `solve_defense_intercept`:
    - Evaluates each fielder in `defense.fielders`:
      - $t_{\text{react}} = 0.45 - (\text{reaction} / 100) \times 0.25\text{s}$
      - $\eta = 0.85 + (\text{route\_efficiency} / 100) \times 0.15$
      - $v_{\text{sprint}} = 22.0 + (\text{range} / 100) \times 8.5\text{ ft/s}$
      - $r_{\text{glove}} = 3.2 + (\text{fielding} / 100) \times 2.3\text{ ft}$
    - Steps in $dt = 0.02\text{s}$ along the trajectory from $t=0$ to $t_{\text{total}}$:
      - Trajectory coordinate: $s, z = \text{position\_at\_t}(t)$, $x = s \cdot \sin(\phi)$, $y = s \cdot \cos(\phi)$.
      - Check wall boundary: if $s \ge s_{\text{fence}}(\phi)$, clamp to wall and stop.
      - Check ceiling: if $z > 8.5\text{ ft}$ (or $9.5\text{ ft}$ if within 5 ft of fence), continue (airborne ball cannot be intercepted).
      - For each fielder:
        - If $t \le t_{\text{react}}$, reachable radius is $r_{\text{glove}}$.
        - If $t > t_{\text{react}}$, reachable radius is $v_{\text{sprint}} \cdot (t - t_{\text{react}}) \cdot \eta + r_{\text{glove}}$.
        - If distance from $(x_{\text{fielder}}, y_{\text{fielder}})$ to $(x, y) \le R_i(t)$: fielder reaches ball!
    - Record the earliest intercept time $t_{\text{int}}$, winning fielder, and $(x, y, z)$.
    - Classify `fielding_type`:
      - `ROUTINE_FLY_CATCH` if $z \ge 2.5\text{ ft}$ and margin $\Delta t \ge 0.35\text{s}$.
      - `RUNNING_CATCH` if $z \ge 2.5\text{ ft}$ and margin $< 0.35\text{s}$.
      - `SLIDING_CATCH` if $0.3\text{ ft} \le z < 2.5\text{ ft}$.
      - `GROUND_SCOOP` if $z < 0.3\text{ ft}$.
      - `WALL_LEAP` if within 5 ft of wall at $z \ge 7.0\text{ ft}$.
      - `UNFIELDED` if no fielder reaches ball before rest or fence.
    - Generate monotonic 20-sample $[x, y, z, t]$ array via `generate_bounded_samples`.
    - Return `InterceptResult`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/game_engine/test_fielder_intercept.py -v`  
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/game_engine/physics/fielder_intercept.py backend/engine/game_engine/physics/ball_flight.py tests/engine/game_engine/test_fielder_intercept.py
git commit -m "feat(physics): implement continuous ball rollout and 3D fielder intercept solver"
```

---

### Task 3: Contact Outcome Resolution & Gameday Telemetry Enrichment

**Files:**
- Modify: `backend/engine/batting_engine/contact/contact_outcome.py`
- Modify: `backend/engine/batting_engine/contact/contact.py`
- Modify: `tests/engine/batting_engine/test_contact_outcome.py`

**Interfaces:**
- Consumes: `ActiveDefense` from `backend.engine.game_engine.defense`, `solve_continuous_ball_flight`, `solve_defense_intercept` from `backend.engine.game_engine.physics.fielder_intercept`.
- Produces:
  - `resolve_contact_outcome(..., defense: Optional[ActiveDefense] = None) -> Optional[Dict[str, Any]]`
  - Enriched gameday packet `batted_ball` containing `fielded`, `fielder_id`, `fielding_type`, `fielder_start`, `intercept_point`, and 4D samples `[x, y, z, t]`.
  - Preserved backward compatibility keys `fielder_name`, `fielder_distance_ft`, `fielder_radius_ft`.

- [ ] **Step 1: Write failing tests verifying enriched telemetry and outcome mapping**

```python
# In tests/engine/batting_engine/test_contact_outcome.py
from backend.engine.game_engine.defense import ActiveDefense


def test_resolve_contact_outcome_emits_enriched_fielding_telemetry():
    res = resolve_contact_outcome(95.0, 20.0, 0.0)
    assert res is not None
    assert "batted_ball" in res
    trace = res["batted_ball"]
    assert "fielded" in trace
    assert "fielder_id" in trace
    assert "fielding_type" in trace
    assert "fielder_start" in trace
    assert "intercept_point" in trace
    assert len(trace["samples"]) == 20
    assert trace["samples"][-1][3] == pytest.approx(trace["hang_time_s"], abs=0.02)


def test_home_run_prescreening_bypasses_fielding():
    # 110 mph at 30 deg to center field clears the fence on the fly
    res = resolve_contact_outcome(110.0, 30.0, 0.0)
    assert res["call"] == "HOME_RUN"
    trace = res["batted_ball"]
    assert trace["fielded"] is False
    assert trace["fielding_type"] == "HOME_RUN"


def test_infield_grounder_out_vs_outfield_base_hit():
    # Routine grounder straight to SS (-18 deg)
    ground_out = resolve_contact_outcome(92.0, 2.0, -18.0)
    assert ground_out["call"] == "IN_PLAY_OUT"
    assert ground_out["batted_ball"]["fielded"] is True
    assert ground_out["batted_ball"]["fielder_id"] == "SS"
    assert ground_out["batted_ball"]["fielding_type"] in ("GROUND_SCOOP", "BACKHAND_PICK")

    # Rocket grounder through the gap (105 mph, -33.6 deg) reaches outfield grass
    gap_hit = resolve_contact_outcome(105.0, 0.0, -33.6)
    assert gap_hit["call"] in ("SINGLE", "DOUBLE")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/batting_engine/test_contact_outcome.py::test_resolve_contact_outcome_emits_enriched_fielding_telemetry -v`  
Expected: FAIL with `KeyError: 'fielded'`

- [ ] **Step 3: Update `backend/engine/batting_engine/contact/contact_outcome.py`**

- Accept `defense: Optional[ActiveDefense] = None` in `resolve_contact_outcome(...)`.
- If `defense is None`: instantiate `defense = ActiveDefense.default()`.
- Pre-screen Home Runs:
  - If fair ball carries beyond the outfield fence distance on the fly ($d \ge \text{fence}$) and clears fence height ($z \ge 8.0\text{ ft}$):
    - `call = 'HOME_RUN'`
    - Generate in-air trace to fence crossover.
    - Set `fielded = False`, `fielding_type = 'HOME_RUN'`, `fielder_id = None`.
- For other fair in-play balls:
  - Call `solve_continuous_ball_flight(ev, launch, spray, contact_height)`.
  - Call `intercept = solve_defense_intercept(motion, spray, defense)`.
  - Resolve play outcome `call`:
    - Airborne catch ($z > 0.3\text{ ft}$ and `intercept.fielded`): `call = 'IN_PLAY_OUT'`.
    - Infield ground intercept ($s_{\text{int}} \le 165.0\text{ ft}$ and `intercept.fielded`): `call = 'IN_PLAY_OUT'`.
    - Outfield ground intercept ($s_{\text{int}} > 165.0\text{ ft}$ and `intercept.fielded`):
      - If $s_{\text{int}} \ge 310.0\text{ ft}$ or $t_{\text{int}} \ge 4.4\text{s}$: `call = 'TRIPLE'`.
      - If $s_{\text{int}} \ge 260.0\text{ ft}$ or $t_{\text{int}} \ge 3.4\text{s}$: `call = 'DOUBLE'`.
      - Otherwise: `call = 'SINGLE'`.
    - Unfielded ball (`not intercept.fielded`):
      - If $s \ge 320.0\text{ ft}$ down the line ($\ge 35^\circ$): `call = 'TRIPLE'`.
      - Otherwise: `call = 'DOUBLE'`.
  - Package `trace` dictionary:
    - Update `hang_time_s = round(intercept.t_intercept, 3)`.
    - Update `landing_x_ft = round(intercept.intercept_x, 1)`.
    - Update `landing_y_ft = round(intercept.intercept_y, 1)`.
    - Update `distance_ft = round(intercept.s_intercept, 1)`.
    - Set `fielded = intercept.fielded`.
    - Set `fielder_id = intercept.fielder_id`.
    - Set `fielder_name = intercept.fielder_name`.
    - Set `fielding_type = intercept.fielding_type`.
    - Set `fielder_start = list(intercept.fielder_start) if intercept.fielder_start else None`.
    - Set `intercept_point = [round(intercept.intercept_x, 2), round(intercept.intercept_y, 2), round(intercept.intercept_z, 2), round(intercept.t_intercept, 3)]`.
    - Set `samples = intercept.samples`.
    - Set `sample_count = len(intercept.samples)`.
  - Ensure backward compatibility fields on returned dict:
    - `fielder_name = intercept.fielder_id if intercept.fielded else None`
    - `fielder_distance_ft = round(math.hypot(intercept.intercept_x - intercept.fielder_start[0], intercept.intercept_y - intercept.fielder_start[1]), 1) if intercept.fielded and intercept.fielder_start else None`
    - `fielder_radius_ft = 60.0`
- In `backend/engine/batting_engine/contact/contact.py`: forward `defense: Optional[ActiveDefense] = None` from `ContactResolver.resolve_contact()` to `resolve_contact_outcome()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/batting_engine/test_contact_outcome.py -v`  
Expected: PASS (all tests pass)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/batting_engine/contact/contact_outcome.py backend/engine/batting_engine/contact/contact.py tests/engine/batting_engine/test_contact_outcome.py
git commit -m "feat(batting): route contact outcomes through dynamic fielder intercept and enrich gameday telemetry"
```

---

### Task 4: Engine Pipeline Orchestration & End-to-End Game State Integration

**Files:**
- Modify: `backend/engine/batting_engine/engine.py`
- Modify: `backend/engine/game_engine/orchestration/pitch_orchestrator.py`
- Modify: `backend/engine/game_engine/main.py`
- Test: `tests/engine/game_engine/test_pitch_orchestrator_pipeline.py`

**Interfaces:**
- Consumes: `ActiveDefense.from_lineup` from `backend.engine.game_engine.defense`.
- Produces:
  - Seamless pass-through of defensive alignment from `PitchOrchestrator` to `BattingEngine`.
  - Gameday pitch resolution payload contains enriched fielding metadata for live gameday events.

- [ ] **Step 1: Write failing test verifying defensive team alignment passed through pitch orchestration**

```python
# In tests/engine/game_engine/test_pitch_orchestrator_pipeline.py
from backend.engine.models.player import Player
from backend.engine.game_engine.defense import ActiveDefense
from tests.conftest import _game


def test_pitch_orchestration_uses_defending_team_active_defense():
    game = _game(seed=2026, batter_id=4)
    # Ensure home/away defending lineup is turned into an ActiveDefense instance
    defense = game.get_active_defense()
    assert isinstance(defense, ActiveDefense)
    assert len(defense.fielders) == 8

    # Throw and resolve pitch with contact to center field
    game.throw_pitch(pitch_intent="STRIKE", target_zone="heart")
    res = game.resolve_pitch(
        contact={
            "contacted": True,
            "exit_velocity_mph": 95.0,
            "launch_angle_deg": 25.0,
            "spray_angle_deg": 0.0,
        }
    )
    details = res["pitch_details"]
    assert details["pitch_result"] == "IN_PLAY_OUT"
    trace = details["batted_ball"]
    assert trace is not None
    assert trace["fielded"] is True
    assert trace["fielder_id"] == "CF"
    assert "fielding_type" in trace
    assert trace["samples"][-1][3] == pytest.approx(trace["hang_time_s"], abs=0.02)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/game_engine/test_pitch_orchestrator_pipeline.py::test_pitch_orchestration_uses_defending_team_active_defense -v`  
Expected: FAIL with `AttributeError: 'GameEngine' object has no attribute 'get_active_defense'`

- [ ] **Step 3: Wire `ActiveDefense` into `GameEngine`, `PitchOrchestrator`, and `BattingEngine`**

- In `backend/engine/game_engine/main.py`:
  - Implement `get_active_defense(self) -> ActiveDefense`:
    - Identifies defending team based on current half-inning (top: home team defends; bottom: away team defends).
    - Resolves defensive lineup and active pitcher from game state.
    - Returns `ActiveDefense.from_lineup(defending_lineup, pitcher)`.
  - In `execute_pitch()` and `resolve_pitch()`: pass `defense=self.get_active_defense()` into `orchestrator.resolve_pitch()`.
- In `backend/engine/game_engine/orchestration/pitch_orchestrator.py`:
  - Accept `defense: Optional[ActiveDefense] = None` in `resolve_pitch()`.
  - Pass `defense=defense` to `batting_engine.resolve_pitch_outcome()`.
- In `backend/engine/batting_engine/engine.py`:
  - Accept `defense: Optional[ActiveDefense] = None` in `resolve_pitch_outcome()`.
  - Forward `defense` into `contact_resolver.resolve_contact(...)` and `resolve_contact_outcome(...)`.

- [ ] **Step 4: Run full engine test suite to verify 0 regressions**

Run: `pytest tests/engine/ -v`  
Expected: ALL PASS (286+ passed, 0 failed)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/game_engine/main.py backend/engine/game_engine/orchestration/pitch_orchestrator.py backend/engine/batting_engine/engine.py tests/engine/game_engine/test_pitch_orchestrator_pipeline.py
git commit -m "feat(engine): wire defending team ActiveDefense into pitch orchestrator pipeline"
```

---

## Plan Review Checklist

1. **Spec Coverage:**
   - Section 3.1 (Seamless Flight $\to$ Rollout Handoff & Fence Boundaries) $\to$ Task 2
   - Section 3.2 (Fielder Pursuit & 3D Intercept Algorithm) $\to$ Task 2
   - Section 3.3 (Catch Classification & Outcome Resolution) $\to$ Task 2 & Task 3
   - Section 3.4 (Bounded Trajectory Sampling) $\to$ Task 2
   - Section 4 (Telemetry Contract: `batted_ball` dictionary) $\to$ Task 3
   - Section 5 (Module Map & Orchestration Wiring) $\to$ Task 1, 3, 4
2. **Step Granularity:** Each step follows the exact pattern (write failing test $\to$ verify fail $\to$ implement $\to$ verify pass $\to$ commit).
3. **Type Consistency:** `ActiveDefense`, `FielderState`, `InterceptResult`, `samples` $[x, y, z, t]$ consistent across all tasks.
4. **Review Focus:** All 5 review focus items explicitly tested in Tasks 1, 2, and 3.
5. **Backward Compatibility:** All existing function signatures remain callable with defaults, verified across all 286+ existing engine tests.

