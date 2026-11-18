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
  position: [0, 400, 280],
  target: [0, -10, -190],
  fov: 28, /* Will eventually follow the ball */
};

/**
 * Elevated vantage behind home plate for ground balls and choppers.
 * Frames the entire infield, baselines, and fielding putout plays.
 */
export const GROUNDER_SHOT: CameraShot = {
  position: [0, 48.0, 48.0],
  target: [0, 1.0, -95.0],
  fov: 46,
};

/**
 * Fast, low-trajectory follow camera for line drives into the gaps or down the lines.
 * Elevated vantage (altitude 54 ft, rear distance 52 ft) to deliver a dramatic,
 * tactile feel for 100+ mph laser trajectories.
 */
export const LINE_DRIVE_SHOT: CameraShot = {
  position: [0, 54.0, 52.0],
  target: [0, 1.0, -100.0],
  fov: 40,
};

/**
 * Stadium press-box tracking camera for fly balls and home runs.
 * Elevated vantage (altitude 85 ft, rear distance 68 ft) framing ball arc against the
 * stadium sky and smoothly transitioning to outfield landing/catch zones.
 */
export const FLY_BALL_SHOT: CameraShot = {
  position: [0, 85.0, 68.0],
  target: [0, 1.0, -120.0],
  fov: 42,
};

/**
 * Broadcast Tracking Camera configuration.
 * Elevated stadium press-box angle (~52 ft up, 36 ft back from home plate)
 * tracking the batted ball smoothly with ball-centering.
 */
export interface TrackingCameraConfig {
  basePosition: [number, number, number];
  lookAtLead: number;
  dollyFactorZ: number;
  dollyFactorX: number;
  fov: number;
}

export const TRACKING_SHOT_CONFIG: TrackingCameraConfig = {
  basePosition: [0, 60.0, 36.0],
  lookAtLead: 0.0,
  dollyFactorZ: 0.15,
  dollyFactorX: 0.25,
  fov: 34,
};

/**
 * Baseball Superstars Isometric Follow Camera configuration.
 * Elevated 45-degree angle (~90 ft up, 90 ft back) that smoothly translates
 * across the diamond with the ball while leading ahead of the play.
 */
export interface IsometricCameraConfig {
  altitude: number;
  rearDistance: number;
  fov: number;
  leadDistance: number;
}

export const ISOMETRIC_SHOT_CONFIG: IsometricCameraConfig = {
  altitude: 90.0,
  rearDistance: 90.0,
  fov: 38,
  leadDistance: 30.0,
};

/** Client-side switch for the Pitch -> Contact -> Result sequence. */
export const CAMERA_SEQUENCE_ENABLED = true;

/**
 * Resolves the active camera mode based on the current pitch phase, active batted ball presence,
 * and result hold state.
 *
 * Ensures the behind-the-plate batting camera (PITCH_SHOT) is retained during the contact impact
 * moment (REACTING beat) so the player sees the bat strike the ball, transitioning cleanly to
 * TRACKING when BATTED_BALL begins.
 */
export function resolveGameCameraMode(
  phase: string,
  hasActiveBattedBall: boolean,
  resultCameraHold: boolean,
  manualMode: GameCameraMode = 'PITCH',
  cameraSequenceEnabled: boolean = CAMERA_SEQUENCE_ENABLED,
  isGrounder: boolean = false,
): GameCameraMode {
  if (
    cameraSequenceEnabled &&
    hasActiveBattedBall &&
    (phase === 'BATTED_BALL' || (phase === 'IDLE' && resultCameraHold))
  ) {
    return isGrounder ? 'GROUNDER' : 'TRACKING';
  }
  return manualMode;
}

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

  if (mode === 'GROUNDER') {
    return computeGrounderShot([0, 0, -30], safeAspect);
  }

  if (mode === 'TRACKING') {
    return computeIsometricFollowPose([0, 0, 0], [0, 0, -1], safeAspect);
  }

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

