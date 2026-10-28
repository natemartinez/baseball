import React from 'react';
import {
  View,
  Text,
  Modal,
  Platform,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { useGameStore } from '../store/gameStore';
import { Colors } from '../theme/colors';

interface SettingsMenuItem {
  key: string;
  icon: string;
  label: string;
  description: string;
  accent: string;
  disabled?: boolean;
  pending?: boolean;
  onPress: () => void;
}

/**
 * SettingsMenuModal — Central hub for game controls and management screens.
 *
 * Visibility is controlled by the store's isSettingsMenuOpen / toggleSettingsMenu
 * (mirrors the StrategyMenuModal pattern). Holds the AI Strategy & Pitch Decider,
 * Gameday Dev Menu, Sim At-Bat, Reset Game, Lineups, and Rotation/Bullpen entries.
 */
export function SettingsMenuModal() {
  const {
    isSettingsMenuOpen,
    toggleSettingsMenu,
    toggleStrategyMenu,
    toggleDevMenu,
    simAtBat,
    resetGame,
    setLineupDialogOpen,
    setRotationDialogOpen,
    togglePitchFeed,
    toggleTrajectory,
    gamedayLog,
    isPitching,
    controlMode,
    battingDrill,
    setBattingDrillOpen,
  } = useGameStore();

  function close() {
    toggleSettingsMenu(false);
  }

  function run(action: () => void) {
    close();
    action();
  }

  const items: SettingsMenuItem[] = [
    {
      key: 'strategy-decider',
      icon: '🎯',
      label: 'AI STRATEGY & PITCH DECIDER',
      description: 'Rationale, ranked pitch weights & recommended target',
      accent: Colors.amber,
      onPress: () => run(() => toggleStrategyMenu(true)),
    },
    {
      key: 'dev-menu',
      icon: '⚡',
      label: 'GAMEDAY DEV MENU',
      description: 'Statcast 2D cross-section & calibration pipeline',
      accent: Colors.gameday.accentCyan,
      onPress: () => run(() => toggleDevMenu(true)),
    },
    {
      key: 'batting-practice',
      icon: '🏏',
      label: battingDrill?.active ? 'BATTING DRILL' : 'BATTING PRACTICE',
      description:
        Platform.OS !== 'web'
          ? 'Web only'
          : battingDrill?.active
            ? 'Pause / edit the current drill playlist'
            : 'Build a pitch/location playlist for the AI',
      accent: Colors.gameday.accentCyan,
      disabled: Platform.OS !== 'web',
      onPress: () => run(() => setBattingDrillOpen(true)),
    },
    {
      key: 'sim-at-bat',
      icon: '⏩',
      label: 'SIM AT-BAT',
      description:
        controlMode === 'BATTING' || battingDrill?.active
          ? 'Disabled in Batting Practice'
          : 'Auto-play the current plate appearance',
      accent: Colors.blue,
      disabled:
        isPitching ||
        controlMode === 'BATTING' ||
        Boolean(battingDrill?.active),
      pending: isPitching,
      onPress: () => run(() => simAtBat()),
    },
    {
      key: 'reset-game',
      icon: '↺',
      label: 'RESET GAME',
      description: 'Restart with fresh rosters, score, and count',
      accent: Colors.redLight,
      disabled: isPitching,
      onPress: () => run(() => resetGame()),
    },
    {
      key: 'lineups',
      icon: '📋',
      label: 'LINEUPS & ROSTER',
      description: 'Batting order and defensive alignment swaps',
      accent: Colors.amber,
      onPress: () => run(() => setLineupDialogOpen(true)),
    },
    {
      key: 'rotation-bullpen',
      icon: '🔄',
      label: 'ROTATION & BULLPEN',
      description: 'Starting rotation order and bullpen depth chart',
      accent: Colors.greenLight,
      onPress: () => run(() => setRotationDialogOpen(true)),
    },
    {
      key: 'pitch-feed',
      icon: '📊',
      label: 'PITCH-BY-PITCH FEED',
      description: 'Statcast telemetry & play-by-play log',
      accent: Colors.blueLight,
      onPress: () => run(() => togglePitchFeed(true)),
    },
    {
      key: 'pitch-trajectory',
      icon: '🎞️',
      label: 'PITCH TRAJECTORY (3D)',
      description: 'Pitch path from the mound to the plate',
      accent: Colors.cyan,
      onPress: () => run(() => toggleTrajectory(true)),
    },
  ];

  return (
    <Modal
      visible={isSettingsMenuOpen}
      transparent
      animationType="fade"
      onRequestClose={close}
    >
      <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={close}>
        <TouchableOpacity activeOpacity={1} style={styles.dialog}>
          {/* Header */}
          <View style={styles.headerRow}>
            <View style={styles.headerLeft}>
              <Text style={styles.headerIcon}>⚙️</Text>
              <View>
                <Text style={styles.title}>SETTINGS & CONTROLS</Text>
                <Text style={[styles.modeLabel, { color: Colors.greenLight }]}>
                  LIVE FLASK API
                </Text>
              </View>
            </View>
            <TouchableOpacity
              onPress={close}
              style={styles.closeBtn}
              accessibilityLabel="Close settings menu"
            >
              <Text style={styles.closeBtnText}>✕ CLOSE</Text>
            </TouchableOpacity>
          </View>

          {/* Menu Items */}
          <ScrollView
            style={styles.body}
            contentContainerStyle={styles.bodyContent}
            showsVerticalScrollIndicator={false}
          >
            {items.map((item) => (
              <SettingsMenuRow key={item.key} item={item} />
            ))}

            {gamedayLog.length > 0 && (
              <Text style={styles.footerMeta}>
                {gamedayLog.length} pitch packet{gamedayLog.length === 1 ? '' : 's'} logged this session
              </Text>
            )}
          </ScrollView>
        </TouchableOpacity>
      </TouchableOpacity>
    </Modal>
  );
}

// ─── Menu Row ────────────────────────────────────────────────────────────────

function SettingsMenuRow({ item }: { item: SettingsMenuItem }) {
  return (
    <TouchableOpacity
      onPress={item.onPress}
      disabled={item.disabled}
      activeOpacity={0.75}
      style={[
        styles.row,
        { borderColor: item.accent },
        item.disabled && styles.rowDisabled,
      ]}
    >
      <View style={[styles.iconWrap, { backgroundColor: `${item.accent}22` }]}>
        <Text style={styles.icon}>{item.icon}</Text>
      </View>

      <View style={styles.rowTextGroup}>
        <Text style={[styles.rowLabel, { color: item.accent }]}>{item.label}</Text>
        <Text style={styles.rowDescription}>{item.description}</Text>
      </View>

      {item.pending ? (
        <ActivityIndicator size="small" color={item.accent} />
      ) : (
        <Text style={styles.chevron}>›</Text>
      )}
    </TouchableOpacity>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  dialog: {
    backgroundColor: Colors.bgDeep,
    borderRadius: 16,
    width: '100%',
    maxWidth: 480,
    maxHeight: '88%',
    padding: 14,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerIcon: {
    fontSize: 18,
  },
  title: {
    fontSize: 13,
    fontWeight: '900',
    color: '#FFF',
    letterSpacing: 1.0,
  },
  modeLabel: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.5,
    marginTop: 1,
  },
  closeBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
  },
  closeBtnText: {
    fontSize: 10,
    fontWeight: '800',
    color: Colors.textSecondary,
  },
  body: {
    flexShrink: 1,
  },
  bodyContent: {
    gap: 8,
    paddingBottom: 4,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: Colors.bgCard,
    borderRadius: 10,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  rowDisabled: {
    opacity: 0.45,
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  icon: {
    fontSize: 17,
  },
  rowTextGroup: {
    flex: 1,
    gap: 2,
  },
  rowLabel: {
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 0.6,
  },
  rowDescription: {
    fontSize: 11,
    color: Colors.textSecondary,
  },
  chevron: {
    fontSize: 22,
    color: Colors.textMuted,
    fontWeight: '700',
  },
  footerMeta: {
    fontSize: 10,
    color: Colors.textMuted,
    textAlign: 'center',
    marginTop: 2,
  },
});
