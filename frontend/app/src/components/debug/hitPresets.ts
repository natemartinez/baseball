import type { ActiveBattedBallData } from '../gamefield/types';

export interface HitPreset {
  id: string;
  name: string;
  category: 'grounder' | 'line_drive' | 'fly_ball' | 'home_run';
  description: string;
  launchAngle: number;
  exitVelocity: number;
  hangTime: number;
  isGrounder: boolean;
  landingPos: [number, number, number];
  apexHeight: number;
  distance: number;
  samples: [number, number, number, number][];
  fielded?: boolean;
  fielderId?: string | null;
  fieldingType?: string | null;
  fielderStart?: [number, number] | null;
  interceptPoint?: [number, number, number] | null;
}

export const G = 32.174;
export const MPH_TO_FPS = 1.46667;
export const CONTACT_HEIGHT_FT = 3.0;
export const TRACE_SAMPLE_COUNT = 20;

export const DRAG_K_AT_45 = 0.20;
export const DRAG_K_AT_70 = 0.12;
export const GROUND_LAUNCH_ANGLE = 10.0;

// Dr. Alan Nathan's ground interaction & turf friction parameters
export const AIR_DRAG_GROUND_FACTOR = 0.93;
export const COR_VERTICAL_DIRT = 0.52;
export const COR_HORIZONTAL_DIRT = 0.78;
export const COR_VERTICAL_GRASS = 0.42;
export const COR_HORIZONTAL_GRASS = 0.70;
export const COR_VERTICAL = 0.52;
export const COR_HORIZONTAL = 0.82;
export const SKID_TO_ROLL_FACTOR = 0.88;
export const TURF_FRICTION_COEFF = 0.48;
export const HOP_CUTOFF_APEX_FT = 0.20;
export const MAX_GROUND_DISTANCE_FT = 340.0;

export interface GroundHop {
  vzHop: number;
  vxyHop: number;
  apexFt: number;
  durationS: number;
  distanceFt: number;
}

export interface GroundMotion {
  v0z: number;
  v0xy: number;
  tDescent: number;
  dDescent: number;
  vzImpact: number;
  hops: GroundHop[];
  aRoll: number;
  vRoll0: number;
  tRoll: number;
  dRoll: number;
  dTotal: number;
  tTotal: number;
}

export interface BattedBallTrajectory {
  exitVelocityMph: number;
  launchAngleDeg: number;
  sprayAngleDeg: number;
  hangTime: number;
  apexHeight: number;
  distance: number;
  landingPos: [number, number, number];
  samples: [number, number, number, number][];
}

export interface AerodynamicFlightData {
  distance: number;
  hangTime: number;
  landingPos: [number, number, number];
  apexHeight: number;
  samples: [number, number, number, number][];
}

export interface KinematicGrounderData {
  distance: number;
  hangTime: number;
  landingPos: [number, number, number];
  apexHeight: number;
  samples: [number, number, number, number][];
}

export function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value));
}

export function roundTo(value: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  return Math.round(value * factor) / factor;
}

export function dragCoefficient(launchAngleDeg: number): number {
  if (launchAngleDeg <= 45.0) {
    return DRAG_K_AT_45;
  }
  if (launchAngleDeg >= 70.0) {
    return DRAG_K_AT_70;
  }
  const span = 70.0 - 45.0;
  const t = (launchAngleDeg - 45.0) / span;
  return DRAG_K_AT_45 + (DRAG_K_AT_70 - DRAG_K_AT_45) * t;
}

/**
 * Kinematic ground motion solver based on Dr. Alan Nathan's equations:
 * - Phase 1: Descent to first impact with z = 0.
 * - Phase 2: Multi-hop skip bounces using vertical and horizontal COR.
 * - Phase 3: Coulomb turf friction rolling deceleration.
 */
