import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import type { StrategyIntentDecision, PitchOptionWeight } from '../types/api';
import { Colors } from '../theme/colors';

interface StrategyDeciderWidgetProps {
  strategyIntent: StrategyIntentDecision;
  selectedPitchIntent?: string;
  selectedTargetZone?: string;
  onSelectPitchIntent?: (name: string) => void;
  onSelectTargetZone?: (zone: string) => void;
}

/**
 * StrategyDeciderWidget
 *
 * Full-fidelity AI Strategy & Pitch Decider widget.
 * Displays situational game leverage, AI strategic rationale,
 * ranked pitch selection weights with visual probability bars,
 * the "#1 Most Likely / Primary Weapon" highlight, Statcast metrics,
 * and the recommended target zone.
 */
export function StrategyDeciderWidget({
  strategyIntent,
  selectedPitchIntent,
  selectedTargetZone,
  onSelectPitchIntent,
  onSelectTargetZone,
}: StrategyDeciderWidgetProps) {
  const {
    strategy_name,
    situation_tag,
    count_context,
    rationale,
    recommended_pitch,
    recommended_zone,
    pitch_weights = [],
    zone_weights = [],
    command_quality,
  } = strategyIntent;

  // Find zone details for recommended zone
  const recZoneItem = zone_weights.find((z) => z.zone === recommended_zone);
  const zoneType = recZoneItem?.zone_type ?? 'COLD_ZONE';

  return (
    <View style={styles.container}>
      {/* ─── Top Header: Situation & Count Context ─────────────────────────── */}
      <View style={styles.headerRow}>
        <View style={styles.headerLeft}>
          <View style={styles.radarDot} />
          <Text style={styles.headerTitle}>AI STRATEGY & PITCH DECIDER</Text>
        </View>
        <View style={styles.situationBadge}>
          <Text style={styles.situationText}>{situation_tag.replace(/_/g, ' ')}</Text>
        </View>
      </View>

      <View style={styles.countContextRow}>
        <Text style={styles.countContextText}>{count_context}</Text>
      </View>

      {/* ─── AI Strategy & Rationale Card ─────────────────────────────────── */}
      <View style={styles.strategyCard}>
        <View style={styles.strategyTitleRow}>
          <Text style={styles.strategyName}>{strategy_name}</Text>
          {command_quality && (
            <View style={styles.commandQualityBadge}>
              <Text style={styles.commandQualityText}>{command_quality.replace(/_/g, ' ')}</Text>
            </View>
          )}
        </View>
        <Text style={styles.rationaleText}>{rationale}</Text>
      </View>

      {/* ─── Dynamic Pitch Selection Weights (Ranked) ─────────────────────── */}
      <View style={styles.weightsSection}>
        <View style={styles.weightsHeaderRow}>
          <View style={styles.weightsHeaderLeft}>
            <Text style={styles.weightsSectionTitle}>DYNAMIC PITCH WEIGHTS (RANKED)</Text>
            <View style={styles.statcastBadge}>
              <Text style={styles.statcastBadgeText}>STATCAST DRIVEN</Text>
            </View>
          </View>
          {onSelectPitchIntent && (
            <Text style={styles.tapHint}>TAP TO SELECT INTENT</Text>
          )}
        </View>

        <View style={styles.weightsList}>
          {pitch_weights.map((pw) => (
            <PitchWeightCard
              key={pw.pitch_name}
              pw={pw}
              isSelected={pw.pitch_name === selectedPitchIntent}
              onSelect={() => onSelectPitchIntent?.(pw.pitch_name)}
            />
          ))}
        </View>
      </View>

      {/* ─── Recommended Target Zone ──────────────────────────────────────── */}
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => onSelectTargetZone?.(recommended_zone)}
        style={[
          styles.recommendedZoneCard,
          selectedTargetZone === recommended_zone && styles.recommendedZoneSelected,
        ]}
      >
        <View style={styles.recZoneLeft}>
          <Text style={styles.recZoneLabel}>Recommended Target:</Text>
          <Text style={styles.recZoneName}>{recommended_zone}</Text>
          <View style={[styles.zoneTypeBadge, getZoneTypeStyle(zoneType)]}>
            <Text style={[styles.zoneTypeText, getZoneTypeTextStyle(zoneType)]}>{zoneType}</Text>
          </View>
        </View>

        <View style={styles.recPitchPill}>
          <Text style={styles.recPitchText}>{recommended_pitch}</Text>
        </View>
      </TouchableOpacity>
    </View>
  );
}

