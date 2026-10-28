import { create } from 'zustand';
import type {
  BatterDecision,
  BattingDrillEntry,
  GameState,
  InitialStateResponse,
  PitchResolveResponse,
  PitchThrowResponse,
  ResolvedPitchDetails,
  SwingContactReport,
  TeamLineup,
  TeamRotation,
  ApiErrorResponse,
} from '../types/api';
import { STRIKE_ZONES, INNER_ZONES, CHASE_ZONES, BaseballApiError } from '../types/api';
import type {
  Gameday2DPitchPacket,
  GamedayFilterOptions,
  CountCategory,
  SituationCategory,
} from '../types/gameday';
import { HttpGameService } from '../services/HttpGameService';
import {
  executeDelivery,
  classifyGamedayZone,
  getZoneNominalTarget,
  isRulebookStrike,
} from '../services/gamedayMath';
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

/** Shared state reset when a seeded game is loaded from the Flask API. */
function seededGamePatch(
  response: InitialStateResponse,
  seed: number,
  previousIntent: string,
): Partial<GameUiState> {
  const firstPitch = response.game?.current_pitcher?.arsenal?.[0]?.name;
  return {
    initialResponse: response,
    gameState: ensureStrategyIntent(response.game) as GameState | null,
    lineups: response.lineups,
    rotations: response.rotations,
    pitchFeed: [],
    currentAtBatPitches: [],
    lastPitchEndedAtBat: false,
    latestPitch: null,
    pitchPhase: 'IDLE',
    pendingThrow: null,
    pendingResolution: null,
    gamedayLog: [],
    selectedPitchPacketIndex: null,
    customTargetCoords: null,
    activeSeed: seed,
    controlMode: 'PITCHING',
    battingDrill: null,
    isBattingDrillOpen: false,
    practiceSaved: null,
    selectedPitchIntent: previousIntent || firstPitch || 'Four-Seam Fastball',
    selectedTargetZone: STRIKE_ZONES.HEART,
    isPitching: false,
    errorMessage: null,
    errorEnvelope: null,
  };
}

// ─── UI State ─────────────────────────────────────────────────────────────────

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';
export type DevTab = 'strategy' | 'gameday' | 'calibration' | 'split' | 'scenarios';
export type PitchPhase = 'IDLE' | 'IN_FLIGHT' | 'RESOLVING' | 'REACTING' | 'BATTED_BALL';
export type ControlMode = 'PITCHING' | 'BATTING';

export interface BattingDrillState {
  active: boolean;
  playing: boolean;
  entries: BattingDrillEntry[];
  index: number;
  pitchesThrown: number;
  loop: boolean;
  intervalMs: number;
}

interface PracticeSavedUi {
  pitchFeed: ResolvedPitchDetails[];
  gamedayLog: Gameday2DPitchPacket[];
  currentAtBatPitches: ResolvedPitchDetails[];
  latestPitch: ResolvedPitchDetails | null;
  lastPitchEndedAtBat: boolean;
}

export interface GameUiState {
  // Server / game data
  initialResponse: InitialStateResponse | null;
  gameState: GameState | null;
  pitchFeed: ResolvedPitchDetails[];
  /** Pitches in the current at-bat, oldest first (for numbered zone markers). */
  currentAtBatPitches: ResolvedPitchDetails[];
  /** True when the most recent pitch ended the at-bat. */
  lastPitchEndedAtBat: boolean;
  latestPitch: ResolvedPitchDetails | null;
  lineups: TeamLineup[];
  rotations: TeamRotation[];

  // Two-phase pitch reveal
  pitchPhase: PitchPhase;
  pendingThrow: PitchThrowResponse | null;
  pendingResolution: PitchResolveResponse | null;

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
  /** Seed used to start the current game; null for an unseeded game. */
  activeSeed: number | null;
  /** Player control mode; Batting Practice is web-only. */
  controlMode: ControlMode;
  battingDrill: BattingDrillState | null;
  isBattingDrillOpen: boolean;
  practiceSaved: PracticeSavedUi | null;

  // Strategy Menu
  isStrategyMenuOpen: boolean;

