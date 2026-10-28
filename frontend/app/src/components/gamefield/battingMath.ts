/**
 * Pure bat–ball contact math for Batting Practice.
 *
 * Scene units are feet. The bat is horizontal along local +X; its origin is
 * the handle/pivot. A positive yaw rotates the barrel forward toward the
 * pitcher. The pointer aims the sweet spot at the contact yaw.
 */
export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export const BALL_RADIUS_FT = 0.121;
export const BAT_LENGTH_FT = 2.75;
export const BAT_SWEET_SPOT_FT = 2.15;
export const BAT_CONTACT_ANGLE_RAD = (20 * Math.PI) / 180;
/** Slight gameplay forgiveness on top of the physical radii. */
export const CONTACT_TOLERANCE_FT = 0.08;
/** Sweep to contact, hold through the plate window, then follow through. */
export const SWING_SWEEP_S = 0.05;
export const SWING_DWELL_S = 0.08;
export const SWING_FOLLOW_S = 0.05;
export const SWING_DURATION_S =
  SWING_SWEEP_S + SWING_DWELL_S + SWING_FOLLOW_S;
export const SWING_SPAN_MIN_RAD = 2.4;
export const SWING_SPAN_MAX_RAD = 4.0;
export const CHARGE_MS = 280;

const TANGENTIAL_TRANSFER = 0.45;
const RESTITUTION_BASE = 0.35;
const RESTITUTION_SWEET = 0.25;

export interface BatSection {
  offset: number;
  length: number;
  radiusStart: number;
  radiusEnd: number;
}

/**
 * Realistic bat taper shared by the rendered meshes and the Rapier colliders.
 * The previous barrel radius (0.045 ft) made the bat read as a thin line.
 */
export const BAT_SECTIONS: BatSection[] = [
  { offset: 0.0, length: 0.55, radiusStart: 0.038, radiusEnd: 0.038 },
  { offset: 0.55, length: 0.6, radiusStart: 0.038, radiusEnd: 0.095 },
  { offset: 1.15, length: 1.3, radiusStart: 0.095, radiusEnd: 0.095 },
  { offset: 2.45, length: 0.3, radiusStart: 0.095, radiusEnd: 0.085 },
];

export function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function piecewise(value: number, points: Array<[number, number]>): number {
  if (value <= points[0][0]) return points[0][1];
  for (let i = 1; i < points.length; i += 1) {
    const [x1, y1] = points[i];
    if (value <= x1) {
      const [x0, y0] = points[i - 1];
      const t = (value - x0) / Math.max(1e-6, x1 - x0);
      return lerp(y0, y1, t);
    }
  }
  return points[points.length - 1][1];
}

/** Bat radius in feet at a distance from the handle. */
export function batRadiusAt(offsetFt: number): number {
  const r = clamp(offsetFt, 0, BAT_LENGTH_FT);
  for (const section of BAT_SECTIONS) {
    const end = section.offset + section.length;
    if (r <= end) {
      const t = clamp((r - section.offset) / Math.max(1e-6, section.length), 0, 1);
      return lerp(section.radiusStart, section.radiusEnd, t);
    }
  }
  return BAT_SECTIONS[BAT_SECTIONS.length - 1].radiusEnd;
}

/** Trampoline effect: weak at the handle, peak near the sweet spot. */
export function sweetSpotFactor(offsetFt: number): number {
  return piecewise(clamp(offsetFt, 0, BAT_LENGTH_FT), [
    [0, 0.25],
    [0.5, 0.45],
    [1.5, 0.8],
    [BAT_SWEET_SPOT_FT, 1.0],
    [2.45, 0.95],
    [BAT_LENGTH_FT, 0.7],
  ]);
}

export function batAxisDirection(yaw: number): Vec3 {
  return { x: Math.cos(yaw), y: 0, z: -Math.sin(yaw) };
}

export function batAxisPoint(pivot: Vec3, yaw: number, offsetFt: number): Vec3 {
  const dir = batAxisDirection(yaw);
  return {
    x: pivot.x + dir.x * offsetFt,
    y: pivot.y,
    z: pivot.z + dir.z * offsetFt,
  };
}

/** Pivot so the sweet spot crosses `aim` at the contact yaw. */
export function aimPivot(
  aim: Vec3,
  yaw = BAT_CONTACT_ANGLE_RAD,
  offsetFt = BAT_SWEET_SPOT_FT,
): Vec3 {
  const dir = batAxisDirection(yaw);
  return {
    x: aim.x - dir.x * offsetFt,
    y: aim.y,
    z: aim.z - dir.z * offsetFt,
  };
}

export function swingSpan(charge: number): number {
  return SWING_SPAN_MIN_RAD + clamp(charge, 0, 1) * (SWING_SPAN_MAX_RAD - SWING_SPAN_MIN_RAD);
}

/** Yaw at normalized swing progress [0,1]; the sweet spot dwells at contact. */
export function swingYawAt(progress: number, charge: number): number {
  const span = swingSpan(charge);
  const half = span / 2;
  const total = SWING_DURATION_S;
  const t = clamp(progress, 0, 1) * total;

  if (t < SWING_SWEEP_S) {
    return BAT_CONTACT_ANGLE_RAD - half + half * (t / SWING_SWEEP_S);
  }
  if (t < SWING_SWEEP_S + SWING_DWELL_S) {
    return BAT_CONTACT_ANGLE_RAD;
  }
  const followT = (t - SWING_SWEEP_S - SWING_DWELL_S) / SWING_FOLLOW_S;
  return BAT_CONTACT_ANGLE_RAD + half * clamp(followT, 0, 1);
}

