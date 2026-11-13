import type {
  BatterDecision,
  BattingDrillEntry,
  GameState,
  InitialStateResponse,
  PitchDetails,
  PitchResolveResponse,
  PitchResultResponse,
  PitchThrowResponse,
  PitchRequest,
  ResolvePitchRequest,
  StartGameRequest,
  SwapLineupRequest,
  SwapRotationRequest,
  SwingContactReport,
  ApiErrorResponse,
  TeamsResponse,
  TeamRosterResponse,
  TimingTier,
} from '../types/api';
import { BaseballApiError } from '../types/api';
import type { Gameday2DPitchPacket } from '../types/gameday';
import {
  classifyGamedayZone,
  getZoneNominalTarget,
  getMaxErrorRadiusInches,
  isRulebookStrike,
  determineSituationCategory,
} from './gamedayMath';
import { calculateStrategyAndIntent } from './strategyEngine';
import {
  defaultRelease,
  movementForPitch,
  type PitcherHand,
} from './pitchTrajectory';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import type { IGameService } from './IGameService';

export function resolveApiBaseUrl(baseUrlOverride?: string): string {
  const envUrl = process.env['EXPO_PUBLIC_API_URL'] || process.env['API_BASE_URL'];
  const candidate = (baseUrlOverride || envUrl || '').trim();

  // If candidate is a remote/custom host (not localhost or loopback), respect it directly
  if (candidate && !candidate.includes('localhost') && !candidate.includes('127.0.0.1')) {
    return candidate.replace(/\/$/, '');
  }

  // On Web, localhost works natively in the browser
  if (Platform.OS === 'web') {
    return (candidate || 'http://localhost:5050').replace(/\/$/, '');
  }

  // In Expo Go or development builds on physical devices / simulators,
  // hostUri holds the Metro server's IP (e.g. "192.168.1.215:8081")
  const hostUri =
    Constants.expoConfig?.hostUri ||
    (Constants as { manifest2?: { extra?: { expoClient?: { hostUri?: string } } } })?.manifest2
      ?.extra?.expoClient?.hostUri;

  if (hostUri) {
    const host = hostUri.split(':')[0];
    if (host) {
      return `http://${host}:5050`;
    }
  }

  // Android emulator loopback fallback
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:5050';
  }

  return (candidate || 'http://localhost:5050').replace(/\/$/, '');
}

/**
 * HTTP Game Service — calls the authoritative Python Flask API.
 * Mirrors Kotlin HttpGameService / Retrofit BaseballApi.
 */
export class HttpGameService implements IGameService {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = resolveApiBaseUrl(baseUrl);
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  setBaseUrl(url: string): void {
    this.baseUrl = url.endsWith('/') ? url.slice(0, -1) : url;
  }

  private url(path: string): string {
    return `${this.baseUrl}/${path}`;
  }

  private timestamp(): string {
    return new Date().toISOString();
  }

  private async parseError(response: Response): Promise<BaseballApiError> {
    try {
      const body = await response.text();
      if (body) {
        const parsed: ApiErrorResponse = JSON.parse(body);
        return new BaseballApiError(parsed, response.status);
      }
    } catch {
      // fall through
    }
    return new BaseballApiError(
      {
        status: 'error',
        error_code: `HTTP_${response.status}`,
        message: response.statusText || 'Network error',
        timestamp: this.timestamp(),
      },
      response.status,
    );
  }

  private async get<T>(path: string): Promise<T> {
    const response = await fetch(this.url(path), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      throw await this.parseError(response);
    }
    return response.json() as Promise<T>;
  }

  private async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(this.url(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      throw await this.parseError(response);
    }
    return response.json() as Promise<T>;
  }

  async getState(): Promise<InitialStateResponse> {
    const res = await this.get<InitialStateResponse>('api/state');
    if (res.game) this.ensureStrategyIntent(res.game);
    return res;
  }

  async getTeams(includePlayers: boolean = false): Promise<TeamsResponse> {
    const query = includePlayers ? '?include_players=true' : '';
    return this.get<TeamsResponse>(`api/teams${query}`);
  }

