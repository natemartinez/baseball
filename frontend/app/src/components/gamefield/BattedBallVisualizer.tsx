import React, { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

import type { ActiveBattedBallData } from './types';

const TRACE_COLOR = '#ffb347';
const BALL_COLOR = '#ffd166';
const LANDING_RING_INNER_RADIUS = 4.5;
const LANDING_RING_OUTER_RADIUS = 6;
const LANDING_RING_Y = 0.15;

interface BattedBallVisualizerProps {
  data: ActiveBattedBallData;
  onComplete: () => void;
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
        ([x, y, z]) => new THREE.Vector3(x, z, -y),
      ),
    [data.samples],
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

  const ballRadius = useMemo(() => {
    const maxDepth = data.samples.reduce(
      (furthest, sample) => Math.max(furthest, sample[1]),
      0,
    );
    return THREE.MathUtils.clamp(0.35 + maxDepth * 0.004, 0.5, 2.2);
  }, [data.samples]);

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

    elapsedRef.current += delta;
    const elapsed = elapsedRef.current;

    const duration = Math.max(data.hangTime, 0.05);
    const progress = Math.min(elapsed / duration, 1);
    const lastIndex = points.length - 1;
    const scaled = progress * lastIndex;
    const index = Math.min(Math.floor(scaled), lastIndex);
    const nextIndex = Math.min(index + 1, lastIndex);
    const alpha = scaled - index;
    ball.position.lerpVectors(points[index], points[nextIndex], alpha);

    if (progress >= 1) {
      completedRef.current = true;
      onCompleteRef.current();
    }
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
