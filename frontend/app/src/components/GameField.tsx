import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Canvas } from '@react-three/fiber';
import { PerspectiveCamera } from '@react-three/drei';

import { FieldScene } from './gamefield/FieldScene';
import { FieldScrims } from './gamefield/FieldScrims';
import { PITCH_SHOT } from './gamefield/cameraShots';
import type { GameFieldProps } from './gamefield/types';
import { Colors } from '../theme/colors';

export type { GameFieldProps } from './gamefield/types';

/**
 * Procedural 3D ballpark rendered with React Three Fiber.
 *
 * The SVG figures, crowd, and stands were intentionally removed. The scene is
 * pure Three.js primitives with no textures; the dark scrims remain as a
 * screen-space overlay so the HUD stays legible.
 */
export const GameField = React.memo(function GameField({
  onPlateProjected,
  activePitch,
  onPitchComplete,
  activeBattedBall,
  onBattedBallComplete,
  cameraMode,
  controlMode,
  pitchPhase,
  battingInputEnabled,
  battingChargeRef,
  onBattingContact,
  onBattingPitchArrival,
}: GameFieldProps) {
  const mode = cameraMode ?? 'PITCH';
  const isBatting = controlMode === 'BATTING';
  return (
    <View accessible={false} style={styles.root}>
      <Canvas
        style={styles.canvas}
        gl={{ antialias: true, powerPreference: 'high-performance' }}
      >
        <PerspectiveCamera
          makeDefault
          position={PITCH_SHOT.position}
          fov={PITCH_SHOT.fov}
        />
        <FieldScene
          onPlateProjected={onPlateProjected}
          activePitch={activePitch}
          onPitchComplete={onPitchComplete}
          activeBattedBall={activeBattedBall}
          onBattedBallComplete={onBattedBallComplete}
          cameraMode={mode}
          controlMode={controlMode}
          pitchPhase={pitchPhase}
          battingInputEnabled={battingInputEnabled}
          battingChargeRef={battingChargeRef}
          onBattingContact={onBattingContact}
          onBattingPitchArrival={onBattingPitchArrival}
        />
      </Canvas>
      <FieldScrims birdseye={mode === 'BIRDSEYE'} batting={isBatting} />
    </View>
  );
});

const styles = StyleSheet.create({
  root: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    overflow: 'hidden',
    backgroundColor: Colors.bgDeep,
    pointerEvents: 'none',
  },
  canvas: {
    flex: 1,
  },
});
