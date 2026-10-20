import React from 'react';
import { View, Text, TouchableOpacity, Switch, StyleSheet } from 'react-native';
import type {
  GameState,
  PitchDetails,
  PitchResultType,
  TeamLineup,
} from '../types/api';
import { ScorebugWidget } from './ScorebugWidget';
import { Colors } from '../theme/colors';

interface ScoreboardControlsWidgetProps {
  gameState: GameState | null;
  lineups?: TeamLineup[];
  latestPitch?: PitchDetails | null;
  isMockMode: boolean;
  onOpenSettings?: () => void;
  onToggleMock: (value: boolean) => void;
}

/**
 * Core UI Component 3: Scoreboard & Game Controls
 * Stadium ticker, settings, and the Mock/Live toggle.
 *
 * Ported from ScoreboardControlsWidget.kt.
 */
export function ScoreboardControlsWidget({
  gameState,
  lineups = [],
  latestPitch,
  isMockMode,
  onOpenSettings,
  onToggleMock,
}: ScoreboardControlsWidgetProps) {
  const gameOver = gameState?.game_over ?? false;
  const resultColor = latestPitch
    ? pitchResultColor(latestPitch.pitch_result)
    : Colors.textMuted;

  return (
    <View style={styles.container}>
      {/* Top row: settings + mock toggle */}
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
          <View style={styles.toggleRow}>
            <Text style={[styles.toggleLabel, { color: isMockMode ? Colors.greenLight : '#FFB74D' }]}>
              {isMockMode ? 'MOCK ENGINE' : 'LIVE FLASK API'}
            </Text>
            <Switch
              value={isMockMode}
              onValueChange={onToggleMock}
              trackColor={{ false: '#E65100', true: '#1B5E20' }}
              thumbColor={isMockMode ? Colors.green : '#FF9800'}
            />
          </View>
        </View>
      </View>

      {/* Broadcast Scorebug */}
      <ScorebugWidget gameState={gameState} lineups={lineups} />

      {/* Latest pitch result */}
      {latestPitch && (
        <View style={[styles.resultRow, { borderColor: `${resultColor}66` }]}>
          <View style={[styles.resultDot, { backgroundColor: resultColor }]} />
          <Text style={[styles.resultLabel, { color: resultColor }]} numberOfLines={1}>
            {latestPitch.pitch_result.replace(/_/g, ' ')}
          </Text>
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
  toggleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  toggleLabel: { fontSize: 10, fontWeight: '700' },
  resultRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderWidth: 1,
    borderRadius: 6,
    backgroundColor: Colors.bgInput,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  resultDot: { width: 8, height: 8, borderRadius: 4 },
  resultLabel: { fontSize: 10, fontWeight: '900', letterSpacing: 0.4 },
  resultMeta: { flex: 1, fontSize: 10, color: Colors.textSecondary },
  inactiveBox: { backgroundColor: Colors.bgInput, borderRadius: 8, height: 44, alignItems: 'center', justifyContent: 'center' },
  inactiveText: { color: Colors.textMuted, fontSize: 12 },
  gameOverBanner: { backgroundColor: 'rgba(239, 68, 68, 0.15)', borderRadius: 8, borderWidth: 1, borderColor: '#EF4444', height: 36, alignItems: 'center', justifyContent: 'center' },
  gameOverText: { color: '#EF4444', fontSize: 12, fontWeight: '900', letterSpacing: 0.8 },
});
