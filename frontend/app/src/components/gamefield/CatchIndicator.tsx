import React, { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

import { getCatchVisualProfile } from './fielderKinematics';

export const CATCH_INDICATOR_DIMENSIONS = {
  ringInner: 2.0,
  ringOuter: 2.6,
  pulseInner: 2.6,
  pulseOuter: 3.2,
  beaconRadius: 0.4,
  beaconY: 1.25,
} as const;

export interface CatchIndicatorProps {
  position: [number, number, number];
  fieldingType?: string | null;
}

/**
 * Animated 3D catch ring and accent marker rendered at the intercept point upon glove arrival.
 */
export const CatchIndicator = React.memo(function CatchIndicator({
  position,
  fieldingType,
}: CatchIndicatorProps) {
  const profile = getCatchVisualProfile(fieldingType);
  const pulseRef = useRef<THREE.Mesh>(null);
  const markerRef = useRef<THREE.Mesh>(null);

  useFrame((_state, delta) => {
    if (!profile.showRing) return;
    if (pulseRef.current) {
      const scale = 1.0 + Math.sin(Date.now() * 0.008) * 0.12;
      pulseRef.current.scale.set(scale, scale, 1.0);
    }
    if (markerRef.current) {
      markerRef.current.rotation.y += delta * 1.5;
    }
  });

  if (!profile.showRing) return null;

  return (
    <group position={position}>
      {/* Ground catch ring */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.08, 0]}>
        <ringGeometry
          args={[
            CATCH_INDICATOR_DIMENSIONS.ringInner,
            CATCH_INDICATOR_DIMENSIONS.ringOuter,
            32,
          ]}
        />
        <meshBasicMaterial
          color={profile.ringColor}
          transparent
          opacity={0.85}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>

      {/* Expanding pulse ripple */}
      <mesh ref={pulseRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.085, 0]}>
        <ringGeometry
          args={[
            CATCH_INDICATOR_DIMENSIONS.pulseInner,
            CATCH_INDICATOR_DIMENSIONS.pulseOuter,
            32,
          ]}
        />
        <meshBasicMaterial
          color={profile.ringColor}
          transparent
          opacity={0.35}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>

      {/* Rotating catch diamond beacon */}
      <mesh ref={markerRef} position={[0, CATCH_INDICATOR_DIMENSIONS.beaconY, 0]}>
        <octahedronGeometry args={[CATCH_INDICATOR_DIMENSIONS.beaconRadius, 0]} />
        <meshStandardMaterial
          color={profile.ringColor}
          emissive={profile.ringColor}
          emissiveIntensity={0.6}
          roughness={0.2}
          metalness={0.3}
        />
      </mesh>
    </group>
  );
});

