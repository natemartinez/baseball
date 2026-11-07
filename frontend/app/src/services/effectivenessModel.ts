/**
 * Pitcher Effectiveness Model — Physical Pitch Quality & Stuff Tracking.
 *
 * Effectiveness is DISTINCT from Confidence:
 * - Confidence: Psychological state → governs command accuracy (error dispersion circle).
 * - Effectiveness: Physical pitch "stuff" quality (bite, movement, deception) → governs
 *   batter whiff probability and exit velocity suppression.
 *
 * Effectiveness starts at each pitch's baseline stuff rating derived from its velocity,
 * break rating, and spin. It is pitch-specific (not holistic like confidence ripple).
 *
 * Ineffectiveness Drivers:
 * 1. Hard contact — batters are squaring the pitch up (seeing it well).
 * 2. Stamina/fatigue — pitch flattens out, loses break and bite.
 * 3. Severe low confidence drag — minor secondary coupling only (mental → physical).
 *
 * Recovery Drivers:
 * 1. Whiff/strikeout — pitch has good bite and is fooling batters.
 * 2. Weak contact (popout/groundout) — pitch is inducing weak contact.
 */

export const MIN_EFFECTIVENESS = 0.0;
export const MAX_EFFECTIVENESS = 100.0;

/** Neutral baseline for effectiveness (pitches start here or above). */
export const NEUTRAL_EFFECTIVENESS_BASELINE = 80.0;

/** Max effectiveness penalty from pure fatigue at 0% stamina. */
export const FATIGUE_EFFECTIVENESS_MAX_PENALTY = 15.0;

/** Below this confidence %, a minor physical drag couples in. */
export const CONFIDENCE_DRAG_THRESHOLD = 25.0;

/** Maximum physical effectiveness drag from severe low confidence. */
export const CONFIDENCE_DRAG_MAX = 5.0;

/**
 * Computes a pitch's starting effectiveness from its physical stuff attributes.
 * Returns a value in [70.0, 95.0] — elite pitches start higher.
 *
 * Formula weights:
 * - Break rating (40%): Primary driver of pitch bite and deception.
 * - Velocity (25%): Raw power.
 * - Spin rate (20%): Sharper movement.
 * - Command (15%): Better command = more consistent stuff execution.
 */
export function computeBaselineEffectiveness(
  velocityMph: number,
  breakRating: number,
  spinRpm: number,
  command: number = 75.0,
): number {
  const veloScore = Math.min(100, Math.max(0, (velocityMph - 80) / (102 - 80) * 100));
  const breakScore = Math.min(100, Math.max(0, breakRating));
  const spinScore = Math.min(100, Math.max(0, (spinRpm - 1800) / (3500 - 1800) * 100));
  const cmdScore = Math.min(100, Math.max(0, command));

  const raw = (
    0.40 * breakScore
    + 0.25 * veloScore
    + 0.20 * spinScore
    + 0.15 * cmdScore
  );

  // Scale to [70, 95]
  const baseline = 70.0 + (raw / 100.0) * 25.0;
  return Math.round(Math.min(MAX_EFFECTIVENESS, Math.max(70.0, baseline)) * 100) / 100;
}

export interface EffectivenessDeltaResult {
  delta: number;
}

/**
 * Calculates the delta to apply to a pitch's effectiveness based on the pitch outcome.
 *
 * Hard contact (batters squaring it up) degrades effectiveness.
 * Whiffs and weak contact (outs) recover effectiveness.
 * Stamina fatigue reduces positive recovery rate.
 * Severely low confidence causes minor additional drag.
 */
