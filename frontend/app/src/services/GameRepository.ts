import { MockGameService } from './MockGameService';
import { HttpGameService } from './HttpGameService';
import type { IGameService } from './IGameService';

/**
 * GameRepository — transparent service switcher.
 * Reads USE_MOCK from environment to decide which implementation to inject.
 *
 * Usage:
 *   const repo = GameRepository.getInstance();
 *   await repo.getState();
 */
export class GameRepository implements IGameService {
  private static _instance: GameRepository | null = null;
  private readonly _mockService: MockGameService;
  private readonly _httpService: HttpGameService;
  private _isMockMode: boolean;

  private constructor(useMock: boolean, baseUrl?: string) {
    this._mockService = new MockGameService();
    const defaultBaseUrl = typeof window !== 'undefined' ? 'http://localhost:5000' : 'http://10.0.2.2:5000';
    this._httpService = new HttpGameService(baseUrl ?? process.env['API_BASE_URL'] ?? defaultBaseUrl);
    this._isMockMode = useMock;
  }

  /** Get or create the singleton repository. */
  static getInstance(useMock?: boolean, baseUrl?: string): GameRepository {
    if (!GameRepository._instance) {
      // Default: check process.env or fall back to mock
      const shouldUseMock = useMock ?? (process.env['USE_MOCK'] !== 'false');
      GameRepository._instance = new GameRepository(shouldUseMock, baseUrl);
    }
    return GameRepository._instance;
  }

  /** Force reset (useful for testing). */
  static reset(): void {
    GameRepository._instance = null;
  }

  get isMockMode(): boolean {
    return this._isMockMode;
  }

  setMockMode(enabled: boolean): void {
    this._isMockMode = enabled;
  }

  getBackendUrl(): string {
    return this._httpService.getBaseUrl();
  }

  setBackendUrl(url: string): void {
    this._httpService.setBaseUrl(url);
  }

  private get activeService(): IGameService {
    return this._isMockMode ? this._mockService : this._httpService;
  }

  getState() { return this.activeService.getState(); }
  startGame(homeTeamId?: number, awayTeamId?: number, seed?: number) {
    return this.activeService.startGame(homeTeamId, awayTeamId, seed);
  }
  pitch(pitchIntent?: string, targetZone?: string, customTarget?: { x: number; z: number }) {
    return this.activeService.pitch(pitchIntent, targetZone, customTarget);
  }
  simAtBat() {
    return this.activeService.simAtBat();
  }
  reset() { return this.activeService.reset(); }
  swapLineup(team: number, pos1: number, pos2: number) { return this.activeService.swapLineup(team, pos1, pos2); }
}
