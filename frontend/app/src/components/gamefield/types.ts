import type { PlayerSummary } from '../../types/api';

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

export interface GameFieldProps {
  batter?: PlayerSummary | null;
  pitcher?: PlayerSummary | null;
  onPlateProjected?: (position: ProjectedPlatePosition) => void;
  activePitch?: ActivePitchData | null;
  onPitchComplete?: () => void;
}
