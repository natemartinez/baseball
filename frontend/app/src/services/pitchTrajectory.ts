import type { PitchArsenalItem } from '../types/api';

export interface PitchPoint3D {
  x: number;
  y: number;
  z: number;
}

export type PitcherHand = 'R' | 'L';

interface MovementEntry {
  match: string;
  hb: number;
  ivb: number;
}

/**
 * Fallback Statcast movement in inches.
 * Horizontal break uses the RHP convention: positive = glove side.
 * IVB positive = ride, negative = drop.
 */
export const DEFAULT_PITCH_MOVEMENT: MovementEntry[] = [
  { match: 'sweeper', hb: 18.2, ivb: 4.5 },
  { match: 'gyro', hb: 5.5, ivb: -1.0 },
  { match: 'slider', hb: 5.5, ivb: -1.0 },
  { match: 'four', hb: -7.5, ivb: 16.0 },
  { match: '4-seam', hb: -7.5, ivb: 16.0 },
  { match: 'curve', hb: -8.0, ivb: -12.0 },
  { match: 'sinker', hb: -14.0, ivb: 6.0 },
  { match: 'change', hb: -12.0, ivb: 2.0 },
  { match: 'split', hb: -6.0, ivb: -2.0 },
  { match: 'cutter', hb: 4.0, ivb: 6.0 },
];

export const DEFAULT_MOVEMENT = { hb: -7.5, ivb: 16.0 };

export function movementForPitch(pitchName?: string): { hb: number; ivb: number } {
  const name = (pitchName ?? '').toLowerCase();
  for (const entry of DEFAULT_PITCH_MOVEMENT) {
    if (name.includes(entry.match)) {
      return { hb: entry.hb, ivb: entry.ivb };
    }
  }
  return { ...DEFAULT_MOVEMENT };
}

export function movementFromArsenal(
  item?: PitchArsenalItem | null,
): { hb: number; ivb: number } {
  const fallback = movementForPitch(item?.name);
  return {
    hb: item?.horizontal_break_in ?? fallback.hb,
    ivb: item?.induced_vertical_break_in ?? fallback.ivb,
  };
}

/**
 * Boundary-constrained constant-acceleration trajectory.
 *
 * x(t) = release.x + (target.x - release.x)·t + (signedHB/12)·(t² − t)
 * z(t) = release.z + (target.z - release.z)·t + (IVB/12)·(t² − t)
 *
 * t=0 is the release, t=1 is the realized plate target. The plate tangent
 * remains in the break direction, so the ball never hooks back. HB is
 * mirrored for left-handed pitchers so the break stays arm-relative.
 */
export function calculatePitchPoint(
  t: number,
  release: PitchPoint3D,
  target: PitchPoint3D,
  hbInches: number,
  ivbInches: number,
  hand: PitcherHand,
): PitchPoint3D {
  const sign = hand === 'L' ? -1 : 1;
  const hbFt = (hbInches * sign) / 12;
  const ivbFt = ivbInches / 12;
  const deviation = t * t - t;

  return {
    x: release.x + (target.x - release.x) * t + hbFt * deviation,
    y: release.y + (target.y - release.y) * t,
    z: release.z + (target.z - release.z) * t + ivbFt * deviation,
  };
}

export function defaultRelease(hand: PitcherHand): PitchPoint3D {
  return { x: hand === 'R' ? -2.1 : 2.1, y: 54.5, z: 5.9 };
}
