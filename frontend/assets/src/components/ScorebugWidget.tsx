import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Polygon } from 'react-native-svg';
import type { GameState, TeamLineup } from '../types/api';

// ─── Design Tokens ────────────────────────────────────────────────────────────

const TOKENS = {
  upperBg: '#16181D',
  gridBorder: '#2B2F38',
  pitcherFill: '#E2E8F0',
  batterFill: '#FFFFFF',
  baseOutline: '#94A3B8',
  activeGold: '#EAB308',
  upperText: '#FFFFFF',
  lowerText: '#0F172A',
  statsMuted: '#475569',
  cardBorder: '#2B2F38',
} as const;

interface ScorebugWidgetProps {
  gameState: GameState | null;
  lineups?: TeamLineup[];
}

function getTeamMonogram(teamName: string): { code: string; badgeBg: string } {
  const t = teamName.toLowerCase();
  if (t.includes('yankees') || t === 'nyy') {
    return { code: 'NYY', badgeBg: '#001C43' };
  }
  if (t.includes('mets') || t === 'nym') {
    return { code: 'NYM', badgeBg: '#002D72' };
  }
  if (t.includes('red sox') || t === 'bos') {
    return { code: 'BOS', badgeBg: '#BD3039' };
  }
  if (t.includes('dodgers') || t === 'lad') {
    return { code: 'LAD', badgeBg: '#005A9C' };
  }
  return {
    code: teamName.slice(0, 3).toUpperCase(),
    badgeBg: '#334155',
  };
}

function extractSurname(name?: string, fallback = 'PLAYER'): string {
  if (!name) return fallback;
  const parts = name.trim().split(' ');
  return (parts[parts.length - 1] ?? fallback).toUpperCase();
}

/**
 * ScorebugWidget — Professional MLB TV broadcast scorebug rectangle.
 * Dimensions: ~250px × 110px.
 *
 * Upper Block:
 *   - Left (50%): Away / Home Team rows (Monogram 60% | Score 40%)
 *   - Right (50%): 2×2 Situation Grid (Bases | Inning / Outs | Count)
 *
 * Lower Ribbon:
 *   - Pitcher Strip (~20px, #E2E8F0): Pitcher surname + Pitch count (P: XX)
 *   - Batter Strip (~18px, #FFFFFF): Order + Batter surname + PA stat/split
 */