export function solveGroundMotion(
  exitVelocityMph: number,
  launchAngleDeg: number,
  contactHeightFt: number = CONTACT_HEIGHT_FT,
): GroundMotion {
  const theta = (launchAngleDeg * Math.PI) / 180.0;
  const v0 = exitVelocityMph * MPH_TO_FPS;
  const v0z = v0 * Math.sin(theta);
  const v0xy = v0 * Math.cos(theta) * AIR_DRAG_GROUND_FACTOR;

  const discriminant = v0z * v0z + 2.0 * G * contactHeightFt;
  const tDescent = (v0z + Math.sqrt(Math.max(0.0, discriminant))) / G;
  const dDescent = v0xy * tDescent;
  const vzImpact = -(v0z - G * tDescent);
  let vxyCurrent = v0xy;
  let vzCurrent = vzImpact;

  const corV = launchAngleDeg < 0.0 ? COR_VERTICAL_DIRT : COR_VERTICAL_GRASS;
  const corH = launchAngleDeg < 0.0 ? COR_HORIZONTAL_DIRT : COR_HORIZONTAL_GRASS;

  const hops: GroundHop[] = [];
  const maxHops = 3;
  while (hops.length < maxHops) {
    const vzHop = vzCurrent * corV;
    const vxyHop = vxyCurrent * corH;
    const apexFt = (vzHop * vzHop) / (2.0 * G);
    if (apexFt < HOP_CUTOFF_APEX_FT) {
      break;
    }
    const tHop = (2.0 * vzHop) / G;
    const dHop = vxyHop * tHop;
    hops.push({
      vzHop,
      vxyHop,
      apexFt,
      durationS: tHop,
      distanceFt: dHop,
    });
    vzCurrent = vzHop;
    vxyCurrent = vxyHop;
  }

  const aRoll = TURF_FRICTION_COEFF * G;
  const vRoll0 = vxyCurrent * SKID_TO_ROLL_FACTOR;
  const tRoll = aRoll > 1e-6 ? vRoll0 / aRoll : 0.0;
  const dRoll = aRoll > 1e-6 ? (vRoll0 * vRoll0) / (2.0 * aRoll) : 0.0;

  const dTotal = dDescent + hops.reduce((acc, h) => acc + h.distanceFt, 0) + dRoll;
  const tTotal = tDescent + hops.reduce((acc, h) => acc + h.durationS, 0) + tRoll;

  return {
    v0z,
    v0xy,
    tDescent,
    dDescent,
    vzImpact,
    hops,
    aRoll,
    vRoll0,
    tRoll,
    dRoll,
    dTotal,
    tTotal,
  };
}

/**
 * Computes exact kinematic time to reach target distance across the 3 phases:
 * - Phase 1: Descent
 * - Phase 2: Multi-hop skips
 * - Phase 3: Coulomb turf friction roll
 */
export function groundTransitTime(motion: GroundMotion, distanceFt: number): number {
  const targetD = Math.max(0.0, distanceFt);
  const v0xy = Math.max(1e-3, motion.v0xy);
  const tDesc = motion.tDescent;
  const dDesc = motion.dDescent;

  if (targetD <= dDesc) {
    return clamp(targetD / v0xy, 0.05, 12.0);
  }

  let curD = dDesc;
  let curT = tDesc;

  for (const hop of motion.hops) {
    const dh = hop.distanceFt;
    const th = hop.durationS;
    const vh = Math.max(1e-3, hop.vxyHop);
    if (targetD <= curD + dh) {
      return clamp(curT + (targetD - curD) / vh, 0.05, 12.0);
    }
    curD += dh;
    curT += th;
  }

  const remD = targetD - curD;
  const vRoll0 = motion.vRoll0;
  const aRoll = motion.aRoll;
  if (aRoll > 1e-6 && vRoll0 > 1e-6) {
    const disc = Math.max(0.0, vRoll0 * vRoll0 - 2.0 * aRoll * remD);
    const tau = (vRoll0 - Math.sqrt(disc)) / aRoll;
    curT += tau;
  }
  return clamp(curT, 0.05, 12.0);
}

export function sampleGroundAtTime(
  motion: GroundMotion,
  contactHeightFt: number,
  t: number,
): [number, number] {
  const tDesc = motion.tDescent;
  const v0xy = motion.v0xy;
  const v0z = motion.v0z;

  if (t <= tDesc) {
    const s = v0xy * t;
    const z = Math.max(0.0, contactHeightFt + v0z * t - 0.5 * G * t * t);
    return [s, z];
  }

  let curT = tDesc;
  let curD = motion.dDescent;
  for (const hop of motion.hops) {
    const th = hop.durationS;
    const dh = hop.distanceFt;
    const vh = hop.vxyHop;
    const vzh = hop.vzHop;
    if (t <= curT + th) {
      const dt = t - curT;
      const s = curD + vh * dt;
      const z = Math.max(0.0, vzh * dt - 0.5 * G * dt * dt);
      return [s, z];
    }
    curT += th;
    curD += dh;
  }

  const dt = t - curT;
  const aRoll = motion.aRoll;
  const vRoll0 = motion.vRoll0;
  const s = curD + vRoll0 * dt - 0.5 * aRoll * dt * dt;
  return [s, 0.0];
}

