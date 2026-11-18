import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  MAX_ERROR_RADIUS_TIERS,
  getMaxErrorRadiusInches,
} from '../gamedayMath.ts';

describe('Gameday Math Radius Tiers', () => {
  it('has Elite (99) error radius of 3.00"', () => {
    assert.equal(getMaxErrorRadiusInches(99), 3.00);
  });

  it('evaluates exact anchor tiers proportionally scaled', () => {
    assert.equal(getMaxErrorRadiusInches(99), 3.00);
    assert.equal(getMaxErrorRadiusInches(90), 3.75);
    assert.equal(getMaxErrorRadiusInches(82), 4.50);
    assert.equal(getMaxErrorRadiusInches(68), 9.00);
    assert.equal(getMaxErrorRadiusInches(55), 13.50);
    assert.equal(getMaxErrorRadiusInches(40), 21.00);
  });

  it('interpolates linearly between tiers', () => {
    // 85 command is halfway between 90 (3.75) and 82 (4.50)
    // t = (90 - 85) / (90 - 82) = 5 / 8 = 0.625
    // radius = 3.75 + (4.50 - 3.75) * 0.625 = 4.21875
    const r85 = getMaxErrorRadiusInches(85);
    assert.ok(Math.abs(r85 - 4.21875) < 1e-4, `Expected ~4.219, got ${r85}`);
  });

  it('clamps commands outside [40, 99]', () => {
    assert.equal(getMaxErrorRadiusInches(20), 21.00);
    assert.equal(getMaxErrorRadiusInches(0), 21.00);
    assert.equal(getMaxErrorRadiusInches(120), 3.00);
  });
});
