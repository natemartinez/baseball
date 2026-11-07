import { useEffect } from 'react';
import * as THREE from 'three';

import {
  HOME_PLATE_DEPTH,
  HOME_PLATE_HALF_WIDTH,
} from '../gamefield/fieldGeometry';
import type { ProjectedPlatePosition } from './types';
import { useThree } from '../gamefield/useThree';

const PLATE_Y = 0.015;
const PLATE_WORLD_POSITION = new THREE.Vector3(0, PLATE_Y, 0);

/** Strike-zone bounds used by the 2D HUD (Statcast feet). */
const STRIKE_ZONE_HALF_WIDTH = 0.7083;
const STRIKE_ZONE_BOTTOM = 1.5;
const STRIKE_ZONE_TOP = 3.5;

export interface PlateProjectorProps {
  onProject?: (position: ProjectedPlatePosition) => void;
}

/**
 * Screen-space camera projector: maps 3D home plate and strike-zone vertices
 * through the active camera frustum into normalized ratios for the 2D HUD overlay.
 */
export function PlateProjector({ onProject }: PlateProjectorProps) {
  const camera = useThree((state) => state.camera);
  const size = useThree((state) => state.size);

  useEffect(() => {
    // Canvas reports 0x0 before its first layout pass, which would make the
    // camera aspect NaN and poison the overlay position.
    if (size.width <= 0 || size.height <= 0) return;

    camera.updateMatrixWorld();

    const projectX = (x: number, z: number) => {
      const projected = new THREE.Vector3(x, PLATE_Y, z).project(camera);
      return ((projected.x + 1) / 2) * size.width;
    };

    // The plate's widest silhouette is its near shoulder edge; the front edge
    // is slightly narrower in perspective. Use the wider of the two so the
    // overlay aligns with the visible left/right plate edges.
    const nearWidth =
      projectX(HOME_PLATE_HALF_WIDTH, -HOME_PLATE_HALF_WIDTH) -
      projectX(-HOME_PLATE_HALF_WIDTH, -HOME_PLATE_HALF_WIDTH);
    const farWidth =
      projectX(HOME_PLATE_HALF_WIDTH, -HOME_PLATE_DEPTH) -
      projectX(-HOME_PLATE_HALF_WIDTH, -HOME_PLATE_DEPTH);
    const plateWidth = Math.max(nearWidth, farWidth);

    const projectRatio = (x: number, y: number, z: number) => {
      const projected = new THREE.Vector3(x, y, z).project(camera);
      return {
        xRatio: (projected.x + 1) / 2,
        yRatio: (1 - projected.y) / 2,
      };
    };

    const apex = PLATE_WORLD_POSITION.clone().project(camera);
    const front = new THREE.Vector3(0, PLATE_Y, -HOME_PLATE_DEPTH).project(camera);
    const zoneTop = projectRatio(0, STRIKE_ZONE_TOP, 0);
    const zoneBottom = projectRatio(0, STRIKE_ZONE_BOTTOM, 0);
    const zoneLeft = projectRatio(-STRIKE_ZONE_HALF_WIDTH, 2.5, 0);
    const zoneRight = projectRatio(STRIKE_ZONE_HALF_WIDTH, 2.5, 0);

    onProject?.({
      xRatio: (apex.x + 1) / 2,
      yRatio: (1 - apex.y) / 2,
      frontRatio: (1 - front.y) / 2,
      widthRatio: plateWidth / size.width,
      zoneTopRatio: zoneTop.yRatio,
      zoneBottomRatio: zoneBottom.yRatio,
      zoneWidthRatio: zoneRight.xRatio - zoneLeft.xRatio,
    });
  }, [camera, size.width, size.height, onProject]);

  return null;
}

