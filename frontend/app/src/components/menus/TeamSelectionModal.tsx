import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { useGameStore } from '../../store/gameStore';
import { Colors } from '../../theme/colors';
import type { TeamDto } from '../../types/api';

/**
 * TeamSelectionModal — Team and Matchup Selection Dialog.
 *
 * Provides the interactive bridge to browse all teams and their full player rosters,
 * designate Home and Away teams, and initiate a new authoritative simulation via "Start Game".
 */
export function TeamSelectionModal() {
  const {
    isTeamSelectionOpen,
    toggleTeamSelection,
    availableTeams,
    loadAvailableTeams,
    selectedHomeTeamId,
    selectedAwayTeamId,
    setSelectedHomeTeamId,
    setSelectedAwayTeamId,
    startNewGame,
    loadingState,
  } = useGameStore();

  const [activeRosterTab, setActiveRosterTab] = useState<number>(0);

  useEffect(() => {
    if (isTeamSelectionOpen && availableTeams.length === 0) {
      loadAvailableTeams();
    }
  }, [isTeamSelectionOpen, availableTeams.length, loadAvailableTeams]);

  // Keep active roster tab within valid range of available teams
  const currentInspectTeam: TeamDto | undefined =
    availableTeams[activeRosterTab] ?? availableTeams[0];

  const homeTeam = availableTeams.find((t) => t.id === selectedHomeTeamId);
  const awayTeam = availableTeams.find((t) => t.id === selectedAwayTeamId);

  const isSameTeam =
    selectedHomeTeamId != null &&
    selectedAwayTeamId != null &&
    selectedHomeTeamId === selectedAwayTeamId;

  const canStartGame =
    selectedHomeTeamId != null &&
    selectedAwayTeamId != null &&
    !isSameTeam &&
    loadingState !== 'loading';

  function handleSwapMatchup() {
    if (selectedHomeTeamId != null && selectedAwayTeamId != null) {
      const prevHome = selectedHomeTeamId;
      setSelectedHomeTeamId(selectedAwayTeamId);
      setSelectedAwayTeamId(prevHome);
    }
  }

  function handleStartGame() {
    if (canStartGame) {
      startNewGame(selectedHomeTeamId, selectedAwayTeamId);
    }
  }

  return (
    <Modal
      visible={isTeamSelectionOpen}
      transparent
      animationType="fade"
      onRequestClose={() => toggleTeamSelection(false)}
    >
      <TouchableOpacity
        style={styles.overlay}
        activeOpacity={1}
        onPress={() => toggleTeamSelection(false)}
      >
        <TouchableOpacity activeOpacity={1} style={styles.dialog}>
          {/* Header */}
          <View style={styles.headerRow}>
            <View>
              <Text style={styles.title}>⚾ TEAMS & MATCHUP SELECTION</Text>
              <Text style={styles.subtitle}>
                Choose Home & Away teams, inspect rosters, and start game.
              </Text>
            </View>
            <TouchableOpacity
              onPress={() => toggleTeamSelection(false)}
              style={styles.closeBtn}
              accessibilityLabel="Close team selection"
            >
              <Text style={styles.closeText}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* Matchup Config Card */}
          <View style={styles.matchupCard}>
            <View style={styles.teamPickerCol}>
              <Text style={styles.pickerLabel}>AWAY (BATS 1ST)</Text>
              <View style={styles.pickerSelector}>
                {availableTeams.map((t) => {
                  const isSelected = t.id === selectedAwayTeamId;
                  return (
                    <TouchableOpacity
                      key={`away-${t.id}`}
                      onPress={() => setSelectedAwayTeamId(t.id)}
                      style={[
                        styles.teamChip,
                        isSelected && styles.teamChipAwaySelected,
                      ]}
                    >
                      <Text
                        style={[
                          styles.teamChipText,
                          isSelected && styles.teamChipTextSelected,
                        ]}
                        numberOfLines={1}
                      >
                        {t.name}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>

            <View style={styles.matchupDivider}>
              <Text style={styles.vsText}>@</Text>
              <TouchableOpacity
                onPress={handleSwapMatchup}
                style={styles.swapBtn}
                accessibilityLabel="Swap home and away"
              >
                <Text style={styles.swapBtnText}>🔄 SWAP</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.teamPickerCol}>
              <Text style={styles.pickerLabel}>HOME (FIELDS 1ST)</Text>
              <View style={styles.pickerSelector}>
                {availableTeams.map((t) => {
                  const isSelected = t.id === selectedHomeTeamId;
                  return (
                    <TouchableOpacity
                      key={`home-${t.id}`}
                      onPress={() => setSelectedHomeTeamId(t.id)}
                      style={[
                        styles.teamChip,
                        isSelected && styles.teamChipHomeSelected,
                      ]}
                    >
                      <Text
                        style={[
                          styles.teamChipText,
                          isSelected && styles.teamChipTextSelected,
                        ]}
                        numberOfLines={1}
                      >
                        {t.name}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
          </View>

          {isSameTeam && (
            <View style={styles.warningBanner}>
              <Text style={styles.warningText}>
                ⚠️ Home and Away must be different teams to begin simulation.
              </Text>
            </View>
          )}

          {/* Roster Inspection Tabs */}
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>ROSTER INSPECTOR</Text>
            <View style={styles.tabRow}>
              {availableTeams.map((t, idx) => {
                const isActive = idx === activeRosterTab;
                return (
                  <TouchableOpacity
                    key={`tab-${t.id}`}
                    onPress={() => setActiveRosterTab(idx)}
                    style={[styles.tab, isActive && styles.tabActive]}
                  >
                    <Text style={[styles.tabText, isActive && styles.tabTextActive]}>
                      {t.name}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          {/* Player Roster Content */}
          <ScrollView style={styles.rosterScroll} contentContainerStyle={styles.rosterContent}>
            {currentInspectTeam ? (
              <View style={styles.rosterSection}>
                <Text style={styles.groupTitle}>
                  📋 Lineup & Position Players ({currentInspectTeam.position_players?.length ?? 0})
                </Text>
                {currentInspectTeam.position_players && currentInspectTeam.position_players.length > 0 ? (
                  currentInspectTeam.position_players.map((p: any, idx: number) => {
                    const orderNum = p.batting_order ?? idx + 1;
                    return (
                      <View key={`pos-${p.id || idx}`} style={styles.playerRow}>
                        <View style={styles.orderBadge}>
                          <Text style={styles.orderBadgeText}>{orderNum}</Text>
                        </View>
                        <View style={styles.playerMeta}>
                          <Text style={styles.playerName}>
                            {p.name ?? `Player ${idx + 1}`} (#{p.number ?? p.jersey_number ?? 99})
                          </Text>
                          <Text style={styles.playerDetails}>
                            {p.position ?? 'DH'} • Power {p.ratings?.Power ?? 80} / Contact {p.ratings?.Contact ?? 80}
                          </Text>
                        </View>
                        <View style={styles.positionBadge}>
                          <Text style={styles.positionBadgeText}>{p.position ?? 'DH'}</Text>
                        </View>
                      </View>
                    );
                  })
                ) : (
                  <Text style={styles.emptyText}>Loading position players...</Text>
                )}

                <Text style={[styles.groupTitle, { marginTop: 12 }]}>
                  ⚾ Pitching Staff (Starters & Bullpen)
                </Text>
                {currentInspectTeam.pitchers?.starters && currentInspectTeam.pitchers.starters.length > 0 ? (
                  currentInspectTeam.pitchers.starters.map((sp: any, idx: number) => (
                    <View key={`sp-${sp.id || idx}`} style={styles.playerRow}>
                      <View style={[styles.orderBadge, styles.pitcherBadge]}>
                        <Text style={styles.orderBadgeText}>SP</Text>
                      </View>
                      <View style={styles.playerMeta}>
                        <Text style={styles.playerName}>
                          {sp.name ?? `Pitcher ${idx + 1}`} (#{sp.number ?? 26})
                        </Text>
                        <Text style={styles.playerDetails}>
                          Starting Pitcher • Control {sp.ratings?.Control ?? 82}
                        </Text>
                      </View>
                      <View style={[styles.positionBadge, styles.starterBadge]}>
                        <Text style={styles.positionBadgeText}>STARTER</Text>
                      </View>
                    </View>
                  ))
                ) : null}

                {currentInspectTeam.pitchers?.bullpen && currentInspectTeam.pitchers.bullpen.length > 0 ? (
                  currentInspectTeam.pitchers.bullpen.map((rp: any, idx: number) => (
                    <View key={`rp-${rp.id || idx}`} style={styles.playerRow}>
                      <View style={[styles.orderBadge, styles.bullpenBadge]}>
                        <Text style={styles.orderBadgeText}>RP</Text>
                      </View>
                      <View style={styles.playerMeta}>
                        <Text style={styles.playerName}>
                          {rp.name ?? `Reliever ${idx + 1}`} (#{rp.number ?? 99})
                        </Text>
                        <Text style={styles.playerDetails}>
                          Bullpen Reliever • Control {rp.ratings?.Control ?? 80}
                        </Text>
                      </View>
                      <View style={[styles.positionBadge, styles.relieverBadge]}>
                        <Text style={styles.positionBadgeText}>BULLPEN</Text>
                      </View>
                    </View>
                  ))
                ) : null}
              </View>
            ) : (
              <ActivityIndicator color={Colors.green} style={{ marginVertical: 20 }} />
            )}
          </ScrollView>

          {/* Action Row */}
          <View style={styles.footerRow}>
            <TouchableOpacity
              onPress={() => toggleTeamSelection(false)}
              style={styles.cancelBtn}
            >
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity
              onPress={handleStartGame}
              disabled={!canStartGame}
              style={[styles.startBtn, !canStartGame && styles.startBtnDisabled]}
              accessibilityRole="button"
              accessibilityLabel="Start game with selected teams"
            >
              {loadingState === 'loading' ? (
                <ActivityIndicator color="#000" size="small" />
              ) : (
                <Text style={styles.startBtnText}>
                  ⚾ START GAME: {awayTeam?.abbreviation ?? 'AWAY'} @ {homeTeam?.abbreviation ?? 'HOME'}
                </Text>
              )}
            </TouchableOpacity>
          </View>
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
    backgroundColor: Colors.bgSurface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    width: '100%',
    maxWidth: 560,
    maxHeight: '90%',
    padding: 16,
    gap: 12,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: 16,
    fontWeight: '900',
    color: '#FFF',
    letterSpacing: 0.5,
  },
  subtitle: {
    fontSize: 11,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  closeBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: Colors.bgInput,
  },
  closeText: {
    color: Colors.textSecondary,
    fontSize: 14,
    fontWeight: '700',
  },
  matchupCard: {
    flexDirection: 'row',
    backgroundColor: Colors.bgInput,
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: Colors.borderSecondary,
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  teamPickerCol: {
    flex: 1,
    gap: 6,
  },
  pickerLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: Colors.textMuted,
    letterSpacing: 0.5,
  },
  pickerSelector: {
    gap: 6,
  },
  teamChip: {
    paddingVertical: 6,
    paddingHorizontal: 8,
    borderRadius: 6,
    backgroundColor: Colors.bgCard,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
  },
  teamChipAwaySelected: {
    backgroundColor: 'rgba(64, 196, 255, 0.25)',
    borderColor: Colors.blue,
  },
  teamChipHomeSelected: {
    backgroundColor: 'rgba(0, 230, 118, 0.25)',
    borderColor: Colors.green,
  },
  teamChipText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.textSecondary,
  },
  teamChipTextSelected: {
    color: '#FFF',
    fontWeight: '800',
  },
  matchupDivider: {
    paddingHorizontal: 8,
    alignItems: 'center',
    gap: 4,
  },
  vsText: {
    fontSize: 16,
    fontWeight: '900',
    color: Colors.amber,
  },
  swapBtn: {
    paddingVertical: 4,
    paddingHorizontal: 6,
    borderRadius: 4,
    backgroundColor: Colors.bgCard,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
  },
  swapBtnText: {
    fontSize: 9,
    fontWeight: '800',
    color: Colors.textSecondary,
  },
  warningBanner: {
    backgroundColor: 'rgba(255, 23, 68, 0.15)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.redLight,
    padding: 8,
  },
  warningText: {
    fontSize: 11,
    color: Colors.redLight,
    fontWeight: '700',
    textAlign: 'center',
  },
  sectionHeader: {
    gap: 6,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: Colors.textMuted,
    letterSpacing: 0.5,
  },
  tabRow: {
    flexDirection: 'row',
    backgroundColor: Colors.bgInput,
    borderRadius: 8,
    overflow: 'hidden',
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
  },
  tabActive: {
    backgroundColor: Colors.bgCard,
    borderBottomWidth: 2,
    borderBottomColor: Colors.amber,
  },
  tabText: {
    fontSize: 11,
    color: Colors.textMuted,
    fontWeight: '600',
  },
  tabTextActive: {
    color: '#FFF',
    fontWeight: '800',
  },
  rosterScroll: {
    maxHeight: 260,
  },
  rosterContent: {
    gap: 6,
    paddingBottom: 8,
  },
  rosterSection: {
    gap: 6,
  },
  groupTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: Colors.textPrimary,
    marginTop: 4,
  },
  playerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.bgListItem,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    paddingHorizontal: 8,
    paddingVertical: 6,
    gap: 8,
  },
  orderBadge: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: Colors.baseDefault,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pitcherBadge: {
    backgroundColor: Colors.metsBlue,
  },
  bullpenBadge: {
    backgroundColor: Colors.blueMid,
  },
  orderBadgeText: {
    fontSize: 10,
    fontWeight: '900',
    color: '#FFF',
  },
  playerMeta: {
    flex: 1,
  },
  playerName: {
    fontSize: 12,
    fontWeight: '700',
    color: '#FFF',
  },
  playerDetails: {
    fontSize: 10,
    color: Colors.textSecondary,
  },
  positionBadge: {
    backgroundColor: Colors.bgInput,
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  starterBadge: {
    backgroundColor: 'rgba(255, 179, 0, 0.2)',
  },
  relieverBadge: {
    backgroundColor: 'rgba(64, 196, 255, 0.2)',
  },
  positionBadgeText: {
    fontSize: 9,
    fontWeight: '800',
    color: Colors.amberLight,
  },
  emptyText: {
    fontSize: 11,
    color: Colors.textMuted,
    fontStyle: 'italic',
    padding: 8,
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 8,
    marginTop: 4,
  },
  cancelBtn: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.borderSecondary,
  },
  cancelBtnText: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.textSecondary,
  },
  startBtn: {
    backgroundColor: Colors.green,
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  startBtnDisabled: {
    opacity: 0.4,
  },
  startBtnText: {
    color: '#000',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 0.3,
  },
});
