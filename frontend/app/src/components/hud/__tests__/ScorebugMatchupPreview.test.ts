import { describe, it } from 'node:test';
import assert from 'node:assert';
import { getAbilityTier, getAbilityTierColor } from '../../../services/gamedayMath.ts';

describe('Scorebug Matchup Preview pitch data formatting', () => {
  it('formats selected pitch stats and tier badge correctly', () => {
    const selectedPitchName = 'Slider';
    const effectiveCommand = 88.4;
    const abilityTier = getAbilityTier(effectiveCommand);
    const tierColor = getAbilityTierColor(abilityTier);

    assert.strictEqual(abilityTier, 'GREAT');
    assert.strictEqual(tierColor, '#3B82F6');
    assert.strictEqual(Math.round(effectiveCommand), 88);
  });
});

