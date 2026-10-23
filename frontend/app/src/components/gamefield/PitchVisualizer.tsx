import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { Sphere, Trail } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';

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
 * quadratic break that ends exactly at `plate`.
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

  useEffect(() => {
    elapsedRef.current = 0;
    completedRef.current = false;
  }, [pitchId]);

  useFrame((_state, delta) => {
    const ball = ballRef.current;
    if (!ball || completedRef.current) return;

    const duration = Math.max(flightTime, 0.01);
    elapsedRef.current = Math.min(elapsedRef.current + delta, duration);
    const normalizedT = elapsedRef.current / duration;
    const timeSeconds = elapsedRef.current;

    // Horizontal: aim at the pre-break target, then add the quadratic break.
    const targetX = plate[0] - pfx[0];
    const horizontalX =
      THREE.MathUtils.lerp(release[0], targetX, normalizedT) +
      pfx[0] * normalizedT * normalizedT;

    // Vertical: IVB is measured relative to a gravity-only baseline. The
    // spinless ball ends at (plate.y - IVB); the IVB lift closes that gap.
    const baselineY = plate[1] - pfx[1];
    const gravity = 32.174; // ft/s²
    const initialVy =
      (baselineY - release[1] + 0.5 * gravity * duration * duration) / duration;
    const gravityY =
      release[1] + initialVy * timeSeconds - 0.5 * gravity * timeSeconds * timeSeconds;
    const verticalY = gravityY + pfx[1] * normalizedT * normalizedT;

    const depthZ = THREE.MathUtils.lerp(release[2], plate[2], normalizedT);

    ball.position.set(horizontalX, verticalY, depthZ);

    if (normalizedT >= 1) {
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
