import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  calculateConsecutiveMissPenalty,
  calculateConfidenceDelta,
  applyHolisticConfidenceUpdate,
  calculateConfidenceEffectiveCommand,
  NEUTRAL_CONFIDENCE,
  RIPPLE_FACTOR,
} from '../confidenceModel.ts';

describe('Pitcher Confidence Model', () => {
  describe('calculateConsecutiveMissPenalty', () => {
    it('returns 0 for zero or negative streaks', () => {
      assert.strictEqual(calculateConsecutiveMissPenalty(0), 0);
      assert.strictEqual(calculateConsecutiveMissPenalty(-1), 0);
    });

    it('returns minor penalty for single miss', () => {
      assert.strictEqual(calculateConsecutiveMissPenalty(1), -2.5);
    });

    it('escalates progressively on consecutive misses (>= 2)', () => {
      const p2 = calculateConsecutiveMissPenalty(2);
      const p3 = calculateConsecutiveMissPenalty(3);
      const p4 = calculateConsecutiveMissPenalty(4);
      const p5 = calculateConsecutiveMissPenalty(5);

      assert.strictEqual(p2, -6.0);
      assert.strictEqual(p3, -10.5);
      assert.strictEqual(p4, -16.0);
      assert.strictEqual(p5, -22.5);

      // Verify that delta accelerates from 1 to 2 (-3.5) and 2 to 3 (-4.5)
      assert.ok(Math.abs(p3 - p2) > Math.abs(p2 - calculateConsecutiveMissPenalty(1)));
    });
  });

  describe('calculateConfidenceDelta', () => {
    it('penalizes hits allowed and resets miss streak', () => {
      const hr = calculateConfidenceDelta('HOME_RUN', 3);
      assert.strictEqual(hr.primaryDelta, -20.0);
      assert.strictEqual(hr.newMissStreak, 0);

      const triple = calculateConfidenceDelta('TRIPLE', 2);
      assert.strictEqual(triple.primaryDelta, -15.0);
      assert.strictEqual(triple.newMissStreak, 0);

      const double = calculateConfidenceDelta('DOUBLE', 1);
      assert.strictEqual(double.primaryDelta, -11.0);
      assert.strictEqual(double.newMissStreak, 0);

      const single = calculateConfidenceDelta('SINGLE', 0);
      assert.strictEqual(single.primaryDelta, -7.0);
      assert.strictEqual(single.newMissStreak, 0);
    });

    it('penalizes hit by pitch and resets streak', () => {
      const hbp = calculateConfidenceDelta('HIT_BY_PITCH', 2);
      assert.strictEqual(hbp.primaryDelta, -9.0);
      assert.strictEqual(hbp.newMissStreak, 0);
    });

    it('stacks penalties for consecutive balls and applies walk penalty on ball 4', () => {
      const b1 = calculateConfidenceDelta('BALL', 0);
      assert.strictEqual(b1.primaryDelta, -2.5);
      assert.strictEqual(b1.newMissStreak, 1);

      const b2 = calculateConfidenceDelta('BALL', b1.newMissStreak);
      assert.strictEqual(b2.primaryDelta, -6.0);
      assert.strictEqual(b2.newMissStreak, 2);

      const b3 = calculateConfidenceDelta('BALL', b2.newMissStreak);
      assert.strictEqual(b3.primaryDelta, -10.5);
      assert.strictEqual(b3.newMissStreak, 3);

      const b4Walk = calculateConfidenceDelta('BALL', b3.newMissStreak, true);
      assert.strictEqual(b4Walk.newMissStreak, 4);
      // -16.0 (streak 4) - 6.0 (walk) = -22.0
      assert.strictEqual(b4Walk.primaryDelta, -22.0);
    });

    it('rewards effective strikes and resets streak', () => {
      const swinging = calculateConfidenceDelta('SWINGING_STRIKE', 3);
      assert.strictEqual(swinging.primaryDelta, 6.5);
      assert.strictEqual(swinging.newMissStreak, 0);

      const out = calculateConfidenceDelta('IN_PLAY_OUT', 2);
      assert.strictEqual(out.primaryDelta, 6.0);
      assert.strictEqual(out.newMissStreak, 0);

      const called = calculateConfidenceDelta('CALLED_STRIKE', 1);
      assert.strictEqual(called.primaryDelta, 4.0);
      assert.strictEqual(called.newMissStreak, 0);

      const foul = calculateConfidenceDelta('FOUL', 2);
      assert.strictEqual(foul.primaryDelta, 1.5);
      assert.strictEqual(foul.newMissStreak, 0);
    });
  });

  describe('applyHolisticConfidenceUpdate', () => {
    it('applies 100% of delta to thrown pitch and 30% ripple to all other pitches', () => {
      const current = {
        'Four-Seam Fastball': 50,
        'Slider': 50,
        'Changeup': 50,
        'Curveball': 50,
      };
      const repertoire = Object.keys(current);

      const updated = applyHolisticConfidenceUpdate(
        current,
        repertoire,
        'Slider',
        -20.0,
      );

      // Thrown pitch took full -20
      assert.strictEqual(updated['Slider'], 30);
      // Other pitches took 30% of -20 = -6
      assert.strictEqual(updated['Four-Seam Fastball'], 44);
      assert.strictEqual(updated['Changeup'], 44);
      assert.strictEqual(updated['Curveball'], 44);

      // Overall average recalculated
      assert.strictEqual(updated['overall'], 40.5);
    });

    it('clamps confidences to [0, 100]', () => {
      const current = { 'Fastball': 10, 'Slider': 95 };
      const updatedLow = applyHolisticConfidenceUpdate(current, ['Fastball', 'Slider'], 'Fastball', -20);
      assert.strictEqual(updatedLow['Fastball'], 0);

      const updatedHigh = applyHolisticConfidenceUpdate(current, ['Fastball', 'Slider'], 'Slider', +15);
      assert.strictEqual(updatedHigh['Slider'], 100);
    });
  });

  describe('calculateConfidenceEffectiveCommand', () => {
    it('preserves base command at neutral 50% confidence', () => {
      assert.strictEqual(calculateConfidenceEffectiveCommand(80, 50), 80);
    });

    it('degrades command progressively below 50% confidence', () => {
      const cmd25 = calculateConfidenceEffectiveCommand(80, 25);
      // Halfway between 50 and 0: penalty = -11 -> 69
      assert.strictEqual(cmd25, 69);

      const cmd0 = calculateConfidenceEffectiveCommand(80, 0);
      // Maximum penalty of -22 -> 58
      assert.strictEqual(cmd0, 58);
    });

    it('boosts command progressively above 50% confidence', () => {
      const cmd75 = calculateConfidenceEffectiveCommand(80, 75);
      // Halfway between 50 and 100: boost = +5 -> 85
      assert.strictEqual(cmd75, 85);

      const cmd100 = calculateConfidenceEffectiveCommand(80, 100);
      // Maximum boost of +10 -> 90
      assert.strictEqual(cmd100, 90);
    });

    it('clamps effective command between [30, 99]', () => {
      assert.strictEqual(calculateConfidenceEffectiveCommand(35, 0), 30);
      assert.strictEqual(calculateConfidenceEffectiveCommand(95, 100), 99);
    });
  });
});
