import { describe, it } from 'node:test';
import assert from 'node:assert';
import { getAbilityTier, getAbilityTierColor } from '../../../services/gamedayMath.ts';
import { calculateCombinedEffectiveCommand } from '../../../services/effectivenessModel.ts';
import type { PitcherInfo } from '../../../types/api.ts';

describe('PitchSelectorWidget ArsenalChip Visual Logic', () => {
  it('computes correct ability tier and color for pitch effective command', () => {
    const effCmdHigh = calculateCombinedEffectiveCommand(90, 80, 92);
    const tierHigh = getAbilityTier(effCmdHigh);
    const colorHigh = getAbilityTierColor(tierHigh);
    assert.strictEqual(tierHigh, 'ELITE');
    assert.strictEqual(colorHigh, '#8B5CF6');

    const effCmdMid = calculateCombinedEffectiveCommand(75, 50, 75);
    const tierMid = getAbilityTier(effCmdMid);
    const colorMid = getAbilityTierColor(tierMid);
    assert.ok(['GREAT', 'GOOD', 'OKAY'].includes(tierMid));
    assert.ok(typeof colorMid === 'string' && colorMid.startsWith('#'));
  });

  it('safely handles pitcher with undefined or null arsenal', () => {
    const pitcherWithoutArsenal = {
      id: 1,
      name: 'Test Pitcher',
      team: 'NYM',
    } as unknown as PitcherInfo;

    const arsenal = pitcherWithoutArsenal.arsenal ?? [];
    assert.strictEqual(arsenal.length, 0);

    const found = arsenal.find(p => p.name === 'Fastball');
    assert.strictEqual(found, undefined);

    const chips = arsenal.map(item => item.name);
    assert.deepStrictEqual(chips, []);
  });
});
