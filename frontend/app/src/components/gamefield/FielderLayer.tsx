import React from 'react';
import * as THREE from 'three';

import { FIELDERS } from '../../services/fielders';

/**
 * Static defensive alignment and baseline reach rings.
 *
 * Positions are authored in Statcast feet (+y toward center field). The scene
 * uses (x, y, -depth), so a fielder at (x, y) stands at (x, 0, -y). The rings
 * are display-only; the authoritative out/hit classification uses the same
 * FIELDERS config in the mock and backend.
 */
export const FielderLayer = React.memo(function FielderLayer() {
  return (
    <group>
      {FIELDERS.map((fielder) => (
        <group key={fielder.id} position={[fielder.x, 0, -fielder.y]}>
          <mesh position={[0, 2.6, 0]} castShadow={false}>
            <cylinderGeometry args={[0.8, 0.95, 5.2, 10]} />
            <meshStandardMaterial color="#1E3A8A" roughness={0.7} />
          </mesh>
          <mesh position={[0, 5.55, 0]} castShadow={false}>
            <sphereGeometry args={[0.55, 12, 12]} />
            <meshStandardMaterial color="#E2E8F0" roughness={0.6} />
          </mesh>
          <mesh
            position={[0, 0.035, 0]}
            rotation={[-Math.PI / 2, 0, 0]}
            renderOrder={1}
          >
            <ringGeometry args={[fielder.radius - 0.6, fielder.radius, 48]} />
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
    </group>
  );
});