  // Settings Menu
  isSettingsMenuOpen: boolean;
  isRotationDialogOpen: boolean;
  isPitchFeedOpen: boolean;
  isTrajectoryOpen: boolean;

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
  resolvePitch(options?: {
    batterDecision?: BatterDecision;
    batterApproach?: string;
    contact?: SwingContactReport;
  }): Promise<void>;
  revealPitch(): void;
  beginBattedBall(): void;
  completeBattedBall(): void;
  clearPendingPitch(): void;
  simAtBat(): Promise<void>;
  swapLineup(teamId: number, pos1: number, pos2: number): Promise<void>;
  swapRotation(teamId: number, pos1: number, pos2: number): Promise<void>;
  loadSeed(seed: number): Promise<void>;
  setControlMode(mode: ControlMode): void;
  startBattingDrill(
    entries: BattingDrillEntry[],
    options?: { loop?: boolean; intervalMs?: number },
  ): Promise<void>;
  pauseBattingDrill(): void;
  resumeBattingDrill(): void;
  updateBattingDrill(
    entries: BattingDrillEntry[],
    options?: { loop?: boolean; intervalMs?: number },
  ): void;
  endBattingDrill(): Promise<void>;
  throwDrillPitch(): Promise<void>;
  setBattingDrillOpen(open: boolean): void;

  // Dev Menu & Gameday Telemetry
  toggleDevMenu(open?: boolean): void;
  setCustomTarget(coords: { x: number; z: number } | null): void;
  setSelectedPitchPacketIndex(index: number | null): void;
  setActiveDevTab(tab: DevTab): void;
  setGamedayFilters(filters: Partial<GamedayFilterOptions>): void;
  clearDebugLog(): void;
  runFastCalibration(commandRating?: number, sampleSize?: number): void;

  // Strategy Menu
  toggleStrategyMenu(open?: boolean): void

  // Settings Menu
  toggleSettingsMenu(open?: boolean): void
  togglePitchFeed(open?: boolean): void
  toggleTrajectory(open?: boolean): void

  // UI mutations
  setSelectedPitchIntent(intent: string): void;
  setSelectedTargetZone(zone: string): void;
  setGloveTarget(x: number, z: number): void;
  setLineupDialogOpen(open: boolean): void;
  setRotationDialogOpen(open: boolean): void;
  clearError(): void;
}

// ─── Store ────────────────────────────────────────────────────────────────────

const api = new HttpGameService(
  process.env['EXPO_PUBLIC_API_URL'] || process.env['API_BASE_URL'],
);

