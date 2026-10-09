import type {
  GameState,
  InitialStateResponse,
  PitchResultResponse,
  PitchRequest,
  StartGameRequest,
  SwapLineupRequest,
  ApiErrorResponse,
} from '../types/api';
import { BaseballApiError } from '../types/api';
import type { Gameday2DPitchPacket } from '../types/gameday';
import {
  classifyGamedayZone,
  getZoneNominalTarget,
  isRulebookStrike,
  determineSituationCategory,
} from './gamedayMath';
import { calculateStrategyAndIntent } from './strategyEngine';
import type { IGameService } from './IGameService';

/**
 * HTTP Game Service — calls the live server.js Node backend.
 * Mirrors Kotlin HttpGameService / Retrofit BaseballApi.
 */
export class HttpGameService implements IGameService {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    const defaultUrl = typeof window !== 'undefined' ? 'http://localhost:5000' : 'http://10.0.2.2:5000';
    this.baseUrl = (baseUrl || defaultUrl).replace(/\/$/, '');
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
    pitchIntent?: string,
    targetZone?: string,
    customTarget?: { x: number; z: number },
  ): Promise<PitchResultResponse> {
    const body: PitchRequest & { target_x?: number; target_z?: number } = {};
    if (pitchIntent) body.pitch_intent = pitchIntent;
    if (targetZone) body.target_zone = targetZone;
    if (customTarget) {
      body.target_x = customTarget.x;
      body.target_z = customTarget.z;
    }
    const res = await this.post<PitchResultResponse>('api/pitch', body);
    this.ensureStrategyIntent(res.game_state);
    this.ensureGamedayPacket(res, customTarget);
    return res;
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

  private ensureGamedayPacket(res: PitchResultResponse, customTarget?: { x: number; z: number }) {
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
          pitcherOvr: 85,
          commandRating: g.current_pitcher?.control ?? 70,
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
          radialMissInches,
          deltaXInches: +(deltaXFeet * 12).toFixed(1),
          deltaZInches: +(deltaZFeet * 12).toFixed(1),
          sigmaXFeet: 0.25,
          sigmaZFeet: 0.25,
          isHeartZoneLeak: intendedCategory !== 'HEART' && realizedCategory === 'HEART',
          hitShadowZoneTarget: intendedCategory === 'SHADOW' && realizedCategory === 'SHADOW',
          realizedZoneCategory: realizedCategory,
        },
        result: {
          call: p.pitch_result === 'BALL'
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
  }

  async reset(): Promise<InitialStateResponse> {
    return this.post<InitialStateResponse>('api/reset');
  }

  async swapLineup(team: number, pos1: number, pos2: number): Promise<void> {
    const body: SwapLineupRequest = { team, pos1, pos2 };
    await this.post<unknown>('api/swap_lineup', body);
  }
}
