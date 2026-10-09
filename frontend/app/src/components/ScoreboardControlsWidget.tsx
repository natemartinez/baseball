import React from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator, Switch, StyleSheet } from 'react-native';
import type { GameState, TeamLineup } from '../types/api';
import { ScorebugWidget } from './ScorebugWidget';
import { Colors } from '../theme/colors';

interface ScoreboardControlsWidgetProps {
  gameState: GameState | null;
  lineups?: TeamLineup[];
  isActionPending: boolean;
  isMockMode: boolean;
  selectedPitchIntent: string;
  selectedTargetZone: string | null;
  gamedayCount?: number;
  onThrowPitch: () => void;
  onSimAtBat: () => void;
  onResetGame: () => void;
  onOpenLineup: () => void;
  onOpenDevMenu?: () => void;
  onToggleMock: (value: boolean) => void;
}

/**
 * Core UI Component 3: Scoreboard & Game Controls
 * Stadium ticker, "Throw Pitch", "Sim At-Bat", "Reset Game", and Mock toggle.
 *
 * Ported from ScoreboardControlsWidget.kt.
 */
export function ScoreboardControlsWidget({
  gameState,
  lineups = [],
  isActionPending,
  isMockMode,
  selectedPitchIntent,
  selectedTargetZone,
  gamedayCount = 0,
  onThrowPitch,
  onSimAtBat,
  onResetGame,
  onOpenLineup,
  onOpenDevMenu,
  onToggleMock,
}: ScoreboardControlsWidgetProps) {
  const gameOver = gameState?.game_over ?? false;
  const actionsDisabled = isActionPending || gameOver;

  return (
    <View style={styles.container}>
      {/* Uppermost Element: Broadcast Scorebug */}
      <ScorebugWidget gameState={gameState} lineups={lineups} />

      {/* Header row: stadium label + mock toggle */}
      <View style={styles.headerRow}>
        <Text style={styles.stadiumLabel}>CITI FIELD • SUBWAY SERIES</Text>
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

      {/* Next pitch intent + zone pill */}
      <View style={styles.intentPill}>
        <View style={styles.intentHalf}>
          <Text style={styles.intentMeta}>Next Pitch:</Text>
          <Text style={styles.intentValue}>{selectedPitchIntent || '—'}</Text>
        </View>
        <View style={styles.intentHalf}>
          <Text style={styles.intentMeta}>Zone:</Text>
          <Text style={[styles.intentValue, { color: Colors.amberLight }]}>{selectedTargetZone || '—'}</Text>
        </View>
      </View>

      {/* Primary buttons */}
      <View style={styles.primaryRow}>
        <TouchableOpacity
          onPress={onThrowPitch}
          disabled={actionsDisabled}
          style={[styles.throwBtn, actionsDisabled && styles.btnDisabled]}
          activeOpacity={0.8}
        >
          {isActionPending ? (
            <ActivityIndicator size="small" color="#000" />
          ) : (
            <Text style={styles.throwBtnText}>THROW PITCH</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          onPress={onSimAtBat}
          disabled={actionsDisabled}
          style={[styles.simBtn, actionsDisabled && styles.btnDisabled]}
          activeOpacity={0.8}
        >
          <Text style={styles.simBtnText}>SIM AT-BAT</Text>
        </TouchableOpacity>
      </View>

      {/* Secondary buttons */}
      <View style={styles.secondaryRow}>
        <TouchableOpacity
          onPress={onOpenLineup}
          style={styles.outlineBtn}
          activeOpacity={0.8}
        >
          <Text style={styles.outlineBtnText}>LINEUPS & ROSTER</Text>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={onResetGame}
          disabled={isActionPending}
          style={[styles.outlineBtn, isActionPending && styles.btnDisabled]}
          activeOpacity={0.8}
        >
          <Text style={[styles.outlineBtnText, { color: Colors.redMild }]}>RESET GAME</Text>
        </TouchableOpacity>
      </View>

      {/* Dev Menu trigger row */}
      {onOpenDevMenu && (
        <TouchableOpacity
          onPress={onOpenDevMenu}
          style={styles.devMenuBtn}
          activeOpacity={0.8}
        >
          <View style={styles.devMenuInner}>
            <Text style={styles.devMenuIcon}>⚡</Text>
            <Text style={styles.devMenuText}>GAMEDAY DEV MENU & CALIBRATION</Text>
          </View>
          {gamedayCount > 0 && (
            <View style={styles.devMenuBadge}>
              <Text style={styles.devMenuBadgeText}>{gamedayCount}</Text>
            </View>
          )}
        </TouchableOpacity>
      )}
    </View>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bgSurface,
    borderRadius: 12,
    padding: 14,
    gap: 12,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  stadiumLabel: { fontSize: 9, fontWeight: '700', color: Colors.textSecondary, letterSpacing: 1.0, textTransform: 'uppercase' },
  toggleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  toggleLabel: { fontSize: 10, fontWeight: '700' },
  inactiveBox: { backgroundColor: Colors.bgInput, borderRadius: 8, height: 44, alignItems: 'center', justifyContent: 'center' },
  inactiveText: { color: Colors.textMuted, fontSize: 12 },
  gameOverBanner: { backgroundColor: 'rgba(239, 68, 68, 0.15)', borderRadius: 8, borderWidth: 1, borderColor: '#EF4444', height: 36, alignItems: 'center', justifyContent: 'center' },
  gameOverText: { color: '#EF4444', fontSize: 12, fontWeight: '900', letterSpacing: 0.8 },
  // Intent pill
  intentPill: { backgroundColor: Colors.bgInput, borderRadius: 8, flexDirection: 'row', paddingHorizontal: 10, paddingVertical: 6, justifyContent: 'space-between' },
  intentHalf: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  intentMeta: { fontSize: 11, color: Colors.textMuted },
  intentValue: { fontSize: 12, fontWeight: '700', color: Colors.blue },
  // Buttons
  primaryRow: { flexDirection: 'row', gap: 8 },
  throwBtn: { flex: 1.3, backgroundColor: '#00C853', borderRadius: 8, height: 44, alignItems: 'center', justifyContent: 'center' },
  throwBtnText: { fontSize: 13, fontWeight: '900', color: '#000', letterSpacing: 0.5 },
  simBtn: { flex: 1, backgroundColor: '#1976D2', borderRadius: 8, height: 44, alignItems: 'center', justifyContent: 'center' },
  simBtnText: { fontSize: 12, fontWeight: '700', color: '#FFF' },
  secondaryRow: { flexDirection: 'row', gap: 8 },
  outlineBtn: { flex: 1, borderRadius: 8, borderWidth: 1, borderColor: Colors.textSecondary, height: 38, alignItems: 'center', justifyContent: 'center' },
  outlineBtnText: { fontSize: 11, fontWeight: '600', color: Colors.textSecondary },
  btnDisabled: { opacity: 0.45 },
  devMenuBtn: {
    backgroundColor: '#0F172A',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#06B6D4',
    paddingVertical: 10,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 2,
  },
  devMenuInner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  devMenuIcon: {
    fontSize: 14,
  },
  devMenuText: {
    color: '#06B6D4',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.6,
  },
  devMenuBadge: {
    backgroundColor: 'rgba(6, 182, 212, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#06B6D4',
  },
  devMenuBadgeText: {
    color: '#06B6D4',
    fontSize: 10,
    fontWeight: '900',
  },
});
