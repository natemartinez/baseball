import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import type { BatterInfo, PitchDetails, PitchResultType } from '../types/api';
import { STRIKE_ZONES } from '../types/api';
import { Colors } from '../theme/colors';

interface StrikeZoneGridWidgetProps {
  selectedZone: string;
  onSelectZone: (zone: string) => void;
  currentBatter: BatterInfo;
  latestPitch?: PitchDetails | null;
}

/**
 * Core UI Component 2: Interactive Strike Zone Grid (3×3 + Chase Border)
 * Displays pitch location, target selection, and batter SLG heatmap.
 *
 * Ported from StrikeZoneGridWidget.kt.
 */
export function StrikeZoneGridWidget({
  selectedZone,
  onSelectZone,
  currentBatter,
  latestPitch,
}: StrikeZoneGridWidgetProps) {
  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.sectionLabel}>STRIKE ZONE (CATCHER'S VIEW)</Text>
          <Text style={styles.targetText}>Target: {selectedZone || '—'}</Text>
        </View>
        <View style={styles.legendRow}>
          <View style={[styles.legendDot, { backgroundColor: Colors.baseDefault }]} />
          <Text style={styles.legendLabel}>Cold</Text>
          <View style={[styles.legendDot, { backgroundColor: '#E65100' }]} />
          <Text style={styles.legendLabel}>Hot</Text>
          <View style={[styles.legendDot, { backgroundColor: Colors.homeRunRed }]} />
          <Text style={[styles.legendLabel, { color: Colors.redLight, fontWeight: '700' }]}>.800+ SLG</Text>
        </View>
      </View>

      {/* Grid Box */}
      <View style={styles.gridBox}>
        {/* Chase High */}
        <ChaseZonePill
          zoneId={STRIKE_ZONES.CHASE_HIGH}
          label="CHASE HIGH"
          isSelected={selectedZone === STRIKE_ZONES.CHASE_HIGH}
          hasPitch={latestPitch?.actual_zone === STRIKE_ZONES.CHASE_HIGH}
          onSelect={onSelectZone}
          horizontal
        />

        {/* Middle row: Chase In + 3×3 + Chase Away */}
        <View style={styles.middleRow}>
          <ChaseZonePill
            zoneId={STRIKE_ZONES.CHASE_IN}
            label={'CHASE\nIN'}
            isSelected={selectedZone === STRIKE_ZONES.CHASE_IN}
            hasPitch={latestPitch?.actual_zone === STRIKE_ZONES.CHASE_IN}
            onSelect={onSelectZone}
            horizontal={false}
          />
          <InnerStrikeZone3x3
            selectedZone={selectedZone}
            onSelectZone={onSelectZone}
            currentBatter={currentBatter}
            latestPitch={latestPitch}
          />
          <ChaseZonePill
            zoneId={STRIKE_ZONES.CHASE_AWAY}
            label={'CHASE\nAWAY'}
            isSelected={selectedZone === STRIKE_ZONES.CHASE_AWAY}
            hasPitch={latestPitch?.actual_zone === STRIKE_ZONES.CHASE_AWAY}
            onSelect={onSelectZone}
            horizontal={false}
          />
        </View>

        {/* Chase Low */}
        <ChaseZonePill
          zoneId={STRIKE_ZONES.CHASE_LOW}
          label="CHASE LOW"
          isSelected={selectedZone === STRIKE_ZONES.CHASE_LOW}
          hasPitch={latestPitch?.actual_zone === STRIKE_ZONES.CHASE_LOW}
          onSelect={onSelectZone}
          horizontal
        />
      </View>

      {/* Latest pitch summary */}
      {latestPitch && <PitchOutcomeSummaryBadge latestPitch={latestPitch} />}
    </View>
  );
}

// ─── Inner 3×3 Strike Zone ───────────────────────────────────────────────────

const INNER_GRID = [
  [
    { id: STRIKE_ZONES.UPPER_IN, label: 'Upper-In' },
    { id: STRIKE_ZONES.UPPER_MIDDLE, label: 'Upper-Mid' },
    { id: STRIKE_ZONES.UPPER_AWAY, label: 'Upper-Away' },
  ],
  [
    { id: STRIKE_ZONES.MIDDLE_IN, label: 'Mid-In' },
    { id: STRIKE_ZONES.HEART, label: 'HEART' },
    { id: STRIKE_ZONES.MIDDLE_AWAY, label: 'Mid-Away' },
  ],
  [
    { id: STRIKE_ZONES.LOWER_IN, label: 'Low-In' },
    { id: STRIKE_ZONES.LOWER_MIDDLE, label: 'Low-Mid' },
    { id: STRIKE_ZONES.LOWER_AWAY, label: 'Low-Away' },
  ],
];

