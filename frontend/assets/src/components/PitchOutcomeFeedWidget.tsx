import React from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import type { PitchDetails, PitchResultType } from '../types/api';
import { Colors } from '../theme/colors';

interface PitchOutcomeFeedWidgetProps {
  pitches: PitchDetails[];
}

/**
 * Core UI Component 5: Pitch Outcome Feed
 * Real-time event log with Statcast telemetry and play-by-play descriptions.
 *
 * Ported from PitchOutcomeFeedWidget.kt.
 */
export function PitchOutcomeFeedWidget({ pitches }: PitchOutcomeFeedWidgetProps) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.sectionLabel}>PITCH-BY-PITCH FEED • STATCAST TELEMETRY</Text>
        <Text style={styles.loggedCount}>{pitches.length} logged</Text>
      </View>

      {pitches.length === 0 ? (
        <View style={styles.emptyBox}>
          <Text style={styles.emptyText}>Ready for first pitch. Press 'Throw Pitch' or 'Sim At-Bat'.</Text>
        </View>
      ) : (
        <View style={styles.list}>
          {pitches.map((item, index) => (
            <PitchFeedItemCard
              key={`${pitches.length - index}-${item.pitch_name}-${index}`}
              pitch={item}
              pitchIndex={pitches.length - index}
            />
          ))}
        </View>
      )}
    </View>
  );
}

// ─── Single Pitch Feed Card ──────────────────────────────────────────────────

function PitchFeedItemCard({ pitch, pitchIndex }: { pitch: PitchDetails; pitchIndex: number }) {
  const badgeColor = resultBadgeColor(pitch.pitch_result);

  return (
    <View style={styles.feedCard}>
      {/* Header: sequence, pitch name, result badge */}
      <View style={styles.feedCardHeader}>
        <View style={styles.feedCardLeft}>
          <Text style={styles.seqNumber}>#{pitchIndex}</Text>
          <Text style={styles.pitchTitle} numberOfLines={1}>
            {pitch.pitch_name} ({pitch.velocity_mph} mph, {pitch.spin_rpm} RPM)
          </Text>
        </View>
        <View style={[styles.resultBadge, { backgroundColor: badgeColor + '33', borderColor: badgeColor }]}>
          <Text style={[styles.resultText, { color: badgeColor }]}>
            {pitch.pitch_result.replace(/_/g, ' ')}
          </Text>
        </View>
      </View>

      {/* Description */}
      <Text style={styles.description}>{pitch.description}</Text>

      {/* Statcast telemetry row */}
      <View style={styles.telemetryRow}>
        <Text style={styles.telemetryItem}>Zone: <Text style={{ color: Colors.blueSky }}>{pitch.actual_zone}</Text></Text>
        <Text style={[styles.telemetryItem, { color: pitch.batter_decision === 'SWING' ? Colors.amber : Colors.textSecondary }]}>
          {pitch.batter_decision}
        </Text>
        {pitch.exit_velocity_mph !== undefined && (
          <Text style={[styles.telemetryItem, { fontWeight: '700', color: pitch.exit_velocity_mph >= 100 ? Colors.redLight : Colors.yellow }]}>
            {Math.round(pitch.exit_velocity_mph)} mph EV
          </Text>
        )}
        {pitch.launch_angle_deg !== undefined && (
          <Text style={[styles.telemetryItem, { color: Colors.greenLight }]}>
            {Math.round(pitch.launch_angle_deg)}° LA
          </Text>
        )}
      </View>
    </View>
  );
}

function resultBadgeColor(result: PitchResultType): string {
  switch (result) {
    case 'HOME_RUN': return Colors.red;
    case 'DOUBLE':
    case 'TRIPLE': return Colors.redLight;
    case 'SINGLE': return Colors.green;
    case 'SWINGING_STRIKE': return '#FF9100';
    case 'CALLED_STRIKE': return Colors.amber;
    case 'FOUL': return '#FFEA00';
    case 'BALL': return Colors.greenDark;
    case 'IN_PLAY_OUT': return Colors.textMuted;
    case 'HIT_BY_PITCH': return '#AB47BC';
    default: return Colors.textMuted;
  }
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bgSurface,
    borderRadius: 12,
    padding: 14,
    gap: 8,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  sectionLabel: { fontSize: 9, fontWeight: '700', color: Colors.textSecondary, letterSpacing: 1.0, textTransform: 'uppercase' },
  loggedCount: { fontSize: 10, color: Colors.blueLight, fontWeight: '600' },
  emptyBox: { backgroundColor: Colors.bgInput, borderRadius: 8, height: 80, alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: Colors.textMuted, fontSize: 12 },
  list: { maxHeight: 240 },
  // Feed card
  feedCard: {
    backgroundColor: Colors.bgFeedItem,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    padding: 10,
    gap: 4,
  },
  feedCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 6 },
  feedCardLeft: { flexDirection: 'row', alignItems: 'center', gap: 4, flex: 1 },
  seqNumber: { fontSize: 11, fontWeight: '900', color: Colors.textSecondary },
  pitchTitle: { fontSize: 12, fontWeight: '700', color: '#FFF', flex: 1 },
  resultBadge: { borderRadius: 4, borderWidth: 1, paddingHorizontal: 6, paddingVertical: 2 },
  resultText: { fontSize: 9, fontWeight: '900' },
  description: { fontSize: 11.5, fontWeight: '500', color: Colors.textPrimary },
  telemetryRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  telemetryItem: { fontSize: 10, color: Colors.textSecondary },
});
