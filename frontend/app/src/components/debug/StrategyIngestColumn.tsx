import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import type { Gameday2DPitchPacket } from '../../types/gameday';
import { Colors } from '../../theme/colors';
import { getPitchTypeColor } from '../../services/gamedayMath';

interface StrategyIngestColumnProps {
  packet: Gameday2DPitchPacket | null;
}

/**
 * Column 1: Strategy & Ingest Panel
 * Visualizes game context, base weights pi_0, dynamic adaptation modifiers W_t,
 * and the decision engine's pitch selection.
 */
export function StrategyIngestColumn({ packet }: StrategyIngestColumnProps) {
  if (!packet) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyTitle}>NO PITCH TELEMETRY</Text>
        <Text style={styles.emptyDesc}>Throw a pitch or run calibration to view strategy trace.</Text>
      </View>
    );
  }

  const { meta, strategy, intent } = packet;
  const count = meta.count;
  const runners = meta.runnersOnBase;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      {/* Header */}
      <View style={styles.headerBox}>
        <Text style={styles.columnTitle}>COLUMN 1: STRATEGY & INGEST</Text>
        <View style={styles.situationBadge}>
          <Text style={styles.situationText}>{meta.situationCategory.replace(/_/g, ' ')}</Text>
        </View>
      </View>

      {/* Game State Card */}
      <View style={styles.card}>
        <Text style={styles.cardLabel}>GAME CONTEXT</Text>
        <View style={styles.metaRow}>
          <Text style={styles.metaKey}>State:</Text>
          <Text style={styles.metaVal}>
            {count.balls}-{count.strikes}, {count.outs} {count.outs === 1 ? 'Out' : 'Outs'} (Inn {meta.inning} {meta.isTopInning ? '▲' : '▼'})
          </Text>
        </View>
        <View style={styles.metaRow}>
          <Text style={styles.metaKey}>Runners:</Text>
          <Text style={styles.metaVal}>
            [1B: {runners.first ? '●' : '○'}, 2B: {runners.second ? '●' : '○'}, 3B: {runners.third ? '●' : '○'}]
          </Text>
        </View>
        <View style={styles.metaRow}>
          <Text style={styles.metaKey}>Batter:</Text>
          <Text style={styles.metaVal}>{meta.batterName}</Text>
        </View>
        <View style={styles.metaRow}>
          <Text style={styles.metaKey}>Pitcher:</Text>
          <Text style={styles.metaVal}>{meta.pitcherName} (#{meta.pitchNumber})</Text>
        </View>
      </View>

      {/* Active Strategy Plan */}
      <View style={styles.card}>
        <Text style={styles.cardLabel}>AI STRATEGY SELECTION</Text>
        <Text style={styles.strategyName}>{strategy.strategyName}</Text>
        <Text style={styles.strategyRationale}>{strategy.rationale}</Text>
      </View>

      {/* Repertoire Weights */}
      <View style={styles.card}>
        <Text style={styles.cardLabel}>STRATEGY PROBABILITIES (π₀)</Text>
        {Object.entries(strategy.repertoireProbabilities).map(([pitchName, prob]) => {
          const isSelected = pitchName === strategy.selectedPitch;
          const pct = Math.round(prob * 100);
          const color = getPitchTypeColor(pitchName);

          return (
            <View key={pitchName} style={styles.probRow}>
              <View style={styles.probHeader}>
                <View style={styles.pitchNameRow}>
                  <View style={[styles.dotIndicator, { backgroundColor: color }]} />
                  <Text style={[styles.pitchName, isSelected && styles.pitchNameSelected]}>
                    {pitchName}
                  </Text>
                </View>
                <View style={styles.probTagRow}>
                  <Text style={[styles.probPct, isSelected && { color: Colors.greenLight }]}>{pct}%</Text>
                  {isSelected && <Text style={styles.selectedBadge}>[Selected]</Text>}
                </View>
              </View>
              <View style={styles.progressBarBg}>
                <View style={[styles.progressBarFill, { width: `${Math.min(100, Math.max(5, pct))}%`, backgroundColor: color }]} />
              </View>
            </View>
          );
        })}
      </View>

      {/* Dynamic Adaptation Multipliers W_t */}
      <View style={styles.card}>
        <Text style={styles.cardLabel}>DYNAMIC ADAPTATION MODIFIER (W_t)</Text>
        <View style={styles.decayRow}>
          <Text style={styles.decayPitch}>{strategy.selectedPitch}</Text>
          <View style={[styles.decayBadge, strategy.dynamicModifier >= 1.0 ? styles.hotBadge : styles.coldBadge]}>
            <Text style={[styles.decayText, strategy.dynamicModifier >= 1.0 ? styles.hotText : styles.coldText]}>
              W_t: {strategy.dynamicModifier.toFixed(2)} ({strategy.dynamicModifier >= 1.0 ? 'Hot' : 'Cold'})
            </Text>
          </View>
        </View>
        <Text style={styles.decayDesc}>
          Pitch selection decay weights adjust dynamically to pitch-mix sequencing and batter plate adjustments.
        </Text>
      </View>

      {/* Ingest Target Info */}
      <View style={styles.card}>
        <Text style={styles.cardLabel}>INGEST TARGET</Text>
        <View style={styles.metaRow}>
          <Text style={styles.metaKey}>Target Zone:</Text>
          <Text style={[styles.metaVal, { color: Colors.amberLight }]}>{intent.intendedZone}</Text>
        </View>
        <View style={styles.metaRow}>
          <Text style={styles.metaKey}>Planned Speed:</Text>
          <Text style={styles.metaVal}>{intent.targetSpeedMph} MPH</Text>
        </View>
        <View style={styles.metaRow}>
          <Text style={styles.metaKey}>Manual Override:</Text>
          <Text style={[styles.metaVal, { color: intent.isManualOverride ? Colors.blueSky : Colors.textMuted }]}>
            {intent.isManualOverride ? 'YES (Custom Target)' : 'NO (Auto Repertoire)'}
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bgDeep },
  content: { padding: 10, gap: 10 },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  emptyTitle: { color: Colors.textSecondary, fontSize: 13, fontWeight: '800', letterSpacing: 1 },
  emptyDesc: { color: Colors.textMuted, fontSize: 11, textAlign: 'center', marginTop: 6 },
  headerBox: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 },
  columnTitle: { color: Colors.textSecondary, fontSize: 10, fontWeight: '800', letterSpacing: 0.8 },
  situationBadge: { backgroundColor: 'rgba(2, 119, 189, 0.25)', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, borderWidth: 1, borderColor: Colors.blueMid },
  situationText: { color: Colors.blue, fontSize: 9, fontWeight: '800' },
  card: {
    backgroundColor: Colors.bgSurface,
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    gap: 6,
  },
  cardLabel: { color: Colors.textMuted, fontSize: 9, fontWeight: '800', letterSpacing: 0.6, textTransform: 'uppercase' },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  metaKey: { color: Colors.textSecondary, fontSize: 11 },
  metaVal: { color: '#FFF', fontSize: 11, fontWeight: '600' },
  strategyName: { color: Colors.blueSky, fontSize: 12, fontWeight: '800' },
  strategyRationale: { color: Colors.textSecondary, fontSize: 11, lineHeight: 15 },
  probRow: { gap: 3, marginVertical: 2 },
  probHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  pitchNameRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dotIndicator: { width: 6, height: 6, borderRadius: 3 },
  pitchName: { color: Colors.textSecondary, fontSize: 11 },
  pitchNameSelected: { color: '#FFF', fontWeight: '800' },
  probTagRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  probPct: { color: Colors.textPrimary, fontSize: 11, fontWeight: '700' },
  selectedBadge: { color: Colors.greenLight, fontSize: 9, fontWeight: '800' },
  progressBarBg: { height: 4, backgroundColor: Colors.bgCard, borderRadius: 2, overflow: 'hidden' },
  progressBarFill: { height: '100%', borderRadius: 2 },
  decayRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  decayPitch: { color: '#FFF', fontSize: 11, fontWeight: '700' },
  decayBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, borderWidth: 1 },
  hotBadge: { backgroundColor: 'rgba(239, 68, 68, 0.2)', borderColor: '#EF4444' },
  coldBadge: { backgroundColor: 'rgba(59, 130, 246, 0.2)', borderColor: '#3B82F6' },
  decayText: { fontSize: 10, fontWeight: '800' },
  hotText: { color: '#FCA5A5' },
  coldText: { color: '#93C5FD' },
  decayDesc: { color: Colors.textMuted, fontSize: 10, lineHeight: 13 },
});