/**
 * Computes the Broadcast Tracking Camera pose dynamically given the ball's current 3D position.
 * Keeps the ball centered in the camera's look-at target.
 * Includes defensive guardrails against NaN / non-finite coordinates.
 */
export function computeBroadcastTrackingPose(
  ballPos: [number, number, number],
  _aspect: number = BASE_ASPECT,
  config: TrackingCameraConfig = TRACKING_SHOT_CONFIG,
): CameraShot {
  const [bx, by, bz] = ballPos;
  const isFinitePos = Number.isFinite(bx) && Number.isFinite(by) && Number.isFinite(bz);

  const safeBx = isFinitePos ? bx : 0;
  const safeBy = isFinitePos ? by : 1.0;
  const safeBz = isFinitePos ? bz : -120;

  const target: [number, number, number] = [
    safeBx,
    Math.max(1.0, safeBy),
    safeBz + (config.lookAtLead || 0),
  ];

  const position: [number, number, number] = [
    config.basePosition[0] + safeBx * config.dollyFactorX,
    config.basePosition[1],
    config.basePosition[2] - Math.abs(safeBz) * config.dollyFactorZ,
  ];

  return {
    position,
    target,
    fov: config.fov,
  };
}

/**
 * Computes adaptive camera shot for batted balls:
 *
 * 1. Grounder / Chopper (isGrounder === true):
 *    - Pulls back to an elevated high-pitch angle behind home plate ([camX, 170, 150])
 *      keeping infield dirt, bases, and converging defenders in frame.
 *    - Soft Look-At weighting: blends between ball ground position (65%) and 1B putout bag (35%).
 *    - Strict bounce filtering: target Y is anchored at 1.0 ft (zero vertical bobbing/horizon jitter).
 *
 * 2. Fly Ball / Line Drive (isGrounder === false):
 *    - Elevation coupling: target Y lifts with ball height, altitude elevates proportionally.
 *    - Dynamic FOV expansion: widens FOV from 40° up to 48° during high flight so ball and outfield turf stay framed.
 *    - Landing zone framing: as progress crosses apex (>= 0.45), smoothstep blends tracking anchor
 *      from ball towards projected landing shadow on the grass, framing the catch play.
 */
/**
 * Computes the dedicated GROUNDER camera shot given the ball's current ground position.
 * Respects GROUNDER_SHOT base position, target, and FOV, adapting dynamically to viewport aspect ratio.
 */
export function computeGrounderShot(
  ballGroundPos: [number, number, number],
  aspect: number = BASE_ASPECT,
  baseShot: CameraShot = GROUNDER_SHOT,
): CameraShot {
  const [bx, _by, bz] = ballGroundPos;
  const safeBx = Number.isFinite(bx) ? bx : 0;
  const safeBz = Number.isFinite(bz) ? bz : -10;

  // 1B bag putout target: [63.64, 0, -63.64]
  const fieldingTargetX = 63.64;
  const fieldingTargetZ = -63.64;
  const w = 0.35;

  const targetX = safeBx * (1 - w) + fieldingTargetX * w;
  const targetZ = safeBz * (1 - w) + fieldingTargetZ * w;
  const target: [number, number, number] = [targetX, 1.0, targetZ];

  const safeAspect = Number.isFinite(aspect) && aspect > 0 ? aspect : BASE_ASPECT;
  const deficit = Math.max(0, BASE_ASPECT - safeAspect);
  const aspectScale = 1.0 + Math.min(0.15, deficit * 0.1);

  // Position is firmly anchored at the established baseShot station behind home plate
  const position: [number, number, number] = [
    baseShot.position[0],
    baseShot.position[1] * aspectScale,
    baseShot.position[2] * aspectScale,
  ];

  // Gentle telephoto zoom for grounders rolling into shallow outfield (> 100 ft)
  const dist = Math.hypot(safeBx, safeBz);
  const zoomProgress = Math.max(0, Math.min(1.0, (dist - 100.0) / 160.0));
  const fov = Math.max(34.0, baseShot.fov - zoomProgress * 8.0);

  return {
    position,
    target,
    fov,
  };
}

