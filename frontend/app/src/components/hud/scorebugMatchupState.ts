/**
 * scorebugMatchupState.ts
 * Pure helpers and data formatting for Plate Matchup UI in Scorebug.
 */

export interface MatchupBatterInput {
  name?: string;
  position?: string;
  handedness?: 'R' | 'L' | 'S' | string;
  power?: number;
  contact?: number;
  vision?: number;
}

export interface MatchupPitcherInput {
  name?: string;
  position?: string;
  throws?: 'R' | 'L' | string;
  control?: number;
  break_rating?: number;
  velocity_rating?: number;
}

export interface FormattedMatchupPlayerInfo {
  batterName: string;
  pitcherName: string;
  batterMeta: string;
  pitcherMeta: string;
  batterStats: {
    pwr?: number;
    con?: number;
    vis?: number;
  };
  pitcherStats: {
    cmd?: number;
    brk?: number;
    vel?: number;
  };
}

/**
 * Formats full names, positions/handedness, and side-by-side stats
 * for the Plate Matchup UI without live selected pitch dependencies.
 */
export function formatMatchupPlayerInfo(
  batter?: MatchupBatterInput | null,
  pitcher?: MatchupPitcherInput | null,
): FormattedMatchupPlayerInfo {
  const batterName = batter?.name?.trim() || 'Batter';
  const pitcherName = pitcher?.name?.trim() || 'Pitcher';

  const batterMetaParts: string[] = [];
  if (batter?.position) {
    batterMetaParts.push(batter.position);
  }
  if (batter?.handedness) {
    const h = batter.handedness.toUpperCase();
    batterMetaParts.push(h.endsWith('HB') ? h : `${h}HB`);
  }
  const batterMeta = batterMetaParts.join(' • ');

  const pitcherMetaParts: string[] = [];
  if (pitcher?.position) {
    pitcherMetaParts.push(pitcher.position);
  }
  if (pitcher?.throws) {
    const t = pitcher.throws.toUpperCase();
    pitcherMetaParts.push(t.endsWith('HP') ? t : `${t}HP`);
  }
  const pitcherMeta = pitcherMetaParts.join(' • ');

  return {
    batterName,
    pitcherName,
    batterMeta,
    pitcherMeta,
    batterStats: {
      pwr: batter?.power,
      con: batter?.contact,
      vis: batter?.vision,
    },
    pitcherStats: {
      cmd: pitcher?.control,
      brk: pitcher?.break_rating,
      vel: pitcher?.velocity_rating,
    },
  };
}
