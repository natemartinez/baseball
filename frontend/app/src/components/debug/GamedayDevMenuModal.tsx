import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  StatusBar,
  Dimensions,
} from 'react-native';
import { useGameStore } from '../../store/gameStore';
import type { DevTab } from '../../store/gameStore';
import { Colors } from '../../theme/colors';
import { StrategyIngestColumn } from './StrategyIngestColumn';
import { GamedayVisualizerColumn } from './GamedayVisualizerColumn';
import { CalibrationDiagnosticsColumn } from './CalibrationDiagnosticsColumn';
import { getPitchTypeColor, getResultRingColor } from '../../services/gamedayMath';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

function getPitchAbbr(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes('four-seam') || lower.includes('4-seam')) return '4SF';
  if (lower.includes('sweeper')) return 'SWP';
  if (lower.includes('slider')) return 'SL';
  if (lower.includes('sinker')) return 'SI';
  if (lower.includes('cutter')) return 'CUT';
  if (lower.includes('change')) return 'CH';
  if (lower.includes('curve')) return 'CU';
  if (lower.includes('split')) return 'FS';
  return name.slice(0, 3).toUpperCase();
}

function getResultSymbol(call: string): string {
  switch (call) {
    case 'CALLED_STRIKE':
      return 'ꓘ';
    case 'SWINGING_STRIKE':
      return 'K';
    case 'BALL':
      return 'B';
    case 'FOUL':
      return 'F';
    case 'IN_PLAY':
      return 'IP';
    default:
      return '•';
  }
}

/**
 * GamedayDevMenuModal — Full developer inspection overlay.
 * Provides the 3-column pitching pipeline inspector:
 * - Col 1: Context & Strategy Weights (pi_0 -> W_t)
 * - Col 2: 2D MLB Gameday Home Plate Cross-Section with Interactive Targeting
 * - Col 3: Empirical Rating-Tier Baselines (EXP vs ACT) & Diagnostics
 */