  async getTeamSelection(): Promise<TeamsResponse> {
    return this.get<TeamsResponse>('api/teams/selection');
  }

  async getTeamRoster(teamIdOrName: number | string, season: number = 2026): Promise<TeamRosterResponse> {
    const param = typeof teamIdOrName === 'number' ? `team_id=${teamIdOrName}` : `team_name=${encodeURIComponent(teamIdOrName)}`;
    return this.get<TeamRosterResponse>(`api/rosters?${param}&season=${season}`);
  }

  async startGame(
    homeTeamId: number = 1,
    awayTeamId: number = 2,
    seed?: number,
  ): Promise<GameState> {
    const body: StartGameRequest = { home_team_id: homeTeamId, away_team_id: awayTeamId };
    if (seed !== undefined) body.seed = seed;
    const state = await this.post<GameState>('api/start_game', body);
    this.ensureStrategyIntent(state);
    return state;
  }

  async pitch(
    pitchName?: string,
    targetZone?: string,
    customTarget?: { x: number; z: number },
  ): Promise<PitchResultResponse> {
    const body = this.buildPitchBody(pitchName, targetZone, customTarget);
    const res = await this.post<PitchResultResponse>('api/pitch', body);
    this.ensureStrategyIntent(res.game_state);
    this.ensureGamedayPacket(res, customTarget);
    return res;
  }

  async throwPitch(
    pitchName?: string,
    targetZone?: string,
    customTarget?: { x: number; z: number },
    timingTier?: TimingTier,
    timingLabel?: string,
    pitchEffectiveness?: number,
  ): Promise<PitchThrowResponse> {
    const body = this.buildPitchBody(pitchName, targetZone, customTarget, timingTier, timingLabel, pitchEffectiveness);
    const res = await this.post<PitchThrowResponse>('api/pitch/throw', body);
    this.ensureStrategyIntent(res.game_state);
    this.ensureGamedayPacket(res, customTarget);
    return res;
  }

  async startPractice(): Promise<InitialStateResponse> {
    const res = await this.post<InitialStateResponse>('api/practice/start', {});
    this.ensureStrategyIntent(res.game ?? undefined);
    return res;
  }

  async practiceThrowPitch(entry: BattingDrillEntry): Promise<PitchThrowResponse> {
    const res = await this.post<PitchThrowResponse>('api/practice/pitch/throw', {
      pitch_name: entry.pitchName,
      target_zone: entry.targetZone,
      target_x: entry.targetX,
      target_z: entry.targetZ,
    });
    this.ensureStrategyIntent(res.game_state);
    this.ensureGamedayPacket(res);
    return res;
  }

  async practiceResolvePitch(options?: {
    batterDecision?: BatterDecision;
    batterApproach?: string;
    contact?: SwingContactReport;
  }): Promise<PitchResolveResponse> {
    const body: ResolvePitchRequest = {};
    if (options?.batterDecision) body.batter_decision = options.batterDecision;
    if (options?.batterApproach) body.batter_approach = options.batterApproach;
    if (options?.contact) body.contact = options.contact;
    const res = await this.post<PitchResolveResponse>(
      'api/practice/pitch/resolve',
      body,
    );
    this.ensureStrategyIntent(res.game_state);
    if (res.pitch_details) {
      this.ensureGamedayPacket({
        pitch_details: res.pitch_details,
        game_state: res.game_state,
      });
    }
    return res;
  }

  async endPractice(): Promise<InitialStateResponse> {
    const res = await this.post<InitialStateResponse>('api/practice/end', {});
    this.ensureStrategyIntent(res.game ?? undefined);
    return res;
  }

  async resolvePitch(
    batterDecision?: BatterDecision,
    batterApproach?: string,
    contact?: SwingContactReport,
  ): Promise<PitchResolveResponse> {
    const body: ResolvePitchRequest = {};
    if (batterDecision) body.batter_decision = batterDecision;
    if (batterApproach) body.batter_approach = batterApproach;
    if (contact) body.contact = contact;
    const res = await this.post<PitchResolveResponse>('api/pitch/resolve', body);
    this.ensureStrategyIntent(res.game_state);
    if (res.pitch_details) {
      this.ensureGamedayPacket(
        { pitch_details: res.pitch_details, game_state: res.game_state },
      );
    }
    return res;
  }

