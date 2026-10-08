/**
 * High-fidelity Deterministic Mock Engine
 * Seeded with Aaron Judge (#99 NYY) vs Nolan McLean (#26 NYM).
 * Provides offline/mock-first parity matching 02_API_CONTRACTS.md.
 *
 * Ported from MockGameService.kt — logic is 1:1 identical.
 */

import type {
  BatterInfo,
  BatterGameStats,
  Bases,
  GameState,
  InitialStateResponse,
  LineupPlayer,
  PitchArsenalItem,
  PitchDetails,
  PitcherGameStats,
  PitcherInfo,
  PitchOptionWeight,
  PitchResultResponse,
  PitchResultType,
  PlayerSummary,
  Score,
  StatcastMetrics,
  StrategyIntentDecision,
  TeamLineup,
  TeamRotation,
  ZoneOptionWeight,
} from '../types/api';
import {
  STRIKE_ZONES,
  ALL_ZONES,
  isStrike,
  isEdge,
  batterToPlayerSummary,
  countRunners,
} from '../types/api';
import type { IGameService } from './IGameService';
import type { Gameday2DPitchPacket } from '../types/gameday';
import {
  executeDelivery,
  getZoneNominalTarget,
  classifyGamedayZone,
  isRulebookStrike,
  determineSituationCategory,
} from './gamedayMath';
import { calculateStrategyAndIntent as calcStrategy } from './strategyEngine';

// ─── Seeded RNG (Mulberry32 — deterministic, matches Java Random(42)) ─────────

function mulberry32(seed: number): () => number {
  let s = seed;
  return () => {
    s |= 0;
    s = (s + 0x6d2b79f5) | 0;
    let z = Math.imul(s ^ (s >>> 15), 1 | s);
    z = (z + Math.imul(z ^ (z >>> 7), 61 | z)) ^ z;
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  };
}

// ─── Seed Player Data ─────────────────────────────────────────────────────────

const NOLAN_MCLEAN: PitcherInfo = {
  id: 26,
  name: 'Nolan McLean',
  jersey_number: 26,
  position: 'SP',
  team: 'New York Mets',
  break_rating: 99,
  velocity_rating: 98,
  arm_strength: 97,
  control: 68,
  arsenal: [
    {
      name: 'Spin Monster Sweeper',
      velocity_mph: 84.5,
      spin_rpm: 3020,
      break_rating: 99,
      control_rating: 65,
      statcast: { whiff_pct: 44.5, chase_pct: 39.0, gb_pct: 38.0, stuff_plus: 135, zone_pct: 42.5, run_value: 8.4 },
    },
    {
      name: 'Four-Seam Fastball',
      velocity_mph: 98.0,
      spin_rpm: 2480,
      break_rating: 82,
      control_rating: 72,
      statcast: { whiff_pct: 27.0, chase_pct: 22.5, gb_pct: 32.0, stuff_plus: 118, zone_pct: 64.0, run_value: 4.2 },
    },
    {
      name: 'Power Sinker',
      velocity_mph: 96.8,
      spin_rpm: 2240,
      break_rating: 91,
      control_rating: 69,
      statcast: { whiff_pct: 18.5, chase_pct: 28.0, gb_pct: 64.5, stuff_plus: 106, zone_pct: 58.0, run_value: 5.1 },
    },
    {
      name: 'Spike Curveball',
      velocity_mph: 81.2,
      spin_rpm: 2890,
      break_rating: 94,
      control_rating: 63,
      statcast: { whiff_pct: 38.0, chase_pct: 35.0, gb_pct: 48.0, stuff_plus: 122, zone_pct: 45.0, run_value: 3.8 },
    },
  ],
  stats: { pitches_thrown: 54, strikeouts: 6, walks: 1, hits_allowed: 3, runs_allowed: 1 },
};

function makeAaronJudge(): BatterInfo {
  return {
    id: 99,
    name: 'Aaron Judge',
    jersey_number: 99,
    position: 'RF',
    team: 'New York Yankees',
    power: 99,
    contact: 88,
    vision: 84,
    traits: ['Home Run Threat', 'First Pitch Hunter', 'Elite Barrel Rate'],
    hot_zones: {
      [STRIKE_ZONES.HEART]: 0.82,
      [STRIKE_ZONES.UPPER_IN]: 0.65,
      [STRIKE_ZONES.LOWER_MIDDLE]: 0.54,
      [STRIKE_ZONES.MIDDLE_IN]: 0.51,
      [STRIKE_ZONES.UPPER_MIDDLE]: 0.49,
    },
    stats: { at_bats: 3, hits: 1, rbis: 2, home_runs: 1 },
  };
}

