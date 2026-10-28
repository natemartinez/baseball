/**
 * Single source of truth for the two fixed camera shots used by the in-game
 * director. Positions and targets are scene-space feet; +X is the first-base
 * side, +Y is up, and -Z is toward center field.
 */
export interface CameraShot {
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
}

/** Behind-plate working camera for aiming and pitch flight. */
export const PITCH_SHOT: CameraShot = {
  position: [0, 4.0, 5.5],
  target: [0, 1.5, -60.5],
  fov: 72,
};

/**
 * High-angle drone shot behind and above home plate. Framed so the fair field
 * sits below the top-center HUD safe area with the plate near the bottom.
 */
export const BIRDSEYE_SHOT: CameraShot = {
  position: [0, 560, 280],
  target: [0, 0, -190],
  fov: 72,
};

/** Client-side switch for the Pitch -> Contact -> Result sequence. */
export const CAMERA_SEQUENCE_ENABLED = true;