/**
 * Constructs a strictly non-decreasing sequence of sample times from t=0 to t=transitTimeS.
 * Captures the initial airborne descent touchdown and first hop apex while guaranteeing
 * strictly monotonic distances and smooth rolling without time or position inversions.
 */
export function buildMonotonicGroundTimes(
  motion: GroundMotion,
  transitTimeS: number,
  sampleCount: number = TRACE_SAMPLE_COUNT,
): number[] {
  const tDesc = motion.tDescent;
  const hops = motion.hops;
  const tSamples = new Array<number>(sampleCount).fill(0.0);

  if (hops.length > 0 && transitTimeS > tDesc + 0.05) {
    const tHop1 = hops[0].durationS;
    if (transitTimeS >= tDesc + tHop1 + 0.1) {
      tSamples[1] = 0.5 * tDesc;
      tSamples[2] = tDesc;
      tSamples[3] = tDesc + 0.5 * tHop1;
      tSamples[4] = tDesc + tHop1;
      const tRemStart = tSamples[4];
      const denom = Math.max(1, sampleCount - 1 - 4);
      for (let k = 5; k < sampleCount; k++) {
        tSamples[k] = tRemStart + ((k - 4) * (transitTimeS - tRemStart)) / denom;
      }
      return tSamples;
    } else if (transitTimeS > tDesc) {
      tSamples[1] = 0.5 * tDesc;
      tSamples[2] = tDesc;
      const tRemStart = tDesc;
      const denom = Math.max(1, sampleCount - 1 - 2);
      for (let k = 3; k < sampleCount; k++) {
        tSamples[k] = tRemStart + ((k - 2) * (transitTimeS - tRemStart)) / denom;
      }
      return tSamples;
    }
  }

  const dt = transitTimeS / Math.max(1, sampleCount - 1);
  for (let k = 0; k < sampleCount; k++) {
    tSamples[k] = k * dt;
  }
  return tSamples;
}

export function generateGroundSamples(
  motion: GroundMotion,
  contactHeightFt: number,
  sinPhi: number,
  cosPhi: number,
  sampleCount: number,
  distanceFt: number,
  transitTimeS: number,
): [number, number, number, number][] {
  const times = buildMonotonicGroundTimes(motion, transitTimeS, sampleCount);
  const samples: [number, number, number, number][] = [];
  for (let k = 0; k < times.length; k++) {
    const t = times[k];
    if (k === 0) {
      samples.push([0.0, 0.0, roundTo(contactHeightFt, 2), 0.0]);
    } else if (k === sampleCount - 1) {
      samples.push([
        roundTo(distanceFt * sinPhi, 1),
        roundTo(distanceFt * cosPhi, 1),
        0.0,
        roundTo(transitTimeS, 3),
      ]);
    } else {
      const [s, z] = sampleGroundAtTime(motion, contactHeightFt, t);
      samples.push([
        roundTo(s * sinPhi, 2),
        roundTo(s * cosPhi, 2),
        roundTo(z, 2),
        roundTo(t, 3),
      ]);
    }
  }
  return samples;
}

/**
 * Universal batted ball trajectory generator: mathematically identical to
 * Dr. Alan Nathan's physical flight engine in backend/engine/game_engine/ball_flight.py.
 */
