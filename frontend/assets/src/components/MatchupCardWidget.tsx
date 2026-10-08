import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import type { BatterInfo, PitcherInfo } from '../types/api';
import { Colors } from '../theme/colors';

interface MatchupCardWidgetProps {
  batter: BatterInfo;
  pitcher: PitcherInfo;
}

/**
 * Core UI Component 4: Lineup & Matchup Card
 * Shows current batter ratings/traits and current pitcher ratings/stats.
 * Features seed players Aaron Judge (NYY) vs Nolan McLean (NYM).
 *
 * Ported from MatchupCardWidget.kt.
 */
export function MatchupCardWidget({
  batter,
  pitcher,
}: MatchupCardWidgetProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>PLATE MATCHUP • STATCAST PREVIEW</Text>
      <BatterProfileCard batter={batter} />
      <PitcherProfileCard pitcher={pitcher} />
    </View>
  );
}

// ─── Batter Card ──────────────────────────────────────────────────────────────

function BatterProfileCard({ batter }: { batter: BatterInfo }) {
  return (
    <View style={styles.profileCard}>
      {/* Header row */}
      <View style={styles.cardHeader}>
        <View style={styles.headerLeft}>
          <View style={[styles.jerseyBadge, { backgroundColor: Colors.yankeesNavy }]}>
            <Text style={styles.jerseyNumber}>#{batter.jersey_number}</Text>
          </View>
          <View>
            <Text style={styles.playerName}>{batter.name}</Text>
            <Text style={styles.playerMeta}>{batter.position} • {batter.team}</Text>
          </View>
        </View>
        <View style={styles.statLineBadge}>
          <Text style={styles.statLineText}>
            {batter.stats.hits}-{batter.stats.at_bats}, {batter.stats.home_runs} HR, {batter.stats.rbis} RBI
          </Text>
        </View>
      </View>

      {/* Rating chips */}
      <View style={styles.ratingsRow}>
        <RatingMetricChip label="POWER" value={batter.power} highlight={batter.power >= 95} />
        <RatingMetricChip label="CONTACT" value={batter.contact} highlight={batter.contact >= 90} />
        <RatingMetricChip label="VISION" value={batter.vision} highlight={batter.vision >= 90} />
      </View>

      {/* Trait pills */}
      {batter.traits.length > 0 && (
        <View style={styles.traitsRow}>
          {batter.traits.map((trait) => {
            const isHrTrait = trait === 'Home Run Threat';
            return (
              <View
                key={trait}
                style={[
                  styles.traitBadge,
                  {
                    backgroundColor: isHrTrait ? Colors.traitHrBg : Colors.traitDefault,
                    borderColor: isHrTrait ? Colors.homeRunGlow : Colors.borderDivider,
                  },
                ]}
              >
                <Text style={[styles.traitText, { color: isHrTrait ? Colors.redMild : Colors.textSecondary }]}>
                  ★ {trait}
                </Text>
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
}

// ─── Pitcher Card ─────────────────────────────────────────────────────────────

function PitcherProfileCard({ pitcher }: { pitcher: PitcherInfo }) {
  return (
    <View style={styles.profileCard}>
      {/* Header */}
      <View style={styles.cardHeader}>
        <View style={styles.headerLeft}>
          <View style={[styles.jerseyBadge, { backgroundColor: Colors.metsOrange }]}>
            <Text style={styles.jerseyNumber}>#{pitcher.jersey_number}</Text>
          </View>
          <View>
            <Text style={styles.playerName}>{pitcher.name}</Text>
            <Text style={styles.playerMeta}>{pitcher.position} • {pitcher.team}</Text>
          </View>
        </View>
        <View style={styles.statLineBadge}>
          <Text style={[styles.statLineText, { color: Colors.blueLight }]}>
            {pitcher.stats.pitches_thrown} Pitches • {pitcher.stats.strikeouts} K
          </Text>
        </View>
      </View>

      {/* Pitcher ratings */}
      <View style={styles.ratingsRow}>
        <RatingMetricChip label="BREAK" value={pitcher.break_rating} highlight />
        <RatingMetricChip label="VELO" value={pitcher.velocity_rating} highlight />
        <RatingMetricChip label="ARM" value={pitcher.arm_strength} highlight />
        <RatingMetricChip label="CTRL" value={pitcher.control} highlight={false} />
      </View>
    </View>
  );
}

// ─── Rating Metric Chip ───────────────────────────────────────────────────────

function RatingMetricChip({ label, value, highlight }: { label: string; value: number; highlight: boolean }) {
  return (
    <View
      style={[
        styles.ratingChip,
        {
          backgroundColor: highlight ? Colors.ratingHighlight : '#10161D',
          borderColor: highlight ? Colors.ratingHighlightBorder : Colors.borderPrimary,
        },
      ]}
    >
      <Text style={[styles.ratingLabel, { color: highlight ? Colors.amberLight : Colors.textMuted }]}>{label}</Text>
      <Text style={[styles.ratingValue, { color: highlight ? Colors.yellow : Colors.textPrimary }]}>{value}</Text>
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
  sectionLabel: { fontSize: 9, fontWeight: '700', color: Colors.textSecondary, letterSpacing: 1.0, textTransform: 'uppercase' },
  profileCard: {
    backgroundColor: Colors.bgCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    padding: 12,
    gap: 8,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  jerseyBadge: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  jerseyNumber: { color: '#FFF', fontWeight: '900', fontSize: 11 },
  playerName: { color: '#FFF', fontWeight: '700', fontSize: 15 },
  playerMeta: { color: Colors.textSecondary, fontSize: 11 },
  statLineBadge: { backgroundColor: Colors.bgInput, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 },
  statLineText: { fontSize: 11, fontWeight: '600', color: Colors.amberHot },
  ratingsRow: { flexDirection: 'row', gap: 6 },
  ratingChip: { flex: 1, borderRadius: 6, borderWidth: 1, paddingVertical: 4, alignItems: 'center' },
  ratingLabel: { fontSize: 9, fontWeight: '700' },
  ratingValue: { fontSize: 14, fontWeight: '900' },
  traitsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  traitBadge: { borderRadius: 4, borderWidth: 1, paddingHorizontal: 6, paddingVertical: 2 },
  traitText: { fontSize: 10, fontWeight: '700' },
  arsenalLabel: { fontSize: 9, fontWeight: '700', color: Colors.textMuted, letterSpacing: 0.5, textTransform: 'uppercase' },
  arsenalRow: { gap: 6 },
  arsenalChip: { flexDirection: 'row', alignItems: 'center', gap: 4, borderRadius: 6, borderWidth: 1, paddingHorizontal: 8, paddingVertical: 5 },
  arsenalDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.blueDeep },
  arsenalName: { fontSize: 11 },
  arsenalVelo: { fontSize: 10, fontWeight: '600' },
  arsenalSpin: { fontSize: 9.5, color: Colors.redMild, fontWeight: '700' },
});
