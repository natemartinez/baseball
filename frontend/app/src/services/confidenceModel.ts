/**
 * Pitcher Confidence & Arsenal Effectiveness Model
 *
 * Implements:
 * 1. Holistic tracking across all pitches with primary impact on the thrown pitch.
 * 2. Ineffectiveness definition:
 *    - Hits allowed (Home Run, Triple, Double, Single).
 *    - Consecutive missed strike zones (stacking escalations at >= 2 misses).
 *    - Walks (ball 4 penalty) & Hit-by-Pitch.
 * 3. Confidence-to-effectiveness translation:
 *    - Low confidence directly reduces effective command, increasing dispersion / error radius.
 *    - High confidence boosts effective command, tightening dispersion.
 */

export const NEUTRAL_CONFIDENCE = 50.0;
export const MAX_CONFIDENCE = 100.0;
export const MIN_CONFIDENCE = 0.0;

/** Holistic ripple fraction applied to other pitches in repertoire (30%). */
export const RIPPLE_FACTOR = 0.30;

/** Maximum command rating reduction when confidence drops to 0%. */
export const MAX_CONFIDENCE_COMMAND_PENALTY = 22.0;

/** Maximum command rating boost when confidence reaches 100%. */
export const MAX_CONFIDENCE_COMMAND_BOOST = 10.0;

/**
 * Calculates progressive penalty for failing to locate the strike zone consecutively.
 *
 * - 1 miss (first ball): minor miss (-2.5%)
 * - 2 consecutive misses: stacking begins (-6.0%)
 * - 3 consecutive misses: escalates harder (-10.5%)
 * - 4 consecutive misses: severe penalty (-16.0%)
 * - 5+ consecutive misses: -16.0% - (N - 4) * 6.5%
 */
export function calculateConsecutiveMissPenalty(missStreak: number): number {
  if (missStreak <= 0) return 0;
  if (missStreak === 1) return -2.5;
  if (missStreak === 2) return -6.0;
  if (missStreak === 3) return -10.5;
  if (missStreak === 4) return -16.0;
  return -16.0 - (missStreak - 4) * 6.5;
}

export interface ConfidenceEvaluation {
  primaryDelta: number;
  newMissStreak: number;
}

/**
 * Evaluates the confidence delta for the thrown pitch.
 */
export function calculateConfidenceDelta(
  pitchResult: string,
  consecutiveMisses: number = 0,
  isWalk: boolean = false,
): ConfidenceEvaluation {
  const result = String(pitchResult || '').toUpperCase();

  // 1. Ineffective: Got hit off of
  if (result === 'HOME_RUN') {
    return { primaryDelta: -20.0, newMissStreak: 0 };
  }
  if (result === 'TRIPLE') {
    return { primaryDelta: -15.0, newMissStreak: 0 };
  }
  if (result === 'DOUBLE') {
    return { primaryDelta: -11.0, newMissStreak: 0 };
  }
  if (result === 'SINGLE') {
    return { primaryDelta: -7.0, newMissStreak: 0 };
  }

  // 2. Ineffective: Hit By Pitch
  if (result === 'HIT_BY_PITCH') {
    return { primaryDelta: -9.0, newMissStreak: 0 };
  }

  // 3. Ineffective: Failed to locate the strike zone (BALL)
  if (result === 'BALL') {
    const newStreak = consecutiveMisses + 1;
    let delta = calculateConsecutiveMissPenalty(newStreak);
    if (isWalk) {
      delta -= 6.0; // Extra penalty for issuing a walk
    }
    return { primaryDelta: Math.round(delta * 10) / 10, newMissStreak: newStreak };
  }

  // 4. Effective strikes, outs, fouls (resets miss streak to 0)
  if (result === 'SWINGING_STRIKE') {
    return { primaryDelta: +6.5, newMissStreak: 0 };
  }
  if (result === 'IN_PLAY_OUT') {
    return { primaryDelta: +6.0, newMissStreak: 0 };
  }
  if (result === 'CALLED_STRIKE') {
    return { primaryDelta: +4.0, newMissStreak: 0 };
  }
  if (result === 'FOUL') {
    return { primaryDelta: +1.5, newMissStreak: 0 };
  }

  return { primaryDelta: -1.0, newMissStreak: 0 };
}

/**
 * Applies a holistic confidence update:
 * The thrown pitch receives the full primary delta;
 * every other pitch in the repertoire receives rippleFactor * primaryDelta.
 */
export function applyHolisticConfidenceUpdate(
  currentConfidences: Record<string, number>,
  allPitchNames: string[],
  thrownPitchName: string,
  primaryDelta: number,
  rippleFactor: number = RIPPLE_FACTOR,
): Record<string, number> {
  const updated: Record<string, number> = {};
  const rippleDelta = primaryDelta * rippleFactor;

  const pitchSet = new Set(allPitchNames);
  pitchSet.add(thrownPitchName);
  for (const name of Object.keys(currentConfidences)) {
    if (name !== 'overall') {
      pitchSet.add(name);
    }
  }

  for (const name of pitchSet) {
    const prev = currentConfidences[name] ?? NEUTRAL_CONFIDENCE;
    const delta = name === thrownPitchName ? primaryDelta : rippleDelta;
    const nextVal = Math.max(MIN_CONFIDENCE, Math.min(MAX_CONFIDENCE, Math.round((prev + delta) * 10) / 10));
    updated[name] = nextVal;
  }

  // Compute holistic overall average (excluding 'overall' key)
  const pitchValues = Object.entries(updated)
    .filter(([k]) => k !== 'overall')
    .map(([, v]) => v);
  const avg = pitchValues.length > 0 ? pitchValues.reduce((sum, v) => sum + v, 0) / pitchValues.length : NEUTRAL_CONFIDENCE;
  updated['overall'] = Math.round(avg * 10) / 10;

  return updated;
}

/**
 * Translates confidence into an effective command rating.
 *
 * At 50% confidence -> baseCommand (unmodified).
 * At < 50% confidence -> command degrades down to -22 points.
 * At > 50% confidence -> command sharpens up to +10 points.
 *
 * Clamped to [30, 99].
 */
export function calculateConfidenceEffectiveCommand(
  baseCommand: number,
  confidence: number = NEUTRAL_CONFIDENCE,
): number {
  const conf = Math.max(MIN_CONFIDENCE, Math.min(MAX_CONFIDENCE, confidence));
  let delta = 0;
  if (conf < NEUTRAL_CONFIDENCE) {
    const t = (NEUTRAL_CONFIDENCE - conf) / NEUTRAL_CONFIDENCE;
    delta = -t * MAX_CONFIDENCE_COMMAND_PENALTY;
  } else {
    const t = (conf - NEUTRAL_CONFIDENCE) / (MAX_CONFIDENCE - NEUTRAL_CONFIDENCE);
    delta = t * MAX_CONFIDENCE_COMMAND_BOOST;
  }
  const effective = baseCommand + delta;
  return Math.max(30, Math.min(99, Math.round(effective * 10) / 10));
}
