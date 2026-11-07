import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  calculatePitchPoint,
  resolveHorizontalBreakInches,
} from '../pitchTrajectory.ts';
import { pitchPointAt } from '../../components/gamefield/pitchPath.ts';

describe('Pitch handedness break resolution', () => {
  it('keeps RHP glove-side break on the first-base side', () => {
    assert.equal(resolveHorizontalBreakInches(18.2, 'R'), 18.2);
    assert.equal(resolveHorizontalBreakInches(-14.0, 'R'), -14.0);
  });

  it('mirrors LHP glove-side break to the third-base side', () => {
    assert.equal(resolveHorizontalBreakInches(18.2, 'L'), -18.2);
    assert.equal(resolveHorizontalBreakInches(-14.0, 'L'), 14.0);
  });
});

describe('2D pitch path handedness', () => {
  const target = { x: 0, y: 1.417, z: 2.5 };

  it('mirrors the horizontal path for LHP while both end at the target', () => {
    const rightRelease = { x: -2.1, y: 54.5, z: 5.9 };
    const leftRelease = { x: 2.1, y: 54.5, z: 5.9 };

    for (const t of [0.25, 0.5, 0.75]) {
      const right = calculatePitchPoint(t, rightRelease, target, 18.2, 4.5, 'R');
      const left = calculatePitchPoint(t, leftRelease, target, 18.2, 4.5, 'L');
      assert.ok(Math.abs(left.x + right.x) < 1e-9);
      assert.equal(left.y, right.y);
      assert.equal(left.z, right.z);
    }

    const rightEnd = calculatePitchPoint(1, rightRelease, target, 18.2, 4.5, 'R');
    const leftEnd = calculatePitchPoint(1, leftRelease, target, 18.2, 4.5, 'L');
    assert.ok(Math.abs(rightEnd.x - target.x) < 1e-9);
    assert.ok(Math.abs(leftEnd.x - target.x) < 1e-9);
  });
});

describe('3D pitch path signed break', () => {
  const release: [number, number, number] = [-2.1, 5.9, -54.5];
  const plate: [number, number, number] = [0, 2.5, 0];

  it('keeps the endpoint at the plate and bends toward signed pfx', () => {
    const path = {
      release,
      plate,
      pfx: [18.2 / 12, 4.5 / 12] as [number, number],
      flightTime: 0.4,
    };

    const end = pitchPointAt(path.flightTime, path);
    assert.ok(Math.abs(end.x - plate[0]) < 1e-9);
    assert.ok(Math.abs(end.y - plate[1]) < 1e-9);

    const mid = pitchPointAt(path.flightTime / 2, path);
    assert.ok(mid.x > release[0]);
  });

  it('mirrors a sweeper for LHP when pfx is pre-signed', () => {
    const rightPath = {
      release,
      plate,
      pfx: [18.2 / 12, 4.5 / 12] as [number, number],
      flightTime: 0.4,
    };
    const leftPath = {
      release: [2.1, 5.9, -54.5] as [number, number, number],
      plate,
      pfx: [-18.2 / 12, 4.5 / 12] as [number, number],
      flightTime: 0.4,
    };

    const rightMid = pitchPointAt(rightPath.flightTime / 2, rightPath);
    const leftMid = pitchPointAt(leftPath.flightTime / 2, leftPath);
    assert.ok(Math.abs(leftMid.x + rightMid.x) < 1e-9);
  });
});