  private buildPitchBody(
    pitchName?: string,
    targetZone?: string,
    customTarget?: { x: number; z: number },
    timingTier?: TimingTier,
    timingLabel?: string,
    pitchEffectiveness?: number,
  ): PitchRequest {
    const body: PitchRequest = {};
    if (pitchName) {
      body.selection_mode = 'user';
      body.pitch_name = pitchName;
    } else {
      body.selection_mode = 'ai';
    }
    if (targetZone) body.target_zone = targetZone;
    if (customTarget) {
      body.target_x = customTarget.x;
      body.target_z = customTarget.z;
    }
    if (timingTier) body.timing_tier = timingTier;
    if (timingLabel) body.timing_label = timingLabel;
    if (pitchEffectiveness != null) body.pitch_effectiveness = pitchEffectiveness;
    return body;
  }

  async simAtBat(): Promise<PitchResultResponse> {
    const res = await this.post<PitchResultResponse>('api/sim_at_bat');
    this.ensureStrategyIntent(res.game_state);
    this.ensureGamedayPacket(res);
    return res;
  }

  private ensureStrategyIntent(game?: GameState) {
    if (game && !game.strategy_intent) {
      game.strategy_intent = calculateStrategyAndIntent(game);
    }
  }

  private ensureGamedayPacket(
    res: { pitch_details: PitchDetails; game_state: GameState },
    customTarget?: { x: number; z: number },
  ) {
    if (!res.pitch_details.gameday_packet) {
      const p = res.pitch_details;
      const g = res.game_state;
      const nominal = getZoneNominalTarget(p.intended_zone || 'heart');
      const targetX = customTarget?.x ?? nominal.x;
      const targetZ = customTarget?.z ?? nominal.z;
      const intendedCategory = customTarget ? classifyGamedayZone(targetX, targetZ) : nominal.category;

      const raw = p as any;
      const realizedX = typeof raw.location_x === 'number' ? raw.location_x : nominal.x;
      const realizedZ = typeof raw.location_y === 'number' ? raw.location_y : nominal.z;
      const deltaXFeet = realizedX - targetX;
      const deltaZFeet = realizedZ - targetZ;
      const radialMissInches = +(Math.sqrt(deltaXFeet * deltaXFeet + deltaZFeet * deltaZFeet) * 12).toFixed(1);
      const realizedCategory = classifyGamedayZone(realizedX, realizedZ);

      const pitcherHand: PitcherHand = g.current_pitcher?.throws === 'L' ? 'L' : 'R';
      const release = g.current_pitcher?.release ?? defaultRelease(pitcherHand);
      const movement = movementForPitch(p.pitch_name);
      const commandRating = g.current_pitcher?.control ?? 82;
      const maxRadiusInches = getMaxErrorRadiusInches(commandRating);

      const sitCategory = determineSituationCategory(
        g.balls,
        g.strikes,
        g.outs,
        g.bases.first !== null,
        g.bases.second !== null,
        g.bases.third !== null,
      );

      p.gameday_packet = {
        meta: {
          pitchNumber: g.current_pitcher?.stats.pitches_thrown ?? 1,
          pitcherName: g.current_pitcher?.name ?? 'Pitcher',
          pitcherHand,
          pitcherOvr: 85,
          commandRating,
          staminaPct: 80,
          pitchesThrown: g.current_pitcher?.stats.pitches_thrown ?? 1,
          inning: g.inning,
          isTopInning: g.top_bottom === 'TOP',
          count: { balls: g.balls, strikes: g.strikes, outs: g.outs },
          runnersOnBase: {
            first: g.bases.first !== null,
            second: g.bases.second !== null,
            third: g.bases.third !== null,
          },
          batterName: g.current_batter?.name ?? 'Batter',
          batterId: g.current_batter?.id ?? 1,
          situationCategory: sitCategory,
        },
        release,
        strategy: {
          repertoireProbabilities: { [p.pitch_name]: 0.5 },
          selectedPitch: p.pitch_name,
          dynamicModifier: 1.0,
          strategyName: p.strategy_name ?? 'NEUTRAL_ATTACK',
          rationale: p.description,
        },
        intent: {
          targetX,
          targetZ,
          intendedZone: intendedCategory,
          targetSpeedMph: p.velocity_mph,
          isManualOverride: !!customTarget,
        },
        execution: {
          realizedX,
          realizedZ,
          realizedSpeedMph: p.velocity_mph,
          releaseSpeedMph: p.velocity_mph,
          horizontalBreakInches: movement.hb,
          inducedVerticalBreakInches: movement.ivb,
          maxRadiusInches,
          radialMissInches,
          deltaXInches: +(deltaXFeet * 12).toFixed(1),
          deltaZInches: +(deltaZFeet * 12).toFixed(1),
          sigmaXFeet: 0.25,
          sigmaZFeet: 0.25,
          isHeartZoneLeak: intendedCategory !== 'HEART' && realizedCategory === 'HEART',
          hitShadowZoneTarget: intendedCategory === 'SHADOW' && realizedCategory === 'SHADOW',
          realizedZoneCategory: realizedCategory,
          abilityTier: (res as any).execution?.ability_tier ?? (res as any).execution?.abilityTier,
          timingTier: (res as any).execution?.timing_tier ?? (res as any).execution?.timingTier,
          timingLabel: (res as any).execution?.timing_label ?? (res as any).execution?.timingLabel,
          baseRadiusInches: (res as any).execution?.base_radius_inches ?? (res as any).execution?.baseRadiusInches,
          executedRadiusInches: (res as any).execution?.executed_radius_inches ?? (res as any).execution?.executedRadiusInches,
        },
        result: {
          call: p.pitch_result === null
            ? null
            : p.pitch_result === 'BALL'
              ? 'BALL'
              : p.pitch_result === 'CALLED_STRIKE'
                ? 'CALLED_STRIKE'
                : p.pitch_result === 'SWINGING_STRIKE'
                  ? 'SWINGING_STRIKE'
                  : p.pitch_result === 'FOUL'
                    ? 'FOUL'
                    : 'IN_PLAY',
          isStrike: isRulebookStrike(realizedX, realizedZ),
          exitVelocityMph: p.exit_velocity_mph,
          launchAngleDeg: p.launch_angle_deg,
          description: p.description,
        },
      };
    }
    const exec = (res as any).execution || res.pitch_details.execution;
    if (exec && res.pitch_details.gameday_packet?.execution) {
      const gExec = res.pitch_details.gameday_packet.execution;
      if (!gExec.abilityTier) gExec.abilityTier = exec.ability_tier ?? exec.abilityTier;
      if (!gExec.timingTier) gExec.timingTier = exec.timing_tier ?? exec.timingTier;
      if (!gExec.timingLabel) gExec.timingLabel = exec.timing_label ?? exec.timingLabel;
      if (gExec.baseRadiusInches === undefined) gExec.baseRadiusInches = exec.base_radius_inches ?? exec.baseRadiusInches;
      if (gExec.executedRadiusInches === undefined) gExec.executedRadiusInches = exec.executed_radius_inches ?? exec.executedRadiusInches;
    }
  }

  async reset(seed?: number): Promise<InitialStateResponse> {
    const body = seed !== undefined ? { seed } : undefined;
    return this.post<InitialStateResponse>('api/reset', body);
  }

  async swapLineup(team: number, pos1: number, pos2: number): Promise<void> {
    const body: SwapLineupRequest = { team, pos1, pos2 };
    await this.post<unknown>('api/swap_lineup', body);
  }

  async swapRotation(team: number, pos1: number, pos2: number): Promise<void> {
    const body: SwapRotationRequest = { team, pos1, pos2 };
    await this.post<unknown>('api/swap_rotation', body);
  }
}
