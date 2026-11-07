import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  MAX_ERROR_RADIUS_TIERS,
  getMaxErrorRadiusInches,
} from '../gamedayMath.ts';

describe('Gameday Math Radius Tiers', () => {
  it('has Elite (99) error radius equal to the former Great radius (1.50")', () => {
    assert.equal(getMaxErrorRadiusInches(99), 1.50);
  });

  it('evaluates exact anchor tiers proportionally scaled by 1.5x', () => {
    assert.equal(getMaxErrorRadiusInches(99), 1.50);
    assert.equal(getMaxErrorRadiusInches(90), 1.875);
    assert.equal(getMaxErrorRadiusInches(82), 2.25);
    assert.equal(getMaxErrorRadiusInches(68), 4.50);
    assert.equal(getMaxErrorRadiusInches(55), 6.75);
    assert.equal(getMaxErrorRadiusInches(40), 10.50);
  });

  it('interpolates linearly between tiers', () => {
    // 85 command is halfway between 90 (1.875) and 82 (2.25)
    // t = (90 - 85) / (90 - 82) = 5 / 8 = 0.625
    // radius = 1.875 + (2.25 - 1.875) * 0.625 = 2.109375
    const r85 = getMaxErrorRadiusInches(85);
    assert.ok(Math.abs(r85 - 2.109375) < 1e-4, `Expected ~2.109, got ${r85}`);
  });

  it('clamps commands outside [40, 99]', () => {
    assert.equal(getMaxErrorRadiusInches(20), 10.50);
    assert.equal(getMaxErrorRadiusInches(0), 10.50);
    assert.equal(getMaxErrorRadiusInches(120), 1.50);
  });
});
