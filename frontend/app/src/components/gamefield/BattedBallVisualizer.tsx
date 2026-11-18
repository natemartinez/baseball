import React, { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

import { DEFAULT_BATTED_BALL_RADIUS, type ActiveBattedBallData } from './types';
import { resolveTrajectoryInterpolation } from '../camera/cameraShots';
import { useGameStore } from '../../store/gameStore';

const TRACE_COLOR = '#ffb347';
const BALL_COLOR = '#ffd166';
const LANDING_RING_INNER_RADIUS = 4.5;
const LANDING_RING_OUTER_RADIUS = 6;
const LANDING_RING_Y = 0.15;
const FLOOR_SURFACE_Y = 0.04;

export { DEFAULT_BATTED_BALL_RADIUS };

export interface BattedBallVisualizerProps {
  data: ActiveBattedBallData;
  onComplete: () => void;
  ballRadius?: number;
}

/**
 * Ball, static arc, and landing ring for one batted ball.
 *
 * Camera framing lives in `GameCameraDirector`; this component must never
 * touch the camera or two owners will fight over the shot.
 */
export const BattedBallVisualizer = React.memo(function BattedBallVisualizer({
  data,
  onComplete,
  ballRadius = DEFAULT_BATTED_BALL_RADIUS,
}: BattedBallVisualizerProps) {
  const ballRef = useRef<THREE.Mesh>(null);
  const elapsedRef = useRef(0);
  const completedRef = useRef(false);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const points = useMemo(
    () =>
      data.samples.map(
        ([x, y, z]) => new THREE.Vector3(x, z + ballRadius + FLOOR_SURFACE_Y, -y),
      ),
    [data.samples, ballRadius],
  );

  const lineGeometry = useMemo(() => {
    const positions = new Float32Array(points.length * 3);
    points.forEach((point, index) => {
      positions[index * 3] = point.x;
      positions[index * 3 + 1] = point.y;
      positions[index * 3 + 2] = point.z;
    });
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geometry;
  }, [points]);

  const lineObject = useMemo(
    () =>
      new THREE.Line(
        lineGeometry,
        new THREE.LineBasicMaterial({
          color: TRACE_COLOR,
          transparent: true,
          opacity: 0.9,
        }),
      ),
    [lineGeometry],
  );

  useEffect(
    () => () => {
      lineGeometry.dispose();
      (lineObject.material as THREE.Material).dispose();
    },
    [lineGeometry, lineObject],
  );

  useFrame((_state, delta) => {
    const ball = ballRef.current;
    if (!ball || completedRef.current || points.length === 0) return;
    if (useGameStore.getState().isBattedBallPaused) return;

    elapsedRef.current += delta;
    const elapsed = elapsedRef.current;
    const duration = Math.max(data.hangTime, 0.05);

    if (elapsed >= duration) {
      ball.position.copy(points[points.length - 1]);
      completedRef.current = true;
      onCompleteRef.current();
      return;
    }

    const { index, nextIndex, alpha } = resolveTrajectoryInterpolation(
      data.samples,
      elapsed,
      duration,
    );
    ball.position.lerpVectors(points[index], points[nextIndex], alpha);
  });

  if (points.length === 0) return null;

  const landing = points[points.length - 1];

  return (
    <>
      <primitive object={lineObject} />
      <mesh
        ref={ballRef}
        position={[points[0].x, points[0].y, points[0].z]}
      >
        <sphereGeometry args={[ballRadius, 16, 16]} />
        <meshBasicMaterial color={BALL_COLOR} />
      </mesh>
      <mesh
        position={[landing.x, LANDING_RING_Y, landing.z]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <ringGeometry
          args={[
            LANDING_RING_INNER_RADIUS,
            LANDING_RING_OUTER_RADIUS,
            32,
          ]}
        />
        <meshBasicMaterial
          color={TRACE_COLOR}
          transparent
          opacity={0.85}
          side={THREE.DoubleSide}
        />
      </mesh>
    </>
  );
});
