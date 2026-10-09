import { create } from 'zustand';
import type {
  GameState,
  InitialStateResponse,
  PitchDetails,
  TeamLineup,
  TeamRotation,
  ApiErrorResponse,
} from '../types/api';
import { STRIKE_ZONES, BaseballApiError } from '../types/api';
import type {
  Gameday2DPitchPacket,
  GamedayFilterOptions,
  CountCategory,
  SituationCategory,
} from '../types/gameday';
import { GameRepository } from '../services/GameRepository';
import { executeDelivery, classifyGamedayZone } from '../services/gamedayMath';
import { calculateStrategyAndIntent } from '../services/strategyEngine';

function ensureStrategyIntent(game?: GameState | null): GameState | null | undefined {
  if (!game) return game;
  if (!game.strategy_intent) {
    return {
      ...game,
      strategy_intent: calculateStrategyAndIntent(game),
    };
  }
  return game;
}

// ─── UI State ─────────────────────────────────────────────────────────────────

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';
export type DevTab = 'strategy' | 'gameday' | 'calibration' | 'split';

export interface GameUiState {
  // Server / game data
  initialResponse: InitialStateResponse | null;
  gameState: GameState | null;
  pitchFeed: PitchDetails[];
  latestPitch: PitchDetails | null;
  lineups: TeamLineup[];
  rotations: TeamRotation[];

  // Gameday Telemetry & Developer Menu State
  gamedayLog: Gameday2DPitchPacket[];
  selectedPitchPacketIndex: number | null; // null = latest pitch
  customTargetCoords: { x: number; z: number } | null;
  isDevMenuOpen: boolean;
  activeDevTab: DevTab;
  countFilter: CountCategory;
  situationFilter: string;
  batterFilter: string;
  pitchTypeFilter: string;

  // UI interaction state
  selectedPitchIntent: string;
  selectedTargetZone: string;
  isLineupDialogOpen: boolean;
  isMockMode: boolean;
  backendUrl: string;

  // Loading / error
  loadingState: LoadingState;
  isPitching: boolean;
  errorMessage: string | null;
  errorEnvelope: ApiErrorResponse | null;
}

// ─── Actions ──────────────────────────────────────────────────────────────────

export interface GameActions {
  // Lifecycle
  loadInitialState(): Promise<void>;
  startNewGame(): Promise<void>;
  resetGame(): Promise<void>;

  // Gameplay
  throwPitch(): Promise<void>;
  simAtBat(): Promise<void>;
  swapLineup(teamId: number, pos1: number, pos2: number): Promise<void>;
  toggleMockMode(useMock: boolean): Promise<void>;
  setBackendUrl(url: string): Promise<void>;

  // Dev Menu & Gameday Telemetry
  toggleDevMenu(open?: boolean): void;
  setCustomTarget(coords: { x: number; z: number } | null): void;
  setSelectedPitchPacketIndex(index: number | null): void;
  setActiveDevTab(tab: DevTab): void;
  setGamedayFilters(filters: Partial<GamedayFilterOptions>): void;
  clearDebugLog(): void;
  runFastCalibration(commandRating?: number, sampleSize?: number): void;

  // UI mutations
  setSelectedPitchIntent(intent: string): void;
  setSelectedTargetZone(zone: string): void;
  setLineupDialogOpen(open: boolean): void;
  clearError(): void;
}

// ─── Store ────────────────────────────────────────────────────────────────────

const repo = GameRepository.getInstance();

const initialState: GameUiState = {
  initialResponse: null,
  gameState: null,
  pitchFeed: [],
  latestPitch: null,
  lineups: [],
  rotations: [],
  gamedayLog: [],
  selectedPitchPacketIndex: null,
  customTargetCoords: null,
  isDevMenuOpen: false,
  activeDevTab: 'gameday',
  countFilter: 'ALL',
  situationFilter: 'ALL',
  batterFilter: 'ALL',
  pitchTypeFilter: 'ALL',
  selectedPitchIntent: 'Spin Monster Sweeper',
  selectedTargetZone: STRIKE_ZONES.HEART,
  isLineupDialogOpen: false,
  isMockMode: repo.isMockMode,
  backendUrl: repo.getBackendUrl(),
  loadingState: 'idle',
  isPitching: false,
  errorMessage: null,
  errorEnvelope: null,
};

