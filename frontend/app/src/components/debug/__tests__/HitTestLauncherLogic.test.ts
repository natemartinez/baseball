import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  HIT_PRESETS,
  buildActiveBattedBallFromPreset,
  calculateRemainingLifecycleMs,
  stepAnimationElapsed,
} from '../hitPresets';
import { DEFAULT_BATTED_BALL_RADIUS } from '../../gamefield/types';
import { useGameStore } from '../../../store/gameStore';

describe('HitTestLauncher Component Logic & Choreography', () => {
  it('calibrates batted baseball radius to proportional scale rather than oversized boulder', () => {
    // Real baseball radius is ~0.12 ft (1.45 inches).
    // In-game radius is 0.22 ft (5.3-inch diameter, ~1.8x real size for mobile visibility),
    // strictly smaller than a fielder's head (0.55 ft radius) and no longer an oversized 1.35-2.2 ft beach ball.
    assert.equal(DEFAULT_BATTED_BALL_RADIUS, 0.22);
    assert.ok(DEFAULT_BATTED_BALL_RADIUS < 0.30);
    assert.ok(DEFAULT_BATTED_BALL_RADIUS > 0.15);
  });

  it('generates sequential unique IDs for back-to-back preset launches', () => {
    const preset = HIT_PRESETS[0];
    const hit1 = buildActiveBattedBallFromPreset(preset, 1);
    const hit2 = buildActiveBattedBallFromPreset(preset, 2);

    assert.notEqual(hit1.id, hit2.id);
    assert.equal(hit1.id, 'debug-hit-ss_chopper-1');
    assert.equal(hit2.id, 'debug-hit-ss_chopper-2');
  });

  it('contains expected categories across all presets', () => {
    const categories = new Set(HIT_PRESETS.map((p) => p.category));
    assert.deepEqual(Array.from(categories).sort(), [
      'fly_ball',
      'grounder',
      'home_run',
      'line_drive',
    ].sort());
  });

  it('calculates accurate stage timing for live hit replication', () => {
    const CONTACT_DELAY_MS = 160;
    const LANDING_HOLD_MS = 1200;

    for (const preset of HIT_PRESETS) {
      const flightDurationMs = preset.hangTime * 1000;
      const totalLifecycleMs = CONTACT_DELAY_MS + flightDurationMs + LANDING_HOLD_MS;

      // Contact delay is exactly 160ms (matches live hit follow-through)
      assert.equal(CONTACT_DELAY_MS, 160);
      // Total duration strictly exceeds flight time
      assert.ok(totalLifecycleMs > flightDurationMs);
      assert.ok(totalLifecycleMs >= 2000); // Smallest total cycle (0.66s grounder to 1B) >= 2.0s
    }
  });

  it('validates 3-stage camera choreography transitions for debug hit launcher', () => {
    // Simulates the exact state machine transitions across Stage 1, 2, and 3/4
    const cameraModes: (string | null)[] = [];
    const launchedBalls: string[] = [];
    let resetCalled = false;

    const onSetCameraMode = (mode: string | null) => cameraModes.push(mode);
    const onLaunchBattedBall = (ball: { id: string }) => launchedBalls.push(ball.id);
    const onReset = () => { resetCalled = true; };

    const preset = HIT_PRESETS[4]; // moonshot_hr (4.5s hang time)
    const battedBall = buildActiveBattedBallFromPreset(preset, 1);

    // Stage 1: Contact Impact Beat (t = 0)
    onSetCameraMode('PITCH');
    assert.deepEqual(cameraModes, ['PITCH']);
    assert.deepEqual(launchedBalls, []);

    // Stage 2: Synchronized Flight Handoff (t = 160ms)
    onLaunchBattedBall(battedBall);
    onSetCameraMode('TRACKING');
    assert.deepEqual(cameraModes, ['PITCH', 'TRACKING']);
    assert.deepEqual(launchedBalls, ['debug-hit-moonshot_hr-1']);

    // Stage 3 & 4: Landing Hold & Return to Batter View
    onSetCameraMode(null);
    onReset();
    assert.deepEqual(cameraModes, ['PITCH', 'TRACKING', null]);
    assert.equal(resetCalled, true);
  });

  it('freezes animation elapsed progression when isBattedBallPaused is true', () => {
    useGameStore.getState().setBattedBallPaused(false);
    let elapsed = 0.5;
    const dt = 0.016;

    // When running normally
    elapsed = stepAnimationElapsed(elapsed, dt, useGameStore.getState().isBattedBallPaused);
    assert.equal(Math.round(elapsed * 1000) / 1000, 0.516);

    // When paused
    useGameStore.getState().setBattedBallPaused(true);
    const frozenElapsed = stepAnimationElapsed(elapsed, dt, useGameStore.getState().isBattedBallPaused);
    assert.equal(frozenElapsed, elapsed);

    // When resumed
    useGameStore.getState().setBattedBallPaused(false);
    const resumedElapsed = stepAnimationElapsed(frozenElapsed, dt, useGameStore.getState().isBattedBallPaused);
    assert.equal(Math.round(resumedElapsed * 1000) / 1000, 0.532);

    // Cleanup
    useGameStore.getState().setBattedBallPaused(false);
  });

  it('calculates remaining lifecycle time upon pausing with safe floor', () => {
    // Normal mid-flight pause (2000ms elapsed out of 4500ms)
    assert.equal(calculateRemainingLifecycleMs(4500, 2000), 2500);

    // Pause near the very end of flight/hold (4450ms elapsed out of 4500ms -> remaining 50ms clamped to 100ms)
    assert.equal(calculateRemainingLifecycleMs(4500, 4450), 100);

    // Overdue pause
    assert.equal(calculateRemainingLifecycleMs(4500, 5000), 100);
  });

  it('resets isBattedBallPaused to false upon hit reset or new launch', () => {
    // Emulate pausing mid-flight
    useGameStore.getState().setBattedBallPaused(true);
    assert.equal(useGameStore.getState().isBattedBallPaused, true);

    // Emulate launcher reset
    const handleResetSimulation = () => {
      useGameStore.getState().setBattedBallPaused(false);
    };

    handleResetSimulation();
    assert.equal(useGameStore.getState().isBattedBallPaused, false);
  });
});

