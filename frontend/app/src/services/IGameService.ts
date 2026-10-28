import type {
  BatterDecision,
  BattingDrillEntry,
  GameState,
  InitialStateResponse,
  PitchResolveResponse,
  PitchResultResponse,
  PitchThrowResponse,
  SwingContactReport,
  TeamsResponse,
  TeamRosterResponse,
} from '../types/api';

/** Interface contract for the authoritative Flask Baseball Simulation API. */
export interface IGameService {
  getState(): Promise<InitialStateResponse>;
  getTeams(): Promise<TeamsResponse>;
  getTeamRoster(teamIdOrName: number | string, season?: number): Promise<TeamRosterResponse>;
  startGame(homeTeamId?: number, awayTeamId?: number, seed?: number): Promise<GameState>;
  pitch(pitchIntent?: string, targetZone?: string, customTarget?: { x: number; z: number }): Promise<PitchResultResponse>;
  throwPitch(pitchIntent?: string, targetZone?: string, customTarget?: { x: number; z: number }): Promise<PitchThrowResponse>;
  resolvePitch(
    batterDecision?: BatterDecision,
    batterApproach?: string,
    contact?: SwingContactReport,
  ): Promise<PitchResolveResponse>;
  simAtBat(): Promise<PitchResultResponse>;
  reset(seed?: number): Promise<InitialStateResponse>;

  // Batting Practice sandbox
  startPractice(): Promise<InitialStateResponse>;
  practiceThrowPitch(entry: BattingDrillEntry): Promise<PitchThrowResponse>;
  practiceResolvePitch(options?: {
    batterDecision?: BatterDecision;
    batterApproach?: string;
    contact?: SwingContactReport;
  }): Promise<PitchResolveResponse>;
  endPractice(): Promise<InitialStateResponse>;

  swapLineup(team: number, pos1: number, pos2: number): Promise<void>;
  swapRotation(team: number, pos1: number, pos2: number): Promise<void>;
}