export function computeAdaptiveBattedBallShot(
  ballGroundPos: [number, number, number],
  travelDirection: [number, number, number] = [0, 0, -1],
  ballHeight: number = 0,
  progress: number = 0,
  isGrounder: boolean = false,
  landingPos?: [number, number, number],
  aspect: number = BASE_ASPECT,
  launchAngle?: number,
  baseShot?: CameraShot,
): CameraShot {
  const safeAspect = Number.isFinite(aspect) && aspect > 0 ? aspect : BASE_ASPECT;

  if (isGrounder) {
    return computeGrounderShot(ballGroundPos, safeAspect);
  }

  const isLineDrive =
    typeof launchAngle === 'number' && Number.isFinite(launchAngle) && launchAngle < 25;
  const activeBaseShot = baseShot ?? (isLineDrive ? LINE_DRIVE_SHOT : FLY_BALL_SHOT);

  const [bx, _by, bz] = ballGroundPos;
  const safeBx = Number.isFinite(bx) ? bx : 0;
  const safeBz = Number.isFinite(bz) ? bz : -10;

  const [dx, _dy, dz] = travelDirection;
  const len = Math.hypot(Number.isFinite(dx) ? dx : 0, Number.isFinite(dz) ? dz : 0);
  const safeDirX = len > 0.001 ? dx / len : 0;
  const safeDirZ = len > 0.001 ? dz / len : -1;

  const safeHeight = Number.isFinite(ballHeight) ? Math.max(0, ballHeight) : 0;
  const safeProgress = Number.isFinite(progress) ? Math.max(0, Math.min(1.0, progress)) : 0;
  const deficit = Math.max(0, BASE_ASPECT - safeAspect);
  const aspectScale = 1.0 + Math.min(0.15, deficit * 0.1);

  // Smoothstep transition from ball anchor to landing zone starting at apex (0.45) to catch (0.95)
  const tau = Math.max(0, Math.min(1.0, (safeProgress - 0.45) / 0.50));
  const landingBlend = tau * tau * (3 - 2 * tau);

  const safeLx = (landingPos && Number.isFinite(landingPos[0])) ? landingPos[0] : safeBx;
  const safeLz = (landingPos && Number.isFinite(landingPos[2])) ? landingPos[2] : safeBz;

  const leadFactor = 20.0 * (1 - landingBlend);
  const curBallX = safeBx + safeDirX * leadFactor;
  const curBallZ = safeBz + safeDirZ * leadFactor;

  const anchorX = curBallX * (1 - landingBlend) + safeLx * landingBlend;
  const anchorZ = curBallZ * (1 - landingBlend) + safeLz * landingBlend;

  const targetY = 1.0 + Math.min(safeHeight * 0.38, 48.0);
  const target: [number, number, number] = [anchorX, targetY, anchorZ];

  // Dynamic Telephoto Optical Zoom:
  // As distance from home plate increases from 40 ft to 360 ft,
  // smoothly narrow FOV from base FOV down to ~22° (line drive) or ~22° (fly ball),
  // keeping the baseball clearly visible and prominent on mobile screens.
  const dist = Math.hypot(anchorX, anchorZ);
  const zoomProgress = Math.max(0, Math.min(1.0, (dist - 40.0) / 320.0));
  const maxZoomDeg = isLineDrive ? 14.0 : 18.0;
  const fov = Math.max(18.0, activeBaseShot.fov - zoomProgress * maxZoomDeg);

  // Camera station is firmly anchored at the established baseShot station behind home plate
  const position: [number, number, number] = [
    activeBaseShot.position[0],
    activeBaseShot.position[1] * aspectScale,
    activeBaseShot.position[2] * aspectScale,
  ];

  return {
    position,
    target,
    fov,
  };
}

/**
 * Computes the Baseball Superstars 45-degree isometric follow camera pose.
 * Keeps the camera at a consistent, tactile altitude while dynamically
 * translating across the field and leading ahead of the ball.
 *
 * Guarded against NaN/non-finite inputs and zero velocity vectors.
 */
