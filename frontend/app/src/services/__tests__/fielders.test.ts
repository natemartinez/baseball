import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { FIELDERS, fielderResponsibleFor, fielderForLanding } from '../fielders';

describe('fielders service responsibility radius', () => {
  it('defines responsibility_radius for all fielders', () => {
    assert.equal(FIELDERS.length, 8);
    for (const fielder of FIELDERS) {
      assert.ok(fielder.responsibility_radius > 0);
      assert.equal((fielder as any).radius, undefined);
    }
  });

  it('determines responsible fielder using fielderResponsibleFor', () => {
    const cf = fielderResponsibleFor(0, 330);
    assert.equal(cf?.id, 'CF');
    assert.equal(cf?.responsibility_radius, 80);
  });

  it('provides backward-compatible fielderForLanding alias', () => {
    assert.equal(fielderForLanding, fielderResponsibleFor);
  });
});