function makeJuanSoto(): BatterInfo {
  return {
    id: 22,
    name: 'Juan Soto',
    jersey_number: 22,
    position: 'LF',
    team: 'New York Yankees',
    power: 92,
    contact: 91,
    vision: 98,
    traits: ['Plate Discipline God', 'Soto Shuffle'],
    hot_zones: { [STRIKE_ZONES.HEART]: 0.78, [STRIKE_ZONES.LOWER_IN]: 0.61 },
    stats: { at_bats: 3, hits: 2, rbis: 1, home_runs: 0 },
  };
}

function makeGiancarloStanton(): BatterInfo {
  return {
    id: 27,
    name: 'Giancarlo Stanton',
    jersey_number: 27,
    position: 'DH',
    team: 'New York Yankees',
    power: 98,
    contact: 74,
    vision: 70,
    traits: ['Maximum Exit Velo'],
    hot_zones: { [STRIKE_ZONES.HEART]: 0.75, [STRIKE_ZONES.LOWER_AWAY]: 0.32 },
    stats: { at_bats: 2, hits: 0, rbis: 0, home_runs: 0 },
  };
}

function makeAnthonyVolpe(): BatterInfo {
  return {
    id: 11,
    name: 'Anthony Volpe',
    jersey_number: 11,
    position: 'SS',
    team: 'New York Yankees',
    power: 76,
    contact: 80,
    vision: 79,
    traits: ['Speed Demon'],
    hot_zones: { [STRIKE_ZONES.HEART]: 0.45 },
    stats: { at_bats: 2, hits: 1, rbis: 0, home_runs: 0 },
  };
}

const YANKEES_BATTERS_SEED: BatterInfo[] = [
  makeJuanSoto(),
  makeAaronJudge(),
  makeGiancarloStanton(),
  makeAnthonyVolpe(),
];

function makeYankeesLineup(): LineupPlayer[] {
  return [
    { batting_order: 1, player: { id: 25, name: 'Gleyber Torres', jersey_number: 25, position: '2B', team: 'New York Yankees' }, ratings: 'Contact: 81 | Power: 78' },
    { batting_order: 2, player: { id: 22, name: 'Juan Soto', jersey_number: 22, position: 'LF', team: 'New York Yankees' }, ratings: 'Contact: 91 | Vision: 98' },
    { batting_order: 3, player: { id: 99, name: 'Aaron Judge', jersey_number: 99, position: 'RF', team: 'New York Yankees' }, ratings: 'Power: 99 | Vision: 84' },
    { batting_order: 4, player: { id: 27, name: 'Giancarlo Stanton', jersey_number: 27, position: 'DH', team: 'New York Yankees' }, ratings: 'Power: 98 | Contact: 74' },
    { batting_order: 5, player: { id: 13, name: 'Jazz Chisholm Jr.', jersey_number: 13, position: '3B', team: 'New York Yankees' }, ratings: 'Speed: 92 | Power: 82' },
    { batting_order: 6, player: { id: 48, name: 'Anthony Rizzo', jersey_number: 48, position: '1B', team: 'New York Yankees' }, ratings: 'Contact: 80 | Power: 80' },
    { batting_order: 7, player: { id: 11, name: 'Anthony Volpe', jersey_number: 11, position: 'SS', team: 'New York Yankees' }, ratings: 'Speed: 89 | Defense: 88' },
    { batting_order: 8, player: { id: 28, name: 'Austin Wells', jersey_number: 28, position: 'C', team: 'New York Yankees' }, ratings: 'Power: 79 | Vision: 82' },
    { batting_order: 9, player: { id: 24, name: 'Alex Verdugo', jersey_number: 24, position: 'CF', team: 'New York Yankees' }, ratings: 'Contact: 83 | Arm: 86' },
  ];
}