export function computeIsometricFollowPose(
  ballGroundPos: [number, number, number],
  travelDirection: [number, number, number] = [0, 0, -1],
  aspect: number = BASE_ASPECT,
  config: IsometricCameraConfig = ISOMETRIC_SHOT_CONFIG,
): CameraShot {
  const [bx, by, bz] = ballGroundPos;
  const isFinitePos = Number.isFinite(bx) && Number.isFinite(by) && Number.isFinite(bz);

  const safeBx = isFinitePos ? bx : 0;
  const safeBz = isFinitePos ? bz : -10;

  // Normalize horizontal travel direction vector
  const [dx, _dy, dz] = travelDirection;
  const len = Math.hypot(Number.isFinite(dx) ? dx : 0, Number.isFinite(dz) ? dz : 0);
  const safeDirX = len > 0.001 ? dx / len : 0;
  const safeDirZ = len > 0.001 ? dz / len : -1;

  // Directional lead ahead of the play
  const targetX = safeBx + safeDirX * config.leadDistance;
  const targetZ = safeBz + safeDirZ * config.leadDistance;
  const target: [number, number, number] = [targetX, 1.0, targetZ];

  // Aspect compensation: subtle scaling on portrait (<16:9), capped at 1.15
  const safeAspect = Number.isFinite(aspect) && aspect > 0 ? aspect : BASE_ASPECT;
  const deficit = Math.max(0, BASE_ASPECT - safeAspect);
  const aspectScale = 1.0 + Math.min(0.15, deficit * 0.1);

  // Position sits 90 ft up (+Y) and 90 ft behind target (+Z toward home plate)
  const position: [number, number, number] = [
    targetX,
    config.altitude * aspectScale,
    targetZ + config.rearDistance * aspectScale,
  ];

  return {
    position,
    target,
    fov: config.fov,
  };
}

export interface GroundTrajectorySample {
  groundPos: [number, number, number];
  travelDirection: [number, number, number];
  ballHeight: number;
}

export interface TrajectoryInterpolationResult {
  index: number;
  nextIndex: number;
  alpha: number;
}

/**
 * Resolves the interpolation segment index and fractional alpha along the trajectory
 * at a given elapsed time using sample timestamps if present, or uniform progress as fallback.
 */
export function resolveTrajectoryInterpolation(
  samples: [number, number, number, number?][] | [number, number, number][],
  elapsed: number,
  hangTime: number,
): TrajectoryInterpolationResult {
  if (!samples || samples.length === 0) {
    return { index: 0, nextIndex: 0, alpha: 0.0 };
  }
  const lastIndex = samples.length - 1;
  if (lastIndex === 0) {
    return { index: 0, nextIndex: 0, alpha: 0.0 };
  }

  const duration = Math.max(0.05, hangTime);
  const safeElapsed = Math.max(0.0, elapsed);

  if (safeElapsed >= duration) {
    return { index: lastIndex, nextIndex: lastIndex, alpha: 1.0 };
  }

  // Check if samples carry timestamps on endpoints
  const hasTimestamps =
    typeof samples[0][3] === 'number' && typeof samples[lastIndex][3] === 'number';

  if (hasTimestamps) {
    let i = 0;
    while (i < lastIndex - 1 && (samples[i + 1][3] ?? 0) <= safeElapsed) {
      i++;
    }
    const t0 = samples[i][3] ?? 0.0;
    const t1 = samples[i + 1][3] ?? duration;
    const dt = Math.max(1e-4, t1 - t0);
    const alpha = Math.min(1.0, Math.max(0.0, (safeElapsed - t0) / dt));
    return { index: i, nextIndex: i + 1, alpha };
  }

  // Fallback to uniform progress for legacy 3D samples
  const progress = Math.min(1.0, safeElapsed / duration);
  const scaled = progress * lastIndex;
  const index = Math.min(Math.floor(scaled), lastIndex);
  const nextIndex = Math.min(index + 1, lastIndex);
  const alpha = scaled - index;
  return { index, nextIndex, alpha };
}

