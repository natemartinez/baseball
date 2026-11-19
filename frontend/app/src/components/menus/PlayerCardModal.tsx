import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  ScrollView,
  Animated,
  Platform,
  StyleSheet,
} from 'react-native';
import { useGameStore } from '../../store/gameStore';
import { Colors } from '../../theme/colors';
import {
  getAbilityTier,
  getAbilityTierColor,
} from '../../services/gamedayMath';
import {
  computeBaselineEffectiveness,
  calculateCombinedEffectiveCommand,
} from '../../services/effectivenessModel';
import type { PitchArsenalItem } from '../../types/api';

const USE_NATIVE_DRIVER = Platform.OS !== 'web';

export function PlayerCardModal() {
  const {
    isPlayerCardModalOpen,
    togglePlayerCardModal,
    gameState,
    selectedPitchName,
    setSelectedPitchName,
    pitcherStamina,
    pitcherConfidence,
    pitcherEffectiveness,
  } = useGameStore();

  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (isPlayerCardModalOpen) {
      // Small 60ms delay allows the strike zone and pitch selector to fade out first
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 150,
        delay: 60,
        useNativeDriver: USE_NATIVE_DRIVER,
      }).start();
    } else {
      fadeAnim.setValue(0);
    }
  }, [isPlayerCardModalOpen, fadeAnim]);

  const handleClose = () => {
    Animated.timing(fadeAnim, {
      toValue: 0,
      duration: 100,
      useNativeDriver: USE_NATIVE_DRIVER,
    }).start(() => {
      togglePlayerCardModal(false);
    });
  };

  const pitcher = gameState?.current_pitcher;

  useEffect(() => {
    if (isPlayerCardModalOpen && !pitcher) {
      togglePlayerCardModal(false);
    }
  }, [isPlayerCardModalOpen, pitcher, togglePlayerCardModal]);

  if (!pitcher) {
    return (
      <Modal
        visible={isPlayerCardModalOpen}
        transparent
        animationType="none"
        onRequestClose={handleClose}
      >
        <View style={styles.overlay}>
          <TouchableOpacity
            style={StyleSheet.absoluteFill}
            activeOpacity={1}
            onPress={handleClose}
            accessibilityLabel="Close overlay backdrop"
          />
          <Animated.View style={[styles.cardContainer, { opacity: fadeAnim }]}>
            <View style={styles.header}>
              <Text style={styles.playerName}>Pitcher Overview</Text>
              <TouchableOpacity
                style={styles.closeButton}
                onPress={handleClose}
                accessibilityLabel="Close player card"
              >
                <Text style={styles.closeText}>✕</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>No pitcher data available.</Text>
            </View>
          </Animated.View>
        </View>
      </Modal>
    );
  }

  const pId = pitcher.id ?? 1;
  const staminaPct = pitcherStamina[pId] ?? 100;
  const confidences = pitcherConfidence[pId] ?? {};
  const effMap = pitcherEffectiveness[pId] ?? {};
  const holisticConfidence = confidences['overall'] ?? 50;
  const pitcherControl = pitcher.control ?? 75;

  return (
    <Modal
      visible={isPlayerCardModalOpen}
      transparent
      animationType="none"
      onRequestClose={handleClose}
    >
      <View style={styles.overlay}>
        <TouchableOpacity
          style={StyleSheet.absoluteFill}
          activeOpacity={1}
          onPress={handleClose}
          accessibilityLabel="Close overlay backdrop"
        />
        <Animated.View style={[styles.cardContainer, { opacity: fadeAnim }]}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerInfo}>
              <View style={styles.jerseyBadge}>
                <Text style={styles.jerseyNumber}>#{pitcher.jersey_number ?? 0}</Text>
              </View>
              <View>
                <Text style={styles.playerName}>{pitcher.name}</Text>
                <Text style={styles.playerMeta}>
                  {pitcher.position ?? 'P'} • {pitcher.team ?? 'PITCHER'} • {pitcher.throws ?? 'RHP'}
                </Text>
              </View>
            </View>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={handleClose}
              accessibilityLabel="Close player card"
            >
              <Text style={styles.closeText}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* Core Ratings Strip */}
          <View style={styles.ratingsStrip}>
            <View style={styles.ratingBox}>
              <Text style={styles.ratingLabel}>VELO</Text>
              <Text style={styles.ratingVal}>{pitcher.velocity_rating ?? '--'}</Text>
            </View>
            <View style={styles.ratingBox}>
              <Text style={styles.ratingLabel}>BREAK</Text>
              <Text style={styles.ratingVal}>{pitcher.break_rating ?? '--'}</Text>
            </View>
            <View style={styles.ratingBox}>
              <Text style={styles.ratingLabel}>CONTROL</Text>
              <Text style={styles.ratingVal}>{pitcher.control ?? '--'}</Text>
            </View>
            <View style={styles.ratingBox}>
              <Text style={styles.ratingLabel}>STAMINA</Text>
              <Text style={[styles.ratingVal, { color: staminaPct > 50 ? '#10B981' : '#EF4444' }]}>
                {Math.round(staminaPct)}%
              </Text>
            </View>
          </View>

          <Text style={styles.sectionTitle}>PITCH ARSENAL & STATCAST METRICS</Text>

          {/* Pitch Arsenal List */}
          <ScrollView style={styles.arsenalScroll} showsVerticalScrollIndicator={false}>
            {(pitcher.arsenal ?? []).length === 0 ? (
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyText}>No pitch arsenal data available.</Text>
              </View>
            ) : (
              (pitcher.arsenal ?? []).map((item: PitchArsenalItem) => {
                const itemEff =
                  effMap[item.name] ??
                  computeBaselineEffectiveness(
                    item.velocity_mph ?? 93,
                    item.break_rating ?? 75,
                    item.spin_rpm ?? 2400,
                    item.control_rating ?? 75,
                  );
                const itemConf = confidences[item.name] ?? holisticConfidence;
                const baseCmd = item.command ?? item.control_rating ?? pitcherControl;
                const effCmd = calculateCombinedEffectiveCommand(baseCmd, itemConf, itemEff);
                const tier = getAbilityTier(effCmd);
                const tierColor = getAbilityTierColor(tier);
                const isSelected = item.name === selectedPitchName;

                const veloText =
                  item.velocity_display ??
                  (item.velocity_min_mph && item.velocity_max_mph
                    ? `${item.velocity_min_mph}–${item.velocity_max_mph} mph`
                    : `${item.velocity_mph ?? '--'} mph`);

                return (
                  <TouchableOpacity
                    key={item.name}
                    style={[
                      styles.pitchItem,
                      isSelected && styles.pitchItemSelected,
                      { borderLeftColor: tierColor },
                    ]}
                    onPress={() => {
                      setSelectedPitchName(item.name);
                    }}
                    activeOpacity={0.8}
                  >
                    <View style={styles.pitchTopRow}>
                      <View style={styles.pitchNameGroup}>
                        <Text style={[styles.pitchName, isSelected && styles.pitchNameSelected]}>
                          {item.name}
                        </Text>
                        <View style={[styles.tierBadge, { backgroundColor: `${tierColor}20`, borderColor: tierColor }]}>
                          <Text style={[styles.tierBadgeText, { color: tierColor }]}>{tier}</Text>
                        </View>
                      </View>
                      <Text style={styles.veloText}>{veloText}</Text>
                    </View>

                    <View style={styles.statGrid}>
                      <View style={styles.statCell}>
                        <Text style={styles.statCellLabel}>CMD</Text>
                        <Text style={[styles.statCellVal, { color: tierColor }]}>{Math.round(effCmd)}</Text>
                      </View>
                      <View style={styles.statCell}>
                        <Text style={styles.statCellLabel}>BRK</Text>
                        <Text style={styles.statCellVal}>{item.break_rating ?? '--'}</Text>
                      </View>
                      <View style={styles.statCell}>
                        <Text style={styles.statCellLabel}>SPIN</Text>
                        <Text style={styles.statCellVal}>{item.spin_rpm ? `${item.spin_rpm}` : '--'}</Text>
                      </View>
                      <View style={styles.statCell}>
                        <Text style={styles.statCellLabel}>EFF</Text>
                        <Text style={[styles.statCellVal, { color: '#38BDF8' }]}>{Math.round(itemEff)}%</Text>
                      </View>
                    </View>
                  </TouchableOpacity>
                );
              })
            )}
          </ScrollView>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  cardContainer: {
    width: '100%',
    maxWidth: 440,
    maxHeight: '85%',
    backgroundColor: '#16181D',
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: '#2B2F38',
    padding: 18,
    boxShadow: '0px 10px 25px rgba(0, 0, 0, 0.6)',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  headerInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  jerseyBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#2563EB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  jerseyNumber: {
    color: '#FFF',
    fontWeight: '900',
    fontSize: 13,
  },
  playerName: {
    color: '#FFF',
    fontSize: 17,
    fontWeight: '800',
  },
  playerMeta: {
    color: '#94A3B8',
    fontSize: 11,
    fontWeight: '600',
  },
  closeButton: {
    padding: 6,
    borderRadius: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  closeText: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: '700',
  },
  ratingsStrip: {
    flexDirection: 'row',
    backgroundColor: '#0F1216',
    borderRadius: 8,
    padding: 10,
    gap: 8,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#262A34',
  },
  ratingBox: {
    flex: 1,
    alignItems: 'center',
  },
  ratingLabel: {
    fontSize: 9,
    fontWeight: '700',
    color: '#64748B',
    marginBottom: 2,
  },
  ratingVal: {
    fontSize: 14,
    fontWeight: '900',
    color: '#F8FAFC',
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: '800',
    color: '#94A3B8',
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  arsenalScroll: {
    maxHeight: 320,
  },
  pitchItem: {
    backgroundColor: '#1C2028',
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#2A303C',
    borderLeftWidth: 4,
  },
  pitchItemSelected: {
    backgroundColor: 'rgba(37, 99, 235, 0.16)',
    borderColor: '#3B82F6',
  },
  pitchTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  pitchNameGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  pitchName: {
    fontSize: 13,
    fontWeight: '700',
    color: '#F1F5F9',
  },
  pitchNameSelected: {
    color: '#60A5FA',
  },
  tierBadge: {
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 4,
    borderWidth: 1,
  },
  tierBadgeText: {
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 0.4,
  },
  veloText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FACC15',
  },
  statGrid: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 4,
  },
  statCell: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statCellLabel: {
    fontSize: 9,
    fontWeight: '700',
    color: '#64748B',
  },
  statCellVal: {
    fontSize: 11,
    fontWeight: '800',
    color: '#E2E8F0',
  },
  emptyContainer: {
    paddingVertical: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    color: '#94A3B8',
    fontSize: 13,
    fontStyle: 'italic',
  },
});

