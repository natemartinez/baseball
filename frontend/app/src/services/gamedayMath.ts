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
export const CHASE_BORDER_FT = 2 * SHADOW_BORDER_FT; // 0.5667 ft (2 ball widths)

// Viewport boundaries for SVG rendering (Statcast Feet)
export const VIEWPORT_X_MIN = -2.0;
export const VIEWPORT_X_MAX = 2.0;
export const VIEWPORT_Z_MIN = 0.0; // Ground level
export const VIEWPORT_Z_MAX = 4.5; // High waste area

export const SIGMA_MAX_FT = 0.50; // Legacy; the radius table is authoritative.
export const SIGMA_MIN_FT = 0.15; // Legacy; the radius table is authoritative.

/** Fatigue is off while the spray-cloud model is being validated. */
export const FATIGUE_ENABLED = false;

/**
 * Command -> hard maximum error radius (inches). Diameter = 2 * radius.
 * Interpolated linearly between tiers and clamped outside the range.
 */
export const MAX_ERROR_RADIUS_TIERS: Array<[number, number]> = [
  [99, 1.0],
  [90, 1.25],
  [82, 1.5],
  [68, 3.0],
  [55, 4.5],
  [40, 7.0],
];

/** sigma = radius / divisor for the truncated Gaussian cloud. */
export const SIGMA_RADIUS_DIVISOR = 2.5;

export function getMaxErrorRadiusInches(commandRating: number): number {
  const command = Math.max(40, Math.min(99, commandRating));
  for (let i = 0; i < MAX_ERROR_RADIUS_TIERS.length - 1; i++) {
    const [highCmd, highRadius] = MAX_ERROR_RADIUS_TIERS[i];
    const [lowCmd, lowRadius] = MAX_ERROR_RADIUS_TIERS[i + 1];
    if (command >= lowCmd && command <= highCmd) {
      const span = highCmd - lowCmd;
      if (span <= 0) return highRadius;
      const t = (highCmd - command) / span;
      return highRadius + (lowRadius - highRadius) * t;
    }
  }
  return MAX_ERROR_RADIUS_TIERS[MAX_ERROR_RADIUS_TIERS.length - 1][1];
}

// ─── Pre-computed Empirical Baselines (from 10,000-pitch calibration protocol) ─

export const EMPIRICAL_BASELINES: Record<number, CalibrationBaseline> = {
  40: {
    commandRating: 40,
    expectedShadowAccuracy: 80.8,
    expectedHeartLeaks: 14.9,
    expectedMissRadiusInches: 3.29,
    expectedAheadOffspeedPct: 58.4,
  },
  55: {
    commandRating: 55,
    expectedShadowAccuracy: 84.1,
    expectedHeartLeaks: 13.0,
    expectedMissRadiusInches: 2.12,
    expectedAheadOffspeedPct: 61.5,
  },
  68: {
    commandRating: 68,
    expectedShadowAccuracy: 86.1,
    expectedHeartLeaks: 11.4,
    expectedMissRadiusInches: 1.42,
    expectedAheadOffspeedPct: 65.1,
  },
  82: {
    commandRating: 82,
    expectedShadowAccuracy: 92.5,
    expectedHeartLeaks: 6.15,
    expectedMissRadiusInches: 0.71,
    expectedAheadOffspeedPct: 67.5,
  },
  85: {
    commandRating: 85,
    expectedShadowAccuracy: 93.1,
    expectedHeartLeaks: 5.66,
    expectedMissRadiusInches: 0.66,
    expectedAheadOffspeedPct: 68.3,
  },
  90: {
    commandRating: 90,
    expectedShadowAccuracy: 94.6,
    expectedHeartLeaks: 4.44,
    expectedMissRadiusInches: 0.59,
    expectedAheadOffspeedPct: 69.9,
  },
  99: {
    commandRating: 99,
    expectedShadowAccuracy: 96.8,
    expectedHeartLeaks: 2.63,
    expectedMissRadiusInches: 0.47,
    expectedAheadOffspeedPct: 71.9,
  },
};

/** Get closest empirical baseline for a given pitcher Command rating */
export function getBaselineForCommand(commandRating: number): CalibrationBaseline {
  const tiers = Object.keys(EMPIRICAL_BASELINES).map(Number).sort((a, b) => a - b);
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
  const radiusFt = getMaxErrorRadiusInches(commandRating) / 12;
  const baseSigma = radiusFt / SIGMA_RADIUS_DIVISOR;
  if (!FATIGUE_ENABLED) return baseSigma;
  const fatigueMultiplier = Math.max(0, (pitchCount - stamina) / 30);
  return baseSigma * (1 + fatigueMultiplier);
}

/**
 * Samples a 2D Gaussian location truncated to a hard max radius using the
 * closed-form truncated Rayleigh radial distribution. The result can never
 * leave the circle and no rejection loop is required.
 */