export function computeBattedBallTrajectory(
  exitVelocityMph: number,
  launchAngleDeg: number,
  sprayAngleDeg: number,
  contactHeightFt: number = CONTACT_HEIGHT_FT,
  sampleCount: number = TRACE_SAMPLE_COUNT,
): BattedBallTrajectory {
  const ev = clamp(exitVelocityMph, 30.0, 125.0);
  const launch = clamp(launchAngleDeg, -30.0, 85.0);
  const spray = clamp(sprayAngleDeg, -80.0, 80.0);
  const contactHeight = clamp(contactHeightFt, 0.0, 6.0);
  const count = clamp(Math.round(sampleCount), 2, 64);

  const theta = (launch * Math.PI) / 180.0;
  const phi = (spray * Math.PI) / 180.0;
  const v0 = ev * MPH_TO_FPS;
  const v0z = v0 * Math.sin(theta);
  const v0xy = v0 * Math.cos(theta);

  if (launch < GROUND_LAUNCH_ANGLE) {
    const motion = solveGroundMotion(ev, launch, contactHeight);
    const distance = Math.min(MAX_GROUND_DISTANCE_FT, motion.dTotal);
    const tHang = groundTransitTime(motion, distance);
    const landingX = roundTo(distance * Math.sin(phi), 1);
    const landingY = roundTo(distance * Math.cos(phi), 1);
    let apexHeight = contactHeight;
    if (motion.hops.length > 0) {
      apexHeight = Math.max(apexHeight, ...motion.hops.map((h) => h.apexFt));
    }
    const samples = generateGroundSamples(
      motion,
      contactHeight,
      Math.sin(phi),
      Math.cos(phi),
      count,
      distance,
      tHang,
    );

    return {
      exitVelocityMph: roundTo(ev, 1),
      launchAngleDeg: roundTo(launch, 1),
      sprayAngleDeg: roundTo(spray, 1),
      hangTime: roundTo(tHang, 3),
      apexHeight: roundTo(apexHeight, 1),
      distance: roundTo(distance, 1),
      landingPos: [landingX, 0, -landingY],
      samples,
    };
  }

  const discriminant = v0z * v0z + 2.0 * G * contactHeight;
  let tVac = (v0z + Math.sqrt(Math.max(0.0, discriminant))) / G;
  tVac = Math.max(tVac, 0.05);

  let hangFactor =
    1.0 -
    0.008 * Math.max(0.0, launch - 45.0) -
    0.0002 * Math.max(0.0, 95.0 - ev);
  hangFactor = clamp(hangFactor, 0.80, 1.05);
  const tHang = clamp(tVac * hangFactor, 0.05, 7.0);

  let distance = 0.0;
  let landingX = 0.0;
  let landingY = 0.0;
  let c = 0.0;

  if (Math.abs(v0xy) >= 1e-6) {
    const k = dragCoefficient(launch);
    distance = (v0xy / k) * (1.0 - Math.exp(-k * tHang));
    landingX = roundTo(distance * Math.sin(phi), 1);
    landingY = roundTo(distance * Math.cos(phi), 1);
    const travel = v0xy * tHang;
    c = travel > 1e-6 ? clamp(1.0 - distance / travel, 0.0, 0.95) : 0.0;
  }

  let gEff = (2.0 * (contactHeight + v0z * tHang)) / (tHang * tHang);
  gEff = clamp(gEff, 1.0, 250.0);

  let apexHeight = contactHeight;
  if (v0z > 0.0) {
    apexHeight += (v0z * v0z) / (2.0 * gEff);
  }

  const sinPhi = Math.sin(phi);
  const cosPhi = Math.cos(phi);
  const samples: [number, number, number, number][] = [];

  for (let i = 0; i < count; i++) {
    const u = i / (count - 1);
    const t = u * tHang;
    const s = v0xy * tHang * u * (1.0 - c * u);
    const x = s * sinPhi;
    const y = s * cosPhi;
    let z = contactHeight + v0z * t - 0.5 * gEff * t * t;
    if (z < 0.0) {
      z = 0.0;
    }
    samples.push([roundTo(x, 2), roundTo(y, 2), roundTo(z, 2), roundTo(t, 3)]);
  }

  samples[0] = [0.0, 0.0, roundTo(contactHeight, 2), 0.0];
  samples[count - 1] = [landingX, landingY, 0.0, roundTo(tHang, 3)];

  return {
    exitVelocityMph: roundTo(ev, 1),
    launchAngleDeg: roundTo(launch, 1),
    sprayAngleDeg: roundTo(spray, 1),
    hangTime: roundTo(tHang, 3),
    apexHeight: roundTo(apexHeight, 1),
    distance: roundTo(distance, 1),
    landingPos: [landingX, 0, -landingY],
    samples,
  };
}

/**
 * Backward compatibility wrapper for aerodynamic flight trajectories.
 */
