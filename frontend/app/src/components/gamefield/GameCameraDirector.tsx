import { useLayoutEffect } from 'react';
import * as THREE from 'three';

import { BIRDSEYE_SHOT, PITCH_SHOT } from './cameraShots';
import type { GameCameraMode } from './types';
import { useThree } from './useThree';

interface GameCameraDirectorProps {
  mode: GameCameraMode;
}

/**
 * Hard-cut camera owner for the Pitch -> Contact -> Result sequence.
 *
 * Runs only when the mode changes: no frame loop, no interpolation, and no
 * per-frame React state. Every other camera animation was removed from the
 * scene components so this stays the single source of truth.
 */
export function GameCameraDirector({ mode }: GameCameraDirectorProps) {
  const camera = useThree((state) => state.camera);

  useLayoutEffect(() => {
    const shot = mode === 'BIRDSEYE' ? BIRDSEYE_SHOT : PITCH_SHOT;

    const position = new THREE.Vector3(
      shot.position[0],
      shot.position[1],
      shot.position[2],
    );
    const target = new THREE.Vector3(
      shot.target[0],
      shot.target[1],
      shot.target[2],
    );

    camera.position.copy(position);
    // Matrix4.lookAt uses the camera convention (-Z toward the target).
    // Object3D.lookAt would point +Z at the target for a non-camera dummy and
    // leave the scene behind the camera.
    camera.quaternion.setFromRotationMatrix(
      new THREE.Matrix4().lookAt(position, target, camera.up),
    );

    const perspective = camera as THREE.PerspectiveCamera;
    if (typeof perspective.fov === 'number') {
      perspective.fov = shot.fov;
      perspective.updateProjectionMatrix();
    }

    camera.updateMatrixWorld();
  }, [camera, mode]);

  return null;
}
