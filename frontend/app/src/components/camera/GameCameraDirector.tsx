import { useLayoutEffect } from 'react';
import * as THREE from 'three';

import { getResponsiveCameraShot } from './cameraShots';
import type { GameCameraMode } from './types';
import { useThree } from '../gamefield/useThree';

export interface GameCameraDirectorProps {
  mode: GameCameraMode;
}

/**
 * Hard-cut camera owner for the Pitch -> Contact -> Result sequence.
 *
 * Runs when the mode or viewport aspect ratio changes, dynamically
 * adapting framing so batter's boxes and field boundaries stay in view
 * on both landscape and portrait screens.
 */
export function GameCameraDirector({ mode }: GameCameraDirectorProps) {
  const camera = useThree((state) => state.camera);
  const size = useThree((state) => state.size);

  useLayoutEffect(() => {
    if (size.width <= 0 || size.height <= 0) return;

    const aspect = size.width / size.height;
    const shot = getResponsiveCameraShot(mode, aspect);

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
      perspective.aspect = aspect;
      perspective.updateProjectionMatrix();
    }

    camera.updateMatrixWorld();
  }, [camera, mode, size.width, size.height]);

  return null;
}