function makeMetsLineup(): LineupPlayer[] {
  return [
    { batting_order: 1, player: { id: 12, name: 'Francisco Lindor', jersey_number: 12, position: 'SS', team: 'New York Mets' }, ratings: 'Power: 86 | Defense: 95' },
    { batting_order: 2, player: { id: 9, name: 'Brandon Nimmo', jersey_number: 9, position: 'LF', team: 'New York Mets' }, ratings: 'Vision: 92 | Contact: 84' },
    { batting_order: 3, player: { id: 27, name: 'Mark Vientos', jersey_number: 27, position: '3B', team: 'New York Mets' }, ratings: 'Power: 88 | Contact: 79' },
    { batting_order: 4, player: { id: 20, name: 'Pete Alonso', jersey_number: 20, position: '1B', team: 'New York Mets' }, ratings: 'Power: 96 | Clutch: 89' },
    { batting_order: 5, player: { id: 33, name: 'Jesse Winker', jersey_number: 33, position: 'DH', team: 'New York Mets' }, ratings: 'Vision: 87 | Contact: 82' },
    { batting_order: 6, player: { id: 6, name: 'Starling Marte', jersey_number: 6, position: 'RF', team: 'New York Mets' }, ratings: 'Speed: 88 | Contact: 81' },
    { batting_order: 7, player: { id: 1, name: 'Jose Iglesias', jersey_number: 1, position: '2B', team: 'New York Mets' }, ratings: 'Contact: 89 | Defense: 91' },
    { batting_order: 8, player: { id: 15, name: 'Tyrone Taylor', jersey_number: 15, position: 'CF', team: 'New York Mets' }, ratings: 'Speed: 85 | Defense: 84' },
    { batting_order: 9, player: { id: 4, name: 'Francisco Alvarez', jersey_number: 4, position: 'C', team: 'New York Mets' }, ratings: 'Power: 85 | Arm: 88' },
  ];
}

// ─── Helper functions ─────────────────────────────────────────────────────────

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}

