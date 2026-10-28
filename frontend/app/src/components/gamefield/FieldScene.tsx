import { useEffect, useRef } from 'react';
import type { MutableRefObject } from 'react';
import * as THREE from 'three';

import type {
  ActiveBattedBallData,
  ActivePitchData,
  GameCameraMode,
  ProjectedPlatePosition,
} from './types';
import type { SwingContactReport } from '../../types/api';
import type { ControlMode, PitchPhase } from '../../store/gameStore';
import { BattedBallVisualizer } from './BattedBallVisualizer';
import { BattingLayer } from './BattingLayer';
import { FielderLayer } from './FielderLayer';
import { GameCameraDirector } from './GameCameraDirector';
import { PitchVisualizer } from './PitchVisualizer';
import { useThree } from './useThree';
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
  HOME_PLATE_DEPTH,
  HOME_PLATE_HALF_WIDTH,
  MOUND_POS,
  RUBBER_POS,
  battersBoxShape,
  dirtSkirtShape,
  homePlateShape,
  infieldGrassShape,
} from './fieldGeometry';

const BACKGROUND_COLOR = '#0A0F15';
const GRASS_COLOR = '#2d6a3f';
const DIRT_COLOR = '#8e5836';
const BASE_COLOR = '#f8f9fa';

const PLATE_Y = 0.015;
const PLATE_WORLD_POSITION = new THREE.Vector3(0, PLATE_Y, 0);
const NOOP = () => {};

/** Strike-zone bounds used by the 2D HUD (Statcast feet). */
const STRIKE_ZONE_HALF_WIDTH = 0.7083;
const STRIKE_ZONE_BOTTOM = 1.5;
const STRIKE_ZONE_TOP = 3.5;

interface PlateProjectorProps {
  onProject?: (position: ProjectedPlatePosition) => void;
}

function PlateProjector({ onProject }: PlateProjectorProps) {
  const camera = useThree((state) => state.camera);
  const size = useThree((state) => state.size);

  useEffect(() => {
    // Canvas reports 0x0 before its first layout pass, which would make the
    // camera aspect NaN and poison the overlay position.
    if (size.width <= 0 || size.height <= 0) return;

    camera.updateMatrixWorld();

    const projectX = (x: number, z: number) => {
      const projected = new THREE.Vector3(x, PLATE_Y, z).project(camera);
      return ((projected.x + 1) / 2) * size.width;
    };

    // The plate's widest silhouette is its near shoulder edge; the front edge
    // is slightly narrower in perspective. Use the wider of the two so the
    // overlay aligns with the visible left/right plate edges.
    const nearWidth =
      projectX(HOME_PLATE_HALF_WIDTH, -HOME_PLATE_HALF_WIDTH) -
      projectX(-HOME_PLATE_HALF_WIDTH, -HOME_PLATE_HALF_WIDTH);
    const farWidth =
      projectX(HOME_PLATE_HALF_WIDTH, -HOME_PLATE_DEPTH) -
      projectX(-HOME_PLATE_HALF_WIDTH, -HOME_PLATE_DEPTH);
    const plateWidth = Math.max(nearWidth, farWidth);

    const projectRatio = (x: number, y: number, z: number) => {
      const projected = new THREE.Vector3(x, y, z).project(camera);
      return {
        xRatio: (projected.x + 1) / 2,
        yRatio: (1 - projected.y) / 2,
      };
    };

    const apex = PLATE_WORLD_POSITION.clone().project(camera);
    const front = new THREE.Vector3(0, PLATE_Y, -HOME_PLATE_DEPTH).project(camera);
    const zoneTop = projectRatio(0, STRIKE_ZONE_TOP, 0);
    const zoneBottom = projectRatio(0, STRIKE_ZONE_BOTTOM, 0);
    const zoneLeft = projectRatio(-STRIKE_ZONE_HALF_WIDTH, 2.5, 0);
    const zoneRight = projectRatio(STRIKE_ZONE_HALF_WIDTH, 2.5, 0);

    onProject?.({
      xRatio: (apex.x + 1) / 2,
      yRatio: (1 - apex.y) / 2,
      frontRatio: (1 - front.y) / 2,
      widthRatio: plateWidth / size.width,
      zoneTopRatio: zoneTop.yRatio,
      zoneBottomRatio: zoneBottom.yRatio,
      zoneWidthRatio: zoneRight.xRatio - zoneLeft.xRatio,
    });
  }, [camera, size.width, size.height, onProject]);

  return null;
}

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

      {/* Infield grass diamond (mound cutout comes from the shape hole) */}
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
