import type { BattedBallTelemetry } from '../types/api';

/**
 * Validates a batted-ball trajectory payload.
 *
 * A trace is playable when it has a finite hang time and 3D/4D samples
 * (e.g., [x, y, z] for fielded grounders or [x, y, z, t] for aerodynamic ball flight).
 */
export function isValidBattedBallTrace(trace: unknown): trace is BattedBallTelemetry {
  if (!trace || typeof trace !== 'object') return false;
  const candidate = trace as Partial<BattedBallTelemetry>;
  if (!Number.isFinite(candidate.hang_time_s)) return false;

  const samples = candidate.samples;
  if (!Array.isArray(samples) || samples.length < 2) return false;

  return samples.every(
    (sample) =>
      Array.isArray(sample) &&
      (sample.length === 3 || sample.length === 4) &&
      sample.every((value) => Number.isFinite(value)),
  );
}