function getAdjacentZone(zone: string): string {
  const map: Record<string, string> = {
    [STRIKE_ZONES.UPPER_IN]: STRIKE_ZONES.UPPER_MIDDLE,
    [STRIKE_ZONES.UPPER_MIDDLE]: STRIKE_ZONES.UPPER_AWAY,
    [STRIKE_ZONES.UPPER_AWAY]: STRIKE_ZONES.MIDDLE_AWAY,
    [STRIKE_ZONES.MIDDLE_IN]: STRIKE_ZONES.HEART,
    [STRIKE_ZONES.HEART]: STRIKE_ZONES.MIDDLE_AWAY,
    [STRIKE_ZONES.MIDDLE_AWAY]: STRIKE_ZONES.LOWER_AWAY,
    [STRIKE_ZONES.LOWER_IN]: STRIKE_ZONES.LOWER_MIDDLE,
    [STRIKE_ZONES.LOWER_MIDDLE]: STRIKE_ZONES.LOWER_AWAY,
    [STRIKE_ZONES.LOWER_AWAY]: STRIKE_ZONES.LOWER_MIDDLE,
    [STRIKE_ZONES.CHASE_HIGH]: STRIKE_ZONES.UPPER_MIDDLE,
    [STRIKE_ZONES.CHASE_LOW]: STRIKE_ZONES.LOWER_MIDDLE,
    [STRIKE_ZONES.CHASE_IN]: STRIKE_ZONES.MIDDLE_IN,
    [STRIKE_ZONES.CHASE_AWAY]: STRIKE_ZONES.MIDDLE_AWAY,
  };
  return map[zone] ?? STRIKE_ZONES.LOWER_AWAY;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ─── MockGameService ──────────────────────────────────────────────────────────

export class MockGameService implements IGameService {
  private seed: number;
  private rng: () => number;
  private yankeesBatters: BatterInfo[];
  private yankeeBatterIndex: number;
  private yankeesLineup: LineupPlayer[];
  private metsLineup: LineupPlayer[];
  private currentGameState!: GameState;

  constructor(seed: number = 42) {
    this.seed = seed;
    this.rng = mulberry32(seed);
    this.yankeesBatters = [...YANKEES_BATTERS_SEED];
    this.yankeeBatterIndex = 1; // Start with Aaron Judge
    this.yankeesLineup = makeYankeesLineup();
    this.metsLineup = makeMetsLineup();
    this._initGameState();
  }

  private _initGameState(): void {
    const base = this._makeInitialState();
    this.currentGameState = { ...base, strategy_intent: this.calculateStrategyAndIntent(base) };
  }

  private _makeInitialState(): GameState {
    return {
      inning: 4,
      top_bottom: 'TOP',
      outs: 1,
      balls: 1,
      strikes: 1,
      score: { home: 1, away: 2 },
      bases: {
        first: { id: 22, name: 'Juan Soto', jersey_number: 22, position: 'LF', team: 'New York Yankees' },
        second: null,
        third: null,
      },
      current_batter: makeAaronJudge(),
      current_pitcher: { ...NOLAN_MCLEAN },
      game_over: false,
      home_team: 'New York Mets',
      away_team: 'New York Yankees',
      win_probability: 0.58,
    };
  }
  // ─── Strategy & Intent Calculation (delegated to strategyEngine) ──────────────

  calculateStrategyAndIntent(state: GameState): StrategyIntentDecision {
    return calcStrategy(state);
  }

  // ─── IGameService implementation ──────────────────────────────────────────────

  async getState(): Promise<InitialStateResponse> {
    await delay(100);
    return {
      teams: ['New York Yankees', 'New York Mets'],
      game: this.currentGameState,
      lineups: [
        { team_id: 1, team_name: 'New York Yankees', lineup: [...this.yankeesLineup] },
        { team_id: 2, team_name: 'New York Mets', lineup: [...this.metsLineup] },
      ],
      rotations: [
        {
          team_id: 1,
          team_name: 'New York Yankees',
          starters: [
            { id: 45, name: 'Gerrit Cole', jersey_number: 45, position: 'SP', team: 'New York Yankees' },
            { id: 55, name: 'Carlos Rodon', jersey_number: 55, position: 'SP', team: 'New York Yankees' },
          ],
        },
        {
          team_id: 2,
          team_name: 'New York Mets',
          starters: [
            { id: 26, name: 'Nolan McLean', jersey_number: 26, position: 'SP', team: 'New York Mets' },
            { id: 34, name: 'Kodai Senga', jersey_number: 34, position: 'SP', team: 'New York Mets' },
          ],
        },
      ],
    };
  }

  async startGame(homeTeamId: number = 1, awayTeamId: number = 2, seed?: number): Promise<GameState> {
    if (seed !== undefined) {
      this.seed = seed;
      this.rng = mulberry32(seed);
    }
    const base: GameState = {
      inning: 1,
      top_bottom: 'TOP',
      outs: 0,
      balls: 0,
      strikes: 0,
      score: { home: 0, away: 0 },
      bases: { first: null, second: null, third: null },
      current_batter: makeAaronJudge(),
      current_pitcher: { ...NOLAN_MCLEAN },
      game_over: false,
      home_team: 'New York Mets',
      away_team: 'New York Yankees',
      win_probability: 0.5,
    };
    this.currentGameState = { ...base, strategy_intent: this.calculateStrategyAndIntent(base) };
    this.yankeeBatterIndex = 1;
    return this.currentGameState;
  }

  async reset(): Promise<InitialStateResponse> {
    await delay(150);
    await this.startGame(2, 1, 42);
    return this.getState();
  }

  async swapLineup(team: number, pos1: number, pos2: number): Promise<void> {
    await delay(80);
    const targetList = team === 1 ? this.yankeesLineup : this.metsLineup;
    const idx1 = pos1 - 1;
    const idx2 = pos2 - 1;
    if (idx1 < 0 || idx1 >= targetList.length || idx2 < 0 || idx2 >= targetList.length) {
      throw new Error(`Invalid lineup indices: ${pos1}, ${pos2}`);
    }
    const p1 = targetList[idx1];
    const p2 = targetList[idx2];
    targetList[idx1] = { ...p1, player: p2.player, ratings: p2.ratings };
    targetList[idx2] = { ...p2, player: p1.player, ratings: p1.ratings };
  }

  async pitch(
    pitchIntent?: string,
    targetZone?: string,
    customTarget?: { x: number; z: number },
  ): Promise<PitchResultResponse> {
    await delay(120);
    return this._resolvePitch(pitchIntent, targetZone, customTarget);
  }

  async simAtBat(): Promise<PitchResultResponse> {
    await delay(300);
    let lastResponse: PitchResultResponse | null = null;
    const startingOuts = this.currentGameState.outs;
    const startingBatter = this.currentGameState.current_batter.id;

    for (let i = 0; i < 10; i++) {
      const strategy = this.calculateStrategyAndIntent(this.currentGameState);
      const response = this._resolvePitch(strategy.recommended_pitch, strategy.recommended_zone);
      lastResponse = response;

      const type = response.pitch_details.pitch_result;
      const batterChanged = response.game_state.current_batter.id !== startingBatter;
      const outsChanged = response.game_state.outs !== startingOuts;

      if (
        batterChanged ||
        outsChanged ||
        type === 'HOME_RUN' ||
        type === 'SINGLE' ||
        type === 'DOUBLE' ||
        type === 'TRIPLE' ||
        type === 'IN_PLAY_OUT' ||
        type === 'HIT_BY_PITCH'
      ) {
        break;
      }
    }

    return lastResponse ?? this._resolvePitch(undefined, undefined);
  }

  // ─── Core pitch resolution (port of resolvePitch) ─────────────────────────

  private _resolvePitch(
    pitchIntent?: string,
    targetZone?: string,
    customTarget?: { x: number; z: number },
  ): PitchResultResponse {
    const strategyDecision = this.calculateStrategyAndIntent(this.currentGameState);
    const isWaste = pitchIntent?.toUpperCase() === 'WASTE';
    const isChase = pitchIntent?.toUpperCase() === 'BALL';

    const selectedPitchName = isWaste || isChase
      ? strategyDecision.recommended_pitch
      : pitchIntent ?? strategyDecision.recommended_pitch;

    const selectedPitch = NOLAN_MCLEAN.arsenal.find((a) => a.name === selectedPitchName) ?? NOLAN_MCLEAN.arsenal[0];

    const intended = isWaste
      ? STRIKE_ZONES.CHASE_HIGH
      : isChase
        ? STRIKE_ZONES.CHASE_AWAY
        : targetZone ?? strategyDecision.recommended_zone;

    // 2D Target Determination
    let targetX: number;
    let targetZ: number;
    let isManualOverride = false;
    let intendedZoneCategory = classifyGamedayZone(0, 2.5);

    if (customTarget) {
      targetX = customTarget.x;
      targetZ = customTarget.z;
      isManualOverride = true;
      intendedZoneCategory = classifyGamedayZone(targetX, targetZ);
    } else {
      const nominal = getZoneNominalTarget(intended);
      targetX = nominal.x;
      targetZ = nominal.z;
      intendedZoneCategory = nominal.category;
    }

    // 2D Bivariate Gaussian Execution Math
    const execution = executeDelivery(
      targetX,
      targetZ,
      NOLAN_MCLEAN.control || 68,
      this.currentGameState.current_pitcher.stats.pitches_thrown,
      70, // Stamina rating
      this.rng,
    );

    const realizedCategory = classifyGamedayZone(execution.realizedX, execution.realizedZ);
    const isHeartZoneLeak = intendedZoneCategory !== 'HEART' && realizedCategory === 'HEART';
    const hitShadowZoneTarget = intendedZoneCategory === 'SHADOW' && realizedCategory === 'SHADOW';

    // Command variance
    const roll = this.rng();
    let actualZone: string;
    let commandQuality: string;

    if (isWaste) {
      actualZone = roll < 0.5 ? STRIKE_ZONES.CHASE_HIGH : STRIKE_ZONES.CHASE_AWAY;
      commandQuality = 'WASTE_EXECUTED';
    } else if (isChase) {
      if (roll < 0.85) { actualZone = intended; commandQuality = 'TARGET_EXECUTED'; }
      else if (roll < 0.94) { actualZone = STRIKE_ZONES.CHASE_LOW; commandQuality = 'SLIGHT_MISS'; }
      else { actualZone = STRIKE_ZONES.LOWER_AWAY; commandQuality = 'MISTAKE_HANG'; }
    } else if (roll < 0.68) {
      actualZone = intended;
      commandQuality = isEdge(intended) ? 'PINPOINT' : 'TARGET_EXECUTED';
    } else if (roll < 0.88) {
      actualZone = getAdjacentZone(intended);
      commandQuality = 'SLIGHT_MISS';
    } else if (roll < 0.95) {
      actualZone = STRIKE_ZONES.HEART;
      commandQuality = 'MISTAKE_HANG';
    } else {
      actualZone = STRIKE_ZONES.CHASE_AWAY;
      commandQuality = 'WILD_MISS';
    }

    const state = this.currentGameState;
    const isPitchInZone = isStrike(actualZone);
    const batter = state.current_batter;
    const hotSlg = batter.hot_zones[actualZone] ?? 0.32;

    const isDoublePlaySituation = state.bases.first !== null && state.outs < 2;
    const isBasesLoaded = state.bases.first !== null && state.bases.second !== null && state.bases.third !== null;

    // Swing probability
    const swingProb = isWaste
      ? 0.0
      : isPitchInZone
        ? actualZone === STRIKE_ZONES.HEART ? 0.92 : 0.76
        : selectedPitch.break_rating > 95 ? 0.44 : 0.28;

    const didSwing = this.rng() < swingProb;

    let pitchResult: PitchResultType;
    let exitVelo: number | undefined;
    let launchAngle: number | undefined;
    let description: string;
    let isDoublePlayTurned = false;

    if (!didSwing) {
      if (isPitchInZone) {
        pitchResult = 'CALLED_STRIKE';
        description = `${NOLAN_MCLEAN.name} paints the ${actualZone} with a ${selectedPitch.velocity_mph} MPH ${selectedPitch.name}. Called strike!`;
      } else {
        pitchResult = 'BALL';
        description = `${batter.name} lays off the ${selectedPitch.name} in ${actualZone}. Ball!`;
      }
    } else {
      // Batter swung
      if (actualZone === STRIKE_ZONES.HEART && hotSlg >= 0.7 && this.rng() < 0.45) {
        pitchResult = 'HOME_RUN';
        exitVelo = 112.5 + this.rng() * 5.0;
        launchAngle = 28.0 + this.rng() * 4.0;
        description = isBasesLoaded
          ? `GRAND SLAM! ${batter.name} annihilates a ${selectedPitch.velocity_mph} MPH hanger in the heart over the bleachers! (440 FT, ${Math.round(exitVelo)} MPH)`
          : `CRACKED! ${batter.name} obliterates a ${selectedPitch.velocity_mph} MPH ${selectedPitch.name} over the centerfield wall! (${Math.round(exitVelo)} MPH, ${Math.round(launchAngle)}°)`;
      } else if (actualZone === STRIKE_ZONES.UPPER_IN && hotSlg >= 0.6 && this.rng() < 0.5) {
        pitchResult = 'DOUBLE';
        exitVelo = 104.2 + this.rng() * 4.0;
        launchAngle = 18.0 + this.rng() * 3.0;
        description = `${batter.name} rips a double into the left-center gap off the high-and-tight ${selectedPitch.name}!`;
      } else if (
        isDoublePlaySituation &&
        (selectedPitch.name.includes('Sinker') ||
          [STRIKE_ZONES.LOWER_IN, STRIKE_ZONES.LOWER_MIDDLE, STRIKE_ZONES.LOWER_AWAY, STRIKE_ZONES.CHASE_LOW].includes(actualZone as any)) &&
        this.rng() < 0.6
      ) {
        pitchResult = 'IN_PLAY_OUT';
        isDoublePlayTurned = true;
        exitVelo = 86.5 + this.rng() * 4.0;
        launchAngle = -12.0;
        description = `DOUBLE PLAY! 6-4-3 Twin Killing! Nolan McLean's ${selectedPitch.velocity_mph} MPH ${selectedPitch.name} induces a sharp grounder to short. Volpe to Torres to first!`;
      } else if (isPitchInZone && this.rng() < 0.3) {
        pitchResult = 'SINGLE';
        exitVelo = 98.0 + this.rng() * 6.0;
        launchAngle = 12.0 + this.rng() * 4.0;
        description = 'Sharp line drive single up the middle into center field!';
      } else if (!isPitchInZone && selectedPitch.break_rating >= 95 && this.rng() < 0.65) {
        pitchResult = 'SWINGING_STRIKE';
        description = `${batter.name} chases the wicked 3020 RPM ${selectedPitch.name} in the ${actualZone}! Whiff for swinging strike!`;
      } else if (this.rng() < 0.38) {
        pitchResult = 'FOUL';
        exitVelo = 91.0 + this.rng() * 8.0;
        launchAngle = 55.0;
        description = 'Fouled back into the netting on a hard hack.';
      } else if (this.rng() < 0.5) {
        pitchResult = 'IN_PLAY_OUT';
        exitVelo = 88.0 + this.rng() * 6.0;
        launchAngle = -8.0;
        description = 'Soft ground ball rolled out to short. Routine 6-3 out.';
      } else {
        pitchResult = 'SWINGING_STRIKE';
        description = `Swing and a miss on high velocity ${selectedPitch.velocity_mph} MPH heater!`;
      }
    }

    const updatedState = this._applyOutcomeToGameState(pitchResult, exitVelo, isDoublePlayTurned);

    const repertoireProbabilities: Record<string, number> = {};
    for (const p of strategyDecision.pitch_weights ?? []) {
      repertoireProbabilities[p.pitch_name] = +(p.probability_pct / 100).toFixed(2);
    }

    const situationCategory = determineSituationCategory(
      state.balls,
      state.strikes,
      state.outs,
      state.bases.first !== null,
      state.bases.second !== null,
      state.bases.third !== null,
    );

    const gamedayPacket: Gameday2DPitchPacket = {
      meta: {
        pitchNumber: this.currentGameState.current_pitcher.stats.pitches_thrown + 1,
        pitcherName: NOLAN_MCLEAN.name,
        pitcherOvr: 88,
        commandRating: NOLAN_MCLEAN.control || 68,
        staminaPct: Math.max(10, Math.round(100 - (this.currentGameState.current_pitcher.stats.pitches_thrown / 70) * 40)),
        pitchesThrown: this.currentGameState.current_pitcher.stats.pitches_thrown + 1,
        inning: state.inning,
        isTopInning: state.top_bottom === 'TOP',
        count: { balls: state.balls, strikes: state.strikes, outs: state.outs },
        runnersOnBase: {
          first: state.bases.first !== null,
          second: state.bases.second !== null,
          third: state.bases.third !== null,
        },
        batterName: batter.name,
        batterId: batter.id,
        situationCategory,
      },
      strategy: {
        repertoireProbabilities,
        selectedPitch: selectedPitch.name,
        dynamicModifier: +(1.0 + (this.rng() * 0.4 - 0.2)).toFixed(2),
        strategyName: strategyDecision.strategy_name,
        rationale: strategyDecision.rationale,
      },
      intent: {
        targetX,
        targetZ,
        intendedZone: intendedZoneCategory,
        targetSpeedMph: selectedPitch.velocity_mph,
        isManualOverride,
      },
      execution: {
        realizedX: execution.realizedX,
        realizedZ: execution.realizedZ,
        realizedSpeedMph: +(selectedPitch.velocity_mph + (this.rng() * 2.4 - 1.2)).toFixed(1),
        radialMissInches: execution.radialMissInches,
        deltaXInches: execution.deltaXInches,
        deltaZInches: execution.deltaZInches,
        sigmaXFeet: execution.sigmaFeet,
        sigmaZFeet: execution.sigmaFeet,
        isHeartZoneLeak,
        hitShadowZoneTarget,
        realizedZoneCategory: realizedCategory,
      },
      result: {
        call: pitchResult === 'BALL'
          ? 'BALL'
          : pitchResult === 'CALLED_STRIKE'
            ? 'CALLED_STRIKE'
            : pitchResult === 'SWINGING_STRIKE'
              ? 'SWINGING_STRIKE'
              : pitchResult === 'FOUL'
                ? 'FOUL'
                : 'IN_PLAY',
        isStrike: isRulebookStrike(execution.realizedX, execution.realizedZ),
        exitVelocityMph: exitVelo ? +exitVelo.toFixed(1) : undefined,
        launchAngleDeg: launchAngle ? +launchAngle.toFixed(1) : undefined,
        description,
      },
    };

    const pitchDetails: PitchDetails = {
      pitch_name: selectedPitch.name,
      velocity_mph: selectedPitch.velocity_mph,
      spin_rpm: selectedPitch.spin_rpm,
      intended_zone: intended,
      actual_zone: actualZone,
      batter_decision: didSwing ? 'SWING' : 'TAKE',
      pitch_result: pitchResult,
      exit_velocity_mph: exitVelo,
      launch_angle_deg: launchAngle,
      description,
      strategy_name: strategyDecision.strategy_name,
      command_quality: commandQuality as any,
      statcast: selectedPitch.statcast,
      gameday_packet: gamedayPacket,
    };

    this.currentGameState = updatedState;
    return { pitch_details: pitchDetails, game_state: updatedState };
  }

  // ─── State mutation (port of applyOutcomeToGameState) ────────────────────────

  private _applyOutcomeToGameState(result: PitchResultType, _exitVelo: number | undefined, isDoublePlayTurned: boolean): GameState {
    let { balls, strikes, outs, bases } = this.currentGameState;
    let scoreHome = this.currentGameState.score.home;
    let scoreAway = this.currentGameState.score.away;
    let inning = this.currentGameState.inning;
    let topBottom = this.currentGameState.top_bottom;
    let nextBatterNeeded = false;
    const batter = this.currentGameState.current_batter;

    if (isDoublePlayTurned) {
      outs += 2;
      bases = { ...bases, first: null };
      balls = 0;
      strikes = 0;
      nextBatterNeeded = true;
    } else {
      switch (result) {
        case 'BALL':
          balls += 1;
          if (balls >= 4) {
            balls = 0; strikes = 0; nextBatterNeeded = true;
            bases = this._advanceRunnersOnWalk(bases, batter);
          }
          break;
        case 'CALLED_STRIKE':
        case 'SWINGING_STRIKE':
          strikes += 1;
          if (strikes >= 3) {
            strikes = 0; balls = 0; outs += 1; nextBatterNeeded = true;
          }
          break;
        case 'FOUL':
          if (strikes < 2) strikes += 1;
          break;
        case 'IN_PLAY_OUT':
          balls = 0; strikes = 0; outs += 1; nextBatterNeeded = true;
          break;
        case 'SINGLE':
          balls = 0; strikes = 0; nextBatterNeeded = true;
          if (bases.third !== null) {
            if (topBottom === 'TOP') scoreAway += 1; else scoreHome += 1;
          }
          bases = { first: batterToPlayerSummary(batter), second: bases.first, third: bases.second };
          break;
        case 'DOUBLE':
          balls = 0; strikes = 0; nextBatterNeeded = true;
          {
            let runs = 0;
            if (bases.third) runs++;
            if (bases.second) runs++;
            if (bases.first) runs++;
            if (topBottom === 'TOP') scoreAway += runs; else scoreHome += runs;
          }
          bases = { first: null, second: batterToPlayerSummary(batter), third: null };
          break;
        case 'TRIPLE':
          balls = 0; strikes = 0; nextBatterNeeded = true;
          {
            const runs = countRunners(bases);
            if (topBottom === 'TOP') scoreAway += runs; else scoreHome += runs;
          }
          bases = { first: null, second: null, third: batterToPlayerSummary(batter) };
          break;
        case 'HOME_RUN':
          balls = 0; strikes = 0; nextBatterNeeded = true;
          {
            const runs = countRunners(bases) + 1;
            if (topBottom === 'TOP') scoreAway += runs; else scoreHome += runs;
          }
          bases = { first: null, second: null, third: null };
          break;
        case 'HIT_BY_PITCH':
          balls = 0; strikes = 0; nextBatterNeeded = true;
          bases = this._advanceRunnersOnWalk(bases, batter);
          break;
      }
    }

    // Inning transition
    if (outs >= 3) {
      outs = 0; balls = 0; strikes = 0;
      bases = { first: null, second: null, third: null };
      if (topBottom === 'TOP') {
        topBottom = 'BOT';
      } else {
        topBottom = 'TOP';
        inning += 1;
      }
    }

    // Next batter
    let nextBatter = batter;
    if (nextBatterNeeded) {
      this.yankeeBatterIndex = (this.yankeeBatterIndex + 1) % this.yankeesBatters.length;
      nextBatter = this.yankeesBatters[this.yankeeBatterIndex];
    }

    const updatedPitcherStats: PitcherGameStats = {
      ...this.currentGameState.current_pitcher.stats,
      pitches_thrown: this.currentGameState.current_pitcher.stats.pitches_thrown + 1,
    };

    const nextState: GameState = {
      ...this.currentGameState,
      inning,
      top_bottom: topBottom,
      outs,
      balls,
      strikes,
      score: { home: scoreHome, away: scoreAway },
      bases,
      current_batter: nextBatter,
      current_pitcher: { ...this.currentGameState.current_pitcher, stats: updatedPitcherStats },
      game_over: inning > 9 && outs >= 3,
    };

    return { ...nextState, strategy_intent: this.calculateStrategyAndIntent(nextState) };
  }

  private _advanceRunnersOnWalk(bases: Bases, batter: BatterInfo): Bases {
    const summary = batterToPlayerSummary(batter);
    if (!bases.first) return { ...bases, first: summary };
    if (!bases.second) return { first: summary, second: bases.first, third: bases.third };
    if (!bases.third) return { first: summary, second: bases.first, third: bases.second };
    // Bases loaded walk — runner on 3rd scores
    if (this.currentGameState.top_bottom === 'TOP') {
      this.currentGameState = {
        ...this.currentGameState,
        score: { ...this.currentGameState.score, away: this.currentGameState.score.away + 1 },
      };
    } else {
      this.currentGameState = {
        ...this.currentGameState,
        score: { ...this.currentGameState.score, home: this.currentGameState.score.home + 1 },
      };
    }
    return { first: summary, second: bases.first, third: bases.second };
  }
}
