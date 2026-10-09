import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Path, Line, Circle, Rect } from 'react-native-svg';
import type { Bases, PlayerSummary } from '../types/api';
import { Colors } from '../theme/colors';

interface BaseballDiamondWidgetProps {
  bases: Bases;
  balls: number;
  strikes: number;
  outs: number;
}

/**
 * Core UI Component 1: Baseball Diamond Widget
 * Visualizes base runners on 1st, 2nd, and 3rd base, current outs (0-2 dots),
 * and count (Balls/Strikes) in a classic umpire indicator format.
 *
 * Ported from BaseballDiamondWidget.kt.
 */
export function BaseballDiamondWidget({ bases, balls, strikes, outs }: BaseballDiamondWidgetProps) {
  return (
    <View style={styles.container}>
      <CountOutsIndicator balls={balls} strikes={strikes} outs={outs} />
      <DiamondFieldGraphic bases={bases} />
      <RunnersSummaryColumn bases={bases} />
    </View>
  );
}

// ─── Count & Outs Indicator ─────────────────────────────────────────────────

function CountOutsIndicator({ balls, strikes, outs }: { balls: number; strikes: number; outs: number }) {
  return (
    <View style={styles.countColumn}>
      <Text style={styles.sectionLabel}>COUNT & OUTS</Text>
      <IndicatorRow label="B" total={3} lit={balls} litColor={Colors.green} litBorder={Colors.greenLight} />
      <IndicatorRow label="S" total={2} lit={strikes} litColor={Colors.amber} litBorder={Colors.amberLight} />
      <IndicatorRow label="O" total={2} lit={outs} litColor={Colors.red} litBorder={Colors.redLight} />
    </View>
  );
}

function IndicatorRow({
  label, total, lit, litColor, litBorder,
}: { label: string; total: number; lit: number; litColor: string; litBorder: string }) {
  return (
    <View style={styles.indicatorRow}>
      <Text style={styles.indicatorLetter}>{label}</Text>
      {Array.from({ length: total }, (_, i) => {
        const isLit = lit > i;
        return (
          <View
            key={i}
            style={[
              styles.dot,
              {
                backgroundColor: isLit ? litColor : Colors.baseDefault,
                borderColor: isLit ? litBorder : Colors.borderSecondary,
              },
            ]}
          />
        );
      })}
    </View>
  );
}

// ─── Diamond Field Graphic ───────────────────────────────────────────────────

const D_SIZE = 150;
const D_CENTER = D_SIZE / 2;
const MARGIN = 26;

// Base positions in SVG space (mirroring Kotlin dp → px mapping)
const HOME = { x: D_CENTER, y: D_SIZE - MARGIN };
const FIRST = { x: D_SIZE - MARGIN, y: D_CENTER };
const SECOND = { x: D_CENTER, y: MARGIN };
const THIRD = { x: MARGIN, y: D_CENTER };

function DiamondFieldGraphic({ bases }: { bases: Bases }) {
  const infieldPath = `M ${HOME.x} ${HOME.y} L ${FIRST.x} ${FIRST.y} L ${SECOND.x} ${SECOND.y} L ${THIRD.x} ${THIRD.y} Z`;

  return (
    <View style={styles.diamondContainer}>
      <Svg width={D_SIZE} height={D_SIZE}>
        {/* Infield dirt fill */}
        <Path d={infieldPath} fill={Colors.infieldClay} />
        {/* Chalk baselines */}
        <Line x1={HOME.x} y1={HOME.y} x2={FIRST.x} y2={FIRST.y} stroke="rgba(236,239,241,0.6)" strokeWidth={2} />
        <Line x1={FIRST.x} y1={FIRST.y} x2={SECOND.x} y2={SECOND.y} stroke="rgba(236,239,241,0.6)" strokeWidth={2} />
        <Line x1={SECOND.x} y1={SECOND.y} x2={THIRD.x} y2={THIRD.y} stroke="rgba(236,239,241,0.6)" strokeWidth={2} />
        <Line x1={THIRD.x} y1={THIRD.y} x2={HOME.x} y2={HOME.y} stroke="rgba(236,239,241,0.6)" strokeWidth={2} />
        {/* Pitcher's mound */}
        <Circle cx={D_CENTER} cy={D_CENTER} r={12} fill={Colors.infieldMound} />
        <Rect x={D_CENTER - 6} y={D_CENTER - 2} width={12} height={4} fill={Colors.textPrimary} />
      </Svg>

      {/* Base markers overlaid */}
      <BaseDiamondMarker
        isOccupied={bases.second !== null}
        style={{ position: 'absolute', top: 2, left: D_CENTER - 18 }}
        label="2B"
      />
      <BaseDiamondMarker
        isOccupied={bases.third !== null}
        style={{ position: 'absolute', top: D_CENTER - 18, left: 2 }}
        label="3B"
      />
      <BaseDiamondMarker
        isOccupied={bases.first !== null}
        style={{ position: 'absolute', top: D_CENTER - 18, right: 2 }}
        label="1B"
      />
      {/* Home plate */}
      <View style={styles.homePlate} />
    </View>
  );
}

