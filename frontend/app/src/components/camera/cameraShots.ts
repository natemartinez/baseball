import type { GameCameraMode } from './types';

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

/** Reference aspect ratio (16:9 widescreen) used when authoring the base shots. */
export const BASE_ASPECT = 16 / 9;

/** Behind-plate working camera for aiming and pitch flight. */
export const PITCH_SHOT: CameraShot = {
  position: [0, 3.0, 8.5], /* Both are => */
  target: [0, 1.5, -60.5], /* [x, height from ground, distance from home plate] */
  fov: 50,
};

/**
 * High-angle drone shot behind and above home plate. Framed so the fair field
 * sits below the top-center HUD safe area with the plate near the bottom.
 */
export const BIRDSEYE_SHOT: CameraShot = {
  position: [0, 560, 280],
  target: [0, -10, -190],
  fov: 28, /* Will eventually follow the ball */
};

/** Client-side switch for the Pitch -> Contact -> Result sequence. */
export const CAMERA_SEQUENCE_ENABLED = true;

/**
 * Computes viewport-responsive camera shots across any screen aspect ratio
 * (from ultrawide 21:9 down to mobile portrait 9:16).
 *
 * Prevents horizontal clipping of batter's boxes in PITCH_SHOT and keeps
 * the entire infield and fair territory framed below the HUD in BIRDSEYE_SHOT.
 */
export function getResponsiveCameraShot(
  mode: GameCameraMode,
  aspect: number,
): CameraShot {
  const safeAspect = Number.isFinite(aspect) && aspect > 0 ? aspect : BASE_ASPECT;

  if (mode === 'BIRDSEYE') {
    if (safeAspect >= BASE_ASPECT) {
      return BIRDSEYE_SHOT;
    }
    const deficit = Math.max(0, BASE_ASPECT - safeAspect);
    const scale = 1 + Math.min(0.5, deficit * 0.35);
    const targetZOffset = Math.min(50, deficit * 35);

    return {
      position: [
        BIRDSEYE_SHOT.position[0],
        BIRDSEYE_SHOT.position[1] * scale,
        BIRDSEYE_SHOT.position[2] * scale,
      ],
      target: [
        BIRDSEYE_SHOT.target[0],
        BIRDSEYE_SHOT.target[1],
        BIRDSEYE_SHOT.target[2] + targetZOffset,
      ],
      fov: BIRDSEYE_SHOT.fov,
    };
  }

  // PITCH_SHOT (behind home plate)
  if (safeAspect >= BASE_ASPECT) {
    return PITCH_SHOT;
  }

  const deficit = Math.max(0, BASE_ASPECT - safeAspect);
  // Slightly adjust vertical FOV between 72° and 75.5° while preserving natural perspective
  const fov = Math.min(76, PITCH_SHOT.fov + deficit * 2.5);
  const halfFovRad = (fov * Math.PI) / 360;

  // Outer batter's box edges sit at X = ±5.21 ft. Target horizontal half-width
  // of 6.8 ft ensures boxes and batter animations stay completely in frame.
  const targetHalfWidth = 6.8;
  const reqDistance = targetHalfWidth / (safeAspect * Math.tan(halfFovRad));
  const deltaZ = Math.min(18, Math.max(0, reqDistance - PITCH_SHOT.position[2]));
  const slopeY = 2.5 / 66.0;

  return {
    position: [
      PITCH_SHOT.position[0],
      PITCH_SHOT.position[1] + deltaZ * slopeY,
      PITCH_SHOT.position[2] + deltaZ,
    ],
    target: [PITCH_SHOT.target[0], PITCH_SHOT.target[1], PITCH_SHOT.target[2]],
    fov,
  };
}