export function generateAerodynamicFlight(
  exitVelocityMph: number,
  launchAngleDeg: number,
  sprayAngleDeg: number,
  contactHeightFt: number = CONTACT_HEIGHT_FT,
  sampleCount: number = TRACE_SAMPLE_COUNT,
): AerodynamicFlightData {
  const traj = computeBattedBallTrajectory(
    exitVelocityMph,
    launchAngleDeg,
    sprayAngleDeg,
    contactHeightFt,
    sampleCount,
  );
  return {
    distance: traj.distance,
    hangTime: traj.hangTime,
    landingPos: traj.landingPos,
    apexHeight: traj.apexHeight,
    samples: traj.samples,
  };
}

/**
 * Backward compatibility wrapper for kinematic ground ball trajectories.
 */
export function generateKinematicGrounder(
  exitVelocityMph: number,
  launchAngleDeg: number,
  sprayAngleDeg: number,
  _frictionCoeff?: number,
  sampleCount: number = TRACE_SAMPLE_COUNT,
): KinematicGrounderData {
  const traj = computeBattedBallTrajectory(
    exitVelocityMph,
    launchAngleDeg,
    sprayAngleDeg,
    CONTACT_HEIGHT_FT,
    sampleCount,
  );
  return {
    distance: traj.distance,
    hangTime: traj.hangTime,
    landingPos: traj.landingPos,
    apexHeight: traj.apexHeight,
    samples: traj.samples,
  };
}

function computeBoundedGrounderTrajectory(
  ev: number,
  launch: number,
  spray: number,
  interceptPt: [number, number, number],
  contactHeightFt: number = CONTACT_HEIGHT_FT,
  count: number = TRACE_SAMPLE_COUNT,
): BattedBallTrajectory {
  const phi = (spray * Math.PI) / 180.0;
  const sinPhi = Math.sin(phi);
  const cosPhi = Math.cos(phi);
  const distance = Math.hypot(interceptPt[0], interceptPt[1]);
  const motion = solveGroundMotion(ev, launch, contactHeightFt);
  const tHang = groundTransitTime(motion, distance);
  let apexHeight = contactHeightFt;
  if (motion.hops.length > 0) {
    apexHeight = Math.max(apexHeight, ...motion.hops.map((h) => h.apexFt));
  }
  const samples = generateGroundSamples(
    motion,
    contactHeightFt,
    sinPhi,
    cosPhi,
    count,
    distance,
    tHang,
  );
  samples[count - 1] = [
    roundTo(interceptPt[0], 2),
    roundTo(interceptPt[1], 2),
    roundTo(interceptPt[2], 2),
    roundTo(tHang, 3),
  ];

  return {
    exitVelocityMph: roundTo(ev, 1),
    launchAngleDeg: roundTo(launch, 1),
    sprayAngleDeg: roundTo(spray, 1),
    hangTime: roundTo(tHang, 3),
    apexHeight: roundTo(apexHeight, 1),
    distance: roundTo(distance, 1),
    landingPos: [roundTo(interceptPt[0], 1), 0, roundTo(-interceptPt[1], 1)],
    samples,
  };
}

const ssChopperTraj = computeBoundedGrounderTrajectory(88.0, -5.0, -19.4, [-38.2, 108.5, 0.0]);
const oneBGrounderTraj = computeBoundedGrounderTrajectory(95.0, 2.0, 44.2, [58.4, 60.1, 0.0]);
const lineDriveGapTraj = computeBattedBallTrajectory(104.0, 16.0, -16.0);
const flyBallRfTraj = computeBattedBallTrajectory(90.0, 32.0, 24.0);
const moonshotTraj = computeBattedBallTrajectory(106.0, 32.0, 0.0);