/**
 * Samples the ball's ground position, instantaneous horizontal travel direction,
 * and vertical height from trajectory samples at a given elapsed time.
 * Decouples vertical hops from ground-plane coordinates (groundPos[1] = 0).
 */
export function sampleBallGroundTrajectory(
  samples: [number, number, number, number?][] | [number, number, number][],
  elapsed: number,
  hangTime: number,
): GroundTrajectorySample {
  if (!samples || samples.length === 0) {
    return {
      groundPos: [0, 0, -40],
      travelDirection: [0, 0, -1],
      ballHeight: 0,
    };
  }

  if (samples.length === 1) {
    const [x, y, z] = samples[0];
    const safeX = Number.isFinite(x) ? x : 0;
    const safeY = Number.isFinite(y) ? y : 50;
    const safeZ = Number.isFinite(z) ? Math.max(0, z) : 0;
    return {
      groundPos: [safeX, 0, -safeY],
      travelDirection: [0, 0, -1],
      ballHeight: safeZ,
    };
  }

  const lastIndex = samples.length - 1;
  const { index, nextIndex, alpha } = resolveTrajectoryInterpolation(samples, elapsed, hangTime);

  const p1 = samples[index];
  const p2 = samples[nextIndex];

  const px = p1[0] + (p2[0] - p1[0]) * alpha;
  const py = p1[1] + (p2[1] - p1[1]) * alpha;
  const pz = p1[2] + (p2[2] - p1[2]) * alpha;

  const safeX = Number.isFinite(px) ? px : 0;
  const safeY = Number.isFinite(py) ? py : 40;
  const safeZ = Number.isFinite(pz) ? Math.max(0, pz) : 0;

  // Tangent vector along trajectory in scene coords (physics dy -> scene -dZ)
  let dx = p2[0] - p1[0];
  let dz = -(p2[1] - p1[1]);

  if (Math.hypot(dx, dz) < 0.001) {
    const first = samples[0];
    const last = samples[lastIndex];
    dx = last[0] - first[0];
    dz = -(last[1] - first[1]);
  }

  const len = Math.hypot(Number.isFinite(dx) ? dx : 0, Number.isFinite(dz) ? dz : 0);
  const travelDirection: [number, number, number] =
    len > 0.001 ? [dx / len, 0, dz / len] : [0, 0, -1];

  return {
    groundPos: [safeX, 0, -safeY],
    travelDirection,
    ballHeight: safeZ,
  };
}

/**
 * Samples the 3D scene-space ball coordinates from physics trajectory samples at a given elapsed time.
 * Translates physics coordinates (x, y, z) into Three.js scene coordinates (x, z, -y).
 * Guarded against empty samples, zero hang time, and non-finite values.
 */
export function sampleBallScenePosition(
  samples: [number, number, number, number?][] | [number, number, number][],
  elapsed: number,
  hangTime: number,
): [number, number, number] {
  if (!samples || samples.length === 0) {
    return [0, 1.0, -40];
  }

  if (samples.length === 1) {
    const [x, y, z] = samples[0];
    const safeX = Number.isFinite(x) ? x : 0;
    const safeY = Number.isFinite(y) ? y : 40;
    const safeZ = Number.isFinite(z) ? z : 1.0;
    return [safeX, safeZ, -safeY];
  }

  const { index, nextIndex, alpha } = resolveTrajectoryInterpolation(samples, elapsed, hangTime);

  const p1 = samples[index];
  const p2 = samples[nextIndex];

  const px = p1[0] + (p2[0] - p1[0]) * alpha;
  const py = p1[1] + (p2[1] - p1[1]) * alpha;
  const pz = p1[2] + (p2[2] - p1[2]) * alpha;

  const safeX = Number.isFinite(px) ? px : 0;
  const safeY = Number.isFinite(py) ? py : 40;
  const safeZ = Number.isFinite(pz) ? pz : 1.0;

  return [safeX, safeZ, -safeY];
}