export function ScorebugWidget({ gameState, lineups = [] }: ScorebugWidgetProps) {
  // ─── Extract Game State Data with Safe Fallbacks ────────────────────────────

  const awayTeam = gameState?.away_team ?? 'New York Yankees';
  const homeTeam = gameState?.home_team ?? 'New York Mets';
  const awayScore = gameState?.score.away ?? 0;
  const homeScore = gameState?.score.home ?? 0;

  const awayMonogram = getTeamMonogram(awayTeam);
  const homeMonogram = getTeamMonogram(homeTeam);

  const inningNum = gameState?.inning ?? 1;
  const isTop = gameState?.top_bottom !== 'BOT';
  const inningArrow = isTop ? '▲' : '▼';

  const balls = gameState?.balls ?? 0;
  const strikes = gameState?.strikes ?? 0;
  const outs = gameState?.outs ?? 0;

  const firstOccupied = Boolean(gameState?.bases.first);
  const secondOccupied = Boolean(gameState?.bases.second);
  const thirdOccupied = Boolean(gameState?.bases.third);

  // ─── Pitcher Strip Data ───────────────────────────────────────────────────

  const currentPitcher = gameState?.current_pitcher;
  const pitcherSurname = extractSurname(currentPitcher?.name, 'PITCHER');
  const pitchesThrown = currentPitcher?.stats?.pitches_thrown ?? 0;

  // ─── Batter Strip Data ────────────────────────────────────────────────────

  const currentBatter = gameState?.current_batter;
  const batterSurname = extractSurname(currentBatter?.name, 'BATTER');

  // Determine batting order from active lineup
  let battingOrderNum = 2; // Default realistic slot
  if (gameState && lineups.length > 0) {
    const isAwayBatting = gameState.top_bottom === 'TOP';
    const activeTeamName = isAwayBatting ? gameState.away_team : gameState.home_team;
    const activeTeamLineup = lineups.find(l =>
      l.team_name.toLowerCase().includes(activeTeamName.toLowerCase()) ||
      activeTeamName.toLowerCase().includes(l.team_name.toLowerCase())
    );

    if (activeTeamLineup && currentBatter) {
      const entry = activeTeamLineup.lineup.find(
        lp => lp.player.id === currentBatter.id || lp.player.name === currentBatter.name
      );
      if (entry) {
        battingOrderNum = entry.batting_order;
      }
    }
  }

  // Calculate batter game stat string
  let batterStatText = '.000 AVG';
  if (currentBatter?.stats) {
    const { at_bats, hits, home_runs } = currentBatter.stats;
    if (home_runs > 0) {
      batterStatText = `${hits}-${at_bats}, ${home_runs} HR`;
    } else if (at_bats > 0) {
      const avg = (hits / at_bats).toFixed(3).replace(/^0/, '');
      batterStatText = `${hits}-${at_bats} (${avg})`;
    } else {
      batterStatText = '0-0';
    }
  }

  return (
    <View style={styles.cardContainer}>
      {/* ── Upper Block: Teams & Situation (72px) ─────────────────────────── */}
      <View style={styles.upperBlock}>
        {/* Left Column (50%): Away / Home Team Rows & Scores */}
        <View style={styles.leftColumn}>
          {/* Away Team Row */}
          <View style={[styles.teamRow, styles.teamRowTop]}>
            <View style={styles.teamCell}>
              <View style={[styles.monogramBadge, { backgroundColor: awayMonogram.badgeBg }]}>
                <Text style={styles.monogramText}>{awayMonogram.code}</Text>
              </View>
            </View>
            <View style={styles.cellDivider} />
            <View style={styles.scoreCell}>
              <Text style={styles.scoreText}>{awayScore}</Text>
            </View>
          </View>

          {/* Home Team Row */}
          <View style={styles.teamRow}>
            <View style={styles.teamCell}>
              <View style={[styles.monogramBadge, { backgroundColor: homeMonogram.badgeBg }]}>
                <Text style={styles.monogramText}>{homeMonogram.code}</Text>
              </View>
            </View>
            <View style={styles.cellDivider} />
            <View style={styles.scoreCell}>
              <Text style={styles.scoreText}>{homeScore}</Text>
            </View>
          </View>
        </View>

        {/* Column Divider */}
        <View style={styles.columnDivider} />

        {/* Right Column (50%): Bases & Situation (2×2 Grid) */}
        <View style={styles.rightColumn}>
          {/* Top Row: Bases (Left) | Inning (Right) */}
          <View style={styles.situationRow}>
            {/* Top-Left: SVG Base Diamond Trio */}
            <View style={styles.basesCell}>
              <Svg width={30} height={20} viewBox="0 0 30 20">
                {/* 2nd Base (Top Center) */}
                <Polygon
                  points="15,2 19,6 15,10 11,6"
                  fill={secondOccupied ? TOKENS.activeGold : 'transparent'}
                  stroke={secondOccupied ? TOKENS.activeGold : TOKENS.baseOutline}
                  strokeWidth={1.4}
                />
                {/* 3rd Base (Bottom Left) */}
                <Polygon
                  points="7,9 11,13 7,17 3,13"
                  fill={thirdOccupied ? TOKENS.activeGold : 'transparent'}
                  stroke={thirdOccupied ? TOKENS.activeGold : TOKENS.baseOutline}
                  strokeWidth={1.4}
                />
                {/* 1st Base (Bottom Right) */}
                <Polygon
                  points="23,9 27,13 23,17 19,13"
                  fill={firstOccupied ? TOKENS.activeGold : 'transparent'}
                  stroke={firstOccupied ? TOKENS.activeGold : TOKENS.baseOutline}
                  strokeWidth={1.4}
                />
              </Svg>
            </View>

            {/* Top-Right: Inning Arrow + Numeral */}
            <View style={styles.inningCell}>
              <Text style={styles.inningArrow}>{inningArrow}</Text>
              <Text style={styles.inningNum}>{inningNum}</Text>
            </View>
          </View>

          {/* Bottom Row: Outs (Left) | Count (Right) */}
          <View style={styles.situationRow}>
            {/* Bottom-Left: Two Inline Out Pips */}
            <View style={styles.outsCell}>
              <View
                style={[
                  styles.outPip,
                  outs >= 1 ? styles.outPipActive : styles.outPipInactive,
                ]}
              />
              <View
                style={[
                  styles.outPip,
                  outs >= 2 ? styles.outPipActive : styles.outPipInactive,
                ]}
              />
            </View>

            {/* Bottom-Right: B-S Count */}
            <View style={styles.countCell}>
              <Text style={styles.countText}>{`${balls}-${strikes}`}</Text>
            </View>
          </View>
        </View>
      </View>

      {/* ── Lower Ribbon: Pitcher & Batter Data ───────────────────────────── */}
      <View style={styles.lowerRibbon}>
        {/* Pitcher Strip (Height ~20px, #E2E8F0) */}
        <View style={styles.pitcherStrip}>
          <Text style={styles.pitcherName} numberOfLines={1}>
            {pitcherSurname}
          </Text>
          <Text style={styles.pitchCount}>P: {pitchesThrown}</Text>
        </View>

        {/* Batter Strip (Height ~18px, #FFFFFF) */}
        <View style={styles.batterStrip}>
          <Text style={styles.batterName} numberOfLines={1}>
            {battingOrderNum}. {batterSurname}
          </Text>
          <Text style={styles.batterStat} numberOfLines={1}>
            {batterStatText}
          </Text>
        </View>
      </View>
    </View>
  );
}