export const useGameStore = create<GameUiState & GameActions>((set, get) => ({
  ...initialState,

  // ─── Lifecycle ─────────────────────────────────────────────────────────────

  async loadInitialState() {
    set({ loadingState: 'loading', errorMessage: null, errorEnvelope: null });
    try {
      const response = await repo.getState();
      const firstPitch = response.game?.current_pitcher?.arsenal?.[0]?.name;
      set((s) => ({
        initialResponse: response,
        gameState: ensureStrategyIntent(response.game) as GameState | null,
        lineups: response.lineups,
        rotations: response.rotations,
        loadingState: 'success',
        pitchFeed: [],
        latestPitch: null,
        gamedayLog: [],
        selectedPitchPacketIndex: null,
        selectedPitchIntent: s.selectedPitchIntent || firstPitch || 'Four-Seam Fastball',
        selectedTargetZone: s.selectedTargetZone || STRIKE_ZONES.HEART,
      }));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({ loadingState: 'error', errorMessage: message, errorEnvelope: envelope });
    }
  },

  async startNewGame() {
    set({ loadingState: 'loading', errorMessage: null, errorEnvelope: null });
    try {
      const state = await repo.startGame(1, 2);
      const firstPitch = state.current_pitcher?.arsenal?.[0]?.name;
      set((s) => ({
        gameState: ensureStrategyIntent(state) as GameState,
        pitchFeed: [],
        latestPitch: null,
        gamedayLog: [],
        selectedPitchPacketIndex: null,
        loadingState: 'success',
        selectedPitchIntent: s.selectedPitchIntent || firstPitch || 'Four-Seam Fastball',
        selectedTargetZone: s.selectedTargetZone || STRIKE_ZONES.HEART,
      }));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({ loadingState: 'error', errorMessage: message, errorEnvelope: envelope });
    }
  },

  async resetGame() {
    set({ isPitching: true, errorMessage: null, errorEnvelope: null });
    try {
      const response = await repo.reset();
      const firstPitch = response.game?.current_pitcher?.arsenal?.[0]?.name;
      set((s) => ({
        initialResponse: response,
        gameState: ensureStrategyIntent(response.game) as GameState | null,
        lineups: response.lineups,
        rotations: response.rotations,
        pitchFeed: [],
        latestPitch: null,
        gamedayLog: [],
        selectedPitchPacketIndex: null,
        customTargetCoords: null,
        isPitching: false,
        selectedPitchIntent: firstPitch || s.selectedPitchIntent || 'Four-Seam Fastball',
        selectedTargetZone: STRIKE_ZONES.HEART,
      }));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({ isPitching: false, errorMessage: message, errorEnvelope: envelope });
    }
  },

  async toggleMockMode(useMock: boolean) {
    repo.setMockMode(useMock);
    set({ isMockMode: useMock });
    await get().loadInitialState();
  },

  // ─── Gameplay ──────────────────────────────────────────────────────────────

  async throwPitch() {
    const { selectedPitchIntent, selectedTargetZone, customTargetCoords, isPitching } = get();
    if (isPitching) return;
    set({ isPitching: true, errorMessage: null, errorEnvelope: null });
    try {
      const result = await repo.pitch(
        selectedPitchIntent || undefined,
        selectedTargetZone || undefined,
        customTargetCoords || undefined,
      );

      const packet = result.pitch_details.gameday_packet;

      set((s) => ({
        gameState: ensureStrategyIntent(result.game_state) as GameState,
        latestPitch: result.pitch_details,
        pitchFeed: [result.pitch_details, ...s.pitchFeed].slice(0, 25),
        gamedayLog: packet ? [packet, ...s.gamedayLog].slice(0, 100) : s.gamedayLog,
        selectedPitchPacketIndex: null, // Reset to latest
        isPitching: false,
      }));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({ isPitching: false, errorMessage: message, errorEnvelope: envelope });
    }
  },

  async simAtBat() {
    const { isPitching } = get();
    if (isPitching) return;
    set({ isPitching: true, errorMessage: null, errorEnvelope: null });
    try {
      const result = await repo.simAtBat();
      const packet = result.pitch_details.gameday_packet;

      set((s) => ({
        gameState: ensureStrategyIntent(result.game_state) as GameState,
        latestPitch: result.pitch_details,
        pitchFeed: [result.pitch_details, ...s.pitchFeed].slice(0, 25),
        gamedayLog: packet ? [packet, ...s.gamedayLog].slice(0, 100) : s.gamedayLog,
        selectedPitchPacketIndex: null,
        isPitching: false,
      }));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({ isPitching: false, errorMessage: message, errorEnvelope: envelope });
    }
  },

  async swapLineup(teamId: number, pos1: number, pos2: number) {
    set({ isPitching: true });
    try {
      await repo.swapLineup(teamId, pos1, pos2);
      set((s) => ({
        isPitching: false,
        lineups: s.lineups.map((tl) => {
          if (tl.team_id !== teamId) return tl;
          const newLineup = [...tl.lineup];
          const i1 = newLineup.findIndex((p) => p.batting_order === pos1);
          const i2 = newLineup.findIndex((p) => p.batting_order === pos2);
          if (i1 >= 0 && i2 >= 0) {
            const tmp = newLineup[i1];
            newLineup[i1] = { ...newLineup[i2], batting_order: newLineup[i1].batting_order };
            newLineup[i2] = { ...tmp, batting_order: newLineup[i2].batting_order };
          }
          return { ...tl, lineup: newLineup };
        }),
      }));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({ isPitching: false, errorMessage: message, errorEnvelope: envelope });
    }
  },

  async setBackendUrl(url: string) {
    repo.setBackendUrl(url);
    repo.setMockMode(false);
    set({ backendUrl: url, isMockMode: false });
    await get().loadInitialState();
  },

  // ─── Dev Menu & Gameday Telemetry ───────────────────────────────────────────

  toggleDevMenu(open?: boolean) {
    set((s) => ({ isDevMenuOpen: open !== undefined ? open : !s.isDevMenuOpen }));
  },

  setCustomTarget(coords: { x: number; z: number } | null) {
    set({ customTargetCoords: coords });
  },

  setSelectedPitchPacketIndex(index: number | null) {
    set({ selectedPitchPacketIndex: index });
  },

  setActiveDevTab(tab: DevTab) {
    set({ activeDevTab: tab });
  },

  setGamedayFilters(filters: Partial<GamedayFilterOptions>) {
    set((s) => ({
      countFilter: filters.countFilter !== undefined ? filters.countFilter : s.countFilter,
      situationFilter: filters.situationFilter !== undefined ? filters.situationFilter : s.situationFilter,
      batterFilter: filters.batterFilter !== undefined ? filters.batterFilter : s.batterFilter,
      pitchTypeFilter: filters.pitchTypeFilter !== undefined ? filters.pitchTypeFilter : s.pitchTypeFilter,
    }));
  },

  clearDebugLog() {
    set({ gamedayLog: [], selectedPitchPacketIndex: null });
  },

  runFastCalibration(commandRating: number = 68, sampleSize: number = 100) {
    const targets = [
      { x: -0.55, z: 3.15 },
      { x: 0.55, z: 3.15 },
      { x: -0.55, z: 1.85 },
      { x: 0.55, z: 1.85 },
      { x: 0.00, z: 2.50 },
      { x: 0.55, z: 2.50 },
      { x: 0.00, z: 1.15 },
      { x: 1.05, z: 2.50 },
    ];

    const newPackets: Gameday2DPitchPacket[] = [];
    const state = get().gameState;
    const pitcherName = state?.current_pitcher.name ?? 'Nolan McLean';
    const batterName = state?.current_batter.name ?? 'Aaron Judge';

    for (let i = 0; i < sampleSize; i++) {
      const target = targets[i % targets.length];
      const intendedCat = classifyGamedayZone(target.x, target.z);
      const execution = executeDelivery(target.x, target.z, commandRating, i, 70);
      const realizedCat = classifyGamedayZone(execution.realizedX, execution.realizedZ);

      const packet: Gameday2DPitchPacket = {
        meta: {
          pitchNumber: i + 1,
          pitcherName,
          pitcherOvr: 88,
          commandRating,
          staminaPct: Math.max(20, 100 - Math.round((i / sampleSize) * 35)),
          pitchesThrown: i + 1,
          inning: Math.floor(i / 15) + 1,
          isTopInning: true,
          count: { balls: i % 4, strikes: (i * 2) % 3, outs: i % 3 },
          runnersOnBase: { first: i % 3 === 0, second: i % 5 === 0, third: i % 7 === 0 },
          batterName,
          batterId: 99,
          situationCategory: i % 4 === 0 ? 'RISP' : i % 3 === 0 ? 'TWO_OUTS' : 'NEUTRAL',
        },
        strategy: {
          repertoireProbabilities: { 'Spin Monster Sweeper': 0.45, 'Four-Seam Fastball': 0.35, 'Power Sinker': 0.15, 'Spike Curveball': 0.05 },
          selectedPitch: i % 2 === 0 ? 'Spin Monster Sweeper' : 'Four-Seam Fastball',
          dynamicModifier: 1.05,
          strategyName: 'CALIBRATION_BENCHMARK_BURST',
          rationale: `Monte Carlo benchmark trial #${i + 1}`,
        },
        intent: {
          targetX: target.x,
          targetZ: target.z,
          intendedZone: intendedCat,
          targetSpeedMph: 94.5,
          isManualOverride: false,
        },
        execution: {
          realizedX: execution.realizedX,
          realizedZ: execution.realizedZ,
          realizedSpeedMph: 94.2,
          radialMissInches: execution.radialMissInches,
          deltaXInches: execution.deltaXInches,
          deltaZInches: execution.deltaZInches,
          sigmaXFeet: execution.sigmaFeet,
          sigmaZFeet: execution.sigmaFeet,
          isHeartZoneLeak: intendedCat !== 'HEART' && realizedCat === 'HEART',
          hitShadowZoneTarget: intendedCat === 'SHADOW' && realizedCat === 'SHADOW',
          realizedZoneCategory: realizedCat,
        },
        result: {
          call: realizedCat === 'HEART' || realizedCat === 'SHADOW' ? 'CALLED_STRIKE' : 'BALL',
          isStrike: realizedCat === 'HEART' || realizedCat === 'SHADOW',
          description: `Fast calibration delivery #${i + 1}`,
        },
      };

      newPackets.push(packet);
    }

    set({ gamedayLog: newPackets, selectedPitchPacketIndex: null });
  },

  // ─── UI mutations ──────────────────────────────────────────────────────────

  setSelectedPitchIntent(intent: string) {
    set({ selectedPitchIntent: intent });
  },

  setSelectedTargetZone(zone: string) {
    set({ selectedTargetZone: zone, customTargetCoords: null });
  },

  setLineupDialogOpen(open: boolean) {
    set({ isLineupDialogOpen: open });
  },

  clearError() {
    set({ errorMessage: null, errorEnvelope: null });
  },
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

function parseError(err: unknown): { message: string; envelope: ApiErrorResponse | null } {
  if (err instanceof BaseballApiError) {
    return {
      message: `[${err.errorResponse.error_code}] ${err.errorResponse.message}`,
      envelope: err.errorResponse,
    };
  }
  if (err instanceof Error) {
    return { message: err.message, envelope: null };
  }
  return { message: String(err), envelope: null };
}