// ─── Sub-Component: Ranked Pitch Weight Card ──────────────────────────────────

function PitchWeightCard({
  pw,
  isSelected,
  onSelect,
}: {
  pw: PitchOptionWeight;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const isMostLikely = pw.is_most_likely;

  return (
    <TouchableOpacity
      activeOpacity={0.75}
      onPress={onSelect}
      style={[
        styles.pitchCard,
        isMostLikely && styles.pitchCardMostLikely,
        isSelected && styles.pitchCardSelected,
      ]}
    >
      {/* Top row: Rank, Name, Badges, Probability % */}
      <View style={styles.pitchCardTopRow}>
        <View style={styles.pitchIdentityGroup}>
          <View style={[styles.rankCircle, isMostLikely ? styles.rankCirclePrimary : styles.rankCircleSecondary]}>
            <Text style={[styles.rankText, isMostLikely ? styles.rankTextPrimary : styles.rankTextSecondary]}>
              #{pw.rank}
            </Text>
          </View>

          <Text style={[styles.pitchNameText, isMostLikely ? styles.pitchNamePrimary : styles.pitchNameSecondary]}>
            {pw.pitch_name}
          </Text>

          {isMostLikely && (
            <View style={styles.primaryPill}>
              <Text style={styles.primaryPillText}>★ MOST LIKELY</Text>
            </View>
          )}

          {isSelected && (
            <View style={styles.selectedPill}>
              <Text style={styles.selectedPillText}>ACTIVE INTENT</Text>
            </View>
          )}

          {pw.is_least_likely && !isSelected && (
            <View style={styles.deprioritizedPill}>
              <Text style={styles.deprioritizedPillText}>DEPRIORITIZED</Text>
            </View>
          )}
        </View>

        <Text style={[styles.probabilityText, isMostLikely ? styles.probPrimary : styles.probSecondary]}>
          {pw.probability_pct}%
        </Text>
      </View>

      {/* Visual Probability Progress Bar */}
      <View style={styles.progressBarTrack}>
        <View
          style={[
            styles.progressBarFill,
            isMostLikely ? styles.progressFillPrimary : styles.progressFillSecondary,
            { width: `${Math.min(100, Math.max(3, pw.probability_pct))}%` },
          ]}
        />
      </View>

      {/* Reasoning & Statcast Telemetry */}
      <View style={styles.pitchCardFooter}>
        <Text style={styles.reasoningText} numberOfLines={1}>
          {pw.reasoning}
        </Text>
        {pw.statcast && (
          <Text style={styles.statcastText}>
            Whiff: {pw.statcast.whiff_pct}% • GB: {pw.statcast.gb_pct}%
            {pw.statcast.stuff_plus ? ` • Stuff+: ${pw.statcast.stuff_plus}` : ''}
          </Text>
        )}
      </View>
    </TouchableOpacity>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getZoneTypeStyle(type: string) {
  switch (type) {
    case 'COLD_ZONE':
      return { backgroundColor: 'rgba(2, 136, 209, 0.2)', borderColor: 'rgba(2, 136, 209, 0.4)' };
    case 'HOT_ZONE':
      return { backgroundColor: 'rgba(211, 47, 47, 0.2)', borderColor: 'rgba(211, 47, 47, 0.4)' };
    case 'CHASE_ZONE':
      return { backgroundColor: 'rgba(142, 36, 170, 0.2)', borderColor: 'rgba(142, 36, 170, 0.4)' };
    default:
      return { backgroundColor: 'rgba(84, 110, 122, 0.2)', borderColor: 'rgba(84, 110, 122, 0.4)' };
  }
}

function getZoneTypeTextStyle(type: string) {
  switch (type) {
    case 'COLD_ZONE':
      return { color: '#40C4FF' };
    case 'HOT_ZONE':
      return { color: '#FF5252' };
    case 'CHASE_ZONE':
      return { color: '#BA68C8' };
    default:
      return { color: '#B0BEC5' };
  }
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bgSurface,
    borderRadius: 14,
    padding: 14,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  radarDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10B981',
  },
  headerTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: Colors.textSecondary,
    letterSpacing: 1.0,
  },
  situationBadge: {
    backgroundColor: 'rgba(255, 179, 0, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(255, 179, 0, 0.4)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  situationText: {
    fontSize: 10,
    fontWeight: '800',
    color: Colors.amber,
    letterSpacing: 0.5,
  },
  countContextRow: {
    marginTop: -2,
  },
  countContextText: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.3,
  },
  strategyCard: {
    backgroundColor: '#0D131A',
    borderRadius: 10,
    padding: 10,
    borderWidth: 1,
    borderColor: '#1E293B',
    gap: 6,
  },
  strategyTitleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  strategyName: {
    fontSize: 13,
    fontWeight: '800',
    color: '#34D399',
    letterSpacing: 0.5,
  },
  commandQualityBadge: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  commandQualityText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#34D399',
    letterSpacing: 0.5,
  },
  rationaleText: {
    fontSize: 11,
    color: '#CBD5E1',
    lineHeight: 16,
  },
  weightsSection: {
    gap: 8,
  },
  weightsHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  weightsHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  weightsSectionTitle: {
    fontSize: 10,
    fontWeight: '800',
    color: Colors.textSecondary,
    letterSpacing: 0.8,
  },
  statcastBadge: {
    backgroundColor: 'rgba(6, 182, 212, 0.15)',
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 4,
  },
  statcastBadgeText: {
    fontSize: 8,
    fontWeight: '700',
    color: '#22D3EE',
    letterSpacing: 0.4,
  },
  tapHint: {
    fontSize: 8,
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.4,
  },
  weightsList: {
    gap: 6,
  },
  pitchCard: {
    backgroundColor: '#0F172A',
    borderWidth: 1,
    borderColor: '#1E293B',
    borderRadius: 8,
    padding: 8,
    gap: 5,
  },
  pitchCardMostLikely: {
    borderColor: 'rgba(16, 185, 129, 0.4)',
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
  },
  pitchCardSelected: {
    borderColor: Colors.blue,
    backgroundColor: '#132337',
  },
  pitchCardTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  pitchIdentityGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexShrink: 1,
  },
  rankCircle: {
    width: 18,
    height: 18,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rankCirclePrimary: {
    backgroundColor: '#10B981',
  },
  rankCircleSecondary: {
    backgroundColor: '#1E293B',
  },
  rankText: {
    fontSize: 10,
    fontWeight: '900',
    fontFamily: 'monospace',
  },
  rankTextPrimary: {
    color: '#0A0F15',
  },
  rankTextSecondary: {
    color: '#94A3B8',
  },
  pitchNameText: {
    fontSize: 12,
    fontWeight: '700',
  },
  pitchNamePrimary: {
    color: '#34D399',
  },
  pitchNameSecondary: {
    color: '#E2E8F0',
  },
  primaryPill: {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.3)',
  },
  primaryPillText: {
    fontSize: 8,
    fontWeight: '800',
    color: '#34D399',
    letterSpacing: 0.3,
  },
  selectedPill: {
    backgroundColor: 'rgba(64, 196, 255, 0.2)',
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(64, 196, 255, 0.4)',
  },
  selectedPillText: {
    fontSize: 8,
    fontWeight: '800',
    color: '#40C4FF',
    letterSpacing: 0.3,
  },
  deprioritizedPill: {
    backgroundColor: 'rgba(100, 116, 139, 0.15)',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 4,
  },
  deprioritizedPillText: {
    fontSize: 7,
    fontWeight: '700',
    color: '#64748B',
    letterSpacing: 0.2,
  },
  probabilityText: {
    fontSize: 12,
    fontFamily: 'monospace',
    fontWeight: '800',
  },
  probPrimary: {
    color: '#34D399',
  },
  probSecondary: {
    color: '#94A3B8',
  },
  progressBarTrack: {
    height: 5,
    backgroundColor: '#1E293B',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  progressFillPrimary: {
    backgroundColor: '#10B981',
  },
  progressFillSecondary: {
    backgroundColor: '#475569',
  },
  pitchCardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 6,
  },
  reasoningText: {
    fontSize: 9,
    color: '#94A3B8',
    flex: 1,
  },
  statcastText: {
    fontSize: 9,
    fontFamily: 'monospace',
    color: '#64748B',
    fontWeight: '600',
  },
  recommendedZoneCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#0D131A',
    borderWidth: 1,
    borderColor: '#1E293B',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  recommendedZoneSelected: {
    borderColor: Colors.blue,
  },
  recZoneLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  recZoneLabel: {
    fontSize: 11,
    color: Colors.textSecondary,
    fontWeight: '600',
  },
  recZoneName: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: '800',
    color: Colors.amber,
  },
  zoneTypeBadge: {
    borderWidth: 1,
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 4,
  },
  zoneTypeText: {
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  recPitchPill: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.3)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  recPitchText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#34D399',
  },
});