// ─── Stylesheet ───────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  cardContainer: {
    width: 250,
    height: 110,
    backgroundColor: TOKENS.upperBg,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: TOKENS.cardBorder,
    overflow: 'hidden',
    alignSelf: 'center',
    marginTop: 2,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.35,
    shadowRadius: 5,
    elevation: 6,
  },

  // ─── Upper Block (72px) ────────────────────────────────────────────────────
  upperBlock: {
    flex: 1, // Fills ~72px above the 38px lower ribbon
    flexDirection: 'row',
    backgroundColor: TOKENS.upperBg,
  },

  // Left Column (50%)
  leftColumn: {
    flex: 1,
    flexDirection: 'column',
  },
  teamRow: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  teamRowTop: {
    borderBottomWidth: 1,
    borderBottomColor: TOKENS.gridBorder,
  },
  teamCell: {
    flex: 0.6,
    paddingLeft: 8,
    justifyContent: 'center',
  },
  monogramBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 3,
    alignSelf: 'flex-start',
  },
  monogramText: {
    color: TOKENS.upperText,
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  cellDivider: {
    width: 1,
    height: '100%',
    backgroundColor: TOKENS.gridBorder,
  },
  scoreCell: {
    flex: 0.4,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scoreText: {
    color: TOKENS.upperText,
    fontSize: 16,
    fontWeight: '900',
    includeFontPadding: false,
  },

  columnDivider: {
    width: 1,
    height: '100%',
    backgroundColor: TOKENS.gridBorder,
  },

  // Right Column (50%)
  rightColumn: {
    flex: 1,
    flexDirection: 'column',
    paddingHorizontal: 8,
    paddingVertical: 4,
    justifyContent: 'space-around',
  },
  situationRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },

  // Top-Left (Bases)
  basesCell: {
    alignItems: 'center',
    justifyContent: 'center',
  },

  // Top-Right (Inning)
  inningCell: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  inningArrow: {
    color: TOKENS.activeGold,
    fontSize: 10,
    fontWeight: '900',
  },
  inningNum: {
    color: TOKENS.upperText,
    fontSize: 14,
    fontWeight: '900',
    includeFontPadding: false,
  },

  // Bottom-Left (Outs)
  outsCell: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingLeft: 4,
  },
  outPip: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  outPipActive: {
    backgroundColor: TOKENS.activeGold,
  },
  outPipInactive: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: TOKENS.baseOutline,
  },

  // Bottom-Right (Count)
  countCell: {
    alignItems: 'flex-end',
  },
  countText: {
    color: TOKENS.upperText,
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 0.5,
    fontVariant: ['tabular-nums'],
    includeFontPadding: false,
  },

  // ─── Lower Ribbon (38px Total) ─────────────────────────────────────────────
  lowerRibbon: {
    flexDirection: 'column',
  },
  pitcherStrip: {
    height: 20,
    backgroundColor: TOKENS.pitcherFill,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 8,
  },
  pitcherName: {
    color: TOKENS.lowerText,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  pitchCount: {
    color: TOKENS.lowerText,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  batterStrip: {
    height: 18,
    backgroundColor: TOKENS.batterFill,
    borderTopWidth: 1,
    borderTopColor: '#CBD5E1',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 8,
  },
  batterName: {
    color: TOKENS.lowerText,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  batterStat: {
    color: TOKENS.statsMuted,
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
});
