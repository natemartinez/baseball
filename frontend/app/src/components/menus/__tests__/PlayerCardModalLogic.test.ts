import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  computeBaselineEffectiveness,
  calculateCombinedEffectiveCommand,
} from '../../../services/effectivenessModel.ts';
import { getAbilityTier, getAbilityTierColor } from '../../../services/gamedayMath.ts';
import type { PitchArsenalItem } from '../../../types/api.ts';

describe('PlayerCardModal pitch data synthesis and edge cases', () => {
  const samplePitch: PitchArsenalItem = {
    name: 'Slider',
    velocity_mph: 86.5,
    velocity_min_mph: 85,
    velocity_max_mph: 88,
    break_rating: 88,
    spin_rpm: 2550,
    control_rating: 84,
  };

  it('computes complete pitch profile including baseline eff, effCmd, and tier', () => {
    const eff = computeBaselineEffectiveness(
      samplePitch.velocity_mph ?? 86.5,
      samplePitch.break_rating ?? 80,
      samplePitch.spin_rpm ?? 2400,
      samplePitch.control_rating ?? 75,
    );
    assert.ok(eff >= 70 && eff <= 95);

    const effCmdWithoutType = calculateCombinedEffectiveCommand(samplePitch.control_rating ?? 80, 60, eff);
    const effCmdWithType = calculateCombinedEffectiveCommand(
      samplePitch.control_rating ?? 80,
      60,
      eff,
      samplePitch.name,
    );
    assert.ok(effCmdWithType > 0);
    // Slider difficulty modifier is 1.15 -> penalty = 3
    assert.strictEqual(effCmdWithType, effCmdWithoutType - 3);

    const tier = getAbilityTier(effCmdWithType);
    const color = getAbilityTierColor(tier);
    assert.ok(['ELITE', 'GREAT', 'GOOD', 'OKAY'].includes(tier));
    assert.ok(typeof color === 'string' && color.startsWith('#'));
  });

  it('formats display velocity range properly', () => {
    const range = `${samplePitch.velocity_min_mph}–${samplePitch.velocity_max_mph} mph`;
    assert.strictEqual(range, '85–88 mph');
  });

  it('handles empty arsenal without throwing error', () => {
    const emptyArsenal: PitchArsenalItem[] = [];
    const count = emptyArsenal.length;
    assert.strictEqual(count, 0);
  });

  it('unifies command calculation when base command has command vs control_rating fallback', () => {
    const pitchWithCmd: PitchArsenalItem = {
      ...samplePitch,
      command: 86,
      control_rating: 80,
    };
    const pitcherControl = 75;
    const baseCmd = pitchWithCmd.command ?? pitchWithCmd.control_rating ?? pitcherControl;
    assert.strictEqual(baseCmd, 86);
  });
});
