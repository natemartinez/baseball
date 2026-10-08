/**
 * MLB Gameday 2D Coordinate Normalization & Bivariate Gaussian Math Engine
 * Converts Statcast plate coordinates to SVG viewport space and models
 * delivery execution error from pitcher Command & Fatigue ratings.
 */

import type { GamedayZoneCategory, CalibrationBaseline } from '../types/gameday';

// ─── Constants: Rulebook & Gameday Zone Dimensions (in Statcast Feet) ──────────

export const PLATE_WIDTH_FT = 17 / 12; // 1.4167 ft
export const HALF_PLATE_WIDTH_FT = PLATE_WIDTH_FT / 2; // 0.7083 ft (~8.5 in)

export const ZONE_X_MIN = -HALF_PLATE_WIDTH_FT; // -0.708 ft
export const ZONE_X_MAX = HALF_PLATE_WIDTH_FT; // +0.708 ft
export const ZONE_Z_BOT = 1.50; // Hollow of the knee in feet
export const ZONE_Z_TOP = 3.50; // Midpoint between shoulders & belt in feet

export const HEART_X_MIN = ZONE_X_MIN / 2; // -0.354 ft
export const HEART_X_MAX = ZONE_X_MAX / 2; // +0.354 ft
export const HEART_Z_BOT = 2.00; // Inner 50% vertical
export const HEART_Z_TOP = 3.00; // Inner 50% vertical

export const BALL_DIAMETER_FT = 2.9 / 12; // ~0.2417 ft
export const SHADOW_BORDER_FT = 3.4 / 12; // 0.2833 ft (1 ball width border)

// Viewport boundaries for SVG rendering (Statcast Feet)
export const VIEWPORT_X_MIN = -2.0;
export const VIEWPORT_X_MAX = 2.0;
export const VIEWPORT_Z_MIN = 0.0; // Ground level
export const VIEWPORT_Z_MAX = 4.5; // High waste area

export const SIGMA_MAX_FT = 0.50; // 6.0 inches (40 Command)
export const SIGMA_MIN_FT = 0.15; // 1.8 inches (99 Command)

// ─── Pre-computed Empirical Baselines (from 10,000-pitch calibration protocol) ─

export const EMPIRICAL_BASELINES: Record<number, CalibrationBaseline> = {
  40: {
    commandRating: 40,
    expectedShadowAccuracy: 68.2,
    expectedHeartLeaks: 9.7,
    expectedMissRadiusInches: 6.22,
    expectedAheadOffspeedPct: 58.4,
  },
  68: {
    commandRating: 68,
    expectedShadowAccuracy: 81.0,
    expectedHeartLeaks: 7.7,
    expectedMissRadiusInches: 4.49,
    expectedAheadOffspeedPct: 65.1,
  },
  85: {
    commandRating: 85,
    expectedShadowAccuracy: 88.2,
    expectedHeartLeaks: 6.0,
    expectedMissRadiusInches: 3.51,
    expectedAheadOffspeedPct: 68.3,
  },
  99: {
    commandRating: 99,
    expectedShadowAccuracy: 94.1,
    expectedHeartLeaks: 3.3,
    expectedMissRadiusInches: 2.63,
    expectedAheadOffspeedPct: 71.9,
  },
};

/** Get closest empirical baseline for a given pitcher Command rating */
export function getBaselineForCommand(commandRating: number): CalibrationBaseline {
  const tiers = [40, 68, 85, 99];
  let closest = tiers[0];
  let minDiff = Math.abs(commandRating - closest);
  for (const t of tiers) {
    const diff = Math.abs(commandRating - t);
    if (diff < minDiff) {
      minDiff = diff;
      closest = t;
    }
  }
  return EMPIRICAL_BASELINES[closest];
}

// ─── Bivariate Gaussian Execution Error ───────────────────────────────────────

/**
 * Calculates bivariate standard deviation from pitcher's Command rating and pitch fatigue.
 * sigma_x = sigma_z = [sigma_max - (Command / 100) * (sigma_max - sigma_min)] * (1 + FatigueMultiplier)
 */
export function calculateExecutionSigma(
  commandRating: number,
  pitchCount: number = 0,
  stamina: number = 70,
): number {
  const clampedCommand = Math.max(20, Math.min(99, commandRating));
  const baseSigma =
    SIGMA_MAX_FT - (clampedCommand / 100) * (SIGMA_MAX_FT - SIGMA_MIN_FT);
  const fatigueMultiplier = Math.max(0, (pitchCount - stamina) / 30);
  return baseSigma * (1 + fatigueMultiplier);
}