/** Effective angular speed at contact (also used during the dwell). */
export function swingAngularVelocity(charge: number): number {
  return swingSpan(charge) / (2 * SWING_SWEEP_S);
}

export function closestPointOnSegment(
  point: Vec3,
  start: Vec3,
  end: Vec3,
): { point: Vec3; t: number } {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dz = end.z - start.z;
  const lengthSq = dx * dx + dy * dy + dz * dz;
  if (lengthSq < 1e-9) {
    return { point: { ...start }, t: 0 };
  }
  const t = clamp(
    ((point.x - start.x) * dx +
      (point.y - start.y) * dy +
      (point.z - start.z) * dz) /
      lengthSq,
    0,
    1,
  );
  return {
    point: { x: start.x + dx * t, y: start.y + dy * t, z: start.z + dz * t },
    t,
  };
}

export interface ContactSolve {
  contactPoint: Vec3;
  normal: Vec3;
  exitVelocityMph: number;
  launchAngleDeg: number;
  sprayAngleDeg: number;
  contactOffsetFt: number;
  batSpeedMph: number;
}

export interface ContactInputs {
  ballCenter: Vec3;
  ballVelocity: Vec3;
  pivot: Vec3;
  yaw: number;
  angularVelocity: number;
  /** Rapier manifold normal (world-space), oriented toward the ball. */
  normalOverride?: Vec3;
  /** The collision event already proved contact; skip the radial gate. */
  skipDistanceCheck?: boolean;
}

/**
 * Solves a contact against the bat cylinder. Returns null when the ball is
 * outside the bat radius or moving away from the bat.
 */
export function computeContact(input: ContactInputs): ContactSolve | null {
  const axisStart = input.pivot;
  const axisEnd = batAxisPoint(input.pivot, input.yaw, BAT_LENGTH_FT);
  const closest = closestPointOnSegment(input.ballCenter, axisStart, axisEnd);
  const offset = closest.t * BAT_LENGTH_FT;
  const radius = batRadiusAt(offset);

  const dx = input.ballCenter.x - closest.point.x;
  const dy = input.ballCenter.y - closest.point.y;
  const dz = input.ballCenter.z - closest.point.z;
  const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);

  if (!input.skipDistanceCheck && distance > BALL_RADIUS_FT + radius + CONTACT_TOLERANCE_FT) {
    return null;
  }

  let normal =
    distance > 1e-6
      ? { x: dx / distance, y: dy / distance, z: dz / distance }
      : { x: 0, y: 0, z: -1 };
  if (input.normalOverride) {
    const length = Math.sqrt(
      input.normalOverride.x * input.normalOverride.x +
        input.normalOverride.y * input.normalOverride.y +
        input.normalOverride.z * input.normalOverride.z,
    );
    if (length > 1e-6) {
      normal = {
        x: input.normalOverride.x / length,
        y: input.normalOverride.y / length,
        z: input.normalOverride.z / length,
      };
    }
  }

  const rX = closest.point.x - input.pivot.x;
  const rZ = closest.point.z - input.pivot.z;
  const batVelocity = {
    x: input.angularVelocity * rZ,
    y: 0,
    z: -input.angularVelocity * rX,
  };

  const rel = {
    x: input.ballVelocity.x - batVelocity.x,
    y: input.ballVelocity.y - batVelocity.y,
    z: input.ballVelocity.z - batVelocity.z,
  };
  const vNormal = rel.x * normal.x + rel.y * normal.y + rel.z * normal.z;
  if (vNormal >= 0) return null;

  const sweet = sweetSpotFactor(offset);
  const restitution = RESTITUTION_BASE + RESTITUTION_SWEET * sweet;
  const batNormal =
    batVelocity.x * normal.x + batVelocity.y * normal.y + batVelocity.z * normal.z;
  const batTangent = {
    x: batVelocity.x - normal.x * batNormal,
    y: batVelocity.y - normal.y * batNormal,
    z: batVelocity.z - normal.z * batNormal,
  };

  const exit = {
    x:
      input.ballVelocity.x -
      (1 + restitution) * vNormal * normal.x +
      TANGENTIAL_TRANSFER * sweet * batTangent.x,
    y:
      input.ballVelocity.y -
      (1 + restitution) * vNormal * normal.y +
      TANGENTIAL_TRANSFER * sweet * batTangent.y,
    z:
      input.ballVelocity.z -
      (1 + restitution) * vNormal * normal.z +
      TANGENTIAL_TRANSFER * sweet * batTangent.z,
  };

  const speed = Math.sqrt(exit.x * exit.x + exit.y * exit.y + exit.z * exit.z);
  const horizontal = Math.sqrt(exit.x * exit.x + exit.z * exit.z);
  const batSpeed = Math.sqrt(
    batVelocity.x * batVelocity.x +
      batVelocity.y * batVelocity.y +
      batVelocity.z * batVelocity.z,
  );

  return {
    contactPoint: closest.point,
    normal,
    exitVelocityMph: clamp(speed / 1.46667, 45, 122),
    launchAngleDeg: clamp((Math.atan2(exit.y, horizontal) * 180) / Math.PI, -25, 78),
    sprayAngleDeg: clamp((Math.atan2(exit.x, -exit.z) * 180) / Math.PI, -65, 65),
    contactOffsetFt: offset,
    batSpeedMph: batSpeed / 1.46667,
  };
}
