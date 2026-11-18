import { useEffect, useMemo, useRef } from 'react';
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
import { FoulPoles } from './FoulPoles';
import { PitchVisualizer } from './PitchVisualizer';
import { WallDistanceMarkers } from './WallDistanceMarkers';
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
  createOutfieldWallCapGeometry,
  createOutfieldWallGeometry,
  dirtSkirtShape,
  homePlateCircleShape,
  homePlateShape,
  infieldGrassShape,
  warningTrackShape,
} from './fieldGeometry';

export const BACKGROUND_COLOR = '#0A0F15';
export const GRASS_COLOR = '#2d6a3f';
export const DIRT_COLOR = '#8e5836';
export const BASE_COLOR = '#f8f9fa';

export const WALL_COLOR = '#12212C';
export const WALL_TRIM_COLOR = '#1F3546';
export const FOUL_POLE_GOLD = '#FFD700';

const NOOP = () => { };

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

  const [outfieldWallGeometry, outfieldWallCapGeometry] = useMemo(() => {
    const wall = createOutfieldWallGeometry();
    const cap = createOutfieldWallCapGeometry();
    return [wall, cap];
  }, []);

  useEffect(() => {
    return () => {
      outfieldWallGeometry.dispose();
      outfieldWallCapGeometry.dispose();
    };
  }, [outfieldWallGeometry, outfieldWallCapGeometry]);

  return (
    <>
      <GameCameraDirector mode={cameraMode} activeBattedBall={activeBattedBall} />
      <color attach="background" args={[BACKGROUND_COLOR]} />

      <ambientLight intensity={0.7} />
      <directionalLight position={[30, 60, 20]} intensity={1.2} castShadow={false} />

      {/* Outfield turf */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -300]}>
        <planeGeometry args={[800, 800]} />
        <meshStandardMaterial color={GRASS_COLOR} roughness={0.9} metalness={0.1} />
      </mesh>

      {/* Outfield warning track dirt */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]}>
        <shapeGeometry args={[warningTrackShape]} />
        <meshStandardMaterial
          color={DIRT_COLOR}
          roughness={0.95}
          polygonOffset
          polygonOffsetFactor={-1}
          polygonOffsetUnits={-1}
        />
      </mesh>

      {/* Infield dirt skirt */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.020, 0]}>
        <shapeGeometry args={[dirtSkirtShape]} />
        <meshStandardMaterial
          color={DIRT_COLOR}
          roughness={0.95}
          polygonOffset
          polygonOffsetFactor={-1}
          polygonOffsetUnits={-1}
        />
      </mesh>

      {/* Home plate sand circle (holds home plate & batter's boxes) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={HOME_PLATE_CIRCLE_POS}>
        <circleGeometry args={[HOME_PLATE_CIRCLE_RADIUS, 64]} />
        <meshStandardMaterial
          color={DIRT_COLOR}
          roughness={0.95}
          polygonOffset
          polygonOffsetFactor={-1}
          polygonOffsetUnits={-1}
        />
      </mesh>

      {/* Infield grass diamond (mound cutout & home plate cutout come from the shape) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.040, 0]}>
        <shapeGeometry args={[infieldGrassShape]} />
        <meshStandardMaterial
          color={GRASS_COLOR}
          roughness={0.9}
          polygonOffset
          polygonOffsetFactor={-2}
          polygonOffsetUnits={-2}
        />
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
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.070, 0]}>
        <shapeGeometry args={[homePlateShape]} />
        <meshStandardMaterial
          color={BASE_COLOR}
          roughness={0.5}
          polygonOffset
          polygonOffsetFactor={-4}
          polygonOffsetUnits={-4}
        />
      </mesh>

      {/* Left Batter's Box */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={BATTERS_BOX_LEFT_POS}>
        <shapeGeometry args={[battersBoxShape]} />
        <meshStandardMaterial
          color="#f8f9fa"
          roughness={0.5}
          polygonOffset
          polygonOffsetFactor={-3}
          polygonOffsetUnits={-3}
        />
      </mesh>

      {/* Right Batter's Box */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={BATTERS_BOX_RIGHT_POS}>
        <shapeGeometry args={[battersBoxShape]} />
        <meshStandardMaterial
          color="#f8f9fa"
          roughness={0.5}
          polygonOffset
          polygonOffsetFactor={-3}
          polygonOffsetUnits={-3}
        />
      </mesh>

      {/* Left-field foul line */}
      <mesh position={FOUL_LINE_LEFT_POS} rotation={FOUL_LINE_LEFT_ROTATION}>
        <boxGeometry args={[0.35, 0.01, FOUL_LINE_LENGTH]} />
        <meshStandardMaterial
          color={BASE_COLOR}
          roughness={0.5}
          polygonOffset
          polygonOffsetFactor={-3}
          polygonOffsetUnits={-3}
        />
      </mesh>

      {/* Right-field foul line */}
      <mesh position={FOUL_LINE_RIGHT_POS} rotation={FOUL_LINE_RIGHT_ROTATION}>
        <boxGeometry args={[0.35, 0.01, FOUL_LINE_LENGTH]} />
        <meshStandardMaterial
          color={BASE_COLOR}
          roughness={0.5}
          polygonOffset
          polygonOffsetFactor={-3}
          polygonOffsetUnits={-3}
        />
      </mesh>

      {/* Outfield home run fence wall */}
      <mesh geometry={outfieldWallGeometry}>
        <meshStandardMaterial color={WALL_COLOR} roughness={0.8} metalness={0.1} />
      </mesh>
      <mesh geometry={outfieldWallCapGeometry}>
        <meshStandardMaterial color={FOUL_POLE_GOLD} roughness={0.4} metalness={0.3} />
      </mesh>

      {/* Outfield distance markers (330, 365, 400) mounted on wall face */}
      <WallDistanceMarkers />

      {/* Outfield foul poles with fair-territory screen wings */}
      <FoulPoles />

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
