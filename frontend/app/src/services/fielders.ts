/**
 * Defensive fielder positions and baseline reach radii.
 *
 * Units are Statcast feet: +x is the right-field/first-base side, +y is depth
 * toward center field. The radii represent how far each fielder can travel to
 * make a play on a batted-ball landing point. Keep in sync with
 * backend/engine/batting_engine/contact_outcome.py FIELDERS.
 */
export interface Fielder {
  id: string;
  label: string;
  name: string;
  x: number;
  y: number;
  radius: number;
}

export interface FielderReach extends Fielder {
  distance: number;
}

export const FIELDERS: Fielder[] = [
  { id: 'P', label: 'P', name: 'pitcher', x: 0, y: 60.5, radius: 34 },
  { id: '1B', label: '1B', name: 'first base', x: 63.6, y: 63.6, radius: 56 },
  { id: '2B', label: '2B', name: 'second base', x: 45, y: 115, radius: 60 },
  { id: 'SS', label: 'SS', name: 'shortstop', x: -45, y: 115, radius: 60 },
  { id: '3B', label: '3B', name: 'third base', x: -63.6, y: 63.6, radius: 56 },
  { id: 'LF', label: 'LF', name: 'left field', x: -115, y: 255, radius: 73 },
  { id: 'CF', label: 'CF', name: 'center field', x: 0, y: 330, radius: 80 },
  { id: 'RF', label: 'RF', name: 'right field', x: 115, y: 255, radius: 73 },
];

/** Nearest fielder whose reach radius contains the landing point. */
export function fielderForLanding(
  landingX: number,
  landingY: number,
): FielderReach | null {
  let nearest: FielderReach | null = null;
  for (const fielder of FIELDERS) {
    const distance = Math.hypot(landingX - fielder.x, landingY - fielder.y);
    if (distance <= fielder.radius && (nearest === null || distance < nearest.distance)) {
      nearest = { ...fielder, distance };
    }
  }
  return nearest;
}