export function calculateEffectivenessDelta(
  pitchResult: string,
  currentStaminaPct: number = 100.0,
  pitchConfidence?: number,
): number {
  const result = String(pitchResult || '').toUpperCase();

  let baseDelta = 0.0;

  // Hard contact: batters are seeing the pitch well
  if (result === 'HOME_RUN') {
    baseDelta = -14.0;
  } else if (result === 'TRIPLE') {
    baseDelta = -10.0;
  } else if (result === 'DOUBLE') {
    baseDelta = -7.0;
  } else if (result === 'SINGLE') {
    baseDelta = -4.0;
  } else if (result === 'HIT_BY_PITCH') {
    baseDelta = -2.0;
  }
  // Recovery: pitch has good bite / fools batters
  else if (result === 'SWINGING_STRIKE') {
    baseDelta = +5.0;
  } else if (result === 'IN_PLAY_OUT') {
    baseDelta = +3.5;
  } else if (result === 'CALLED_STRIKE') {
    baseDelta = +1.5;
  } else if (result === 'FOUL') {
    baseDelta = +0.5;
  } else if (result === 'BALL') {
    baseDelta = -0.5;
  }

  // Stamina fatigue drag on recovery
  const stamina = Math.max(0, Math.min(100, currentStaminaPct));
  if (baseDelta > 0) {
    const staminaMultiplier = Math.max(0.3, stamina / 100.0);
    baseDelta = baseDelta * staminaMultiplier;
  }

  // Low confidence secondary drag (minor coupling, only below threshold)
  if (pitchConfidence !== undefined) {
    const conf = Math.max(0, Math.min(100, pitchConfidence));
    if (conf < CONFIDENCE_DRAG_THRESHOLD) {
      const dragScale = (CONFIDENCE_DRAG_THRESHOLD - conf) / CONFIDENCE_DRAG_THRESHOLD;
      const confidenceDrag = -dragScale * CONFIDENCE_DRAG_MAX;
      baseDelta = baseDelta + confidenceDrag;
    }
  }

  return Math.round(baseDelta * 100) / 100;
}

/**
 * Applies a stamina-based fatigue floor to effectiveness.
 * As stamina drops, effectiveness is gently pulled toward a lower fatigue floor.
 * At 100% stamina: no pull. At 0% stamina: floor = baseline - MAX_PENALTY.
 */
export function applyStaminaFatigueToEffectiveness(
  currentEffectiveness: number,
  currentStaminaPct: number,
  baselineEffectiveness: number,
): number {
  const stamina = Math.max(0, Math.min(100, currentStaminaPct));
  const fatigueFactor = 1.0 - (stamina / 100.0);
  const fatigueFloor = Math.max(MIN_EFFECTIVENESS, baselineEffectiveness - (fatigueFactor * FATIGUE_EFFECTIVENESS_MAX_PENALTY));

  if (currentEffectiveness > fatigueFloor) {
    const pull = (currentEffectiveness - fatigueFloor) * 0.05 * fatigueFactor;
    return Math.round(Math.max(fatigueFloor, currentEffectiveness - pull) * 100) / 100;
  }
  return Math.round(currentEffectiveness * 100) / 100;
}

/**
 * Full effectiveness update for a single pitch: applies outcome delta,
 * stamina fatigue pull, and clamps to valid range.
 */
export function updatePitchEffectiveness(
  currentEffectiveness: number,
  pitchResult: string,
  currentStaminaPct: number = 100.0,
  pitchConfidence?: number,
  baselineEffectiveness: number = 80.0,
): number {
  const delta = calculateEffectivenessDelta(pitchResult, currentStaminaPct, pitchConfidence);
  let newVal = currentEffectiveness + delta;

  newVal = applyStaminaFatigueToEffectiveness(newVal, currentStaminaPct, baselineEffectiveness);

  return Math.max(MIN_EFFECTIVENESS, Math.min(MAX_EFFECTIVENESS, Math.round(newVal * 100) / 100));
}

/**
 * Adjusts a base whiff probability using current pitch effectiveness.
 * Neutral baseline is 80 (not 50 — that's confidence).
 * High effectiveness → more whiffs. Low effectiveness → easier contact.
 * Scale: ±0.0015 per point from 80, capped at ±0.12.
 */
export function applyEffectivenessToWhiffRate(
  baseWhiffProb: number,
  pitchEffectiveness: number,
): number {
  const neutral = NEUTRAL_EFFECTIVENESS_BASELINE;
  const effectiveness = Math.max(MIN_EFFECTIVENESS, Math.min(MAX_EFFECTIVENESS, pitchEffectiveness));
  let delta = (effectiveness - neutral) * 0.0015;
  delta = Math.max(-0.12, Math.min(0.12, delta));
  return Math.max(0.05, Math.min(0.80, baseWhiffProb + delta));
}

/**
 * Adjusts mean exit velocity based on pitch effectiveness.
 * Neutral baseline is 80. High effectiveness → suppresses exit velocity.
 * Low effectiveness → batters square up more easily.
 */
export function applyEffectivenessToExitVelocity(
  baseExitVelocity: number,
  pitchEffectiveness: number,
): number {
  const neutral = NEUTRAL_EFFECTIVENESS_BASELINE;
  const effectiveness = Math.max(MIN_EFFECTIVENESS, Math.min(MAX_EFFECTIVENESS, pitchEffectiveness));
  let evAdj: number;
  if (effectiveness < neutral) {
    evAdj = (neutral - effectiveness) * 0.225;   // Flatter pitch → harder contact
  } else {
    evAdj = -(effectiveness - neutral) * 0.15;   // Sharper stuff → weaker contact
  }
  return Math.round((baseExitVelocity + evAdj) * 10) / 10;
}

