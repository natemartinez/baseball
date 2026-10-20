import React from 'react';
import { View, Text, Modal, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { useGameStore } from '../store/gameStore';
import { StrategyDeciderWidget } from './StrategyDeciderWidget';
import { StrikeZoneGridWidget } from './StrikeZoneGridWidget';
import { Colors } from '../theme/colors';

/**
 * StrategyMenuModal — Overlay menu that hosts the AI Strategy & Pitch Decider.
 *
 * Visibility is controlled by the store's isStrategyMenuOpen / toggleStrategyMenu
 * (mirrors the GamedayDevMenuModal pattern). The current batter's strike zone is
 * shown at the top; when no strategy intent is available the modal shows an empty
 * state instead of the decider widget.
 */
export function StrategyMenuModal() {
  const {
    isStrategyMenuOpen,
    toggleStrategyMenu,
    gameState,
    selectedPitchIntent,
    setSelectedPitchIntent,
    selectedTargetZone,
    setSelectedTargetZone,
    latestPitch,
    pitchFeed,
    currentAtBatPitches,
  } = useGameStore();

  const strategyIntent = gameState?.strategy_intent ?? null;
  const currentBatter = gameState?.current_batter;

  return (
    <Modal
      visible={isStrategyMenuOpen}
      transparent
      animationType="fade"
      onRequestClose={() => toggleStrategyMenu(false)}
    >
      <TouchableOpacity
        style={styles.overlay}
        activeOpacity={1}
        onPress={() => toggleStrategyMenu(false)}
      >
        <TouchableOpacity activeOpacity={1} style={styles.dialog}>
          <View style={styles.headerRow}>
            <View style={styles.headerLeft}>
              <View style={styles.radarDot} />
              <Text style={styles.title}>STRATEGY MENU</Text>
            </View>
            <TouchableOpacity
              onPress={() => toggleStrategyMenu(false)}
              style={styles.closeBtn}
              accessibilityLabel="Close strategy menu"
            >
              <Text style={styles.closeBtnText}>✕ CLOSE</Text>
            </TouchableOpacity>
          </View>

          <ScrollView
            style={styles.body}
            contentContainerStyle={styles.bodyContent}
            showsVerticalScrollIndicator={false}
          >
            {/* Current batter's strike zone */}
            {currentBatter && (
              <StrikeZoneGridWidget
                selectedZone={selectedTargetZone ?? ''}
                onSelectZone={setSelectedTargetZone}
                currentBatter={currentBatter}
                latestPitch={latestPitch ?? pitchFeed[0]}
                atBatPitches={currentAtBatPitches}
              />
            )}

            {strategyIntent ? (
              <StrategyDeciderWidget
                strategyIntent={strategyIntent}
                selectedPitchIntent={selectedPitchIntent}
                onSelectPitchIntent={setSelectedPitchIntent}
              />
            ) : (
              <View style={styles.emptyBox}>
                <Text style={styles.emptyText}>
                  No strategy available. Load the game or press Reset to initialize.
                </Text>
              </View>
            )}
          </ScrollView>
        </TouchableOpacity>
      </TouchableOpacity>
    </Modal>
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
  radarDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.green,
  },
  title: {
    fontSize: 13,
    fontWeight: '900',
    color: '#FFF',
    letterSpacing: 1.0,
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
    gap: 10,
    paddingBottom: 4,
  },
  emptyBox: {
    backgroundColor: Colors.bgInput,
    borderRadius: 10,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    color: Colors.textMuted,
    fontSize: 12,
    textAlign: 'center',
  },
});
