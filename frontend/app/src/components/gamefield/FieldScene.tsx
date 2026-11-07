import { useRef } from 'react';
import type { MutableRefObject } from 'react';
import * as THREE from 'three';

import type { ActiveBattedBallData, ActivePitchData } from './types';
import {
  GameCameraDirector,
  PlateProjector,
  type GameCameraMode,
  type ProjectedPlatePosition,
} from '../camera';
import type { SwingContactReport } from '../../types/api';
import type { ControlMode, PitchPhase } from '../../store/gameStore';
import { BattedBallVisualizer } from './BattedBallVisualizer';
import { BattingLayer } from './BattingLayer';
import { FielderLayer } from './FielderLayer';
import { PitchVisualizer } from './PitchVisualizer';
import {
  BATTERS_BOX_LEFT_POS,
  BATTERS_BOX_RIGHT_POS,
  BASE_1B_POS,
  BASE_2B_POS,
  BASE_3B_POS,
  FOUL_LINE_LENGTH,
  FOUL_LINE_LEFT_POS,
  FOUL_LINE_LEFT_ROTATION,
  FOUL_LINE_RIGHT_POS,
  FOUL_LINE_RIGHT_ROTATION,
  HOME_PLATE_CIRCLE_POS,
  HOME_PLATE_CIRCLE_RADIUS,
  MOUND_POS,
  RUBBER_POS,
  battersBoxShape,
  dirtSkirtShape,
  homePlateCircleShape,
  homePlateShape,
  infieldGrassShape,
} from './fieldGeometry';

const BACKGROUND_COLOR = '#0A0F15';
const GRASS_COLOR = '#2d6a3f';
const DIRT_COLOR = '#8e5836';
const BASE_COLOR = '#f8f9fa';

const NOOP = () => {};

