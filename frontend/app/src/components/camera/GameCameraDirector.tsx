import React, { useEffect, useLayoutEffect, useRef } from 'react';
import * as THREE from 'three';

import {
  BASE_ASPECT,
  CAMERA_FAR_CLIP,
  computeAdaptiveBattedBallShot,
  computeGrounderShot,
  computeIsometricFollowPose,
  getResponsiveCameraShot,
  sampleBallGroundTrajectory,
  type CameraShot,
} from './cameraShots';
import type { GameCameraMode } from './types';
import type { ActiveBattedBallData } from '../gamefield/types';
import { useFrame, useThree } from '../gamefield/useThree';
import { useGameStore } from '../../store/gameStore';

export interface GameCameraDirectorProps {
  mode: GameCameraMode;
  activeBattedBall?: ActiveBattedBallData | null;
}

/**
 * Snaps camera position, rotation, and FOV for static modes (PITCH, BIRDSEYE)
 * or initial tracking placement.
 */
function applyStaticShot(
  camera: THREE.Camera,
  shot: CameraShot,
  aspect: number,
) {
  camera.position.set(shot.position[0], shot.position[1], shot.position[2]);
  const target = new THREE.Vector3(shot.target[0], shot.target[1], shot.target[2]);
  camera.quaternion.setFromRotationMatrix(
    new THREE.Matrix4().lookAt(camera.position, target, camera.up),
  );

  const perspective = camera as THREE.PerspectiveCamera;
  if (typeof perspective.fov === 'number') {
    perspective.fov = shot.fov;
    perspective.aspect = aspect;
    perspective.near = 1.0;
    perspective.far = CAMERA_FAR_CLIP;
    perspective.updateProjectionMatrix();
  }

  camera.updateMatrixWorld();
}

/**
 * Camera owner for the Pitch -> Contact -> Result sequence.
 *
 * Runs when the mode or viewport aspect ratio changes for static shots (PITCH, BIRDSEYE),
 * and dynamically executes smooth translating isometric tracking of batted balls in useFrame
 * without triggering React re-renders or garbage collection overhead.
 */
export const GameCameraDirector = React.memo(function GameCameraDirector({
  mode,
  activeBattedBall,
}: GameCameraDirectorProps) {
  const camera = useThree((state) => state.camera);
  const size = useThree((state) => state.size);

  // Persistent hot-path vectors allocated once on mount (0 GC churn)
  const currentTarget = useRef(new THREE.Vector3(0, 1.0, -30));
  const tempTarget = useRef(new THREE.Vector3());
  const tempPosition = useRef(new THREE.Vector3());
  const elapsedRef = useRef(0);
  const lastBattedBallRef = useRef<ActiveBattedBallData | null>(null);

  useLayoutEffect(() => {
    if (size.width <= 0 || size.height <= 0) return;

    const aspect = size.width / size.height;

    const isDynamic = mode === 'TRACKING' || mode === 'GROUNDER';
    if (!isDynamic) {
      elapsedRef.current = 0;
      lastBattedBallRef.current = null;
      const shot = getResponsiveCameraShot(mode, aspect);
      applyStaticShot(camera, shot, aspect);
      currentTarget.current.set(shot.target[0], shot.target[1], shot.target[2]);
      return;
    }

    // Initial pose when transitioning into dynamic tracking (at contact / home plate)
    const { groundPos: initGroundPos, travelDirection: initDir, ballHeight: initHeight } = activeBattedBall
      ? sampleBallGroundTrajectory(activeBattedBall.samples, 0, activeBattedBall.hangTime)
      : {
          groundPos: [0, 0, 0] as [number, number, number],
          travelDirection: [0, 0, -1] as [number, number, number],
          ballHeight: 0,
        };
    const initialShot = mode === 'GROUNDER'
      ? computeGrounderShot(initGroundPos, aspect)
      : computeAdaptiveBattedBallShot(
          initGroundPos,
          initDir,
          initHeight,
          0,
          false,
          activeBattedBall?.landingPos,
          aspect,
          activeBattedBall?.launchAngle,
        );
    applyStaticShot(camera, initialShot, aspect);
    currentTarget.current.set(
      initialShot.target[0],
      initialShot.target[1],
      initialShot.target[2],
    );
  }, [camera, mode, activeBattedBall, size.width, size.height]);

  useEffect(() => {
    return () => {
      elapsedRef.current = 0;
      lastBattedBallRef.current = null;
    };
  }, []);

  useFrame((_state, delta) => {
    // Guardrail: Only track during dynamic modes (TRACKING / GROUNDER) when active batted ball data exists
    const isDynamic = mode === 'TRACKING' || mode === 'GROUNDER';
    if (!isDynamic || !activeBattedBall) {
      if (lastBattedBallRef.current !== null) {
        lastBattedBallRef.current = null;
        elapsedRef.current = 0;
      }
      return;
    }

    // Reset trajectory timer if a new batted ball instance is supplied
    if (lastBattedBallRef.current !== activeBattedBall) {
      lastBattedBallRef.current = activeBattedBall;
      elapsedRef.current = 0;
    }

    if (useGameStore.getState().isBattedBallPaused) {
      return;
    }

    // Defensive clamping on delta to prevent camera jumps on backgrounding/lag
    const dt = Math.min(delta, 0.1);
    elapsedRef.current += dt;

    // Sample ground coordinates, directional travel vector, and vertical height
    const { groundPos, travelDirection, ballHeight } = sampleBallGroundTrajectory(
      activeBattedBall.samples,
      elapsedRef.current,
      activeBattedBall.hangTime,
    );

    const progress = Math.min(1.0, elapsedRef.current / Math.max(0.05, activeBattedBall.hangTime));
    const aspect =
      size.width > 0 && size.height > 0 ? size.width / size.height : BASE_ASPECT;

    const targetShot = mode === 'GROUNDER'
      ? computeGrounderShot(groundPos, aspect)
      : computeAdaptiveBattedBallShot(
          groundPos,
          travelDirection,
          ballHeight,
          progress,
          false,
          activeBattedBall.landingPos,
          aspect,
          activeBattedBall.launchAngle,
        );

    tempPosition.current.set(
      targetShot.position[0],
      targetShot.position[1],
      targetShot.position[2],
    );
    tempTarget.current.set(
      targetShot.target[0],
      targetShot.target[1],
      targetShot.target[2],
    );

    // Smooth damping: camera smoothly glides (0.16) and look-at tracks leading target (0.22)
    camera.position.lerp(tempPosition.current, 0.16);
    currentTarget.current.lerp(tempTarget.current, 0.22);
    camera.lookAt(currentTarget.current);

    // Smoothly update FOV for dynamic zoom during flight
    if ('fov' in camera && typeof camera.fov === 'number' && Math.abs(camera.fov - targetShot.fov) > 0.05) {
      camera.fov = THREE.MathUtils.lerp(camera.fov, targetShot.fov, 0.15);
      camera.updateProjectionMatrix();
    }
  });

  return null;
});
