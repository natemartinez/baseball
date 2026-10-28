import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { Sphere, Trail } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';

import { pitchPointAt, type PitchPath } from './pitchPath';

interface PitchVisualizerProps {
  pitchId: string;
  release: [number, number, number];
  plate: [number, number, number];
  pfx: [number, number];
  flightTime: number;
  onComplete: () => void;
}

/**
 * One-shot data-driven pitch: release ghost, white ball, and red trail.
 * `pfx` is the total break in feet from the virtual aim point; the path is a
 * quadratic break that ends exactly at `plate`. The path math is shared with
 * the Rapier batting ball via `pitchPath.ts`.
 */
export function PitchVisualizer({
  pitchId,
  release,
  plate,
  pfx,
  flightTime,
  onComplete,
}: PitchVisualizerProps) {
  const ballRef = useRef<THREE.Mesh>(null);
  const elapsedRef = useRef(0);
  const completedRef = useRef(false);
  const releaseVec = useMemo(() => new THREE.Vector3(...release), [release]);
  const path = useMemo<PitchPath>(
    () => ({ release, plate, pfx, flightTime }),
    [release, plate, pfx, flightTime],
  );

  useEffect(() => {
    elapsedRef.current = 0;
    completedRef.current = false;
  }, [pitchId]);

  useFrame((_state, delta) => {
    const ball = ballRef.current;
    if (!ball || completedRef.current) return;

    const duration = Math.max(flightTime, 0.01);
    elapsedRef.current = Math.min(elapsedRef.current + delta, duration);
    const point = pitchPointAt(elapsedRef.current, path);
    ball.position.set(point.x, point.y, point.z);

    if (elapsedRef.current >= duration) {
      completedRef.current = true;
      onComplete();
    }
  });

  return (
    <>
      <Sphere args={[0.2, 16, 16]} position={releaseVec}>
        <meshBasicMaterial color="#00f0ff" transparent opacity={0.8} />
      </Sphere>

      <Trail width={0.2} length={20} color="#ff0044" attenuation={(t) => t * t}>
        <Sphere ref={ballRef} args={[0.12, 16, 16]} position={releaseVec}>
          <meshStandardMaterial color="#ffffff" roughness={0.4} />
        </Sphere>
      </Trail>
    </>
  );
}