/**
 * Calculates command modifier from a pitch's physical effectiveness.
 * Baseline neutral is 80.0 (0.0 adjustment).
 *
 * - Higher effectiveness (sharp stuff / great feel) boosts command:
 *   e.g., at 90.0 effectiveness: +6.0 command; at 100.0: +12.0 command.
 * - Lower effectiveness (flattening pitch / losing stuff) degrades command:
 *   e.g., at 75.0 effectiveness: -3.75 command; at 60.0: -15.0; at 40.0: -30.0.
 */
export function calculateCommandAdjustmentFromEffectiveness(
  effectiveness: number,
): number {
  const eff = Math.max(MIN_EFFECTIVENESS, Math.min(MAX_EFFECTIVENESS, effectiveness));
  if (eff >= NEUTRAL_EFFECTIVENESS_BASELINE) {
    return Math.round((eff - NEUTRAL_EFFECTIVENESS_BASELINE) * 0.60 * 100) / 100;
  } else {
    const penalty = (NEUTRAL_EFFECTIVENESS_BASELINE - eff) * 0.75;
    return Math.round(-Math.min(30.0, penalty) * 100) / 100;
  }
}

/**
 * Calculates combined effective command factoring both psychological confidence
 * and physical pitch effectiveness.
 *
 * Clamped to [30, 99].
 */
export function calculateCombinedEffectiveCommand(
  baseCommand: number,
  confidence: number = 50.0,
  effectiveness: number = 80.0,
): number {
  const conf = Math.max(0, Math.min(100, confidence));
  let confDelta = 0;
  if (conf < 50.0) {
    confDelta = -((50.0 - conf) / 50.0) * 22.0;
  } else {
    confDelta = ((conf - 50.0) / 50.0) * 10.0;
  }

  const effDelta = calculateCommandAdjustmentFromEffectiveness(effectiveness);
  const effective = baseCommand + confDelta + effDelta;
  return Math.max(30, Math.min(99, Math.round(effective * 10) / 10));
}

/**
 * Scales pitch release velocity based on pitch effectiveness.
 * - At 80.0 (neutral baseline): no velocity change.
 * - At > 80.0: consistent higher velocity (up to +2.5 mph).
 * - At < 80.0: losing velocity (down to -5.0 mph).
 */
export function applyEffectivenessToVelocity(
  baseVelocity: number,
  pitchEffectiveness: number,
): number {
  const eff = Math.max(MIN_EFFECTIVENESS, Math.min(MAX_EFFECTIVENESS, pitchEffectiveness));
  let veloAdj: number;
  if (eff >= NEUTRAL_EFFECTIVENESS_BASELINE) {
    veloAdj = ((eff - NEUTRAL_EFFECTIVENESS_BASELINE) / 20.0) * 2.5;
  } else {
    veloAdj = -((NEUTRAL_EFFECTIVENESS_BASELINE - eff) / 20.0) * 5.0;
  }
  return Math.round((baseVelocity + veloAdj) * 10) / 10;
}

/**
 * Scales physical pitch break ('bite') based on pitch effectiveness.
 * - At 80.0: neutral multiplier 1.0.
 * - At > 80.0: sharper bite / increased break (up to +15% at 100 effectiveness).
 * - At < 80.0: flatter pitch / reduced bite (down to -35% at 40 effectiveness).
 */
export function applyEffectivenessToBreak(
  horizontalBreakIn: number,
  inducedVerticalBreakIn: number,
  pitchEffectiveness: number,
): [number, number] {
  const eff = Math.max(MIN_EFFECTIVENESS, Math.min(MAX_EFFECTIVENESS, pitchEffectiveness));
  let multiplier: number;
  if (eff >= NEUTRAL_EFFECTIVENESS_BASELINE) {
    multiplier = 1.0 + ((eff - NEUTRAL_EFFECTIVENESS_BASELINE) / 20.0) * 0.15;
  } else {
    multiplier = 1.0 - ((NEUTRAL_EFFECTIVENESS_BASELINE - eff) / 80.0) * 0.40;
  }
  multiplier = Math.max(0.50, Math.min(1.25, multiplier));
  const hb = Math.round(horizontalBreakIn * multiplier * 100) / 100;
  const ivb = Math.round(inducedVerticalBreakIn * multiplier * 100) / 100;
  return [hb, ivb];
}

