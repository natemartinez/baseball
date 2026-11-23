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

export interface FielderLayerProps {
  activeBattedBall?: ActiveBattedBallData | null;
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
          {/* Fielder body torso */}
          <mesh position={[0, 2.6, 0]} castShadow={false}>
            <cylinderGeometry args={[0.8, 0.95, 5.2, 10]} />
            <meshStandardMaterial color="#1E3A8A" roughness={0.7} />
          </mesh>

          {/* Fielder head */}
          <mesh position={[0, 5.55, 0]} castShadow={false}>
            <sphereGeometry args={[0.55, 12, 12]} />
            <meshStandardMaterial color="#E2E8F0" roughness={0.6} />
          </mesh>

          {/* Cap visor pointing forward in local +Z */}
          <mesh position={[0, 5.65, 0.55]} rotation={[0.15, 0, 0]} castShadow={false}>
            <boxGeometry args={[0.6, 0.08, 0.4]} />
            <meshStandardMaterial color="#1E3A8A" roughness={0.5} />
          </mesh>

          {/* Glove on left arm pointing forward */}
          <mesh position={[0.75, 3.0, 0.4]} castShadow={false}>
            <sphereGeometry args={[0.32, 8, 8]} />
            <meshStandardMaterial color="#92400E" roughness={0.8} />
          </mesh>

          {/* Static reach circle on grass */}
          <mesh
            position={[0, 0.08, 0]}
            rotation={[-Math.PI / 2, 0, 0]}
            renderOrder={1}
          >
            <ringGeometry args={[fielder.responsibility_radius - 0.6, fielder.responsibility_radius, 48]} />
            <meshBasicMaterial
              color="#67E8F9"
              transparent
              opacity={0.18}
              depthWrite={false}
              side={THREE.DoubleSide}
            />
          </mesh>
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