export function FieldScene({
  onPlateProjected,
  activePitch,
  onPitchComplete,
  activeBattedBall,
  onBattedBallComplete,
  cameraMode = 'PITCH',
  controlMode = 'PITCHING',
  pitchPhase = 'IDLE',
  battingInputEnabled = false,
  battingChargeRef,
  onBattingContact,
  onBattingPitchArrival,
}: {
  onPlateProjected?: (p: ProjectedPlatePosition) => void;
  activePitch?: ActivePitchData | null;
  onPitchComplete?: () => void;
  activeBattedBall?: ActiveBattedBallData | null;
  onBattedBallComplete?: () => void;
  cameraMode?: GameCameraMode;
  controlMode?: ControlMode;
  pitchPhase?: PitchPhase;
  battingInputEnabled?: boolean;
  battingChargeRef?: MutableRefObject<number>;
  onBattingContact?: (contact: SwingContactReport) => void;
  onBattingPitchArrival?: (swingAttempted: boolean) => void;
}) {
  const fallbackChargeRef = useRef(0);
  const chargeRef = battingChargeRef ?? fallbackChargeRef;
  const isBatting = controlMode === 'BATTING';

  return (
    <>
      <GameCameraDirector mode={cameraMode} />
      <color attach="background" args={[BACKGROUND_COLOR]} />

      <ambientLight intensity={0.7} />
      <directionalLight position={[30, 60, 20]} intensity={1.2} castShadow={false} />

      {/* Outfield turf */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -300]}>
        <planeGeometry args={[800, 800]} />
        <meshStandardMaterial color={GRASS_COLOR} roughness={0.9} metalness={0.1} />
      </mesh>

      {/* Infield dirt skirt */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <shapeGeometry args={[dirtSkirtShape]} />
        <meshStandardMaterial color={DIRT_COLOR} roughness={0.95} />
      </mesh>

      {/* Home plate sand circle (holds home plate & batter's boxes) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={HOME_PLATE_CIRCLE_POS}>
        <circleGeometry args={[HOME_PLATE_CIRCLE_RADIUS, 64]} />
        <meshStandardMaterial color={DIRT_COLOR} roughness={0.95} />
      </mesh>

      {/* Infield grass diamond (mound cutout & home plate cutout come from the shape) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.010, 0]}>
        <shapeGeometry args={[infieldGrassShape]} />
        <meshStandardMaterial color={GRASS_COLOR} roughness={0.9} />
      </mesh>

      {/* Pitcher's mound */}
      <mesh position={MOUND_POS}>
        <cylinderGeometry args={[8.5, 9.0, 0.83, 32]} />
        <meshStandardMaterial color={DIRT_COLOR} roughness={0.95} />
      </mesh>

      {/* Pitching rubber */}
      <mesh position={RUBBER_POS}>
        <boxGeometry args={[2.0, 0.1, 0.5]} />
        <meshStandardMaterial color={BASE_COLOR} roughness={0.5} />
      </mesh>

      {/* 1st base */}
      <mesh position={BASE_1B_POS}>
        <boxGeometry args={[1.25, 0.2, 1.25]} />
        <meshStandardMaterial color={BASE_COLOR} roughness={0.5} />
      </mesh>

      {/* 2nd base */}
      <mesh position={BASE_2B_POS}>
        <boxGeometry args={[1.25, 0.2, 1.25]} />
        <meshStandardMaterial color={BASE_COLOR} roughness={0.5} />
      </mesh>

      {/* 3rd base */}
      <mesh position={BASE_3B_POS}>
        <boxGeometry args={[1.25, 0.2, 1.25]} />
        <meshStandardMaterial color={BASE_COLOR} roughness={0.5} />
      </mesh>

      {/* Home plate */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]}>
        <shapeGeometry args={[homePlateShape]} />
        <meshStandardMaterial color={BASE_COLOR} roughness={0.5} />
      </mesh>

      {/* Left Batter's Box */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={BATTERS_BOX_LEFT_POS}>
        <shapeGeometry args={[battersBoxShape]} />
        <meshStandardMaterial color="#f8f9fa" roughness={0.5} />
      </mesh>

      {/* Right Batter's Box */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={BATTERS_BOX_RIGHT_POS}>
        <shapeGeometry args={[battersBoxShape]} />
        <meshStandardMaterial color="#f8f9fa" roughness={0.5} />
      </mesh>

      {/* Left-field foul line */}
      <mesh position={FOUL_LINE_LEFT_POS} rotation={FOUL_LINE_LEFT_ROTATION}>
        <boxGeometry args={[0.35, 0.01, FOUL_LINE_LENGTH]} />
        <meshStandardMaterial color={BASE_COLOR} roughness={0.5} />
      </mesh>

      {/* Right-field foul line */}
      <mesh position={FOUL_LINE_RIGHT_POS} rotation={FOUL_LINE_RIGHT_ROTATION}>
        <boxGeometry args={[0.35, 0.01, FOUL_LINE_LENGTH]} />
        <meshStandardMaterial color={BASE_COLOR} roughness={0.5} />
      </mesh>

      <FielderLayer />

      {isBatting ? (
        <BattingLayer
          activePitch={activePitch ?? null}
          pitchPhase={pitchPhase}
          inputEnabled={battingInputEnabled}
          chargeRef={chargeRef}
          onContact={onBattingContact ?? NOOP}
          onPitchArrival={onBattingPitchArrival ?? NOOP}
        />
      ) : (
        activePitch && (
          <PitchVisualizer
            key={activePitch.id}
            pitchId={activePitch.id}
            release={activePitch.release}
            plate={activePitch.plate}
            pfx={activePitch.pfx}
            flightTime={activePitch.flightTime}
            onComplete={onPitchComplete ?? NOOP}
          />
        )
      )}

      {activeBattedBall && (
        <BattedBallVisualizer
          key={activeBattedBall.id}
          data={activeBattedBall}
          onComplete={onBattedBallComplete ?? NOOP}
        />
      )}

      {cameraMode === 'PITCH' && (
        <PlateProjector onProject={onPlateProjected} />
      )}
    </>
  );
}
