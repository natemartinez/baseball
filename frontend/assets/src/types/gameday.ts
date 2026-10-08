/**
 * MLB Gameday 2D Telemetry & Diagnostics Contract
 * Standardized 2D vertical cross-section at home plate.
 */

export type GamedayZoneCategory = 'HEART' | 'SHADOW' | 'CHASE' | 'WASTE';

export type SituationCategory =
  | 'NEUTRAL'
  | 'AHEAD_IN_COUNT'
  | 'BEHIND_IN_COUNT'
  | 'TWO_OUTS'
  | 'RISP'
  | 'DOUBLE_PLAY'
  | 'BASES_LOADED';

export type CountCategory = 'ALL' | 'AHEAD' | 'BEHIND' | 'FULL' | 'EVEN';

export interface Gameday2DPitchPacket {
  meta: {
    pitchNumber: number;
    pitcherName: string;
    pitcherOvr: number;
    commandRating: number;
    staminaPct: number;
    pitchesThrown: number;
    inning: number;
    isTopInning: boolean;
    count: { balls: number; strikes: number; outs: number };
    runnersOnBase: { first: boolean; second: boolean; third: boolean };
    batterName: string;
    batterId: number;
    situationCategory: SituationCategory;
  };

  strategy: {
    repertoireProbabilities: Record<string, number>; // e.g. { "4-Seam Fastball": 0.35, "Spin Monster Sweeper": 0.45 }
    selectedPitch: string;
    dynamicModifier: number; // Current W_t decay multiplier (e.g. 1.15 for Hot, 0.82 for Cold)
    strategyName: string;
    rationale: string;
  };

  intent: {
    targetX: number; // Statcast feet relative to plate center (-0.708 to +0.708 ft rulebook)
    targetZ: number; // Statcast feet off ground (1.50 to 3.50 ft rulebook)
    intendedZone: GamedayZoneCategory;
    targetSpeedMph: number;
    isManualOverride: boolean;
  };

  execution: {
    realizedX: number; // Statcast feet
    realizedZ: number; // Statcast feet
    realizedSpeedMph: number;
    radialMissInches: number;
    deltaXInches: number;
    deltaZInches: number;
    sigmaXFeet: number;
    sigmaZFeet: number;
    isHeartZoneLeak: boolean;
    hitShadowZoneTarget: boolean;
    realizedZoneCategory: GamedayZoneCategory;
  };

  result: {
    call: 'BALL' | 'CALLED_STRIKE' | 'SWINGING_STRIKE' | 'FOUL' | 'IN_PLAY';
    isStrike: boolean;
    exitVelocityMph?: number;
    launchAngleDeg?: number;
    description: string;
  };
}

export interface CalibrationBaseline {
  commandRating: number;
  expectedShadowAccuracy: number; // Percentage, e.g. 66.2%
  expectedHeartLeaks: number; // Percentage, e.g. 5.1%
  expectedMissRadiusInches: number; // e.g. 3.12"
  expectedAheadOffspeedPct: number; // e.g. 59.8%
}

export interface CalibrationDiagnostics {
  sampleSize: number;
  actualShadowAccuracy: number;
  expectedShadowAccuracy: number;
  actualHeartLeaks: number;
  expectedHeartLeaks: number;
  actualMissRadiusInches: number;
  expectedMissRadiusInches: number;
  actualAheadOffspeedPct: number;
  expectedAheadOffspeedPct: number;
  isLeakingAlert: boolean; // Triggers when actual heart leaks exceed expected by > 2.0%
}

export interface GamedayFilterOptions {
  countFilter: CountCategory;
  situationFilter: string; // 'ALL' | SituationCategory
  batterFilter: string; // 'ALL' | batter name
  pitchTypeFilter: string; // 'ALL' | pitch name
}