/**
 * Generates Gaussian random numbers using the Box-Muller transform.
 */
export function sampleGaussian(mean: number, stdDev: number, rng: () => number = Math.random): number {
  let u1 = rng();
  let u2 = rng();
  while (u1 <= 1e-7) u1 = rng(); // Avoid zero for log
  const z0 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
  return mean + z0 * stdDev;
}

/**
 * Computes realized delivery coordinate given an intended target and variance.
 */
export function executeDelivery(
  targetX: number,
  targetZ: number,
  commandRating: number,
  pitchCount: number = 0,
  stamina: number = 70,
  rng: () => number = Math.random,
): {
  realizedX: number;
  realizedZ: number;
  sigmaFeet: number;
  radialMissInches: number;
  deltaXInches: number;
  deltaZInches: number;
} {
  const sigma = calculateExecutionSigma(commandRating, pitchCount, stamina);
  const realizedX = sampleGaussian(targetX, sigma, rng);
  const realizedZ = sampleGaussian(targetZ, sigma, rng);

  const deltaXFeet = realizedX - targetX;
  const deltaZFeet = realizedZ - targetZ;
  const radialMissFeet = Math.sqrt(deltaXFeet * deltaXFeet + deltaZFeet * deltaZFeet);

  return {
    realizedX: +realizedX.toFixed(3),
    realizedZ: +realizedZ.toFixed(3),
    sigmaFeet: +sigma.toFixed(3),
    radialMissInches: +(radialMissFeet * 12).toFixed(1),
    deltaXInches: +(deltaXFeet * 12).toFixed(1),
    deltaZInches: +(deltaZFeet * 12).toFixed(1),
  };
}

// ─── Zone Classification ──────────────────────────────────────────────────────

/**
 * Returns whether a point (X, Z) is inside the rulebook strike zone.
 */
export function isRulebookStrike(x: number, z: number): boolean {
  return x >= ZONE_X_MIN && x <= ZONE_X_MAX && z >= ZONE_Z_BOT && z <= ZONE_Z_TOP;
}

/**
 * Categorizes a 2D coordinate into HEART, SHADOW, CHASE, or WASTE.
 */
export function classifyGamedayZone(x: number, z: number): GamedayZoneCategory {
  // 1. Heart: Inner 50% box
  if (
    x >= HEART_X_MIN &&
    x <= HEART_X_MAX &&
    z >= HEART_Z_BOT &&
    z <= HEART_Z_TOP
  ) {
    return 'HEART';
  }

  // Distance from strike zone rectangle
  const dx = Math.max(0, ZONE_X_MIN - x, x - ZONE_X_MAX);
  const dz = Math.max(0, ZONE_Z_BOT - z, z - ZONE_Z_TOP);
  const distFromZone = Math.sqrt(dx * dx + dz * dz);

  // If inside rulebook zone (but outside Heart), it's Shadow
  if (distFromZone === 0) {
    return 'SHADOW';
  }

  // 2. Shadow border extends ~1 ball width (0.283 ft) outside zone
  if (distFromZone <= SHADOW_BORDER_FT) {
    return 'SHADOW';
  }

  // 3. Chase: 1-2 ball widths outside (0.283 to 0.50 ft)
  if (distFromZone <= 0.50) {
    return 'CHASE';
  }

  // 4. Waste: > 6 inches (0.50 ft) outside zone
  return 'WASTE';
}

/**
 * Maps standard 13 strike zone names into nominal Statcast (X, Z) target coordinates in feet.
 */
export function getZoneNominalTarget(zoneName: string): { x: number; z: number; category: GamedayZoneCategory } {
  switch (zoneName.toLowerCase()) {
    case 'upper-in':
      return { x: -0.55, z: 3.15, category: 'SHADOW' };
    case 'upper-middle':
      return { x: 0.00, z: 3.15, category: 'SHADOW' };
    case 'upper-away':
      return { x: 0.55, z: 3.15, category: 'SHADOW' };
    case 'middle-in':
      return { x: -0.55, z: 2.50, category: 'SHADOW' };
    case 'heart':
      return { x: 0.00, z: 2.50, category: 'HEART' };
    case 'middle-away':
      return { x: 0.55, z: 2.50, category: 'SHADOW' };
    case 'lower-in':
      return { x: -0.55, z: 1.85, category: 'SHADOW' };
    case 'lower-middle':
      return { x: 0.00, z: 1.85, category: 'SHADOW' };
    case 'lower-away':
      return { x: 0.55, z: 1.85, category: 'SHADOW' };
    case 'chase-high':
      return { x: 0.00, z: 3.85, category: 'CHASE' };
    case 'chase-low':
      return { x: 0.00, z: 1.15, category: 'CHASE' };
    case 'chase-in':
      return { x: -1.05, z: 2.50, category: 'CHASE' };
    case 'chase-away':
      return { x: 1.05, z: 2.50, category: 'CHASE' };
    default:
      return { x: 0.00, z: 2.50, category: 'HEART' };
  }
}

