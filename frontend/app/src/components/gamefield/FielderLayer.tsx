import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

import { FIELDERS, type Fielder } from '../../services/fielders';
import type { ActiveBattedBallData } from './types';
import {
  computeAllFielderPositions,
  statcastToScene,
  type FielderRenderState,
} from './fielderKinematics';
import { CatchIndicator } from './CatchIndicator';
import { useGameStore } from '../../store/gameStore';

export const DEFAULT_SHOW_RESPONSIBILITY_RINGS = false;

export const FIELDER_MODEL_SCALE = 0.72;

export const FIELDER_MESH_DIMENSIONS = {
  torso: {
    radiusTop: 0.52,
    radiusBottom: 0.62,
    height: 4.8,
    radialSegments: 10,
    position: [0, 2.4, 0] as [number, number, number],
  },
  head: {
    radius: 0.42,
    widthSegments: 12,
    heightSegments: 12,
    position: [0, 5.18, 0] as [number, number, number],
  },
  visor: {
    size: [0.48, 0.07, 0.34] as [number, number, number],
    position: [0, 5.28, 0.40] as [number, number, number],
    rotation: [0.15, 0, 0] as [number, number, number],
  },
  glove: {
    radius: 0.26,
    widthSegments: 8,
    heightSegments: 8,
    position: [0.58, 2.75, 0.35] as [number, number, number],
  },
} as const;

export function shouldRenderResponsibilityRing(
  showResponsibilityRings: boolean = DEFAULT_SHOW_RESPONSIBILITY_RINGS,
): boolean {
  return Boolean(showResponsibilityRings);
}

export interface FielderLayerProps {
  activeBattedBall?: ActiveBattedBallData | null;
  showResponsibilityRings?: boolean;
}

/**
 * Dynamic defensive alignment, pursuit sprint animation, and catch indicators.
 *
 * Positions are authored in Statcast feet (+y toward center field). The scene
 * uses (x, y, -depth), so a fielder at (x, y) stands at (x, 0, -y).
 * During active batted ball trajectories, fielders sprint along Statcast pursuit paths
 * and display catch indicators upon glove arrival.
 */