export const HIT_PRESETS: HitPreset[] = [
  {
    id: 'ss_chopper',
    name: 'Chopper to Shortstop',
    category: 'grounder',
    description: 'Bouncing chopper toward shortstop. Tests 1B soft look-at weighting & turf bounce filtering.',
    launchAngle: -5.0,
    exitVelocity: 88.0,
    hangTime: ssChopperTraj.hangTime,
    isGrounder: true,
    landingPos: ssChopperTraj.landingPos,
    apexHeight: ssChopperTraj.apexHeight,
    distance: ssChopperTraj.distance,
    samples: ssChopperTraj.samples,
    fielded: true,
    fielderId: 'SS',
    fieldingType: 'GROUND_SCOOP',
    fielderStart: [-45.0, 115.0],
    interceptPoint: [-38.2, 108.5, 0.0],
  },
  {
    id: '1b_grounder',
    name: 'Sharp Grounder to 1B',
    category: 'grounder',
    description: 'Hard-hit ground ball hugging the first-base line.',
    launchAngle: 2.0,
    exitVelocity: 95.0,
    hangTime: oneBGrounderTraj.hangTime,
    isGrounder: true,
    landingPos: oneBGrounderTraj.landingPos,
    apexHeight: oneBGrounderTraj.apexHeight,
    distance: oneBGrounderTraj.distance,
    samples: oneBGrounderTraj.samples,
    fielded: true,
    fielderId: '1B',
    fieldingType: 'BACKHAND_PICK',
    fielderStart: [63.6, 63.6],
    interceptPoint: [58.4, 60.1, 0.0],
  },
  {
    id: 'line_drive_gap',
    name: 'Line Drive into Gap',
    category: 'line_drive',
    description: 'Searing line drive into the left-center alley. Tests rapid translation pan.',
    launchAngle: 16.0,
    exitVelocity: 104.0,
    hangTime: lineDriveGapTraj.hangTime,
    isGrounder: false,
    landingPos: lineDriveGapTraj.landingPos,
    apexHeight: lineDriveGapTraj.apexHeight,
    distance: lineDriveGapTraj.distance,
    samples: lineDriveGapTraj.samples,
    fielded: true,
    fielderId: 'LF',
    fieldingType: 'GROUND_SCOOP',
    fielderStart: [-115.0, 255.0],
    interceptPoint: [-75.0, 260.0, 0.0],
  },
  {
    id: 'fly_ball_rf',
    name: 'Fly Ball to Right Field',
    category: 'fly_ball',
    description: 'Towering fly ball to RF. Tests elevation coupling, dynamic FOV zoom, and catch framing.',
    launchAngle: 32.0,
    exitVelocity: 90.0,
    hangTime: flyBallRfTraj.hangTime,
    isGrounder: false,
    landingPos: flyBallRfTraj.landingPos,
    apexHeight: flyBallRfTraj.apexHeight,
    distance: flyBallRfTraj.distance,
    samples: flyBallRfTraj.samples,
    fielded: true,
    fielderId: 'RF',
    fieldingType: 'ROUTINE_FLY_CATCH',
    fielderStart: [115.0, 255.0],
    interceptPoint: [102.5, 272.0, 4.5],
  },
  {
    id: 'moonshot_hr',
    name: 'Moonshot Home Run',
    category: 'home_run',
    description: '415-ft blast over dead center. Tests max elevation and expansive stadium tracking.',
    launchAngle: 32.0,
    exitVelocity: 106.0,
    hangTime: moonshotTraj.hangTime,
    isGrounder: false,
    landingPos: moonshotTraj.landingPos,
    apexHeight: moonshotTraj.apexHeight,
    distance: moonshotTraj.distance,
    samples: moonshotTraj.samples,
    fielded: false,
    fielderId: null,
    fieldingType: 'HOME_RUN',
    fielderStart: null,
    interceptPoint: null,
  },
];

/**
 * Advances or freezes animation elapsed time based on pause state.
 */
export function stepAnimationElapsed(
  currentElapsed: number,
  delta: number,
  isPaused: boolean,
): number {
  if (isPaused) {
    return currentElapsed;
  }
  return currentElapsed + delta;
}

/**
 * Computes remaining lifecycle duration upon pause, safely clamped to at least 100ms.
 */
export function calculateRemainingLifecycleMs(
  totalOrRemainingMs: number,
  elapsedMs: number,
): number {
  return Math.max(100, Math.round(totalOrRemainingMs - elapsedMs));
}

/**
 * Builds an ActiveBattedBallData object from a calibrated preset.
 */
export function buildActiveBattedBallFromPreset(
  preset: HitPreset,
  sequence: number,
): ActiveBattedBallData {
  return {
    id: `debug-hit-${preset.id}-${sequence}`,
    hangTime: preset.hangTime,
    samples: preset.samples,
    isGrounder: preset.isGrounder,
    landingPos: preset.landingPos,
    launchAngle: preset.launchAngle,
    apexHeight: preset.apexHeight,
    distance: preset.distance,
    fielded: preset.fielded,
    fielderId: preset.fielderId,
    fieldingType: preset.fieldingType,
    fielderStart: preset.fielderStart,
    interceptPoint: preset.interceptPoint,
  };
}
