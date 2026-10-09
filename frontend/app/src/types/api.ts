import type { Gameday2DPitchPacket } from './gameday';
export * from './gameday';

// ─── Strike Zone Constants ────────────────────────────────────────────────────

export const STRIKE_ZONES = {
  // 9 Inner Zones (3×3 grid)
  UPPER_IN: 'upper-in',
  UPPER_MIDDLE: 'upper-middle',
  UPPER_AWAY: 'upper-away',
  MIDDLE_IN: 'middle-in',
  HEART: 'heart',
  MIDDLE_AWAY: 'middle-away',
  LOWER_IN: 'lower-in',
  LOWER_MIDDLE: 'lower-middle',
  LOWER_AWAY: 'lower-away',
  // 4 Chase Zones (outer boundary)
  CHASE_HIGH: 'chase-high',
  CHASE_LOW: 'chase-low',
  CHASE_IN: 'chase-in',
  CHASE_AWAY: 'chase-away',
} as const;

export type ZoneId = (typeof STRIKE_ZONES)[keyof typeof STRIKE_ZONES];

export const INNER_ZONES: ZoneId[] = [
  STRIKE_ZONES.UPPER_IN,
  STRIKE_ZONES.UPPER_MIDDLE,
  STRIKE_ZONES.UPPER_AWAY,
  STRIKE_ZONES.MIDDLE_IN,
  STRIKE_ZONES.HEART,
  STRIKE_ZONES.MIDDLE_AWAY,
  STRIKE_ZONES.LOWER_IN,
  STRIKE_ZONES.LOWER_MIDDLE,
  STRIKE_ZONES.LOWER_AWAY,
];

export const CHASE_ZONES: ZoneId[] = [
  STRIKE_ZONES.CHASE_HIGH,
  STRIKE_ZONES.CHASE_LOW,
  STRIKE_ZONES.CHASE_IN,
  STRIKE_ZONES.CHASE_AWAY,
];

export const ALL_ZONES: ZoneId[] = [...INNER_ZONES, ...CHASE_ZONES];

export const EDGE_ZONES: ZoneId[] = [
  STRIKE_ZONES.UPPER_IN,
  STRIKE_ZONES.UPPER_AWAY,
  STRIKE_ZONES.LOWER_IN,
  STRIKE_ZONES.LOWER_AWAY,
];

export function isStrike(zone: string): boolean {
  return INNER_ZONES.includes(zone as ZoneId);
}

export function isEdge(zone: string): boolean {
  return EDGE_ZONES.includes(zone as ZoneId);
}

// ─── Enums ────────────────────────────────────────────────────────────────────

export type PitchResultType =
  | 'BALL'
  | 'CALLED_STRIKE'
  | 'SWINGING_STRIKE'
  | 'FOUL'
  | 'IN_PLAY_OUT'
  | 'SINGLE'
  | 'DOUBLE'
  | 'TRIPLE'
  | 'HOME_RUN'
  | 'HIT_BY_PITCH';

export type BatterDecision = 'TAKE' | 'SWING';

export type PitchIntent = 'STRIKE' | 'CHASE' | 'WASTE' | 'CORNER' | 'BALL';

export type CommandQuality =
  | 'PINPOINT'
  | 'TARGET_EXECUTED'
  | 'SLIGHT_MISS'
  | 'MISTAKE_HANG'
  | 'WILD_MISS'
  | 'WASTE_EXECUTED';

// ─── Data Transfer Objects ────────────────────────────────────────────────────

export interface PlayerSummary {
  id: number;
  name: string;
  jersey_number: number;
  position: string;
  team: string;
}

export interface BatterGameStats {
  at_bats: number;
  hits: number;
  rbis: number;
  home_runs: number;
}

export interface BatterInfo {
  id: number;
  name: string;
  jersey_number: number;
  position: string;
  team: string;
  power: number;
  contact: number;
  vision: number;
  traits: string[];
  hot_zones: Record<string, number>;
  stats: BatterGameStats;
}

export interface StatcastMetrics {
  whiff_pct: number;
  chase_pct: number;
  gb_pct: number;
  stuff_plus: number;
  zone_pct: number;
  run_value: number;
}

export interface PitchArsenalItem {
  name: string;
  velocity_mph: number;
  spin_rpm: number;
  break_rating: number;
  control_rating: number;
  statcast: StatcastMetrics;
}

