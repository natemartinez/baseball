import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import type {
  GameState,
  PitchResultType,
  ResolvedPitchDetails,
  TeamLineup,
} from '../types/api';
import { ScorebugWidget } from './ScorebugWidget';
import { Colors } from '../theme/colors';
import type { ControlMode } from '../store/gameStore';

interface ScoreboardControlsWidgetProps {
  gameState: GameState | null;
  lineups?: TeamLineup[];
  latestPitch?: ResolvedPitchDetails | null;
  onOpenSettings?: () => void;
  activeSeed?: number | null;
  controlMode?: ControlMode;
  onOpenBattingDrill?: () => void;
}

/**
 * Core UI Component 3: Scoreboard & Game Controls
 * Stadium ticker and settings.
 *
 * Ported from ScoreboardControlsWidget.kt.
 */
export function ScoreboardControlsWidget({
  gameState,
  lineups = [],
  latestPitch,
  onOpenSettings,
  activeSeed = null,
  controlMode,
  onOpenBattingDrill,
}: ScoreboardControlsWidgetProps) {
  const gameOver = gameState?.game_over ?? false;
  const resultColor = latestPitch
    ? pitchResultColor(latestPitch.pitch_result)
    : Colors.textMuted;

  return (
    <View style={styles.container}>
      {/* Top row: settings and mode chips */}
      <View style={styles.headerRow}>
        <View style={styles.headerActions}>
          {onOpenSettings && (
            <TouchableOpacity
              onPress={onOpenSettings}
              style={styles.settingsBtn}
              activeOpacity={0.75}
              accessibilityLabel="Open settings menu"
            >
              <Text style={styles.settingsBtnText}>⚙️ SETTINGS</Text>
            </TouchableOpacity>
          )}
          {controlMode === 'BATTING' && (
            <TouchableOpacity
              style={styles.battingChip}
              onPress={onOpenBattingDrill}
              activeOpacity={0.75}
            >
              <Text style={styles.battingChipText} numberOfLines={1}>
                🏏 BATTING
              </Text>
            </TouchableOpacity>
          )}
          {activeSeed !== null && (
            <View style={styles.seedChip}>
              <Text style={styles.seedChipText} numberOfLines={1}>
                🌱 SEED {activeSeed}
              </Text>
            </View>
          )}
        </View>
      </View>

      {/* Broadcast Scorebug */}
      <ScorebugWidget gameState={gameState} lineups={lineups} />

      {/* Latest pitch result */}
      {latestPitch && (
        <View style={[styles.resultRow, { borderColor: `${resultColor}66` }]}>
          <View style={styles.resultHeader}>
            <View style={[styles.resultDot, { backgroundColor: resultColor }]} />
            <Text style={[styles.resultLabel, { color: resultColor }]} numberOfLines={1}>
              {latestPitch.pitch_result.replace(/_/g, ' ')}
            </Text>
          </View>
          <Text style={styles.resultMeta} numberOfLines={1}>
            {latestPitch.pitch_name} • {latestPitch.velocity_mph} mph
          </Text>
        </View>
      )}

      {/* Game Over / Inactive Status */}
      {gameOver && (
        <View style={styles.gameOverBanner}>
          <Text style={styles.gameOverText}>GAME OVER • FINAL</Text>
        </View>
      )}
      {!gameState && (
        <View style={styles.inactiveBox}>
          <Text style={styles.inactiveText}>Game Inactive – Press Reset to Initialize</Text>
        </View>
      )}
    </View>
  );
}

function pitchResultColor(result: PitchResultType): string {
  switch (result) {
    case 'HOME_RUN':
      return Colors.red;
    case 'DOUBLE':
    case 'TRIPLE':
      return Colors.redLight;
    case 'SINGLE':
      return Colors.green;
    case 'SWINGING_STRIKE':
      return '#FF9100';
    case 'CALLED_STRIKE':
      return Colors.amber;
    case 'FOUL':
      return '#FFEA00';
    case 'BALL':
      return Colors.greenDark;
    case 'IN_PLAY_OUT':
      return Colors.textMuted;
    case 'HIT_BY_PITCH':
      return '#AB47BC';
    default:
      return Colors.textMuted;
  }
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    minHeight: 150,
    backgroundColor: 'transparent',
    borderRadius: 12,
    borderWidth: 0,
    padding: 10,
    gap: 6,
  },
  headerRow: { flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center' },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  settingsBtn: {
    backgroundColor: Colors.bgInput,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.borderSecondary,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  settingsBtnText: { fontSize: 9, fontWeight: '800', color: Colors.textPrimary, letterSpacing: 0.5 },
  seedChip: {
    maxWidth: 150,
    backgroundColor: 'rgba(6, 182, 212, 0.15)',
    borderWidth: 1,
    borderColor: '#06B6D4',
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 3,
  },
  seedChipText: { fontSize: 9, fontWeight: '800', color: '#67E8F9' },
  battingChip: {
    backgroundColor: 'rgba(255, 179, 0, 0.16)',
    borderWidth: 1,
    borderColor: '#FFB300',
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 3,
  },
  battingChipText: { fontSize: 9, fontWeight: '900', color: '#FFD54F' },
  resultRow: {
    alignSelf: 'flex-start',
    maxWidth: 280,
    borderWidth: 1,
    borderRadius: 6,
    backgroundColor: Colors.bgInput,
    paddingHorizontal: 8,
    paddingVertical: 4,
    gap: 2,
  },
  resultHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  resultDot: { width: 8, height: 8, borderRadius: 4 },
  resultLabel: { fontSize: 10, fontWeight: '900', letterSpacing: 0.4 },
  resultMeta: { fontSize: 10, color: Colors.textSecondary },
  inactiveBox: { backgroundColor: Colors.bgInput, borderRadius: 8, height: 44, alignItems: 'center', justifyContent: 'center' },
  inactiveText: { color: Colors.textMuted, fontSize: 12 },
  gameOverBanner: { backgroundColor: 'rgba(239, 68, 68, 0.15)', borderRadius: 8, borderWidth: 1, borderColor: '#EF4444', height: 36, alignItems: 'center', justifyContent: 'center' },
  gameOverText: { color: '#EF4444', fontSize: 12, fontWeight: '900', letterSpacing: 0.8 },
});
