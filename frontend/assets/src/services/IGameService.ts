import type {
  GameState,
  InitialStateResponse,
  PitchResultResponse,
} from '../types/api';

/**
 * Interface contract for Baseball Simulation Engine operations.
 * Allows transparent swapping between HttpGameService and MockGameService.
 */
export interface IGameService {
  getState(): Promise<InitialStateResponse>;
  startGame(homeTeamId?: number, awayTeamId?: number, seed?: number): Promise<GameState>;
  pitch(pitchIntent?: string, targetZone?: string, customTarget?: { x: number; z: number }): Promise<PitchResultResponse>;
  simAtBat(): Promise<PitchResultResponse>;
  reset(): Promise<InitialStateResponse>;
  swapLineup(team: number, pos1: number, pos2: number): Promise<void>;
}