export function GamedayDevMenuModal() {
  const {
    isDevMenuOpen,
    toggleDevMenu,
    activeDevTab,
    setActiveDevTab,
    gamedayLog,
    selectedPitchPacketIndex,
    setSelectedPitchPacketIndex,
    customTargetCoords,
    setCustomTarget,
    countFilter,
    situationFilter,
    batterFilter,
    pitchTypeFilter,
    setGamedayFilters,
    clearDebugLog,
    runFastCalibration,
    isMockMode,
    backendUrl,
    setBackendUrl,
    toggleMockMode,
    gameState,
  } = useGameStore();

  if (!isDevMenuOpen) return null;

  // Resolve currently inspected pitch packet
  const selectedIndex =
    selectedPitchPacketIndex !== null
      ? selectedPitchPacketIndex
      : gamedayLog.length > 0
      ? gamedayLog.length - 1
      : null;

  const currentPacket = selectedIndex !== null ? gamedayLog[selectedIndex] ?? null : null;

  // Resolve current pitcher metadata
  const currentPitcher = gameState?.current_pitcher ?? {
    name: 'Pitcher',
    control: 68,
    break_rating: 70,
  };

  return (
    <Modal
      visible={isDevMenuOpen}
      animationType="slide"
      presentationStyle="fullScreen"
      onRequestClose={() => toggleDevMenu(false)}
    >
      <SafeAreaView style={styles.modalRoot}>
        <StatusBar barStyle="light-content" backgroundColor="#050B14" />

        {/* ── Top Header ─────────────────────────────────────────── */}
        <View style={styles.header}>
          <View style={styles.headerTitleGroup}>
            <View style={styles.titleRow}>
              <Text style={styles.headerIcon}>⚡</Text>
              <Text style={styles.headerTitle}>GAMEDAY DEV & CALIBRATION</Text>
            </View>
            <Text style={styles.headerSubtitle}>
              MLB Statcast 2D Cross-Section • Engine Telemetry Pipeline
            </Text>
          </View>

          <View style={styles.headerActionGroup}>
            {/* Interactive Backend Selector Pill */}
            <TouchableOpacity
              activeOpacity={0.7}
              onPress={() => {
                if (isMockMode) {
                  setBackendUrl('http://localhost:5000');
                } else if (backendUrl.includes('5000')) {
                  setBackendUrl('http://localhost:3000');
                } else {
                  toggleMockMode(true);
                }
              }}
              style={[
                styles.modeBadge,
                {
                  backgroundColor: isMockMode
                    ? 'rgba(16, 185, 129, 0.15)'
                    : backendUrl.includes('5000')
                    ? 'rgba(59, 130, 246, 0.15)'
                    : 'rgba(249, 115, 22, 0.15)',
                },
                {
                  borderColor: isMockMode
                    ? Colors.gameday.statusPass
                    : backendUrl.includes('5000')
                    ? '#3B82F6'
                    : Colors.gameday.statusWarn,
                },
              ]}
            >
              <View
                style={[
                  styles.modeDot,
                  {
                    backgroundColor: isMockMode
                      ? Colors.gameday.statusPass
                      : backendUrl.includes('5000')
                      ? '#3B82F6'
                      : Colors.gameday.statusWarn,
                  },
                ]}
              />
              <Text
                style={[
                  styles.modeText,
                  {
                    color: isMockMode
                      ? Colors.gameday.statusPass
                      : backendUrl.includes('5000')
                      ? '#60A5FA'
                      : Colors.gameday.statusWarn,
                  },
                ]}
              >
                {isMockMode
                  ? 'MOCK ENGINE ⇄'
                  : backendUrl.includes('5000')
                  ? 'PYTHON FLASK (5000) ⇄'
                  : 'NODE SERVER (3000) ⇄'}
              </Text>
            </TouchableOpacity>

            {/* Clear Log Button */}
            {gamedayLog.length > 0 && (
              <TouchableOpacity
                style={styles.clearBtn}
                onPress={clearDebugLog}
                activeOpacity={0.7}
              >
                <Text style={styles.clearBtnText}>CLEAR</Text>
              </TouchableOpacity>
            )}

            {/* Close Modal Button */}
            <TouchableOpacity
              style={styles.closeBtn}
              onPress={() => toggleDevMenu(false)}
              activeOpacity={0.7}
            >
              <Text style={styles.closeBtnText}>✕ CLOSE</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* ── Pitch Scrubber Bar ─────────────────────────────────── */}
        <View style={styles.scrubberSection}>
          <View style={styles.scrubberMetaRow}>
            <Text style={styles.scrubberTitle}>
              SESSION PITCH HISTORY ({gamedayLog.length} LOGGED)
            </Text>
            {selectedPitchPacketIndex !== null && gamedayLog.length > 0 && (
              <TouchableOpacity
                onPress={() => setSelectedPitchPacketIndex(null)}
                style={styles.latestPill}
              >
                <Text style={styles.latestPillText}>➜ JUMP TO LATEST</Text>
              </TouchableOpacity>
            )}
          </View>

          {gamedayLog.length === 0 ? (
            <View style={styles.scrubberEmpty}>
              <Text style={styles.scrubberEmptyText}>
                No pitch telemetry logged yet. Throw a pitch or run calibration below.
              </Text>
            </View>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.scrubberScrollContent}
            >
              {gamedayLog.map((pkt, idx) => {
                const isSelected = selectedIndex === idx;
                const typeColor = getPitchTypeColor(pkt.strategy.selectedPitch);
                const ringColor = getResultRingColor(pkt.result.call);
                const abbr = getPitchAbbr(pkt.strategy.selectedPitch);
                const symbol = getResultSymbol(pkt.result.call);

                return (
                  <TouchableOpacity
                    key={`pitch-${idx}-${pkt.meta.pitchNumber}`}
                    style={[
                      styles.pitchScrubberItem,
                      isSelected && styles.pitchScrubberItemSelected,
                    ]}
                    onPress={() => setSelectedPitchPacketIndex(idx)}
                    activeOpacity={0.7}
                  >
                    <View style={styles.scrubberItemTop}>
                      <Text
                        style={[
                          styles.scrubberPitchNum,
                          isSelected && { color: Colors.gameday.accentCyan },
                        ]}
                      >
                        #{pkt.meta.pitchNumber}
                      </Text>
                      <View style={[styles.resultBadge, { backgroundColor: ringColor }]}>
                        <Text style={styles.resultSymbol}>{symbol}</Text>
                      </View>
                    </View>
                    <Text style={[styles.scrubberPitchType, { color: typeColor }]}>
                      {abbr}
                    </Text>
                    <Text style={styles.scrubberPitchSpeed}>
                      {pkt.execution.realizedSpeedMph.toFixed(0)} MPH
                    </Text>
                    {pkt.execution.isHeartZoneLeak && (
                      <View style={styles.leakTag}>
                        <Text style={styles.leakTagText}>LEAK</Text>
                      </View>
                    )}
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          )}
        </View>

        {/* ── Segmented Tab Selector ─────────────────────────────── */}
        <View style={styles.tabBar}>
          <TouchableOpacity
            style={[styles.tabButton, activeDevTab === 'strategy' && styles.tabButtonActive]}
            onPress={() => setActiveDevTab('strategy')}
          >
            <Text
              style={[styles.tabButtonText, activeDevTab === 'strategy' && styles.tabButtonTextActive]}
            >
              1. STRATEGY
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tabButton, activeDevTab === 'gameday' && styles.tabButtonActive]}
            onPress={() => setActiveDevTab('gameday')}
          >
            <Text
              style={[styles.tabButtonText, activeDevTab === 'gameday' && styles.tabButtonTextActive]}
            >
              2. GAMEDAY 2D
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tabButton, activeDevTab === 'calibration' && styles.tabButtonActive]}
            onPress={() => setActiveDevTab('calibration')}
          >
            <Text
              style={[styles.tabButtonText, activeDevTab === 'calibration' && styles.tabButtonTextActive]}
            >
              3. CALIBRATION
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tabButton, activeDevTab === 'split' && styles.tabButtonActive]}
            onPress={() => setActiveDevTab('split')}
          >
            <Text
              style={[styles.tabButtonText, activeDevTab === 'split' && styles.tabButtonTextActive]}
            >
              ⚡ 3-COL SPLIT
            </Text>
          </TouchableOpacity>
        </View>

        {/* ── Main Inspector Content ─────────────────────────────── */}
        <View style={styles.contentContainer}>
          {activeDevTab === 'strategy' && (
            <ScrollView style={styles.tabScroll}>
              <StrategyIngestColumn packet={currentPacket} />
              <View style={styles.bottomSpacer} />
            </ScrollView>
          )}

          {activeDevTab === 'gameday' && (
            <ScrollView style={styles.tabScroll}>
              <GamedayVisualizerColumn
                packet={currentPacket}
                customTarget={customTargetCoords}
                onSetCustomTarget={setCustomTarget}
              />
              <View style={styles.bottomSpacer} />
            </ScrollView>
          )}

          {activeDevTab === 'calibration' && (
            <ScrollView style={styles.tabScroll}>
              <CalibrationDiagnosticsColumn
                packets={gamedayLog}
                currentPitcher={currentPitcher}
                countFilter={countFilter}
                situationFilter={situationFilter}
                batterFilter={batterFilter}
                pitchTypeFilter={pitchTypeFilter}
                onUpdateFilters={setGamedayFilters}
                onRunFastCalibration={() => runFastCalibration(currentPitcher.control ?? 68, 100)}
              />
              <View style={styles.bottomSpacer} />
            </ScrollView>
          )}

          {activeDevTab === 'split' && (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={true}
              contentContainerStyle={styles.splitScrollContent}
            >
              <View style={styles.splitColumn}>
                <ScrollView showsVerticalScrollIndicator={false}>
                  <StrategyIngestColumn packet={currentPacket} />
                  <View style={styles.bottomSpacer} />
                </ScrollView>
              </View>

              <View style={styles.splitDivider} />

              <View style={styles.splitColumn}>
                <ScrollView showsVerticalScrollIndicator={false}>
                  <GamedayVisualizerColumn
                    packet={currentPacket}
                    customTarget={customTargetCoords}
                    onSetCustomTarget={setCustomTarget}
                  />
                  <View style={styles.bottomSpacer} />
                </ScrollView>
              </View>

              <View style={styles.splitDivider} />

              <View style={styles.splitColumn}>
                <ScrollView showsVerticalScrollIndicator={false}>
                  <CalibrationDiagnosticsColumn
                    packets={gamedayLog}
                    currentPitcher={currentPitcher}
                    countFilter={countFilter}
                    situationFilter={situationFilter}
                    batterFilter={batterFilter}
                    pitchTypeFilter={pitchTypeFilter}
                    onUpdateFilters={setGamedayFilters}
                    onRunFastCalibration={() => runFastCalibration(currentPitcher.control ?? 68, 100)}
                  />
                  <View style={styles.bottomSpacer} />
                </ScrollView>
              </View>
            </ScrollView>
          )}
        </View>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalRoot: {
    flex: 1,
    backgroundColor: '#030712',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#0B132B',
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  headerTitleGroup: {
    flex: 1,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  headerIcon: {
    fontSize: 18,
  },
  headerTitle: {
    color: '#F8FAFC',
    fontSize: 15,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  headerSubtitle: {
    color: '#64748B',
    fontSize: 10,
    fontWeight: '500',
    marginTop: 2,
  },
  headerActionGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  modeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
  },
  modeDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  modeText: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  clearBtn: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 6,
    backgroundColor: 'rgba(239, 68, 68, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.4)',
  },
  clearBtnText: {
    color: '#EF4444',
    fontSize: 10,
    fontWeight: '700',
  },
  closeBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    backgroundColor: '#1E293B',
    borderWidth: 1,
    borderColor: '#334155',
  },
  closeBtnText: {
    color: '#E2E8F0',
    fontSize: 11,
    fontWeight: '700',
  },
  scrubberSection: {
    backgroundColor: '#070D1F',
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
    paddingVertical: 8,
  },
  scrubberMetaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    marginBottom: 6,
  },
  scrubberTitle: {
    color: '#64748B',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  latestPill: {
    backgroundColor: 'rgba(6, 182, 212, 0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(6, 182, 212, 0.3)',
  },
  latestPillText: {
    color: Colors.gameday.accentCyan,
    fontSize: 9,
    fontWeight: '700',
  },
  scrubberEmpty: {
    paddingHorizontal: 16,
    paddingVertical: 6,
  },
  scrubberEmptyText: {
    color: '#475569',
    fontSize: 11,
    fontStyle: 'italic',
  },
  scrubberScrollContent: {
    paddingHorizontal: 12,
    gap: 8,
  },
  pitchScrubberItem: {
    backgroundColor: '#0F172A',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    minWidth: 78,
    borderWidth: 1,
    borderColor: '#1E293B',
    alignItems: 'center',
  },
  pitchScrubberItemSelected: {
    borderColor: Colors.gameday.accentCyan,
    backgroundColor: '#16233B',
    shadowColor: Colors.gameday.accentCyan,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 4,
    elevation: 3,
  },
  scrubberItemTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    marginBottom: 2,
  },
  scrubberPitchNum: {
    color: '#94A3B8',
    fontSize: 10,
    fontWeight: '700',
  },
  resultBadge: {
    width: 14,
    height: 14,
    borderRadius: 7,
    alignItems: 'center',
    justifyContent: 'center',
  },
  resultSymbol: {
    color: '#FFF',
    fontSize: 8,
    fontWeight: '900',
  },
  scrubberPitchType: {
    fontSize: 11,
    fontWeight: '800',
    marginVertical: 1,
  },
  scrubberPitchSpeed: {
    color: '#CBD5E1',
    fontSize: 9,
    fontWeight: '600',
  },
  leakTag: {
    marginTop: 3,
    backgroundColor: 'rgba(239, 68, 68, 0.25)',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 3,
  },
  leakTagText: {
    color: '#EF4444',
    fontSize: 7,
    fontWeight: '900',
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#0F172A',
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  tabButton: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabButtonActive: {
    borderBottomColor: Colors.gameday.accentCyan,
    backgroundColor: '#1E293B',
  },
  tabButtonText: {
    color: '#64748B',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  tabButtonTextActive: {
    color: '#F8FAFC',
    fontWeight: '800',
  },
  contentContainer: {
    flex: 1,
    backgroundColor: '#030712',
  },
  tabScroll: {
    flex: 1,
  },
  splitScrollContent: {
    flexDirection: 'row',
    paddingVertical: 8,
  },
  splitColumn: {
    width: Math.max(340, Math.min(420, SCREEN_WIDTH * 0.85)),
  },
  splitDivider: {
    width: 1,
    backgroundColor: '#1E293B',
    marginHorizontal: 4,
  },
  bottomSpacer: {
    height: 48,
  },
});