function BaseDiamondMarker({
  isOccupied, label, style,
}: { isOccupied: boolean; label: string; style?: object }) {
  return (
    <View style={[styles.baseMarkerWrapper, style]}>
      <View
        style={[
          styles.baseSquare,
          {
            backgroundColor: isOccupied ? Colors.amberHot : Colors.baseDefault,
            borderColor: isOccupied ? Colors.yellowLight : Colors.textDisabled,
          },
        ]}
      >
        {isOccupied && <View style={styles.runnerDot} />}
      </View>
      <Text style={[styles.baseLabel, { color: isOccupied ? Colors.amberHot : Colors.textMuted }]}>
        {label}
      </Text>
    </View>
  );
}

// ─── Runners Summary Column ──────────────────────────────────────────────────

function RunnersSummaryColumn({ bases }: { bases: Bases }) {
  return (
    <View style={styles.runnersColumn}>
      <Text style={styles.sectionLabel}>ON BASE</Text>
      <RunnerRow base="3rd" runner={bases.third} />
      <RunnerRow base="2nd" runner={bases.second} />
      <RunnerRow base="1st" runner={bases.first} />
    </View>
  );
}

function RunnerRow({ base, runner }: { base: string; runner: PlayerSummary | null }) {
  const lastName = runner ? runner.name.split(' ').pop() ?? runner.name : null;
  return (
    <View style={styles.runnerRow}>
      <Text style={[styles.runnerBaseLabel, { color: runner ? Colors.amberHot : Colors.textDisabled }]}>
        {base}
      </Text>
      {runner ? (
        <Text style={styles.runnerName} numberOfLines={1}>
          #{runner.jersey_number} {lastName}
        </Text>
      ) : (
        <Text style={styles.runnerEmpty}>Empty</Text>
      )}
    </View>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bgSurface,
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  // Count column
  countColumn: { gap: 8 },
  sectionLabel: { fontSize: 9, fontWeight: '700', color: Colors.textSecondary, letterSpacing: 1.0, textTransform: 'uppercase' },
  indicatorRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  indicatorLetter: { fontSize: 14, fontWeight: '800', color: Colors.textPrimary, width: 16 },
  dot: { width: 14, height: 14, borderRadius: 7, borderWidth: 1 },
  // Diamond
  diamondContainer: { width: D_SIZE, height: D_SIZE, position: 'relative' },
  baseMarkerWrapper: { alignItems: 'center' },
  baseSquare: { width: 24, height: 24, borderRadius: 4, borderWidth: 2, transform: [{ rotate: '45deg' }], alignItems: 'center', justifyContent: 'center' },
  runnerDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#E65100' },
  baseLabel: { fontSize: 9, fontWeight: '700', marginTop: 2 },
  homePlate: { position: 'absolute', bottom: 4, left: D_CENTER - 8, width: 16, height: 12, backgroundColor: Colors.textPrimary, borderRadius: 2, borderWidth: 1, borderColor: Colors.textSecondary },
  // Runners column
  runnersColumn: { width: 100, gap: 4, alignItems: 'flex-end' },
  runnerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', gap: 4 },
  runnerBaseLabel: { fontSize: 11, fontWeight: '700' },
  runnerName: { fontSize: 12, fontWeight: '600', color: Colors.textPrimary },
  runnerEmpty: { fontSize: 11, color: Colors.textDisabled },
});