export function sampleTruncatedGaussian(
  targetX: number,
  targetZ: number,
  sigma: number,
  maxRadiusFt: number,
  rng: () => number = Math.random,
): { x: number; z: number } {
  if (maxRadiusFt <= 0 || sigma <= 0) {
    return { x: targetX, z: targetZ };
  }
  const u = rng();
  const expTerm = Math.exp(-(maxRadiusFt * maxRadiusFt) / (2 * sigma * sigma));
  const oneMinus = 1 - u * (1 - expTerm);
  const r = Math.min(
    sigma * Math.sqrt(-2 * Math.log(Math.max(1e-12, oneMinus))),
    maxRadiusFt,
  );
  const theta = 2 * Math.PI * rng();
  return {
    x: targetX + r * Math.cos(theta),
    z: targetZ + r * Math.sin(theta),
  };
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
  maxRadiusInches: number;
  radialMissInches: number;
  deltaXInches: number;
  deltaZInches: number;
} {
  const sigma = calculateExecutionSigma(commandRating, pitchCount, stamina);
  const maxRadiusInches = getMaxErrorRadiusInches(commandRating);
  const sample = sampleTruncatedGaussian(
    targetX,
    targetZ,
    sigma,
    maxRadiusInches / 12,
    rng,
  );

  const deltaXFeet = sample.x - targetX;
  const deltaZFeet = sample.z - targetZ;
  const radialMissFeet = Math.sqrt(deltaXFeet * deltaXFeet + deltaZFeet * deltaZFeet);

  return {
    realizedX: +sample.x.toFixed(3),
    realizedZ: +sample.z.toFixed(3),
    sigmaFeet: +sigma.toFixed(3),
    maxRadiusInches: +maxRadiusInches.toFixed(3),
    radialMissInches: +(radialMissFeet * 12).toFixed(1),
    deltaXInches: +(deltaXFeet * 12).toFixed(1),
    deltaZInches: +(deltaZFeet * 12).toFixed(1),
  };
}

// ─── Spray cloud (deterministic Monte Carlo) ─────────────────────────────────

function mulberry32(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let z = Math.imul(s ^ (s >>> 15), 1 | s);
    z = (z + Math.imul(z ^ (z >>> 7), 61 | z)) ^ z;
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  };
}

export function sprayCloudSeed(
  targetX: number,
  targetZ: number,
  commandRating: number,
): number {
  return (
    (Math.round((targetX + 2) * 1000) * 73856093) ^
    (Math.round((targetZ + 0.5) * 1000) * 19349663) ^
    Math.round(commandRating * 83492791)
  ) >>> 0;
}

export interface SprayCloudPoint {
  x: number;
  z: number;
  zone: GamedayZoneCategory;
}

export interface SprayCloud {
  points: SprayCloudPoint[];
  radiusInches: number;
  sigmaInches: number;
}

/**
 * Builds a deterministic spray cloud around the glove target using the same
 * truncated command model as the pitch engine. The cloud is stable for a given
 * target/command, so it does not jitter on re-render.
 */
export function buildSprayCloud(
  targetX: number,
  targetZ: number,
  commandRating: number,
  sampleCount: number = 150,
  seed?: number,
): SprayCloud {
  const sigma = calculateExecutionSigma(commandRating);
  const radiusInches = getMaxErrorRadiusInches(commandRating);
  const radiusFt = radiusInches / 12;
  const rng = mulberry32(
    seed ?? sprayCloudSeed(targetX, targetZ, commandRating),
  );
  const points: SprayCloudPoint[] = [];

  for (let i = 0; i < sampleCount; i++) {
    const sample = sampleTruncatedGaussian(targetX, targetZ, sigma, radiusFt, rng);
    points.push({
      x: sample.x,
      z: sample.z,
      zone: classifyGamedayZone(sample.x, sample.z),
    });
  }

  return {
    points,
    radiusInches,
    sigmaInches: +(sigma * 12).toFixed(2),
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

  // Rectangular bands, matching the backend classifier exactly. This is
  // important at the four corners: a diagonal point just outside both edges is
  // in the chase band, not the waste band.
  if (
    x >= ZONE_X_MIN - SHADOW_BORDER_FT &&
    x <= ZONE_X_MAX + SHADOW_BORDER_FT &&
    z >= ZONE_Z_BOT - SHADOW_BORDER_FT &&
    z <= ZONE_Z_TOP + SHADOW_BORDER_FT
  ) {
    return 'SHADOW';
  }

  if (
    x >= ZONE_X_MIN - CHASE_BORDER_FT &&
    x <= ZONE_X_MAX + CHASE_BORDER_FT &&
    z >= ZONE_Z_BOT - CHASE_BORDER_FT &&
    z <= ZONE_Z_TOP + CHASE_BORDER_FT
  ) {
    return 'CHASE';
  }

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

