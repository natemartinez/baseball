import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import type { Gameday2DPitchPacket, CountCategory, SituationCategory } from '../../types/gameday';
import { Colors } from '../../theme/colors';
import { getBaselineForCommand } from '../../services/gamedayMath';

interface CalibrationDiagnosticsColumnProps {
  packets: Gameday2DPitchPacket[];
  currentPitcher: { name: string; control?: number; break_rating?: number } | null;
  countFilter: CountCategory;
  situationFilter: string;
  batterFilter: string;
  pitchTypeFilter: string;
  onUpdateFilters: (filters: {
    countFilter?: CountCategory;
    situationFilter?: string;
    batterFilter?: string;
    pitchTypeFilter?: string;
  }) => void;
  onRunFastCalibration: () => void;
}

/**
 * Column 3: Rating-Tier Baseline & Calibration Diagnostics
 * Compares cumulative pitch telemetry against empirical benchmark distributions,
 * highlights Heart Zone leaks, and provides situational & batter filtering.
 */
export function CalibrationDiagnosticsColumn({
  packets,
  currentPitcher,
  countFilter,
  situationFilter,
  batterFilter,
  pitchTypeFilter,
  onUpdateFilters,
  onRunFastCalibration,
}: CalibrationDiagnosticsColumnProps) {
  const commandRating = currentPitcher?.control ?? 68;
  const baseline = getBaselineForCommand(commandRating);

  // Apply filters to calculate diagnostic metrics
  const filteredPackets = packets.filter((p) => {
    // Count filter
    if (countFilter === 'AHEAD' && p.meta.count.strikes !== 2) return false;
    if (countFilter === 'BEHIND' && !(p.meta.count.balls >= 2 && p.meta.count.strikes < 2)) return false;
    if (countFilter === 'FULL' && !(p.meta.count.balls === 3 && p.meta.count.strikes === 2)) return false;
    if (countFilter === 'EVEN' && !(p.meta.count.balls === p.meta.count.strikes)) return false;

    // Situation filter
    if (situationFilter !== 'ALL' && p.meta.situationCategory !== situationFilter) return false;

    // Batter filter
    if (batterFilter !== 'ALL' && p.meta.batterName !== batterFilter) return false;

    // Pitch type filter
    if (pitchTypeFilter !== 'ALL' && !p.strategy.selectedPitch.toLowerCase().includes(pitchTypeFilter.toLowerCase())) return false;

    return true;
  });

  const sampleSize = filteredPackets.length;

  // Compute actual metrics
  let shadowIntended = 0;
  let shadowHit = 0;
  let nonHeartIntended = 0;
  let heartLeaks = 0;
  let totalMissInches = 0;
  let aheadPitches = 0;
  let aheadOffspeed = 0;

  for (const p of filteredPackets) {
    if (p.intent.intendedZone === 'SHADOW') shadowIntended++;
    if (p.intent.intendedZone !== 'HEART') nonHeartIntended++;

    if (p.intent.intendedZone === 'SHADOW' && p.execution.hitShadowZoneTarget) shadowHit++;
    if (p.execution.isHeartZoneLeak) heartLeaks++;

    totalMissInches += p.execution.radialMissInches;

    if (p.meta.count.strikes === 2) {
      aheadPitches++;
      const name = p.strategy.selectedPitch.toLowerCase();
      if (name.includes('sweeper') || name.includes('slider') || name.includes('curve') || name.includes('change')) {
        aheadOffspeed++;
      }
    }
  }

  const actShadowAcc = shadowIntended > 0 ? (shadowHit / shadowIntended) * 100 : baseline.expectedShadowAccuracy;
  const actHeartLeaks = nonHeartIntended > 0 ? (heartLeaks / nonHeartIntended) * 100 : baseline.expectedHeartLeaks;
  const actMissRadius = sampleSize > 0 ? totalMissInches / sampleSize : baseline.expectedMissRadiusInches;
  const actAheadOffspeed = aheadPitches > 0 ? (aheadOffspeed / aheadPitches) * 100 : baseline.expectedAheadOffspeedPct;

  const isLeakingAlert = actHeartLeaks > baseline.expectedHeartLeaks + 2.0;

  // Extract unique batters from session
  const uniqueBatters = Array.from(new Set(packets.map((p) => p.meta.batterName)));

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      {/* Header */}
      <View style={styles.headerBox}>
        <Text style={styles.columnTitle}>COLUMN 3: CALIBRATION & DIAGNOSTICS</Text>
        <TouchableOpacity onPress={onRunFastCalibration} style={styles.runCalBtn}>
          <Text style={styles.runCalText}>⚡ Fast Cal (100)</Text>
        </TouchableOpacity>
      </View>

      {/* Pitcher Profile Banner */}
      <View style={styles.profileCard}>
        <Text style={styles.pitcherName}>{currentPitcher?.name ?? 'Nolan McLean'} (OVR: 88)</Text>
        <View style={styles.ratingsRow}>
          <Text style={styles.ratingChip}>Cmd: {commandRating}</Text>
          <Text style={styles.ratingChip}>Brk: {currentPitcher?.break_rating ?? 99}</Text>
          <Text style={styles.ratingChip}>Pitches: {packets.length}</Text>
        </View>
      </View>

      {/* Calibration Comparison Table */}
      <View style={styles.tableCard}>
        <View style={styles.tableHeaderRow}>
          <Text style={[styles.colHeader, { flex: 2 }]}>METRIC</Text>
          <Text style={[styles.colHeader, { flex: 1, textAlign: 'center' }]}>EXP</Text>
          <Text style={[styles.colHeader, { flex: 1, textAlign: 'center' }]}>ACT</Text>
        </View>

        <MetricRow label="Shadow Acc:" exp={`${baseline.expectedShadowAccuracy.toFixed(1)}%`} act={`${actShadowAcc.toFixed(1)}%`} />
        <MetricRow
          label="Heart Leaks:"
          exp={`${baseline.expectedHeartLeaks.toFixed(1)}%`}
          act={`${actHeartLeaks.toFixed(1)}%${isLeakingAlert ? '*' : ''}`}
          highlight={isLeakingAlert}
        />
        <MetricRow label="Miss Radius:" exp={`${baseline.expectedMissRadiusInches.toFixed(2)}"`} act={`${actMissRadius.toFixed(2)}"`} />
        <MetricRow label="Ahead Offspd:" exp={`${baseline.expectedAheadOffspeedPct.toFixed(1)}%`} act={`${actAheadOffspeed.toFixed(1)}%`} />

        {isLeakingAlert && (
          <View style={styles.alertBox}>
            <Text style={styles.alertText}>*ALERT: Leaking over plate (+{(actHeartLeaks - baseline.expectedHeartLeaks).toFixed(1)}% vs baseline)</Text>
          </View>
        )}
      </View>

      {/* Filter by Situation */}
      <View style={styles.filterSection}>
        <Text style={styles.filterLabel}>FILTER BY SITUATION</Text>
        <View style={styles.chipsRow}>
          {(['ALL', 'RISP', 'DOUBLE_PLAY', 'TWO_OUTS', 'BASES_LOADED'] as const).map((s) => (
            <TouchableOpacity
              key={s}
              onPress={() => onUpdateFilters({ situationFilter: s })}
              style={[styles.chip, situationFilter === s && styles.chipActive]}
            >
              <Text style={[styles.chipText, situationFilter === s && styles.chipTextActive]}>
                {s.replace(/_/g, ' ')}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Filter by Count */}
      <View style={styles.filterSection}>
        <Text style={styles.filterLabel}>FILTER BY COUNT</Text>
        <View style={styles.chipsRow}>
          {(['ALL', 'AHEAD', 'BEHIND', 'FULL', 'EVEN'] as CountCategory[]).map((c) => (
            <TouchableOpacity
              key={c}
              onPress={() => onUpdateFilters({ countFilter: c })}
              style={[styles.chip, countFilter === c && styles.chipActive]}
            >
              <Text style={[styles.chipText, countFilter === c && styles.chipTextActive]}>
                {c === 'AHEAD' ? 'Ahead (2 Strikes)' : c === 'BEHIND' ? 'Behind (3 Balls)' : c}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Filter by Batter */}
      {uniqueBatters.length > 0 && (
        <View style={styles.filterSection}>
          <Text style={styles.filterLabel}>FILTER BY BATTER</Text>
          <View style={styles.chipsRow}>
            {['ALL', ...uniqueBatters].map((b) => (
              <TouchableOpacity
                key={b}
                onPress={() => onUpdateFilters({ batterFilter: b })}
                style={[styles.chip, batterFilter === b && styles.chipActive]}
              >
                <Text style={[styles.chipText, batterFilter === b && styles.chipTextActive]}>{b}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* Filter by Pitch Type */}
      <View style={styles.filterSection}>
        <Text style={styles.filterLabel}>FILTER BY PITCH TYPE</Text>
        <View style={styles.chipsRow}>
          {['ALL', 'Fastball', 'Sweeper', 'Sinker', 'Curveball'].map((pt) => {
            const shortLabel = pt === 'Fastball' ? '4SFB' : pt === 'Sweeper' ? 'SL' : pt === 'Sinker' ? 'SI' : pt === 'Curveball' ? 'CB' : 'ALL';
            return (
              <TouchableOpacity
                key={pt}
                onPress={() => onUpdateFilters({ pitchTypeFilter: pt === 'ALL' ? 'ALL' : pt })}
                style={[styles.chip, (pitchTypeFilter === pt || (pitchTypeFilter === 'ALL' && pt === 'ALL')) && styles.chipActive]}
              >
                <Text style={[styles.chipText, (pitchTypeFilter === pt || (pitchTypeFilter === 'ALL' && pt === 'ALL')) && styles.chipTextActive]}>
                  {shortLabel}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>
    </ScrollView>
  );
}

function MetricRow({ label, exp, act, highlight }: { label: string; exp: string; act: string; highlight?: boolean }) {
  return (
    <View style={[styles.metricRow, highlight && styles.metricRowHighlight]}>
      <Text style={[styles.metricLabel, { flex: 2 }]}>{label}</Text>
      <Text style={[styles.metricVal, { flex: 1, textAlign: 'center', color: Colors.textSecondary }]}>{exp}</Text>
      <Text style={[styles.metricVal, { flex: 1, textAlign: 'center', color: highlight ? Colors.redLight : '#FFF', fontWeight: '800' }]}>{act}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bgDeep },
  content: { padding: 10, gap: 10 },
  headerBox: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 },
  columnTitle: { color: Colors.textSecondary, fontSize: 10, fontWeight: '800', letterSpacing: 0.8 },
  runCalBtn: { backgroundColor: 'rgba(0, 230, 118, 0.15)', borderWidth: 1, borderColor: Colors.green, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  runCalText: { color: Colors.greenLight, fontSize: 9, fontWeight: '800' },
  profileCard: { backgroundColor: Colors.bgSurface, borderRadius: 8, padding: 10, borderWidth: 1, borderColor: Colors.borderPrimary, gap: 6 },
  pitcherName: { color: '#FFF', fontSize: 12, fontWeight: '800' },
  ratingsRow: { flexDirection: 'row', gap: 6 },
  ratingChip: { backgroundColor: Colors.bgCard, color: Colors.textSecondary, fontSize: 10, fontWeight: '700', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  tableCard: { backgroundColor: Colors.bgSurface, borderRadius: 8, padding: 10, borderWidth: 1, borderColor: Colors.borderPrimary, gap: 4 },
  tableHeaderRow: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: Colors.borderDivider, paddingBottom: 4, marginBottom: 2 },
  colHeader: { color: Colors.textMuted, fontSize: 9, fontWeight: '800', letterSpacing: 0.6 },
  metricRow: { flexDirection: 'row', paddingVertical: 3, alignItems: 'center' },
  metricRowHighlight: { backgroundColor: 'rgba(239, 68, 68, 0.12)', borderRadius: 4, paddingHorizontal: 4 },
  metricLabel: { color: Colors.textSecondary, fontSize: 11 },
  metricVal: { fontSize: 11 },
  alertBox: { backgroundColor: 'rgba(239, 68, 68, 0.2)', borderWidth: 1, borderColor: '#EF4444', borderRadius: 4, padding: 6, marginTop: 4, alignItems: 'center' },
  alertText: { color: '#FCA5A5', fontSize: 10, fontWeight: '800' },
  filterSection: { gap: 4 },
  filterLabel: { color: Colors.textMuted, fontSize: 9, fontWeight: '800', letterSpacing: 0.6 },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 4 },
  chip: { backgroundColor: Colors.bgSurface, borderWidth: 1, borderColor: Colors.borderPrimary, borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 },
  chipActive: { backgroundColor: Colors.blueMid, borderColor: Colors.blue },
  chipText: { color: Colors.textSecondary, fontSize: 10, fontWeight: '600' },
  chipTextActive: { color: '#FFF', fontWeight: '800' },
});
