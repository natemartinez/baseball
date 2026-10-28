import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { BattedBallTelemetry } from '../types/api';
import { Colors } from '../theme/colors';

interface BattedBallMetricsWidgetProps {
  telemetry?: BattedBallTelemetry | null;
}

function formatSpray(angle: number): string {
  if (Math.abs(angle) < 0.5) return 'CF';
  return `${angle > 0 ? 'RF' : 'LF'} ${Math.abs(angle).toFixed(0)}°`;
}

export const BattedBallMetricsWidget = React.memo(function BattedBallMetricsWidget({
  telemetry,
}: BattedBallMetricsWidgetProps) {
  if (!telemetry) return null;

  return (
    <View pointerEvents="none" style={styles.card}>
      <View style={styles.header}>
        <View style={styles.dot} />
        <Text style={styles.title}>BATTED BALL</Text>
      </View>

      <View style={styles.primaryGrid}>
        <Metric label="EXIT VELO" value={`${telemetry.exit_velocity_mph.toFixed(1)} MPH`} />
        <Metric label="LAUNCH" value={`${telemetry.launch_angle_deg.toFixed(1)}°`} />
        <Metric label="DISTANCE" value={`${telemetry.distance_ft.toFixed(0)} FT`} />
        <Metric label="PEAK HEIGHT" value={`${telemetry.apex_height_ft.toFixed(0)} FT`} />
      </View>

      <View style={styles.secondaryRow}>
        <Metric
          compact
          label="HANG TIME"
          value={`${telemetry.hang_time_s.toFixed(2)} S`}
        />
        <Metric
          compact
          label="SPRAY"
          value={formatSpray(telemetry.spray_angle_deg)}
        />
      </View>
    </View>
  );
});

function Metric({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: string;
  compact?: boolean;
}) {
  return (
    <View style={[styles.metric, compact && styles.metricCompact]}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, compact && styles.metricValueCompact]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: 'rgba(19, 27, 36, 0.92)',
    borderColor: Colors.borderSecondary,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    width: 280,
    gap: 6,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.amber,
  },
  title: {
    color: Colors.textSecondary,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1.4,
  },
  primaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  metric: {
    width: '50%',
    paddingVertical: 2,
  },
  metricCompact: {
    flex: 1,
    width: 'auto',
  },
  metricLabel: {
    color: Colors.textMuted,
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  metricValue: {
    color: Colors.textPrimary,
    fontSize: 17,
    fontWeight: '900',
    letterSpacing: 0.2,
  },
  metricValueCompact: {
    fontSize: 13,
  },
  secondaryRow: {
    flexDirection: 'row',
    borderTopColor: Colors.borderPrimary,
    borderTopWidth: 1,
    paddingTop: 5,
  },
});
