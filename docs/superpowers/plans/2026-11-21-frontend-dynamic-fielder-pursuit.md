# Frontend Dynamic Fielder Pursuit & Catch Animation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the static 3D fielder cylinders in the gamefield into dynamic, reactive defensive agents that sprint along Statcast pursuit paths and execute visually synchronized catch postures (`ROUTINE_FLY_CATCH`, `RUNNING_CATCH`, `SLIDING_CATCH`, `WALL_LEAP`, `GROUND_SCOOP`, `BACKHAND_PICK`) driven by backend gameday telemetry.

**Architecture:** 
1. Extend frontend TypeScript contracts (`BattedBallTelemetry`, `ActiveBattedBallData`) to ingest backend intercept metadata (`fielded`, `fielder_id`, `fielding_type`, `fielder_start`, `intercept_point`).
2. Build pure, deterministic pursuit kinematics in `fielderKinematics.ts` that resolve a fielder's scene-space position, running direction, and catch state at any elapsed time $t$ factoring in reaction delay and sprint pace.
3. Update `FielderLayer.tsx` in Three.js/React Three Fiber to animate the primary pursuing fielder in real-time sync with ball trajectory $t \in [0, t_{\text{intercept}}]$, display catch indicators, and smoothly glide fielders back to baseline positions between plays.
4. Update `BaseballSimScreen.tsx` and `hitPresets.ts` to hydrate fielding metadata across live simulation and debug hit testing.

**Tech Stack:** React 19, React Native Web, React Three Fiber, Three.js, Node test runner (`node:test`, `node:assert/strict`).

