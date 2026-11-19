import { describe, it } from 'node:test';
import assert from 'node:assert';
import { formatMatchupPlayerInfo } from '../scorebugMatchupState.ts';

describe('Scorebug Matchup Preview data formatting', () => {
  it('displays full names and sub-meta for batter and pitcher', () => {
    const batter = {
      name: 'Aaron Judge',
      position: 'CF',
      handedness: 'R' as const,
      power: 99,
      contact: 92,
      vision: 88,
    };
    const pitcher = {
      name: 'Nolan McLean',
      position: 'SP',
      throws: 'R' as const,
      control: 78,
      break_rating: 84,
      velocity_rating: 92,
    };

    const info = formatMatchupPlayerInfo(batter, pitcher);

    assert.strictEqual(info.batterName, 'Aaron Judge');
    assert.strictEqual(info.pitcherName, 'Nolan McLean');
    assert.strictEqual(info.batterMeta, 'CF • RHB');
    assert.strictEqual(info.pitcherMeta, 'SP • RHP');
  });

  it('formats side-by-side matchup stats for batter (PWR, CON, VIS) and pitcher (CMD, BRK, VEL)', () => {
    const batter = {
      name: 'Juan Soto',
      power: 94,
      contact: 96,
      vision: 99,
    };
    const pitcher = {
      name: 'Gerrit Cole',
      control: 82,
      break_rating: 85,
      velocity_rating: 97,
    };

    const info = formatMatchupPlayerInfo(batter, pitcher);

    assert.deepStrictEqual(info.batterStats, {
      pwr: 94,
      con: 96,
      vis: 99,
    });

    assert.deepStrictEqual(info.pitcherStats, {
      cmd: 82,
      brk: 85,
      vel: 97,
    });
  });

  it('handles missing batter or pitcher data gracefully with default fallbacks', () => {
    const info = formatMatchupPlayerInfo(null, null);

    assert.strictEqual(info.batterName, 'Batter');
    assert.strictEqual(info.pitcherName, 'Pitcher');
    assert.strictEqual(info.batterMeta, '');
    assert.strictEqual(info.pitcherMeta, '');
    assert.strictEqual(info.batterStats.pwr, undefined);
    assert.strictEqual(info.batterStats.con, undefined);
    assert.strictEqual(info.batterStats.vis, undefined);
    assert.strictEqual(info.pitcherStats.cmd, undefined);
    assert.strictEqual(info.pitcherStats.brk, undefined);
    assert.strictEqual(info.pitcherStats.vel, undefined);
  });

  it('normalizes handedness and throwing hand correctly', () => {
    const batter = {
      name: 'Francisco Lindor',
      position: 'SS',
      handedness: 'S',
    };
    const pitcher = {
      name: 'Carlos Rodon',
      position: 'SP',
      throws: 'L',
      control: 80,
      break_rating: 86,
      velocity_rating: 94,
    };

    const info = formatMatchupPlayerInfo(batter, pitcher);

    assert.strictEqual(info.batterMeta, 'SS • SHB');
    assert.strictEqual(info.pitcherMeta, 'SP • LHP');
  });
});