export const FielderLayer = React.memo(function FielderLayer({
  activeBattedBall,
  showResponsibilityRings = DEFAULT_SHOW_RESPONSIBILITY_RINGS,
}: FielderLayerProps = {}) {
  const elapsedRef = useRef(0);
  const activeBallIdRef = useRef<string | null>(null);
  const [showCatch, setShowCatch] = useState(false);

  // Map of Three.js group refs for each fielder
  const groupRefs = useRef<Map<string, THREE.Group>>(new Map());

  // Reset animation timer and catch indicator when active ball changes
  useEffect(() => {
    if (activeBattedBall?.id !== activeBallIdRef.current) {
      activeBallIdRef.current = activeBattedBall?.id ?? null;
      elapsedRef.current = 0;
      setShowCatch(false);
    }
  }, [activeBattedBall?.id]);

  useFrame((_state, delta) => {
    const isPaused = useGameStore.getState().isBattedBallPaused;

    if (activeBattedBall && !isPaused) {
      elapsedRef.current += delta;
      const elapsed = elapsedRef.current;
      const hangTime = Math.max(activeBattedBall.hangTime, 0.05);

      // Trigger catch indicator upon fielder arrival on fielded plays
      if (elapsed >= hangTime && activeBattedBall.fielded) {
        if (!showCatch) {
          setShowCatch(true);
        }
      }

      // Compute kinematic positions for all 8 fielders
      const states = computeAllFielderPositions({
        activeFielderId: activeBattedBall.fielderId,
        activeStartStatcast: activeBattedBall.fielderStart,
        activeTargetStatcast: activeBattedBall.interceptPoint,
        elapsedTime: elapsed,
        totalDuration: hangTime,
      });

      for (const fielder of FIELDERS) {
        const group = groupRefs.current.get(fielder.id);
        const state = states.get(fielder.id);
        if (group && state) {
          group.position.set(state.scenePos[0], state.scenePos[1], state.scenePos[2]);
          group.rotation.y = state.headingAngle;
        }
      }
    } else if (!activeBattedBall) {
      // Smoothly ease fielders back to baseline stations
      if (showCatch) {
        setShowCatch(false);
      }
      const lerpSpeed = Math.min(1.0, delta * 3.5);
      for (const fielder of FIELDERS) {
        const group = groupRefs.current.get(fielder.id);
        if (group) {
          const baselinePos = new THREE.Vector3(fielder.x, 0, -fielder.y);
          group.position.lerp(baselinePos, lerpSpeed);
          group.rotation.y = THREE.MathUtils.lerp(group.rotation.y, 0, lerpSpeed);
        }
      }
    }
  });

  // Calculate catch indicator scene position
  const catchPos: [number, number, number] | null =
    showCatch && activeBattedBall?.interceptPoint
      ? statcastToScene(
          activeBattedBall.interceptPoint[0],
          activeBattedBall.interceptPoint[1],
          0.0,
        )
      : null;

  return (
    <group>
      {FIELDERS.map((fielder) => (
        <group
          key={fielder.id}
          ref={(el) => {
            if (el) {
              groupRefs.current.set(fielder.id, el);
            } else {
              groupRefs.current.delete(fielder.id);
            }
          }}
          position={[fielder.x, 0, -fielder.y]}
        >
          <group scale={FIELDER_MODEL_SCALE}>
            {/* Fielder body torso */}
            <mesh position={FIELDER_MESH_DIMENSIONS.torso.position} castShadow={false}>
              <cylinderGeometry
                args={[
                  FIELDER_MESH_DIMENSIONS.torso.radiusTop,
                  FIELDER_MESH_DIMENSIONS.torso.radiusBottom,
                  FIELDER_MESH_DIMENSIONS.torso.height,
                  FIELDER_MESH_DIMENSIONS.torso.radialSegments,
                ]}
              />
              <meshStandardMaterial color="#1E3A8A" roughness={0.7} />
            </mesh>

            {/* Fielder head */}
            <mesh position={FIELDER_MESH_DIMENSIONS.head.position} castShadow={false}>
              <sphereGeometry
                args={[
                  FIELDER_MESH_DIMENSIONS.head.radius,
                  FIELDER_MESH_DIMENSIONS.head.widthSegments,
                  FIELDER_MESH_DIMENSIONS.head.heightSegments,
                ]}
              />
              <meshStandardMaterial color="#E2E8F0" roughness={0.6} />
            </mesh>

            {/* Cap visor pointing forward in local +Z */}
            <mesh
              position={FIELDER_MESH_DIMENSIONS.visor.position}
              rotation={FIELDER_MESH_DIMENSIONS.visor.rotation}
              castShadow={false}
            >
              <boxGeometry args={[...FIELDER_MESH_DIMENSIONS.visor.size]} />
              <meshStandardMaterial color="#1E3A8A" roughness={0.5} />
            </mesh>

            {/* Glove on left arm pointing forward */}
            <mesh position={FIELDER_MESH_DIMENSIONS.glove.position} castShadow={false}>
              <sphereGeometry
                args={[
                  FIELDER_MESH_DIMENSIONS.glove.radius,
                  FIELDER_MESH_DIMENSIONS.glove.widthSegments,
                  FIELDER_MESH_DIMENSIONS.glove.heightSegments,
                ]}
              />
              <meshStandardMaterial color="#92400E" roughness={0.8} />
            </mesh>
          </group>

          {/* Opt-in static reach circle on grass */}
          {shouldRenderResponsibilityRing(showResponsibilityRings) && (
            <mesh
              position={[0, 0.08, 0]}
              rotation={[-Math.PI / 2, 0, 0]}
              renderOrder={1}
            >
              <ringGeometry args={[fielder.responsibility_radius - 0.6, fielder.responsibility_radius, 48]} />
              <meshBasicMaterial
                color="#67E8F9"
                transparent
                opacity={0.12}
                depthWrite={false}
                side={THREE.DoubleSide}
              />
            </mesh>
          )}
        </group>
      ))}

      {/* Dynamic catch indicator at arrival point */}
      {catchPos && (
        <CatchIndicator
          position={catchPos}
          fieldingType={activeBattedBall?.fieldingType}
        />
      )}
    </group>
  );
});