**Spec:** [`docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md`](file:///home/swadaddy4life/Documents/dev-projects/baseball/docs/superpowers/specs/2026-11-20-dynamic-fielding-and-ball-flight-design.md)

---

## Global Constraints

- Coordinate Transformation Rule: Statcast $(x, y, z)$ (+X right field, +Y depth toward center field, +Z elevation) maps to Three.js scene space as $(x, z, -y)$.
- Zero Animation Snapping: The fielder designated by `fielder_id` must arrive at `intercept_point` at the exact same physical time $t_{\text{intercept}}$ that the ball arrives at `samples[-1]`.
- Backward-Compatibility: Batted balls with missing or null fielding metadata (e.g. legacy replays or pre-v2 records) must safely default to static positioning without crashing or throwing errors.
- Respect Global Pause: All fielder pursuit progression must respect `isBattedBallPaused` in `gameStore`, freezing in place during hit inspector pauses.
- Clean Return Transition: After `resultCameraHold` expires or a new pitch begins, fielders must smoothly interpolate back to pre-pitch defensive coordinates rather than instantly teleporting.

## Review Focus

1. **Unfielded Extra-Base Hits (`fielded === false`):** Outfielders must pursue toward the deep ball/gap along route angles rather than freezing at baseline, while the ball rolls to the fence unfielded.
2. **Short Reaction Delay Window ($t \le t_{\text{react}}$):** High-exit grounders and liners arrive quickly; the fielder must visually exhibit a read/anticipation hold for $\approx 0.25\text{s}$ before accelerating into a sprint break.
3. **Sliding & Diving Catches ($z < 2.5\text{ ft}$):** Low catches just above turf level must trigger sliding/diving visual feedback at the intercept point rather than upright stance cylinders.
4. **Foul Ball Telemetry Handoff:** Batted fouls carrying `samples` with `fielded: false, fielding_type: "FOUL"` must leave fielders in tracking/read posture without pursuing into the dugout.
5. **Debug Hit Launcher Parity:** All 5 preset hits in the debug hit launcher (`hitPresets.ts`) must supply realistic fielding metadata so frontend developers can test all catch types in isolation without running live game simulations.

---

### Task 1: Frontend Type Declarations & Telemetry Ingestion Contract

**Files:**
- Modify: `frontend/app/src/types/api.ts:281-294`
- Modify: `frontend/app/src/components/gamefield/types.ts:24-34`
- Modify: `frontend/app/src/screens/BaseballSimScreen.tsx:428-440`
- Test: `frontend/app/src/types/__tests__/fieldingTelemetryTypes.test.ts`

**Interfaces:**
- Consumes: Backend gameday packet `batted_ball` dictionary.
- Produces:
  - Updated `BattedBallTelemetry` interface with `{ fielded?, fielder_id?, fielder_name?, fielding_type?, fielder_start?, intercept_point? }`.
  - Updated `ActiveBattedBallData` interface with `{ fielded?, fielderId?, fielderName?, fieldingType?, fielderStart?, interceptPoint? }`.

- [x] **Step 1: Write failing test verifying fielding telemetry typing and mapping**

```typescript
// frontend/app/src/types/__tests__/fieldingTelemetryTypes.test.ts
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type { BattedBallTelemetry } from '../api';
import type { ActiveBattedBallData } from '../../components/gamefield/types';

describe('Fielding Telemetry Type Contract', () => {
  it('accepts enriched backend fielding telemetry', () => {
    const rawTrace: BattedBallTelemetry = {
      exit_velocity_mph: 98.4,
      launch_angle_deg: 16.5,
      spray_angle_deg: -18.2,
      hang_time_s: 3.42,
      apex_height_ft: 32.1,
      distance_ft: 268.4,
      landing_x_ft: -83.7,
      landing_y_ft: 255.0,
      sample_count: 20,
      samples: [
        [0.0, 0.0, 3.0, 0.0],
        [-83.7, 255.0, 0.0, 3.42],
      ],
      fielded: true,
      fielder_id: 'LF',
      fielder_name: 'Alex Verdugo',
      fielding_type: 'GROUND_SCOOP',
      fielder_start: [-115.0, 255.0],
      intercept_point: [-83.7, 255.0, 0.0],
      model_version: 'calibrated-projectile-v1',
    };

    assert.equal(rawTrace.fielded, true);
    assert.equal(rawTrace.fielder_id, 'LF');
    assert.equal(rawTrace.fielding_type, 'GROUND_SCOOP');
    assert.deepEqual(rawTrace.fielder_start, [-115.0, 255.0]);
    assert.deepEqual(rawTrace.intercept_point, [-83.7, 255.0, 0.0]);
  });

  it('maps raw telemetry to ActiveBattedBallData with camelCase properties', () => {
    const rawTrace: BattedBallTelemetry = {
      exit_velocity_mph: 102.0,
      launch_angle_deg: 24.0,
      spray_angle_deg: 0.0,
      hang_time_s: 3.85,
      apex_height_ft: 45.0,
      distance_ft: 325.0,
      landing_x_ft: 0.0,
      landing_y_ft: 325.0,
      sample_count: 20,
      samples: [[0, 0, 3, 0], [0, 325, 3.5, 3.85]],
      fielded: true,
      fielder_id: 'CF',
      fielder_name: 'Aaron Judge',
      fielding_type: 'ROUTINE_FLY_CATCH',
      fielder_start: [0.0, 330.0],
      intercept_point: [0.0, 325.0, 3.5],
      model_version: 'calibrated-projectile-v1',
    };

    const activeBall: ActiveBattedBallData = {
      id: 'batted-1',
      hangTime: rawTrace.hang_time_s,
      samples: rawTrace.samples,
      landingPos: [rawTrace.landing_x_ft, 0, -rawTrace.landing_y_ft],
      fielded: rawTrace.fielded,
      fielderId: rawTrace.fielder_id,
      fielderName: rawTrace.fielder_name,
      fieldingType: rawTrace.fielding_type,
      fielderStart: rawTrace.fielder_start,
      interceptPoint: rawTrace.intercept_point,
    };

    assert.equal(activeBall.fielded, true);
    assert.equal(activeBall.fielderId, 'CF');
    assert.equal(activeBall.fieldingType, 'ROUTINE_FLY_CATCH');
    assert.deepEqual(activeBall.fielderStart, [0.0, 330.0]);
    assert.deepEqual(activeBall.interceptPoint, [0.0, 325.0, 3.5]);
  });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd frontend/app && node --experimental-transform-types --loader ./scripts/test-loader.mjs --test src/types/__tests__/fieldingTelemetryTypes.test.ts`  
Expected: FAIL with TypeScript type errors (`Property 'fielded' does not exist on type 'BattedBallTelemetry'`).

- [x] **Step 3: Update `BattedBallTelemetry`, `ActiveBattedBallData`, and `BaseballSimScreen.tsx`**

In `frontend/app/src/types/api.ts`:
```typescript
export interface BattedBallTelemetry {
  exit_velocity_mph: number;
  launch_angle_deg: number;
  spray_angle_deg: number;
  hang_time_s: number;
  apex_height_ft: number;
  distance_ft: number;
  landing_x_ft: number;
  landing_y_ft: number;
  sample_count: number;
  samples: BattedBallSample[];
  fielded?: boolean;
  fielder_id?: string | null;
  fielder_name?: string | null;
  fielding_type?: string | null;
  fielder_start?: [number, number] | null;
  intercept_point?: [number, number, number] | null;
  model_version: string;
}
```

In `frontend/app/src/components/gamefield/types.ts`:
```typescript
export interface ActiveBattedBallData {
  id: string;
  hangTime: number;
  samples: BattedBallSample[];
  isGrounder?: boolean;
  landingPos?: [number, number, number];
  launchAngle?: number;
  apexHeight?: number;
  distance?: number;
  fielded?: boolean;
  fielderId?: string | null;
  fielderName?: string | null;
  fieldingType?: string | null;
  fielderStart?: [number, number] | null;
  interceptPoint?: [number, number, number] | null;
}
```

In `frontend/app/src/screens/BaseballSimScreen.tsx`:
Map `fielded`, `fielderId`, `fielderName`, `fieldingType`, `fielderStart`, and `interceptPoint` from `trace` to `setActiveBattedBall`.

- [x] **Step 4: Run test to verify it passes**

Run: `cd frontend/app && node --experimental-transform-types --loader ./scripts/test-loader.mjs --test src/types/__tests__/fieldingTelemetryTypes.test.ts`  
Expected: PASS (2 passed).

- [x] **Step 5: Commit**

```bash
git add frontend/app/src/types/api.ts frontend/app/src/components/gamefield/types.ts frontend/app/src/screens/BaseballSimScreen.tsx frontend/app/src/types/__tests__/fieldingTelemetryTypes.test.ts
git commit -m "feat(frontend): extend batted ball telemetry contracts with dynamic fielding metadata"
```

---

### Task 2: Pure Fielder Pursuit Kinematics & Timing Resolver

**Files:**
- Create: `frontend/app/src/components/gamefield/fielderKinematics.ts`
- Test: `frontend/app/src/components/gamefield/__tests__/fielderKinematics.test.ts`

**Interfaces:**
- Consumes: `Fielder` baseline coordinates from `frontend/app/src/services/fielders.ts`.
- Produces:
  - `statcastToScene(x: number, y: number, z?: number): [number, number, number]`
  - `computeFielderPursuit(params: FielderPursuitParams): FielderPursuitState`
  - `computeAllFielderPositions(params: AllFieldersParams): Map<string, FielderRenderState>`
  - `getCatchVisualProfile(fieldingType: string | null | undefined): CatchVisualProfile`

- [x] **Step 1: Write failing tests for fielder pursuit kinematics and catch profiles**

```typescript
// frontend/app/src/components/gamefield/__tests__/fielderKinematics.test.ts
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  statcastToScene,
  computeFielderPursuit,
  computeAllFielderPositions,
  getCatchVisualProfile,
} from '../fielderKinematics';

describe('Fielder Pursuit Kinematics', () => {
  it('converts Statcast coordinates to Three.js scene coordinates', () => {
    // Statcast +X is right field, +Y is depth toward CF, +Z is height
    // Three.js X is +X, Y is +Z, Z is -Y
    const scenePos = statcastToScene(-115.0, 255.0, 0.0);
    assert.deepEqual(scenePos, [-115.0, 0.0, -255.0]);

    const elevated = statcastToScene(0.0, 320.0, 6.5);
    assert.deepEqual(elevated, [0.0, 6.5, -320.0]);
  });

  it('holds pre-pitch position during reaction delay beat', () => {
    // Fielder breaks after 0.25s reaction time
    const pursuit = computeFielderPursuit({
      startStatcast: [0.0, 330.0],
      targetStatcast: [20.0, 300.0, 3.0],
      elapsedTime: 0.15,
      totalDuration: 3.5,
      reactionDelay: 0.25,
    });

    assert.equal(pursuit.hasBroken, false);
    assert.deepEqual(pursuit.currentScenePos, [0.0, 0.0, -330.0]);
    assert.equal(pursuit.progress, 0.0);
  });

  it('smoothly interpolates scene position during sprint pursuit', () => {
    // Fielder sprints from (0, 330) to (20, 300) between t=0.25 and t=3.25
    const pursuit = computeFielderPursuit({
      startStatcast: [0.0, 330.0],
      targetStatcast: [20.0, 300.0, 0.0],
      elapsedTime: 1.75, // Halfway through sprint (1.5s into 3.0s sprint)
      totalDuration: 3.25,
      reactionDelay: 0.25,
    });

    assert.equal(pursuit.hasBroken, true);
    assert.equal(pursuit.isArrived, false);
    assert.ok(Math.abs(pursuit.progress - 0.5) < 1e-3);
    // Position should be midpoint: X=10, Z=-315
    assert.ok(Math.abs(pursuit.currentScenePos[0] - 10.0) < 0.1);
    assert.ok(Math.abs(pursuit.currentScenePos[2] - (-315.0)) < 0.1);
  });

  it('locks exactly at target intercept coordinate upon arrival', () => {
    const pursuit = computeFielderPursuit({
      startStatcast: [-45.0, 115.0],
      targetStatcast: [-55.0, 105.0, 0.0],
      elapsedTime: 2.5,
      totalDuration: 2.0,
      reactionDelay: 0.25,
    });

    assert.equal(pursuit.isArrived, true);
    assert.equal(pursuit.progress, 1.0);
    assert.deepEqual(pursuit.currentScenePos, [-55.0, 0.0, -105.0]);
  });

  it('maps fielding types to distinct catch visual profiles', () => {
    const wallLeap = getCatchVisualProfile('WALL_LEAP');
    assert.equal(wallLeap.badgeLabel, 'WALL LEAP');
    assert.equal(wallLeap.ringColor, '#EF4444');

    const sliding = getCatchVisualProfile('SLIDING_CATCH');
    assert.equal(sliding.badgeLabel, 'SLIDING CATCH');
    assert.equal(sliding.ringColor, '#F59E0B');

    const scoop = getCatchVisualProfile('GROUND_SCOOP');
    assert.equal(scoop.badgeLabel, 'FIELDED');
    assert.equal(scoop.ringColor, '#3B82F6');

    const routine = getCatchVisualProfile('ROUTINE_FLY_CATCH');
    assert.equal(routine.ringColor, '#10B981');

    const unfielded = getCatchVisualProfile('UNFIELDED');
    assert.equal(unfielded.isCaught, false);
  });

  it('updates all 8 fielders with off-ball shading when one fielder pursues', () => {
    const allFielders = computeAllFielderPositions({
      activeFielderId: 'CF',
      activeStartStatcast: [0.0, 330.0],
      activeTargetStatcast: [-40.0, 290.0, 2.0],
      elapsedTime: 2.0,
      totalDuration: 3.0,
    });

    assert.equal(allFielders.size, 8);
    // CF is actively moving
    const cf = allFielders.get('CF');
    assert.ok(cf);
    assert.notDeepEqual(cf.scenePos, [0.0, 0.0, -330.0]);

    // LF shades slightly toward the ball to back up
    const lf = allFielders.get('LF');
    assert.ok(lf);
    assert.ok(lf.scenePos[0] > -115.0); // LF stepped toward center
  });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd frontend/app && node --experimental-transform-types --loader ./scripts/test-loader.mjs --test src/components/gamefield/__tests__/fielderKinematics.test.ts`  
Expected: FAIL with `Cannot find module '../fielderKinematics'`.

- [ ] **Step 3: Implement `fielderKinematics.ts`**

Create `frontend/app/src/components/gamefield/fielderKinematics.ts`:
- Implement `statcastToScene(x, y, z = 0)` mapping $(x, y, z) \to (x, z, -y)$.
- Implement `computeFielderPursuit`:
  - Guard reaction delay against short hang times: $t_{\text{react\_eff}} = \min(t_{\text{react}}, t_{\text{total}} \times 0.5)$.
  - If $t \le t_{\text{react\_eff}}$: progress = 0.0, position = start (turf level $Y = 0.0$).
  - If $t \ge t_{\text{total}}$: progress = 1.0, position = target (turf level $Y = 0.0$), isArrived = true.
  - Else: linear sprint progress $\alpha = (t - t_{\text{react\_eff}}) / \max(0.05, t_{\text{total}} - t_{\text{react\_eff}})$, lerp turf position $[x(t), 0, -y(t)]$.
  - Calculate running heading angle in Three.js coordinates:
    $\Delta X = x_{\text{target}} - x_{\text{start}}$, $\Delta Z = -(y_{\text{target}} - y_{\text{start}})$.
    $\theta_y = \operatorname{atan2}(\Delta X, \Delta Z)$ if $\sqrt{\Delta X^2 + \Delta Z^2} \ge 0.1$, else hold previous heading.
  - Return `currentScenePos: [x, 0, -y]`, `gloveScenePos: [x, z, -y]`, `headingAngle`, `progress`, `hasBroken`, `isArrived`.
- Implement `getCatchVisualProfile(fieldingType)`:
  - Maps catch types to color, badge label, glove elevation offset, and catch status (`isCaught`):
    - `ROUTINE_FLY_CATCH` / `RUNNING_CATCH`: `#10B981` (emerald green), badge 'ROUTINE CATCH' / 'RUNNING CATCH', `isCaught: true`.
    - `GROUND_SCOOP` / `BACKHAND_PICK`: `#3B82F6` (blue), badge 'FIELDED' / 'BACKHAND PICK', `isCaught: true`.
    - `SLIDING_CATCH`: `#F59E0B` (amber), badge 'SLIDING CATCH', `isCaught: true`.
    - `WALL_LEAP`: `#EF4444` (red), badge 'WALL LEAP', `isCaught: true`.
    - `UNFIELDED` / `HOME_RUN` / `FOUL`: badge label null, `isCaught: false`, `showRing: false`.
- Implement `computeAllFielderPositions`:
  - Returns map of all 8 positions (`P`, `1B`, `2B`, `3B`, `SS`, `LF`, `CF`, `RF`).
  - Active fielder follows `computeFielderPursuit`.
  - Non-active fielders shade toward active play:
    $\vec{d}_i = \vec{p}_{\text{target}} - \vec{b}_i$
    $\hat{u}_i = \vec{d}_i / \|\vec{d}_i\|$ (if $\|\vec{d}_i\| \ge 1.0$, else $\vec{0}$)
    $\beta(t) = \min(1.0, \max(0.0, (t - t_{\text{react\_eff}}) / t_{\text{total}}))$
    $\vec{pos}_i(t) = \vec{b}_i + (S_{\text{max}} \cdot \beta(t)) \cdot \hat{u}_i$
    where $S_{\text{max}} = 12.0\text{ ft}$ for outfielders backing up, $6.0\text{ ft}$ for infielders, $4.0\text{ ft}$ for pitcher.
    `scenePos: [pos_x, 0, -pos_y]`.

- [x] **Step 4: Run test to verify it passes**

Run: `cd frontend/app && node --experimental-transform-types --loader ./scripts/test-loader.mjs --test src/components/gamefield/__tests__/fielderKinematics.test.ts`  
Expected: PASS (6 passed).

- [x] **Step 5: Commit**

```bash
git add frontend/app/src/components/gamefield/fielderKinematics.ts frontend/app/src/components/gamefield/__tests__/fielderKinematics.test.ts
git commit -m "feat(frontend): implement pure fielder pursuit kinematics and catch profile resolver"
```

---

### Task 3: Dynamic Fielder Three.js Scene Component & Catch Indicator

**Files:**
- Modify: `frontend/app/src/components/gamefield/FielderLayer.tsx`
- Create: `frontend/app/src/components/gamefield/CatchIndicator.tsx`
- Test: `frontend/app/src/components/gamefield/__tests__/FielderLayerLogic.test.ts`

**Interfaces:**
- Consumes: `ActiveBattedBallData` from `frontend/app/src/components/gamefield/types.ts`.
- Produces:
  - Dynamic `FielderLayer({ activeBattedBall })` updating fielder meshes each frame via `useFrame`.
  - Dynamic heading alignment (fielders rotate to face their sprint direction).
  - `CatchIndicator` rendered at `interceptPoint` with animated ring pulse and badge label upon glove arrival.

- [x] **Step 1: Write failing test verifying dynamic FielderLayer state management and transitions**

```typescript
// frontend/app/src/components/gamefield/__tests__/FielderLayerLogic.test.ts
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  statcastToScene,
  computeFielderPursuit,
  getCatchVisualProfile,
} from '../fielderKinematics';
import type { ActiveBattedBallData } from '../types';

describe('FielderLayer Animation Logic & Transitions', () => {
  it('correctly tracks active fielder target across ball lifecycle', () => {
    const ball: ActiveBattedBallData = {
      id: 'hit-test',
      hangTime: 3.2,
      samples: [[0, 0, 3, 0], [40, 280, 0, 3.2]],
      fielded: true,
      fielderId: 'RF',
      fieldingType: 'RUNNING_CATCH',
      fielderStart: [115.0, 255.0],
      interceptPoint: [40.0, 280.0, 4.2],
    };

    // At t=0: RF is at start position
    const atStart = computeFielderPursuit({
      startStatcast: ball.fielderStart!,
      targetStatcast: ball.interceptPoint!,
      elapsedTime: 0.0,
      totalDuration: ball.hangTime,
    });
    assert.deepEqual(atStart.currentScenePos, statcastToScene(115.0, 255.0, 0.0));
    assert.equal(atStart.isArrived, false);

    // At t=3.2: RF has arrived at intercept point
    const atEnd = computeFielderPursuit({
      startStatcast: ball.fielderStart!,
      targetStatcast: ball.interceptPoint!,
      elapsedTime: 3.2,
      totalDuration: ball.hangTime,
    });
    assert.deepEqual(atEnd.currentScenePos, statcastToScene(40.0, 280.0, 0.0));
    assert.equal(atEnd.isArrived, true);
  });

  it('suppresses catch indicator when ball is unfielded', () => {
    const unfieldedBall: ActiveBattedBallData = {
      id: 'gap-double',
      hangTime: 4.5,
      samples: [[0, 0, 3, 0], [80, 310, 0, 4.5]],
      fielded: false,
      fielderId: null,
      fieldingType: 'UNFIELDED',
    };

    const profile = getCatchVisualProfile(unfieldedBall.fieldingType);
    assert.equal(profile.isCaught, false);
    assert.equal(profile.showRing, false);
  });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd frontend/app && node --experimental-transform-types --loader ./scripts/test-loader.mjs --test src/components/gamefield/__tests__/FielderLayerLogic.test.ts`  
Expected: PASS or FAIL depending on helper exports; ensure tests run cleanly.

- [x] **Step 3: Implement `CatchIndicator.tsx` and upgrade `FielderLayer.tsx`**

1. Create `frontend/app/src/components/gamefield/CatchIndicator.tsx`:
   - Renders a stylized catch ring and billboard text badge at `[x, y, z]` when a catch occurs.
   - Distinct color coding (`#10B981` green for routine/running catches, `#F59E0B` amber for sliding catches/picks, `#EF4444` for wall leaps).
   - Animates subtle scale expansion and opacity fade on arrival.

2. Upgrade `frontend/app/src/components/gamefield/FielderLayer.tsx`:
   - Accept `activeBattedBall?: ActiveBattedBallData | null`.
   - Use `useRef` for tracking elapsed animation time and fielder mesh positions.
   - In `useFrame`, when `activeBattedBall` is active and not paused (`!isBattedBallPaused`):
     - Advance elapsed time.
     - Compute updated positions for all 8 fielders using `computeAllFielderPositions`.
     - Smoothly orient each fielder mesh toward their movement direction (`rotation.y`).
   - When play completes, fielders smoothly ease back to pre-pitch coordinates over 1.2s.
   - Render `CatchIndicator` at `interceptPoint` when the primary fielder arrives at `progress === 1.0` and `fielded === true`.

- [x] **Step 4: Run test to verify it passes**

Run: `cd frontend/app && npm test`  
Expected: ALL PASS (188+ passed).

- [x] **Step 5: Commit**

```bash
git add frontend/app/src/components/gamefield/FielderLayer.tsx frontend/app/src/components/gamefield/CatchIndicator.tsx frontend/app/src/components/gamefield/__tests__/FielderLayerLogic.test.ts
git commit -m "feat(frontend): upgrade FielderLayer with dynamic 3D pursuit animation and catch indicator"
```

---

### Task 4: Scene Wiring, Hit Test Presets & End-to-End Choreography

**Files:**
- Modify: `frontend/app/src/components/gamefield/FieldScene.tsx:260-270`
- Modify: `frontend/app/src/components/gamefield/GameField.tsx:20-55`
- Modify: `frontend/app/src/components/debug/hitPresets.ts:10-150`
- Modify: `frontend/app/src/components/debug/__tests__/hitPresets.test.ts:40-100`
- Test: `frontend/app/src/components/gamefield/__tests__/FieldSceneWiring.test.ts`

**Interfaces:**
- Consumes: `activeBattedBall` prop from `BaseballSimScreen.tsx`.
- Produces:
  - `<FielderLayer activeBattedBall={activeBattedBall} />` in `FieldScene.tsx`.
  - Realistic fielding metadata across all 5 debug presets in `hitPresets.ts` (`ss_chopper`, `1b_grounder`, `line_drive_gap`, `fly_ball_rf`, `moonshot_hr`).

- [x] **Step 1: Write failing test verifying hit presets carry authentic fielding metadata**

```typescript
// In frontend/app/src/components/debug/__tests__/hitPresets.test.ts
it('equips all presets with authentic fielding metadata', () => {
  const ssChopper = HIT_PRESETS.find(p => p.id === 'ss_chopper');
  assert.ok(ssChopper);
  assert.equal(ssChopper.fielded, true);
  assert.equal(ssChopper.fielderId, 'SS');
  assert.equal(ssChopper.fieldingType, 'GROUND_SCOOP');
  assert.ok(Array.isArray(ssChopper.fielderStart));
  assert.ok(Array.isArray(ssChopper.interceptPoint));

  const grounder1B = HIT_PRESETS.find(p => p.id === '1b_grounder');
  assert.ok(grounder1B);
  assert.equal(grounder1B.fielded, true);
  assert.equal(grounder1B.fielderId, '1B');
  assert.equal(grounder1B.fieldingType, 'BACKHAND_PICK');

  const gapDouble = HIT_PRESETS.find(p => p.id === 'line_drive_gap');
  assert.ok(gapDouble);
  assert.equal(gapDouble.fielded, true);
  assert.equal(gapDouble.fielderId, 'LF');
  assert.equal(gapDouble.fieldingType, 'GROUND_SCOOP');

  const moonshot = HIT_PRESETS.find(p => p.id === 'moonshot_hr');
  assert.ok(moonshot);
  assert.equal(moonshot.fielded, false);
  assert.equal(moonshot.fieldingType, 'HOME_RUN');
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd frontend/app && node --experimental-transform-types --loader ./scripts/test-loader.mjs --test src/components/debug/__tests__/hitPresets.test.ts`  
Expected: FAIL with `AssertionError: undefined == true`.

- [x] **Step 3: Update `FieldScene.tsx`, `GameField.tsx`, and `hitPresets.ts`**

1. In `frontend/app/src/components/gamefield/FieldScene.tsx`:
   - Pass `activeBattedBall={activeBattedBall}` to `<FielderLayer activeBattedBall={activeBattedBall} />`.
2. In `frontend/app/src/components/debug/hitPresets.ts`:
   - Extend `HitPreset` type with `{ fielded?: boolean; fielderId?: string; fieldingType?: string; fielderStart?: [number, number]; interceptPoint?: [number, number, number] }`.
   - Update `ss_chopper`: `fielded: true, fielderId: 'SS', fieldingType: 'GROUND_SCOOP', fielderStart: [-45.0, 115.0], interceptPoint: [-38.2, 108.5, 0.0]`.
   - Update `1b_grounder`: `fielded: true, fielderId: '1B', fieldingType: 'BACKHAND_PICK', fielderStart: [63.6, 63.6], interceptPoint: [58.4, 60.1, 0.0]`.
   - Update `fly_ball_rf`: `fielded: true, fielderId: 'RF', fieldingType: 'ROUTINE_FLY_CATCH', fielderStart: [115.0, 255.0], interceptPoint: [102.5, 272.0, 4.5]`.
   - Update `line_drive_gap`: `fielded: true, fielderId: 'LF', fieldingType: 'GROUND_SCOOP', fielderStart: [-115.0, 255.0], interceptPoint: [-75.0, 260.0, 0.0]`.
   - Update `moonshot_hr`: `fielded: false, fielderId: null, fieldingType: 'HOME_RUN'`.
   - Ensure `buildActiveBattedBallFromPreset` forwards these fields to `ActiveBattedBallData`.

- [x] **Step 4: Run full frontend test suite to verify 0 regressions**

Run: `cd frontend/app && npm test`  
Expected: ALL PASS (188+ passed, 0 failed).

- [x] **Step 5: Run full backend test suite to guarantee end-to-end compatibility**

Run: `pytest tests/ -v`  
Expected: ALL PASS (430 passed, 0 failed).

- [x] **Step 6: Commit**

```bash
git add frontend/app/src/components/gamefield/FieldScene.tsx frontend/app/src/components/gamefield/GameField.tsx frontend/app/src/components/debug/hitPresets.ts frontend/app/src/components/debug/__tests__/hitPresets.test.ts
git commit -m "feat(frontend): wire dynamic fielding into FieldScene and calibrate hit test presets"
```

---

## Plan Review Checklist

1. **Spec Alignment:** Realizes the 4D handoff contract `samples[-1] = [x_glove, y_glove, z_glove, t_intercept]` from Section 3.4 and Section 4 of the spec directly in the 3D scene.
2. **Step Granularity:** Every task strictly follows `Write failing test` $\to$ `Verify fail` $\to$ `Implement` $\to$ `Verify pass` $\to$ `Commit`.
3. **Pure Logic Isolation:** Kinematics are cleanly separated into `fielderKinematics.ts`, keeping Three.js rendering code uncluttered and 100% unit-testable in Node without headless canvas dependencies.
4. **Zero Regressions:** Preserves all existing camera tracking modes (`resolveGameCameraMode`, `GameCameraDirector`) and pause states (`isBattedBallPaused`).
5. **Debug Parity:** Developers can test all catch types in isolation directly from the Hit Test Launcher without needing a full backend match simulation.