function InnerStrikeZone3x3({
  selectedZone,
  onSelectZone,
  currentBatter,
  latestPitch,
}: {
  selectedZone: string;
  onSelectZone: (z: string) => void;
  currentBatter: BatterInfo;
  latestPitch?: PitchDetails | null;
}) {
  return (
    <View style={styles.innerGrid}>
      {INNER_GRID.map((row) => (
        <View key={row[0].id} style={styles.innerRow}>
          {row.map((cell) => (
            <InnerZoneCell
              key={cell.id}
              zoneId={cell.id}
              displayLabel={cell.label}
              selectedZone={selectedZone}
              currentBatter={currentBatter}
              latestPitch={latestPitch}
              onSelect={onSelectZone}
            />
          ))}
        </View>
      ))}
    </View>
  );
}

function InnerZoneCell({
  zoneId,
  displayLabel,
  selectedZone,
  currentBatter,
  latestPitch,
  onSelect,
}: {
  zoneId: string;
  displayLabel: string;
  selectedZone: string;
  currentBatter: BatterInfo;
  latestPitch?: PitchDetails | null;
  onSelect: (z: string) => void;
}) {
  const isSelected = selectedZone === zoneId;
  const hasPitch = latestPitch?.actual_zone === zoneId;
  const slg = currentBatter.hot_zones[zoneId] ?? 0.35;

  const heatBg =
    slg >= 0.8
      ? 'rgba(183, 28, 28, 0.8)'
      : slg >= 0.6
        ? 'rgba(191, 54, 12, 0.8)'
        : slg >= 0.45
          ? 'rgba(255, 143, 0, 0.6)'
          : 'rgba(55, 71, 79, 0.33)';

  const slgLabel = '.' + String(Math.floor(slg * 1000)).padStart(3, '0');

  return (
    <TouchableOpacity
      onPress={() => onSelect(zoneId)}
      activeOpacity={0.75}
      style={[
        styles.innerCell,
        {
          backgroundColor: isSelected ? 'rgba(2, 136, 209, 0.5)' : heatBg,
          borderColor: isSelected ? Colors.blue : 'rgba(144, 164, 174, 0.27)',
          borderWidth: isSelected ? 2 : 1,
        },
      ]}
    >
      <Text style={[styles.cellLabel, { fontWeight: zoneId === STRIKE_ZONES.HEART ? '900' : '400' }]}>
        {displayLabel}
      </Text>
      <Text style={[styles.slgLabel, { color: slg >= 0.6 ? Colors.yellow : Colors.textSecondary }]}>
        {slgLabel}
      </Text>
      {hasPitch && latestPitch && <PitchLocationMarker pitch={latestPitch} />}
    </TouchableOpacity>
  );
}

// ─── Chase Zone Pill ──────────────────────────────────────────────────────────

function ChaseZonePill({
  zoneId, label, isSelected, hasPitch, onSelect, horizontal,
}: {
  zoneId: string;
  label: string;
  isSelected: boolean;
  hasPitch: boolean;
  onSelect: (z: string) => void;
  horizontal: boolean;
}) {
  return (
    <TouchableOpacity
      onPress={() => onSelect(zoneId)}
      activeOpacity={0.75}
      style={[
        styles.chasePill,
        horizontal ? styles.chasePillH : styles.chasePillV,
        {
          backgroundColor: isSelected ? 'rgba(2, 136, 209, 0.35)' : '#1E2833',
          borderColor: isSelected ? Colors.blue : Colors.borderSecondary,
          borderWidth: isSelected ? 2 : 1,
        },
      ]}
    >
      <Text style={[styles.chaseLabel, { color: isSelected ? Colors.blueSky : Colors.textMuted }]}>
        {label}
      </Text>
      {hasPitch && <View style={styles.chasePitchDot} />}
    </TouchableOpacity>
  );
}

// ─── Pitch Markers ────────────────────────────────────────────────────────────

