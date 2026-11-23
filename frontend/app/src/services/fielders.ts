/**
 * Defensive fielder positions and baseline responsibility radii.
 *
 * Units are Statcast feet: +x is the right-field/first-base side, +y is depth
 * toward center field. The responsibility radius represents the area/zone
 * that each fielder is responsible for fielding. Keep in sync with
 * backend/engine/batting_engine/contact_outcome.py FIELDERS.
 */
export interface Fielder {
  id: string;
  label: string;
  name: string;
  x: number;
  y: number;
  responsibility_radius: number;
}

export interface FielderReach extends Fielder {
  distance: number;
}

export const FIELDERS: Fielder[] = [
  { id: 'P', label: 'P', name: 'pitcher', x: 0, y: 60.5, responsibility_radius: 34 },
  { id: '1B', label: '1B', name: 'first base', x: 63.6, y: 63.6, responsibility_radius: 56 },
  { id: '2B', label: '2B', name: 'second base', x: 45, y: 115, responsibility_radius: 60 },
  { id: 'SS', label: 'SS', name: 'shortstop', x: -45, y: 115, responsibility_radius: 60 },
  { id: '3B', label: '3B', name: 'third base', x: -63.6, y: 63.6, responsibility_radius: 56 },
  { id: 'LF', label: 'LF', name: 'left field', x: -115, y: 255, responsibility_radius: 73 },
  { id: 'CF', label: 'CF', name: 'center field', x: 0, y: 330, responsibility_radius: 80 },
  { id: 'RF', label: 'RF', name: 'right field', x: 115, y: 255, responsibility_radius: 73 },
];

/** Nearest fielder whose responsibility radius contains the landing point. */
export function fielderResponsibleFor(
  landingX: number,
  landingY: number,
): FielderReach | null {
  let nearest: FielderReach | null = null;
  for (const fielder of FIELDERS) {
    const distance = Math.hypot(landingX - fielder.x, landingY - fielder.y);
    if (distance <= fielder.responsibility_radius && (nearest === null || distance < nearest.distance)) {
      nearest = { ...fielder, distance };
    }
  }
  return nearest;
}

/** Backward-compatible alias for fielderResponsibleFor. */
export const fielderForLanding = fielderResponsibleFor;
