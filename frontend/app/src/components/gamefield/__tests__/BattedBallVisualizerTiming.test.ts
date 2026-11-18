import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  resolveTrajectoryInterpolation,
  sampleBallScenePosition,
  sampleBallGroundTrajectory,
} from '../../camera/cameraShots';

describe('Batted Ball Trajectory Time-Aware Sampling', () => {
  it('resolves interpolation segment and alpha using sample timestamps', () => {
    // Segment 0->1 takes 0.5s (covers 60 ft), segment 1->2 takes 1.5s (covers next 40 ft)
    const samples: [number, number, number, number][] = [
      [0, 0, 3, 0.0],
      [0, 60, 0, 0.5],
      [0, 100, 0, 2.0],
    ];

    // At t = 0.25s (halfway through first segment in time):
    const res = resolveTrajectoryInterpolation(samples, 0.25, 2.0);
    assert.equal(res.index, 0);
    assert.equal(res.nextIndex, 1);
    assert.ok(Math.abs(res.alpha - 0.5) < 1e-4);

    // Ball position should be at y = 30 ft (Three.js Z = -30)
    const scenePos = sampleBallScenePosition(samples, 0.25, 2.0);
    assert.ok(Math.abs(scenePos[2] - (-30)) < 0.5);

    // Camera ground position should match ball ground position exactly
    const groundTraj = sampleBallGroundTrajectory(samples, 0.25, 2.0);
    assert.ok(Math.abs(groundTraj.groundPos[2] - (-30)) < 0.5);
  });

  it('falls back to uniform linear progress when 3D samples have no timestamps', () => {
    const legacySamples: [number, number, number][] = [
      [0, 0, 3],
      [0, 50, 10],
      [0, 100, 0],
    ];

    // At t = 1.0s of 2.0s duration (progress = 0.5):
    const res = resolveTrajectoryInterpolation(legacySamples, 1.0, 2.0);
    assert.equal(res.index, 1);
    assert.equal(res.nextIndex, 2);
    assert.equal(res.alpha, 0.0);

    const scenePos = sampleBallScenePosition(legacySamples, 1.0, 2.0);
    assert.equal(scenePos[2], -50);
  });

  it('safely locks to final sample at or beyond duration', () => {
    const samples: [number, number, number, number][] = [
      [0, 0, 3, 0.0],
      [0, 100, 0, 2.0],
    ];
    const res = resolveTrajectoryInterpolation(samples, 2.5, 2.0);
    assert.equal(res.index, 1);
    assert.equal(res.nextIndex, 1);
    assert.equal(res.alpha, 1.0);

    const scenePos = sampleBallScenePosition(samples, 2.5, 2.0);
    assert.equal(scenePos[2], -100);
  });
});
