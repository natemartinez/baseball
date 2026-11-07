import type { MutableRefObject } from 'react';
import type {
  BattedBallSample,
  PlayerSummary,
  SwingContactReport,
} from '../../types/api';
import type { ControlMode, PitchPhase } from '../../store/gameStore';
import type { GameCameraMode, ProjectedPlatePosition } from '../camera/types';

export type { GameCameraMode, ProjectedPlatePosition };

export interface ActivePitchData {
  id: string;
  release: [number, number, number];
  plate: [number, number, number];
  /** Scene-space total break in feet: [hand-resolved horizontal, induced vertical]. */
  pfx: [number, number];
  flightTime: number;
}

export interface ActiveBattedBallData {
  id: string;
  hangTime: number;
  samples: BattedBallSample[];
}

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
