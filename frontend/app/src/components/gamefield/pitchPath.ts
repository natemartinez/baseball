/**
 * Shared pitch-flight path used by the visual pitch ball and the Rapier ball.
 *
 * The formula is the existing PitchVisualizer quadratic break model:
 * horizontal position is linear-to-target plus pfx·t², vertical is gravity
 * plus IVB·t², and depth is linear to the plate. Keeping one implementation
 * ensures the physics ball and the existing renderer cannot diverge.
 */
const GRAVITY = 32.174;

export interface PitchPathPoint {
  x: number;
  y: number;
  z: number;
}

export interface PitchPath {
  release: [number, number, number];
  plate: [number, number, number];
  /** Total break in feet: [horizontal, induced vertical]. */
  pfx: [number, number];
  flightTime: number;
}

function durationOf(path: PitchPath): number {
  return Math.max(path.flightTime, 0.01);
}

function initialVerticalVelocity(path: PitchPath): number {
  const duration = durationOf(path);
  const baselineY = path.plate[1] - path.pfx[1];
  return (
    (baselineY - path.release[1] + 0.5 * GRAVITY * duration * duration) /
    duration
  );
}

export function pitchPointAt(timeSeconds: number, path: PitchPath): PitchPathPoint {
  const duration = durationOf(path);
  const u = Math.max(0, Math.min(1, timeSeconds / duration));
  const t = Math.max(0, Math.min(duration, timeSeconds));
  const targetX = path.plate[0] - path.pfx[0];
  const initialVy = initialVerticalVelocity(path);

  return {
    x: path.release[0] + (targetX - path.release[0]) * u + path.pfx[0] * u * u,
    y:
      path.release[1] +
      initialVy * t -
      0.5 * GRAVITY * t * t +
      path.pfx[1] * u * u,
    z: path.release[2] + (path.plate[2] - path.release[2]) * u,
  };
}

export function pitchVelocityAt(
  timeSeconds: number,
  path: PitchPath,
): PitchPathPoint {
  const duration = durationOf(path);
  const u = Math.max(0, Math.min(1, timeSeconds / duration));
  const t = Math.max(0, Math.min(duration, timeSeconds));
  const targetX = path.plate[0] - path.pfx[0];
  const initialVy = initialVerticalVelocity(path);

  return {
    x: (targetX - path.release[0]) / duration + (2 * path.pfx[0] * u) / duration,
    y: initialVy - GRAVITY * t + (2 * path.pfx[1] * u) / duration,
    z: (path.plate[2] - path.release[2]) / duration,
  };
}

export function pitchAcceleration(path: PitchPath): PitchPathPoint {
  const duration = durationOf(path);
  return {
    x: (2 * path.pfx[0]) / (duration * duration),
    y: -GRAVITY + (2 * path.pfx[1]) / (duration * duration),
    z: 0,
  };
}
