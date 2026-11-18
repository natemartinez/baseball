import React from 'react';

import {
  FENCE_WALL_HEIGHT,
  FOUL_POLE_HEIGHT,
  FOUL_POLE_LEFT_POS,
  FOUL_POLE_RADIUS,
  FOUL_POLE_RIGHT_POS,
} from './fieldGeometry';

/**
 * Regulation Foul Pole Color
 * MLB Rule 2.01 specifies foul poles painted yellow / gold for optimal contrast.
 */
export const FOUL_POLE_COLOR = '#FFD700';

/**
 * Regulation Screen Wing Dimensions
 * Netting attached to each pole extends from fence top (8 ft) to pole top (32 ft),
 * projecting 2.5 ft into fair territory facing towards center field.
 */
export const FOUL_POLE_WING_WIDTH = 2.5;
export const FOUL_POLE_WING_HEIGHT = 24.0;
export const FOUL_POLE_WING_THICKNESS = 0.05;
export const FOUL_POLE_WING_ELEVATION = FENCE_WALL_HEIGHT + FOUL_POLE_WING_HEIGHT / 2; // 20.0 ft

// Calculate angle of right foul line from home plate
const rfAngle = Math.atan2(
  Math.abs(FOUL_POLE_RIGHT_POS[0]),
  Math.abs(FOUL_POLE_RIGHT_POS[2]),
);

// Inward fair-territory direction unit vector components
const cosRf = Math.cos(rfAngle);
const sinRf = Math.sin(rfAngle);

// Distance from pole center to screen wing center
const wingDist = FOUL_POLE_RADIUS + FOUL_POLE_WING_WIDTH / 2;

// Offsets for left and right screen wings
const leftWingOffset: [number, number, number] = [
  wingDist * cosRf,
  FOUL_POLE_WING_ELEVATION,
  -wingDist * sinRf,
];
const rightWingOffset: [number, number, number] = [
  -wingDist * cosRf,
  FOUL_POLE_WING_ELEVATION,
  -wingDist * sinRf,
];

// Rotations around Y so local Z (wing width) extends into fair territory
const leftWingRotation: [number, number, number] = [0, Math.atan2(cosRf, -sinRf), 0];
const rightWingRotation: [number, number, number] = [0, Math.atan2(-cosRf, -sinRf), 0];

/**
 * FoulPoles Component
 *
 * Renders the left and right regulation 32 ft yellow foul poles at the 330 ft outfield
 * fence intersections, complete with fair-territory screen wings (24 ft x 2.5 ft)
 * extending from the top of the 8 ft wall to the pole top.
 */
export function FoulPoles(props?: React.ComponentProps<'group'>) {
  return (
    <group {...props}>
      {/* Left-field Foul Pole (at LF 330 ft corner) */}
      <group position={FOUL_POLE_LEFT_POS}>
        {/* Main Pole */}
        <mesh position={[0, FOUL_POLE_HEIGHT / 2, 0]}>
          <cylinderGeometry
            args={[FOUL_POLE_RADIUS, FOUL_POLE_RADIUS, FOUL_POLE_HEIGHT, 16]}
          />
          <meshStandardMaterial
            color={FOUL_POLE_COLOR}
            roughness={0.4}
            metalness={0.2}
          />
        </mesh>

        {/* Fair-territory Screen Wing */}
        <mesh position={leftWingOffset} rotation={leftWingRotation}>
          <boxGeometry
            args={[
              FOUL_POLE_WING_THICKNESS,
              FOUL_POLE_WING_HEIGHT,
              FOUL_POLE_WING_WIDTH,
            ]}
          />
          <meshStandardMaterial
            color={FOUL_POLE_COLOR}
            roughness={0.4}
            metalness={0.2}
          />
        </mesh>
      </group>

      {/* Right-field Foul Pole (at RF 330 ft corner) */}
      <group position={FOUL_POLE_RIGHT_POS}>
        {/* Main Pole */}
        <mesh position={[0, FOUL_POLE_HEIGHT / 2, 0]}>
          <cylinderGeometry
            args={[FOUL_POLE_RADIUS, FOUL_POLE_RADIUS, FOUL_POLE_HEIGHT, 16]}
          />
          <meshStandardMaterial
            color={FOUL_POLE_COLOR}
            roughness={0.4}
            metalness={0.2}
          />
        </mesh>

        {/* Fair-territory Screen Wing */}
        <mesh position={rightWingOffset} rotation={rightWingRotation}>
          <boxGeometry
            args={[
              FOUL_POLE_WING_THICKNESS,
              FOUL_POLE_WING_HEIGHT,
              FOUL_POLE_WING_WIDTH,
            ]}
          />
          <meshStandardMaterial
            color={FOUL_POLE_COLOR}
            roughness={0.4}
            metalness={0.2}
          />
        </mesh>
      </group>
    </group>
  );
}

export default FoulPoles;