function PitchLocationMarker({ pitch }: { pitch: PitchDetails }) {
  const color = pitchMarkerColor(pitch.pitch_result);
  return (
    <View style={[styles.pitchMarker, { backgroundColor: color }]}>
      <Text style={styles.pitchMarkerText}>{Math.round(pitch.velocity_mph)}</Text>
    </View>
  );
}

function PitchOutcomeSummaryBadge({ latestPitch }: { latestPitch: PitchDetails }) {
  const color = outcomeSummaryColor(latestPitch.pitch_result);
  return (
    <View style={[styles.summaryBadge, { borderColor: color + '99' }]}>
      <View style={[styles.summaryDot, { backgroundColor: color }]} />
      <Text style={styles.summaryText} numberOfLines={2}>
        {latestPitch.pitch_name} ({latestPitch.velocity_mph} mph, {latestPitch.spin_rpm} RPM) in{' '}
        {latestPitch.actual_zone} → {latestPitch.pitch_result.replace(/_/g, ' ')}
      </Text>
    </View>
  );
}

function pitchMarkerColor(result: PitchResultType): string {
  switch (result) {
    case 'HOME_RUN':
    case 'DOUBLE':
    case 'SINGLE':
    case 'TRIPLE':
      return Colors.red;
    case 'SWINGING_STRIKE':
    case 'CALLED_STRIKE':
      return '#FF9100';
    case 'FOUL':
      return '#FFEA00';
    case 'BALL':
      return Colors.green;
    default:
      return '#2979FF';
  }
}

function outcomeSummaryColor(result: PitchResultType): string {
  switch (result) {
    case 'HOME_RUN': return Colors.red;
    case 'SWINGING_STRIKE': return '#FF9100';
    case 'CALLED_STRIKE': return Colors.amber;
    case 'BALL': return Colors.green;
    case 'FOUL': return '#FFEA00';
    default: return Colors.blue;
  }
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#161E27',
    borderRadius: 12,
    padding: 14,
    gap: 10,
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', width: '100%' },
  sectionLabel: { fontSize: 9, fontWeight: '700', color: Colors.textSecondary, letterSpacing: 1.0, textTransform: 'uppercase' },
  targetText: { fontSize: 12, fontWeight: '600', color: Colors.blueLight },
  legendRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot: { width: 8, height: 8, borderRadius: 2 },
  legendLabel: { fontSize: 10, color: Colors.textMuted },
  // Grid outer box
  gridBox: {
    width: '92%',
    backgroundColor: Colors.bgInput,
    borderRadius: 8,
    padding: 6,
    gap: 4,
  },
  middleRow: { flexDirection: 'row', alignItems: 'stretch', gap: 4, height: 180 },
  // Inner 3×3
  innerGrid: { flex: 1, borderWidth: 2, borderColor: Colors.textPrimary, borderRadius: 4, backgroundColor: '#1B2430', padding: 2, gap: 2 },
  innerRow: { flex: 1, flexDirection: 'row', gap: 2 },
  innerCell: { flex: 1, borderRadius: 3, alignItems: 'center', justifyContent: 'center', padding: 2 },
  cellLabel: { fontSize: 9, color: '#FFF', textAlign: 'center' },
  slgLabel: { fontSize: 8.5, fontWeight: '700', textAlign: 'center' },
  // Pitch marker
  pitchMarker: { position: 'absolute', width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: '#FFF', alignItems: 'center', justifyContent: 'center', elevation: 4 },
  pitchMarkerText: { color: '#000', fontSize: 7.5, fontWeight: '900' },
  // Chase pill
  chasePill: { borderRadius: 4, alignItems: 'center', justifyContent: 'center', padding: 4 },
  chasePillH: { height: 26 },
  chasePillV: { width: 28 },
  chaseLabel: { fontSize: 8.5, fontWeight: '700', textAlign: 'center' },
  chasePitchDot: { width: 14, height: 14, borderRadius: 7, backgroundColor: Colors.green, borderWidth: 2, borderColor: '#FFF', position: 'absolute' },
  // Summary badge
  summaryBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#0A0E13', borderRadius: 6, borderWidth: 1, paddingHorizontal: 8, paddingVertical: 4, width: '100%' },
  summaryDot: { width: 8, height: 8, borderRadius: 4 },
  summaryText: { flex: 1, fontSize: 11, fontWeight: '600', color: '#FFF' },
});