export interface PitcherGameStats {
  pitches_thrown: number;
  strikeouts: number;
  walks: number;
  hits_allowed: number;
  runs_allowed: number;
}

export interface PitcherInfo {
  id: number;
  name: string;
  jersey_number: number;
  position: string;
  team: string;
  break_rating: number;
  velocity_rating: number;
  arm_strength: number;
  control: number;
  arsenal: PitchArsenalItem[];
  stats: PitcherGameStats;
}

export interface Score {
  home: number;
  away: number;
}

export interface Bases {
  first: PlayerSummary | null;
  second: PlayerSummary | null;
  third: PlayerSummary | null;
}

export interface PitchOptionWeight {
  pitch_name: string;
  weight: number;
  probability_pct: number;
  rank: number;
  is_most_likely: boolean;
  is_least_likely: boolean;
  reasoning: string;
  statcast: StatcastMetrics;
}

export interface ZoneOptionWeight {
  zone: string;
  weight: number;
  probability_pct: number;
  rank: number;
  is_strike: boolean;
  zone_type: 'HOT_ZONE' | 'COLD_ZONE' | 'NEUTRAL_ZONE' | 'CHASE_ZONE';
  is_most_likely: boolean;
  is_least_likely: boolean;
}

export interface StrategyIntentDecision {
  strategy_name: string;
  situation_tag: 'BASES_LOADED' | 'DOUBLE_PLAY_SITUATION' | 'SCORING_POSITION' | 'BASES_EMPTY';
  count_context: string;
  rationale: string;
  recommended_pitch: string;
  recommended_zone: string;
  pitch_weights: PitchOptionWeight[];
  zone_weights: ZoneOptionWeight[];
  command_quality?: CommandQuality;
}

export interface GameState {
  inning: number;
  top_bottom: 'TOP' | 'BOT';
  outs: number;
  balls: number;
  strikes: number;
  score: Score;
  bases: Bases;
  current_batter: BatterInfo;
  current_pitcher: PitcherInfo;
  game_over: boolean;
  home_team: string;
  away_team: string;
  win_probability?: number;
  strategy_intent?: StrategyIntentDecision;
}

export interface PitchDetails {
  pitch_name: string;
  velocity_mph: number;
  spin_rpm: number;
  intended_zone?: string;
  actual_zone: string;
  batter_decision: BatterDecision;
  pitch_result: PitchResultType;
  exit_velocity_mph?: number;
  launch_angle_deg?: number;
  description: string;
  strategy_name?: string;
  command_quality?: CommandQuality;
  statcast?: StatcastMetrics;
  gameday_packet?: Gameday2DPitchPacket;
}

export interface PitchResultResponse {
  pitch_details: PitchDetails;
  game_state: GameState;
}

export interface ApiErrorResponse {
  status: string;
  error_code: string;
  message: string;
  details?: Record<string, string>;
  timestamp: string;
}

export interface LineupPlayer {
  batting_order: number;
  player: PlayerSummary;
  ratings: string;
}

export interface TeamLineup {
  team_id: number;
  team_name: string;
  lineup: LineupPlayer[];
}

export interface TeamRotation {
  team_id: number;
  team_name: string;
  starters: PlayerSummary[];
}

export interface InitialStateResponse {
  teams: string[];
  game: GameState | null;
  lineups: TeamLineup[];
  rotations: TeamRotation[];
}

// ─── Request Types ─────────────────────────────────────────────────────────────

export interface StartGameRequest {
  home_team_id: number;
  away_team_id: number;
  seed?: number;
}

export interface PitchRequest {
  pitch_intent?: string;
  target_zone?: string;
}

export interface SwapLineupRequest {
  team: number;
  pos1: number;
  pos2: number;
}

// ─── Error Type ────────────────────────────────────────────────────────────────

export class BaseballApiError extends Error {
  constructor(
    public readonly errorResponse: ApiErrorResponse,
    public readonly httpStatusCode: number = 400,
  ) {
    super(`[${errorResponse.error_code}] ${errorResponse.message}`);
    this.name = 'BaseballApiError';
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

export function batterToPlayerSummary(batter: BatterInfo): PlayerSummary {
  return {
    id: batter.id,
    name: batter.name,
    jersey_number: batter.jersey_number,
    position: batter.position,
    team: batter.team,
  };
}

export function countRunners(bases: Bases): number {
  return (bases.first ? 1 : 0) + (bases.second ? 1 : 0) + (bases.third ? 1 : 0);
}
