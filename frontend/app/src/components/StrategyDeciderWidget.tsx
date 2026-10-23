import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import type { StrategyIntentDecision, PitchOptionWeight } from '../types/api';
import { Colors } from '../theme/colors';

interface StrategyDeciderWidgetProps {
  strategyIntent: StrategyIntentDecision;
  selectedPitchIntent?: string;
  onSelectPitchIntent?: (name: string) => void;
}

/**
 * StrategyDeciderWidget
 *
 * AI Strategy & Pitch Decider widget.
 * Displays count context, the AI strategic rationale, and ranked pitch
 * selection weights with the "#1 Most Likely / Primary Weapon" highlight.
 * Situation leverage, recommended target, pitch percentages, and Statcast
 * rates now live in the Pitch Selector widget.
 */
export function StrategyDeciderWidget({
  strategyIntent,
  selectedPitchIntent,
  onSelectPitchIntent,
}: StrategyDeciderWidgetProps) {
  const {
    strategy_name,
    count_context,
    rationale,
    pitch_weights = [],
    command_quality,
  } = strategyIntent;

  return (
    <View style={styles.container}>
      {/* ─── Top Header: Count Context ─────────────────────────────────────── */}
      <View style={styles.headerRow}>
        <View style={styles.headerLeft}>
          <View style={styles.radarDot} />
          <Text style={styles.headerTitle}>AI STRATEGY & PITCH DECIDER</Text>
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

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bgSurface,
    borderRadius: 14,
    marginTop: 10,
    padding: 34,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    elevation: 4,
    boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.3)',
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
});