const initialState: GameUiState = {
  initialResponse: null,
  gameState: null,
  pitchFeed: [],
  currentAtBatPitches: [],
  lastPitchEndedAtBat: false,
  latestPitch: null,
  lineups: [],
  rotations: [],
  pitchPhase: 'IDLE',
  pendingThrow: null,
  pendingResolution: null,
  gamedayLog: [],
  selectedPitchPacketIndex: null,
  customTargetCoords: null,
  isDevMenuOpen: false,
  isStrategyMenuOpen: false,
  isSettingsMenuOpen: false,
  isRotationDialogOpen: false,
  isPitchFeedOpen: false,
  isTrajectoryOpen: false,
  activeDevTab: 'gameday',
  countFilter: 'ALL',
  situationFilter: 'ALL',
  batterFilter: 'ALL',
  pitchTypeFilter: 'ALL',
  selectedPitchIntent: 'Spin Monster Sweeper',
  selectedTargetZone: STRIKE_ZONES.HEART,
  isLineupDialogOpen: false,
  activeSeed: null,
  controlMode: 'PITCHING',
  battingDrill: null,
  isBattingDrillOpen: false,
  practiceSaved: null,
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
      if (get().battingDrill?.active) {
        await api.endPractice();
      }
      const response = await api.getState();
      const firstPitch = response.game?.current_pitcher?.arsenal?.[0]?.name;
      set((s) => ({
        initialResponse: response,
        gameState: ensureStrategyIntent(response.game) as GameState | null,
        lineups: response.lineups,
        rotations: response.rotations,
        loadingState: 'success',
        pitchFeed: [],
        currentAtBatPitches: [],
        lastPitchEndedAtBat: false,
        latestPitch: null,
        pitchPhase: 'IDLE',
        pendingThrow: null,
        pendingResolution: null,
        gamedayLog: [],
        selectedPitchPacketIndex: null,
        activeSeed: null,
        controlMode: 'PITCHING',
        battingDrill: null,
        isBattingDrillOpen: false,
        practiceSaved: null,
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
      const state = await api.startGame(1, 2);
      const firstPitch = state.current_pitcher?.arsenal?.[0]?.name;
      set((s) => ({
        gameState: ensureStrategyIntent(state) as GameState,
        pitchFeed: [],
        currentAtBatPitches: [],
        lastPitchEndedAtBat: false,
        latestPitch: null,
        pitchPhase: 'IDLE',
        pendingThrow: null,
        pendingResolution: null,
        gamedayLog: [],
        selectedPitchPacketIndex: null,
        activeSeed: null,
        controlMode: 'PITCHING',
        battingDrill: null,
        isBattingDrillOpen: false,
        practiceSaved: null,
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
      const response = await api.reset();
      const firstPitch = response.game?.current_pitcher?.arsenal?.[0]?.name;
      set((s) => ({
        initialResponse: response,
        gameState: ensureStrategyIntent(response.game) as GameState | null,
        lineups: response.lineups,
        rotations: response.rotations,
        pitchFeed: [],
        currentAtBatPitches: [],
        lastPitchEndedAtBat: false,
        latestPitch: null,
        pitchPhase: 'IDLE',
        pendingThrow: null,
        pendingResolution: null,
        gamedayLog: [],
        selectedPitchPacketIndex: null,
        customTargetCoords: null,
        activeSeed: null,
        controlMode: 'PITCHING',
        battingDrill: null,
        isBattingDrillOpen: false,
        practiceSaved: null,
        isPitching: false,
        selectedPitchIntent: firstPitch || s.selectedPitchIntent || 'Four-Seam Fastball',
        selectedTargetZone: STRIKE_ZONES.HEART,
      }));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({ isPitching: false, errorMessage: message, errorEnvelope: envelope });
    }
  },

  async loadSeed(seed: number) {
    const { isPitching, pitchPhase, controlMode } = get();
    if (isPitching || pitchPhase !== 'IDLE' || controlMode !== 'PITCHING') return;
    if (!Number.isInteger(seed) || seed < 0 || seed > 0xFFFFFFFF) {
      set({ errorMessage: 'Seed must be an integer between 0 and 4294967295' });
      return;
    }

    set({ isPitching: true, errorMessage: null, errorEnvelope: null });
    try {
      const response = await api.reset(seed);
      set((s) => seededGamePatch(response, seed, s.selectedPitchIntent));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({ isPitching: false, errorMessage: message, errorEnvelope: envelope });
    }
  },

  setControlMode(mode: ControlMode) {
    const { controlMode, isPitching, pitchPhase, battingDrill } = get();
    if (mode === 'PITCHING') {
      if (battingDrill?.active) {
        void get().endBattingDrill();
        return;
      }
      if (controlMode === 'PITCHING') return;
      if (isPitching || pitchPhase !== 'IDLE') return;
      set({ controlMode: 'PITCHING', customTargetCoords: null });
      return;
    }

    // Entering batting practice always opens the drill setup; the mode only
    // changes after a playlist is started.
    if (isPitching || pitchPhase !== 'IDLE') return;
    set({ isBattingDrillOpen: true });
  },

  setBattingDrillOpen(open: boolean) {
    if (open) {
      get().pauseBattingDrill();
      set({ isBattingDrillOpen: true });
      return;
    }
    set({ isBattingDrillOpen: false });
  },

  pauseBattingDrill() {
    const drill = get().battingDrill;
    if (!drill || !drill.playing) return;
    set({ battingDrill: { ...drill, playing: false } });
  },

  resumeBattingDrill() {
    const drill = get().battingDrill;
    if (!drill || !drill.active || drill.playing) return;
    set({ battingDrill: { ...drill, playing: true } });
  },

  updateBattingDrill(entries, options) {
    const drill = get().battingDrill;
    if (!drill?.active || entries.length === 0) return;
    const nextEntries = entries.map((entry) => ({ ...entry }));
    set({
      battingDrill: {
        ...drill,
        entries: nextEntries,
        index: 0,
        loop: options?.loop ?? drill.loop,
        intervalMs: options?.intervalMs ?? drill.intervalMs,
      },
      selectedPitchIntent: nextEntries[0].pitchName,
      selectedTargetZone: nextEntries[0].targetZone ?? STRIKE_ZONES.HEART,
    });
  },

  async startBattingDrill(entries, options) {
    const { isPitching, pitchPhase, battingDrill } = get();
    if (isPitching || pitchPhase !== 'IDLE' || battingDrill?.active) return;
    if (entries.length === 0) {
      set({ errorMessage: 'Add at least one pitch to the drill.' });
      return;
    }

    set({ isPitching: true, errorMessage: null, errorEnvelope: null });
    try {
      const response = await api.startPractice();
      const drillEntries = entries.map((entry) => ({ ...entry }));
      const first = drillEntries[0];
      const firstPitch = response.game?.current_pitcher?.arsenal?.[0]?.name;

      set((s) => ({
        initialResponse: response,
        gameState: ensureStrategyIntent(response.game) as GameState,
        lineups: response.lineups,
        rotations: response.rotations,
        controlMode: 'BATTING',
        isBattingDrillOpen: false,
        battingDrill: {
          active: true,
          playing: true,
          entries: drillEntries,
          index: 0,
          pitchesThrown: 0,
          loop: options?.loop ?? true,
          intervalMs: options?.intervalMs ?? 2500,
        },
        practiceSaved: {
          pitchFeed: s.pitchFeed,
          gamedayLog: s.gamedayLog,
          currentAtBatPitches: s.currentAtBatPitches,
          latestPitch: s.latestPitch,
          lastPitchEndedAtBat: s.lastPitchEndedAtBat,
        },
        pitchFeed: [],
        currentAtBatPitches: [],
        lastPitchEndedAtBat: false,
        latestPitch: null,
        pitchPhase: 'IDLE',
        pendingThrow: null,
        pendingResolution: null,
        gamedayLog: [],
        selectedPitchPacketIndex: null,
        customTargetCoords: null,
        selectedPitchIntent: first.pitchName ?? firstPitch ?? 'Four-Seam Fastball',
        selectedTargetZone: first.targetZone ?? STRIKE_ZONES.HEART,
        isPitching: false,
      }));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({
        isPitching: false,
        errorMessage: message,
        errorEnvelope: envelope,
      });
    }
  },

  async endBattingDrill() {
    const drill = get().battingDrill;
    if (!drill?.active) {
      set({
        controlMode: 'PITCHING',
        isBattingDrillOpen: false,
        battingDrill: null,
        practiceSaved: null,
      });
      return;
    }

    set({ isPitching: true, errorMessage: null, errorEnvelope: null });
    try {
      const response = await api.endPractice();
      const saved = get().practiceSaved;
      set({
        initialResponse: response,
        gameState: ensureStrategyIntent(response.game) as GameState,
        lineups: response.lineups,
        rotations: response.rotations,
        controlMode: 'PITCHING',
        battingDrill: null,
        isBattingDrillOpen: false,
        practiceSaved: null,
        pitchPhase: 'IDLE',
        pendingThrow: null,
        pendingResolution: null,
        latestPitch: saved?.latestPitch ?? null,
        pitchFeed: saved?.pitchFeed ?? [],
        currentAtBatPitches: saved?.currentAtBatPitches ?? [],
        lastPitchEndedAtBat: saved?.lastPitchEndedAtBat ?? false,
        gamedayLog: saved?.gamedayLog ?? [],
        selectedPitchPacketIndex: null,
        customTargetCoords: null,
        isPitching: false,
      });
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      const current = get().battingDrill;
      set({
        isPitching: false,
        errorMessage: message,
        errorEnvelope: envelope,
        ...(current ? { battingDrill: { ...current, playing: false } } : {}),
      });
    }
  },

  async throwDrillPitch() {
    const { battingDrill, isPitching, pitchPhase } = get();
    if (!battingDrill?.active || !battingDrill.playing) return;
    if (isPitching || pitchPhase !== 'IDLE') return;
    const entries = battingDrill.entries;
    if (entries.length === 0) return;

    const entry = entries[battingDrill.index] ?? entries[0];
    const isLast = battingDrill.index >= entries.length - 1;
    const nextIndex = battingDrill.loop
      ? (battingDrill.index + 1) % entries.length
      : Math.min(battingDrill.index + 1, entries.length - 1);
    const nextPlaying = battingDrill.loop || !isLast;

    set({
      isPitching: true,
      errorMessage: null,
      errorEnvelope: null,
      battingDrill: {
        ...battingDrill,
        index: nextIndex,
        pitchesThrown: battingDrill.pitchesThrown + 1,
        playing: nextPlaying,
      },
      selectedPitchIntent: entry.pitchName,
      selectedTargetZone: entry.targetZone ?? STRIKE_ZONES.HEART,
    });

    try {
      const response = await api.practiceThrowPitch(entry);
      if (!get().battingDrill?.active) return;
      set({
        pendingThrow: response,
        pitchPhase: 'IN_FLIGHT',
        isPitching: false,
      });
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      const current = get().battingDrill;
      set({
        isPitching: false,
        errorMessage: message,
        errorEnvelope: envelope,
        ...(current ? { battingDrill: { ...current, playing: false } } : {}),
      });
    }
  },

  // ─── Gameplay ──────────────────────────────────────────────────────────────

  async throwPitch() {
    if (get().battingDrill?.active) return;
    const {
      selectedPitchIntent,
      selectedTargetZone,
      customTargetCoords,
      isPitching,
      pitchPhase,
    } = get();
    if (isPitching || pitchPhase !== 'IDLE') return;
    set({
      isPitching: true,
      pitchPhase: 'IN_FLIGHT',
      pendingThrow: null,
      pendingResolution: null,
      errorMessage: null,
      errorEnvelope: null,
    });
    try {
      const result = await api.throwPitch(
        selectedPitchIntent || undefined,
        selectedTargetZone || undefined,
        customTargetCoords || undefined,
      );
      // Publish only the delivery. No game state, feed, or log entry changes
      // until revealPitch().
      set({ pendingThrow: result });
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({
        isPitching: false,
        pitchPhase: 'IDLE',
        pendingThrow: null,
        errorMessage: message,
        errorEnvelope: envelope,
      });
    }
  },

  async resolvePitch(options?: {
    batterDecision?: BatterDecision;
    batterApproach?: string;
    contact?: SwingContactReport;
  }) {
    const { pendingThrow, pitchPhase, battingDrill } = get();
    if (!pendingThrow || pitchPhase !== 'IN_FLIGHT') return;
    set({ pitchPhase: 'RESOLVING', errorMessage: null, errorEnvelope: null });
    try {
      const result = battingDrill?.active
        ? await api.practiceResolvePitch({
            batterDecision: options?.batterDecision,
            batterApproach: options?.batterApproach,
            contact: options?.contact,
          })
        : await api.resolvePitch(
            options?.batterDecision,
            options?.batterApproach,
            options?.contact,
          );
      set({ pendingResolution: result, pitchPhase: 'REACTING' });
    } catch (err: unknown) {
      // The server may have committed before the response was lost. Keep the
      // last revealed state rather than guessing with a second resolve (which
      // would conflict). The next successful reveal reconciles the state.
      const { message, envelope } = parseError(err);
      set({
        isPitching: false,
        pitchPhase: 'IDLE',
        pendingThrow: null,
        pendingResolution: null,
        errorMessage: message,
        errorEnvelope: envelope,
      });
    }
  },

  revealPitch() {
    const { pendingResolution } = get();
    const pitch = pendingResolution?.pitch_details;
    if (!pendingResolution || !pitch) return;

    const packet = pitch.gameday_packet;
    // A 0-0 count after a pitch means the at-bat ended (new batter up).
    const atBatEnded =
      pendingResolution.game_state.balls === 0 &&
      pendingResolution.game_state.strikes === 0;

    set((s) => ({
      gameState: ensureStrategyIntent(pendingResolution.game_state) as GameState,
      latestPitch: pitch,
      // Keep the pitch that ended the at-bat visible; the next at-bat's first
      // pitch starts a fresh list.
      currentAtBatPitches: s.lastPitchEndedAtBat
        ? [pitch]
        : [...s.currentAtBatPitches, pitch],
      lastPitchEndedAtBat: atBatEnded,
      pitchFeed: [pitch, ...s.pitchFeed].slice(0, 25),
      gamedayLog: packet ? [packet, ...s.gamedayLog].slice(0, 100) : s.gamedayLog,
      selectedPitchPacketIndex: null,
      pitchPhase: 'IDLE',
      pendingThrow: null,
      pendingResolution: null,
      isPitching: false,
    }));
  },

  beginBattedBall() {
    const { pitchPhase, pendingResolution } = get();
    if (pitchPhase !== 'REACTING') return;
    if (!pendingResolution?.pitch_details?.batted_ball) return;
    set({ pitchPhase: 'BATTED_BALL' });
  },

  completeBattedBall() {
    const { pitchPhase, pendingResolution } = get();
    if (pitchPhase !== 'BATTED_BALL') return;
    if (!pendingResolution) {
      set({ pitchPhase: 'IDLE', isPitching: false });
      return;
    }
    get().revealPitch();
  },

  clearPendingPitch() {
    set({
      pitchPhase: 'IDLE',
      pendingThrow: null,
      pendingResolution: null,
      isPitching: false,
    });
  },

  async simAtBat() {
    const { isPitching, pitchPhase, controlMode } = get();
    if (isPitching || pitchPhase !== 'IDLE') return;
    if (controlMode !== 'PITCHING') return;
    set({ isPitching: true, errorMessage: null, errorEnvelope: null });
    try {
      const result = await api.simAtBat();
      const packet = result.pitch_details.gameday_packet;
      const atBatEnded =
        result.game_state.balls === 0 && result.game_state.strikes === 0;

      set((s) => ({
        gameState: ensureStrategyIntent(result.game_state) as GameState,
        latestPitch: result.pitch_details,
        currentAtBatPitches: s.lastPitchEndedAtBat
          ? [result.pitch_details]
          : [...s.currentAtBatPitches, result.pitch_details],
        lastPitchEndedAtBat: atBatEnded,
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
      await api.swapLineup(teamId, pos1, pos2);
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

  async swapRotation(teamId: number, pos1: number, pos2: number) {
    set({ isPitching: true });
    try {
      await api.swapRotation(teamId, pos1, pos2);
      set((s) => ({
        isPitching: false,
        rotations: s.rotations.map((tr) => {
          if (tr.team_id !== teamId) return tr;
          const newStarters = [...tr.starters];
          const i1 = pos1 - 1;
          const i2 = pos2 - 1;
          if (i1 >= 0 && i1 < newStarters.length && i2 >= 0 && i2 < newStarters.length) {
            const tmp = newStarters[i1];
            newStarters[i1] = newStarters[i2];
            newStarters[i2] = tmp;
          }
          return { ...tr, starters: newStarters };
        }),
      }));
    } catch (err: unknown) {
      const { message, envelope } = parseError(err);
      set({ isPitching: false, errorMessage: message, errorEnvelope: envelope });
    }
  },

  // ─── Dev Menu & Gameday Telemetry ───────────────────────────────────────────

  toggleDevMenu(open?: boolean) {
    set((s) => ({ isDevMenuOpen: open !== undefined ? open : !s.isDevMenuOpen }));
  },

  toggleSettingsMenu(open?: boolean) {
    set((s) => ({ isSettingsMenuOpen: open !== undefined ? open : !s.isSettingsMenuOpen }));
  },

  togglePitchFeed(open?: boolean) {
    set((s) => ({ isPitchFeedOpen: open !== undefined ? open : !s.isPitchFeedOpen }));
  },

  toggleTrajectory(open?: boolean) {
    set((s) => ({ isTrajectoryOpen: open !== undefined ? open : !s.isTrajectoryOpen }));
  },

  toggleStrategyMenu(open?: boolean) {
    set((s) => ({ isStrategyMenuOpen: open !== undefined ? open : !s.isStrategyMenuOpen }));
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
      // boundary-adjacent targets exercise the natural heart leak
      { x: 0.40, z: 2.15 },
      { x: -0.40, z: 2.15 },
      { x: 0.40, z: 2.85 },
      { x: -0.40, z: 2.85 },
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
          maxRadiusInches: execution.maxRadiusInches,
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
          call: isRulebookStrike(execution.realizedX, execution.realizedZ)
            ? 'CALLED_STRIKE'
            : 'BALL',
          isStrike: isRulebookStrike(execution.realizedX, execution.realizedZ),
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

  setGloveTarget(x: number, z: number) {
    // Keep the zone label in the same category as the target. A glove just
    // outside a corner is a ball; it should not inherit the nearest inner
    // corner's strike label.
    const candidates = isRulebookStrike(x, z) ? INNER_ZONES : CHASE_ZONES;
    let best: string = candidates[0];
    let bestDist = Number.POSITIVE_INFINITY;
    for (const name of candidates) {
      const center = getZoneNominalTarget(name);
      const dx = x - center.x;
      const dz = z - center.z;
      const dist = dx * dx + dz * dz;
      if (dist < bestDist) {
        bestDist = dist;
        best = name;
      }
    }
    set({ customTargetCoords: { x, z }, selectedTargetZone: best });
  },

  setLineupDialogOpen(open: boolean) {
    set({ isLineupDialogOpen: open });
  },

  setRotationDialogOpen(open: boolean) {
    set({ isRotationDialogOpen: open });
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
