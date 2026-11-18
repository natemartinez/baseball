import { describe, it } from 'node:test';
import assert from 'node:assert';
import { getAbilityTier, getAbilityTierColor } from '../../../services/gamedayMath.ts';
import { calculateCombinedEffectiveCommand } from '../../../services/effectivenessModel.ts';
import type { PitcherInfo } from '../../../types/api.ts';
import {
  resolveInitialWidgetViewMode,
  resolveUpdatedWidgetViewMode,
  canSwitchOrSelectPitch,
  shouldResetToChipsOnPitchComplete,
  type WidgetViewMode,
} from '../pitchSelectorState.ts';

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

  it('differentiates chip effective command based on pitch type difficulty modifier', () => {
    const fbCmd = calculateCombinedEffectiveCommand(80, 50, 80, '4-Seam Fastball');
    const slCmd = calculateCombinedEffectiveCommand(80, 50, 80, 'Slider');
    const cbCmd = calculateCombinedEffectiveCommand(80, 50, 80, 'Curveball');
    assert.strictEqual(fbCmd, 80);
    assert.strictEqual(slCmd, 77); // (1.15 - 1.0) * 20 = 3
    assert.strictEqual(cbCmd, 76); // (1.20 - 1.0) * 20 = 4
    assert.ok(slCmd < fbCmd);
    assert.ok(cbCmd < slCmd);
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

describe('PitchSelectorWidget State Manager Logic', () => {
  it('initializes to "chips" mode so player selects a pitch from the arsenal first', () => {
    const mode = resolveInitialWidgetViewMode('Four-Seam Fastball', ['Four-Seam Fastball', 'Slider']);
    assert.strictEqual(mode, 'chips');
  });

  it('initializes to "chips" mode when selectedPitchName is empty, null, or not in arsenal', () => {
    const emptyMode = resolveInitialWidgetViewMode('', ['Four-Seam Fastball']);
    assert.strictEqual(emptyMode, 'chips');

    const missingMode = resolveInitialWidgetViewMode('Sweeper', ['Four-Seam Fastball', 'Slider']);
    assert.strictEqual(missingMode, 'chips');

    const nullArsenalMode = resolveInitialWidgetViewMode('Slider', undefined);
    assert.strictEqual(nullArsenalMode, 'chips');

    const nullSelectedMode = resolveInitialWidgetViewMode(null, ['Four-Seam Fastball']);
    assert.strictEqual(nullSelectedMode, 'chips');
  });

  it('respects explicit initialMode parameter if specified', () => {
    assert.strictEqual(resolveInitialWidgetViewMode('Slider', ['Slider'], 'throw'), 'throw');
    assert.strictEqual(resolveInitialWidgetViewMode('Slider', ['Slider'], 'chips'), 'chips');
  });

  it('transitions correctly between chips and throw views', () => {
    let mode: WidgetViewMode = 'chips';
    const selectPitch = (name: string) => {
      mode = 'throw';
    };
    const changePitch = () => {
      mode = 'chips';
    };

    selectPitch('Slider');
    assert.strictEqual(mode, 'throw');

    changePitch();
    assert.strictEqual(mode, 'chips');
  });

  it('disables pitch changing and throwing when isActionPending or disabled is true', () => {
    const isActionPending = true;
    const disabled = false;
    const selectedPitchName = 'Slider';

    const canChangePitch = !disabled && !isActionPending;
    const canThrow = !disabled && !isActionPending && Boolean(selectedPitchName);

    assert.strictEqual(canChangePitch, false);
    assert.strictEqual(canThrow, false);
  });

  it('selects recommended pitch from strategy intent and transitions to throw mode', () => {
    let mode: WidgetViewMode = 'chips';
    let currentPitch = 'Four-Seam Fastball';

    const onSelectPitchName = (name: string) => {
      currentPitch = name;
      mode = 'throw';
    };

    const strategyIntent = {
      situation_tag: 'BEHIND_IN_COUNT',
      recommended_pitch: 'Slider',
      recommended_zone: 'low_away',
    };

    onSelectPitchName(strategyIntent.recommended_pitch);
    assert.strictEqual(currentPitch, 'Slider');
    assert.strictEqual(mode, 'throw');
  });

  it('resets to chips mode when pitch execution completes', () => {
    assert.strictEqual(shouldResetToChipsOnPitchComplete(true, false), true);
    assert.strictEqual(shouldResetToChipsOnPitchComplete(false, false), false);
    assert.strictEqual(shouldResetToChipsOnPitchComplete(true, true), false);
    assert.strictEqual(shouldResetToChipsOnPitchComplete(false, true), false);
  });

  it('safely handles empty or null pitcher arsenal in state manager', () => {
    const emptyArsenalPitchNames: string[] = [];
    const mode = resolveInitialWidgetViewMode('Slider', emptyArsenalPitchNames);
    assert.strictEqual(mode, 'chips');
  });

  it('correctly handles pitcher substitution via resolveUpdatedWidgetViewMode', () => {
    // Relief pitcher enters who does NOT throw 'Cutter'
    const updatedMode = resolveUpdatedWidgetViewMode('throw', 'Cutter', ['Four-Seam Fastball', 'Changeup']);
    assert.strictEqual(updatedMode, 'chips');

    // Relief pitcher enters who DOES throw the selected pitch
    const sameMode = resolveUpdatedWidgetViewMode('throw', 'Four-Seam Fastball', ['Four-Seam Fastball', 'Changeup']);
    assert.strictEqual(sameMode, 'throw');

    // When in chips mode, stays in chips mode so player can select next pitch
    const chipsMode = resolveUpdatedWidgetViewMode('chips', 'Changeup', ['Four-Seam Fastball', 'Changeup']);
    assert.strictEqual(chipsMode, 'chips');
  });

  it('evaluates canSwitchOrSelectPitch correctly based on disabled and isActionPending', () => {
    assert.strictEqual(canSwitchOrSelectPitch(false, false), true);
    assert.strictEqual(canSwitchOrSelectPitch(true, false), false);
    assert.strictEqual(canSwitchOrSelectPitch(false, true), false);
    assert.strictEqual(canSwitchOrSelectPitch(true, true), false);
  });
});
