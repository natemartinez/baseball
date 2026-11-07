import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  computeBaselineEffectiveness,
  calculateEffectivenessDelta,
  applyStaminaFatigueToEffectiveness,
  updatePitchEffectiveness,
  applyEffectivenessToWhiffRate,
  applyEffectivenessToExitVelocity,
  calculateCommandAdjustmentFromEffectiveness,
  calculateCombinedEffectiveCommand,
  applyEffectivenessToVelocity,
  applyEffectivenessToBreak,
  NEUTRAL_EFFECTIVENESS_BASELINE,
  CONFIDENCE_DRAG_THRESHOLD,
  CONFIDENCE_DRAG_MAX,
  FATIGUE_EFFECTIVENESS_MAX_PENALTY,
} from '../effectivenessModel.ts';
import { evaluateChargingTiming, getAbilityTier } from '../gamedayMath.ts';

describe('Pitch Effectiveness Model', () => {
  describe('computeBaselineEffectiveness', () => {
    it('elite pitch starts near the high end [88, 95]', () => {
      const baseline = computeBaselineEffectiveness(98.0, 95.0, 3200, 90.0);
      assert.ok(baseline >= 88.0 && baseline <= 95.0, `Expected 88-95, got ${baseline}`);
    });

    it('always returns values in [70, 95] range', () => {
      const low = computeBaselineEffectiveness(60, 0, 1000, 30);
      const high = computeBaselineEffectiveness(105, 100, 4000, 99);
      assert.ok(low >= 70.0, `Low should be >= 70, got ${low}`);
      assert.ok(high <= 95.0, `High should be <= 95, got ${high}`);
    });

    it('fastball with more velocity has higher baseline than slower offspeed', () => {
      const fb = computeBaselineEffectiveness(95, 80, 2400, 82);
      const ch = computeBaselineEffectiveness(82, 70, 1800, 78);
      assert.ok(fb > ch, `Fastball (${fb}) should be higher than changeup (${ch})`);
    });
  });

  describe('calculateEffectivenessDelta', () => {
    it('home run causes largest effectiveness degradation', () => {
      const hrDelta = calculateEffectivenessDelta('HOME_RUN', 100);
      const tripleDelta = calculateEffectivenessDelta('TRIPLE', 100);
      const doubleDelta = calculateEffectivenessDelta('DOUBLE', 100);
      const singleDelta = calculateEffectivenessDelta('SINGLE', 100);

      assert.ok(hrDelta < 0);
      assert.ok(hrDelta < tripleDelta);
      assert.ok(tripleDelta < doubleDelta);
      assert.ok(doubleDelta < singleDelta);
      assert.ok(singleDelta < 0);
    });

    it('swinging strike recovers effectiveness the most', () => {
      const swinging = calculateEffectivenessDelta('SWINGING_STRIKE', 100);
      const out = calculateEffectivenessDelta('IN_PLAY_OUT', 100);
      const called = calculateEffectivenessDelta('CALLED_STRIKE', 100);

      assert.ok(swinging > 0);
      assert.ok(swinging > out);
      assert.ok(out > called);
    });

    it('fatigue reduces recovery rate (lower stamina = smaller positive delta)', () => {
      const freshRecovery = calculateEffectivenessDelta('SWINGING_STRIKE', 100);
      const tiredRecovery = calculateEffectivenessDelta('SWINGING_STRIKE', 20);
      assert.ok(tiredRecovery < freshRecovery);
      assert.ok(tiredRecovery > 0); // Still positive but reduced
    });

    it('confidence below threshold causes minor drag', () => {
      const neutralConf = calculateEffectivenessDelta('BALL', 100, 50);
      const lowConf = calculateEffectivenessDelta('BALL', 100, 10);
      assert.ok(lowConf < neutralConf, `Low conf (${lowConf}) should be less than neutral (${neutralConf})`);
    });

    it('confidence above threshold causes no drag', () => {
      const conf50 = calculateEffectivenessDelta('BALL', 100, 50);
      const conf80 = calculateEffectivenessDelta('BALL', 100, 80);
      assert.strictEqual(conf50, conf80);
    });

    it('confidence drag is minor — much smaller than hard-contact degradation', () => {
      const maxConfDrag = CONFIDENCE_DRAG_MAX;
      const hrDeg = Math.abs(calculateEffectivenessDelta('HOME_RUN', 100, 0));
      assert.ok(maxConfDrag < hrDeg * 0.5, `Conf drag (${maxConfDrag}) should be << HR degradation (${hrDeg})`);
    });
  });

  describe('SEPARATION: Effectiveness is independent of Confidence', () => {
    it('identical outcomes with different (non-extreme) confidence produce identical effectiveness deltas', () => {
      const d50 = calculateEffectivenessDelta('SWINGING_STRIKE', 100, 50);
      const d80 = calculateEffectivenessDelta('SWINGING_STRIKE', 100, 80);
      const dNone = calculateEffectivenessDelta('SWINGING_STRIKE', 100, undefined);
      assert.strictEqual(d50, d80);
      assert.strictEqual(d50, dNone);
    });
  });

  describe('applyEffectivenessToWhiffRate', () => {
    it('neutral effectiveness (80) does not change whiff probability', () => {
      const base = 0.30;
      const adjusted = applyEffectivenessToWhiffRate(base, NEUTRAL_EFFECTIVENESS_BASELINE);
      assert.ok(Math.abs(adjusted - base) < 0.001, `Expected ~${base}, got ${adjusted}`);
    });

    it('high effectiveness increases whiff rate', () => {
      const base = 0.25;
      const adjusted = applyEffectivenessToWhiffRate(base, 95.0);
      assert.ok(adjusted > base, `High eff whiff (${adjusted}) should exceed base (${base})`);
    });

    it('low effectiveness decreases whiff rate', () => {
      const base = 0.25;
      const adjusted = applyEffectivenessToWhiffRate(base, 55.0);
      assert.ok(adjusted < base, `Low eff whiff (${adjusted}) should be below base (${base})`);
    });
  });

  describe('applyEffectivenessToExitVelocity', () => {
    it('neutral effectiveness (80) does not change exit velocity', () => {
      const base = 90.0;
      const adjusted = applyEffectivenessToExitVelocity(base, NEUTRAL_EFFECTIVENESS_BASELINE);
      assert.ok(Math.abs(adjusted - base) < 0.01, `Expected ~${base}, got ${adjusted}`);
    });

    it('low effectiveness increases exit velocity (flat pitch)', () => {
      const base = 88.0;
      const adjusted = applyEffectivenessToExitVelocity(base, 50.0);
      assert.ok(adjusted > base, `Low eff EV (${adjusted}) should exceed base (${base})`);
    });

    it('high effectiveness suppresses exit velocity (sharp stuff)', () => {
      const base = 88.0;
      const adjusted = applyEffectivenessToExitVelocity(base, 95.0);
      assert.ok(adjusted < base, `High eff EV (${adjusted}) should be below base (${base})`);
    });
  });

  describe('Effectiveness Command, Timing & Delivery Scaling', () => {
    it('calculates command adjustments relative to baseline 80', () => {
      assert.strictEqual(calculateCommandAdjustmentFromEffectiveness(80.0), 0);
      assert.strictEqual(calculateCommandAdjustmentFromEffectiveness(90.0), 6.0);
      assert.strictEqual(calculateCommandAdjustmentFromEffectiveness(100.0), 12.0);
      assert.strictEqual(calculateCommandAdjustmentFromEffectiveness(75.0), -3.75);
      assert.strictEqual(calculateCommandAdjustmentFromEffectiveness(60.0), -15.0);
    });

    it('combined effective command incorporates both confidence and pitch effectiveness', () => {
      // Base command 90, neutral confidence 50, 90 effectiveness (+6)
      const p1 = calculateCombinedEffectiveCommand(90.0, 50.0, 90.0);
      assert.strictEqual(p1, 96.0);

      // Base command 90, neutral confidence 50, 75 effectiveness (-3.75 -> rounded to 86.3)
      const p2 = calculateCombinedEffectiveCommand(90.0, 50.0, 75.0);
      assert.strictEqual(p2, 86.3);

      assert.ok(p1 > p2);
      // Pitcher 1 remains ELITE (>= 90), Pitcher 2 drops into GREAT (< 90)
      assert.strictEqual(getAbilityTier(p1), 'ELITE');
      assert.strictEqual(getAbilityTier(p2), 'GREAT');
    });

    it('Pitcher 1 (90 Eff) throws consistently faster than Pitcher 2 (75 Eff)', () => {
      const baseVelo = 95.0;
      const veloP1 = applyEffectivenessToVelocity(baseVelo, 90.0);
      const veloP2 = applyEffectivenessToVelocity(baseVelo, 75.0);

      assert.ok(veloP1 > baseVelo, `P1 (${veloP1}) should exceed base (${baseVelo})`);
      assert.ok(veloP2 < baseVelo, `P2 (${veloP2}) should be lower than base (${baseVelo})`);
      assert.ok(veloP1 - veloP2 >= 2.0, `Velo gap (${veloP1 - veloP2}) should be >= 2.0 mph`);
    });

    it('Pitcher 1 (90 Eff) has sharper bite (break) than Pitcher 2 (75 Eff)', () => {
      const hbBase = -6.0;
      const ivbBase = 16.0;
      const [hbP1, ivbP1] = applyEffectivenessToBreak(hbBase, ivbBase, 90.0);
      const [hbP2, ivbP2] = applyEffectivenessToBreak(hbBase, ivbBase, 75.0);

      assert.ok(Math.abs(hbP1) > Math.abs(hbBase) && Math.abs(hbBase) > Math.abs(hbP2));
      assert.ok(Math.abs(ivbP1) > Math.abs(ivbBase) && Math.abs(ivbBase) > Math.abs(ivbP2));
      assert.ok(ivbP1 - ivbP2 > 1.5, `IVB gap (${ivbP1 - ivbP2}) should be > 1.5 in`);
    });

    it('Pitcher 1 (90 Eff) has a wider charging timing window than Pitcher 2 (75 Eff)', () => {
      const sweetSpotMs = 1000.0;

      // Hold time 1055 ms (ratio 1.055):
      // On 90% effectiveness: within expanded PERFECT window (ratio <= 1.0575)
      // On 75% effectiveness: outside contracted PERFECT window (ratio > 1.0481), slips to GOOD
      const resultP1 = evaluateChargingTiming(1055, sweetSpotMs, 90.0);
      const resultP2 = evaluateChargingTiming(1055, sweetSpotMs, 75.0);
      assert.strictEqual(resultP1.timingTier, 'PERFECT');
      assert.strictEqual(resultP2.timingTier, 'GOOD');

      // Hold time 840 ms (ratio 0.840):
      // On 90% effectiveness: within expanded GOOD window (ratio >= 0.8275)
      // On 75% effectiveness: outside contracted GOOD window (ratio < 0.8556), slips to OKAY
      const goodCheckP1 = evaluateChargingTiming(840, sweetSpotMs, 90.0);
      const goodCheckP2 = evaluateChargingTiming(840, sweetSpotMs, 75.0);
      assert.strictEqual(goodCheckP1.timingTier, 'GOOD');
      assert.strictEqual(goodCheckP2.timingTier, 'OKAY');
    });

    it('Pitcher 1 (90 Eff) suppresses contact better than Pitcher 2 (75 Eff)', () => {
      const baseWhiff = 0.25;
      const baseEv = 89.0;

      const whiffP1 = applyEffectivenessToWhiffRate(baseWhiff, 90.0);
      const whiffP2 = applyEffectivenessToWhiffRate(baseWhiff, 75.0);
      const evP1 = applyEffectivenessToExitVelocity(baseEv, 90.0);
      const evP2 = applyEffectivenessToExitVelocity(baseEv, 75.0);

      assert.ok(whiffP1 > baseWhiff && baseWhiff > whiffP2);
      assert.ok(evP1 < baseEv && baseEv < evP2);
      assert.ok(evP2 - evP1 >= 2.0);
    });
  });
});