// ─── SVG Coordinate Normalization ─────────────────────────────────────────────

/**
 * Converts Statcast Feet (X: [-2.0, 2.0], Z: [0.0, 4.5]) to SVG Pixel Coordinates.
 */
export function statcastToSvg(
  x: number,
  z: number,
  svgWidth: number,
  svgHeight: number,
): { svgX: number; svgY: number } {
  // Horizontal: [-2.0, 2.0] -> [0, svgWidth]
  const svgX = ((x - VIEWPORT_X_MIN) / (VIEWPORT_X_MAX - VIEWPORT_X_MIN)) * svgWidth;
  // Vertical: [0.0, 4.5] -> [svgHeight, 0] (SVG Y is flipped)
  const svgY = svgHeight - ((z - VIEWPORT_Z_MIN) / (VIEWPORT_Z_MAX - VIEWPORT_Z_MIN)) * svgHeight;
  return { svgX, svgY };
}

/**
 * Inverse conversion: Converts SVG Touch/Click Pixel Coordinates back to Statcast Feet (X, Z).
 */
export function svgToStatcast(
  svgX: number,
  svgY: number,
  svgWidth: number,
  svgHeight: number,
): { statcastX: number; statcastZ: number } {
  const statcastX = VIEWPORT_X_MIN + (svgX / svgWidth) * (VIEWPORT_X_MAX - VIEWPORT_X_MIN);
  const statcastZ = VIEWPORT_Z_MIN + ((svgHeight - svgY) / svgHeight) * (VIEWPORT_Z_MAX - VIEWPORT_Z_MIN);
  return {
    statcastX: +Math.max(VIEWPORT_X_MIN, Math.min(VIEWPORT_X_MAX, statcastX)).toFixed(2),
    statcastZ: +Math.max(VIEWPORT_Z_MIN, Math.min(VIEWPORT_Z_MAX, statcastZ)).toFixed(2),
  };
}

// ─── Color Palette for Pitch Types & Results ──────────────────────────────────

export function getPitchTypeColor(pitchName: string): string {
  const p = pitchName.toLowerCase();
  if (p.includes('four-seam') || p.includes('4-seam') || p.includes('4sfb')) {
    return '#EF4444'; // Red
  }
  if (p.includes('sinker') || p.includes('cutter')) {
    return '#F97316'; // Orange
  }
  if (p.includes('slider') || p.includes('sweeper')) {
    return '#06B6D4'; // Cyan
  }
  if (p.includes('curve') || p.includes('knuckle')) {
    return '#3B82F6'; // Blue
  }
  if (p.includes('change') || p.includes('split') || p.includes('fork')) {
    return '#10B981'; // Green
  }
  return '#A855F7'; // Purple fallback
}

export function getResultRingColor(call: string): string {
  switch (call) {
    case 'CALLED_STRIKE':
    case 'SWINGING_STRIKE':
      return '#EF4444'; // Red ring
    case 'BALL':
      return '#10B981'; // Green ring
    case 'IN_PLAY':
    case 'FOUL':
    default:
      return '#3B82F6'; // Blue ring
  }
}

// ─── Situational Evaluation & Packet Builder ──────────────────────────────────

export function determineSituationCategory(
  balls: number,
  strikes: number,
  outs: number,
  first: boolean,
  second: boolean,
  third: boolean,
): import('../types/gameday').SituationCategory {
  if (first && second && third) return 'BASES_LOADED';
  if (first && outs < 2) return 'DOUBLE_PLAY';
  if (second || third) return 'RISP';
  if (outs === 2) return 'TWO_OUTS';
  if (strikes === 2) return 'AHEAD_IN_COUNT';
  if (balls >= 2 && strikes < 2) return 'BEHIND_IN_COUNT';
  return 'NEUTRAL';
}

