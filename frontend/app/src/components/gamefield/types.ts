import type { MutableRefObject } from 'react';
import type {
  BattedBallSample,
  PlayerSummary,
  SwingContactReport,
} from '../../types/api';
import type { ControlMode, PitchPhase } from '../../store/gameStore';

export interface ProjectedPlatePosition {
  xRatio: number;
  yRatio: number;
  /** Projected top (front edge) of the plate; use this to place HUD above it. */
  frontRatio: number;
  /** Projected plate width as a fraction of the Canvas width. */
  widthRatio: number;
  /** Projected top/bottom of the 3D strike zone at the plate plane. */
  zoneTopRatio: number;
  zoneBottomRatio: number;
  /** Projected strike-zone width as a fraction of the Canvas width. */
  zoneWidthRatio: number;
}

export interface ActivePitchData {
  id: string;
  release: [number, number, number];
  plate: [number, number, number];
  pfx: [number, number];
  flightTime: number;
}

export interface ActiveBattedBallData {
  id: string;
  hangTime: number;
  samples: BattedBallSample[];
}

export type GameCameraMode = 'PITCH' | 'BIRDSEYE';

export interface BattingLayerProps {
  activePitch: ActivePitchData | null;
  pitchPhase: PitchPhase;
  inputEnabled: boolean;
  chargeRef: MutableRefObject<number>;
  onContact: (contact: SwingContactReport) => void;
  onPitchArrival: (swingAttempted: boolean) => void;
}

export interface GameFieldProps {
  batter?: PlayerSummary | null;
  pitcher?: PlayerSummary | null;
  onPlateProjected?: (position: ProjectedPlatePosition) => void;
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
}
