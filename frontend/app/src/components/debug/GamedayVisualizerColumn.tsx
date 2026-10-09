import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, GestureResponderEvent } from 'react-native';
import Svg, { Rect, Line, Circle, Polygon, Text as SvgText, G } from 'react-native-svg';
import type { Gameday2DPitchPacket } from '../../types/gameday';
import { Colors } from '../../theme/colors';
import {
  statcastToSvg,
  svgToStatcast,
  getPitchTypeColor,
  getResultRingColor,
  ZONE_X_MIN,
  ZONE_X_MAX,
  ZONE_Z_BOT,
  ZONE_Z_TOP,
  HEART_X_MIN,
  HEART_X_MAX,
  HEART_Z_BOT,
  HEART_Z_TOP,
  SHADOW_BORDER_FT,
} from '../../services/gamedayMath';

interface GamedayVisualizerColumnProps {
  packet: Gameday2DPitchPacket | null;
  customTarget: { x: number; z: number } | null;
  onSetCustomTarget: (coords: { x: number; z: number } | null) => void;
}

const SVG_WIDTH = 260;
const SVG_HEIGHT = 290;

/**
 * Column 2: MLB Gameday 2D Target Zone Visualizer
 * Renders the 2D home plate cross-section, 9-box rulebook strike zone,
 * Heart/Shadow boundary outlines, target reticle, realized pitch dot,
 * execution error vector, and interactive touch targeting.
 */
export function GamedayVisualizerColumn({
  packet,
  customTarget,
  onSetCustomTarget,
}: GamedayVisualizerColumnProps) {
  // SVG Strike Zone coordinates
  const szTopLeft = statcastToSvg(ZONE_X_MIN, ZONE_Z_TOP, SVG_WIDTH, SVG_HEIGHT);
  const szBotRight = statcastToSvg(ZONE_X_MAX, ZONE_Z_BOT, SVG_WIDTH, SVG_HEIGHT);
  const szWidth = szBotRight.svgX - szTopLeft.svgX;
  const szHeight = szBotRight.svgY - szTopLeft.svgY;

  // Heart zone box (inner 50%)
  const heartTopLeft = statcastToSvg(HEART_X_MIN, HEART_Z_TOP, SVG_WIDTH, SVG_HEIGHT);
  const heartBotRight = statcastToSvg(HEART_X_MAX, HEART_Z_BOT, SVG_WIDTH, SVG_HEIGHT);
  const heartWidth = heartBotRight.svgX - heartTopLeft.svgX;
  const heartHeight = heartBotRight.svgY - heartTopLeft.svgY;

  // Shadow outer border (1 ball width = 0.283 ft margin)
  const shadowTopLeft = statcastToSvg(ZONE_X_MIN - SHADOW_BORDER_FT, ZONE_Z_TOP + SHADOW_BORDER_FT, SVG_WIDTH, SVG_HEIGHT);
  const shadowBotRight = statcastToSvg(ZONE_X_MAX + SHADOW_BORDER_FT, ZONE_Z_BOT - SHADOW_BORDER_FT, SVG_WIDTH, SVG_HEIGHT);
  const shadowWidth = shadowBotRight.svgX - shadowTopLeft.svgX;
  const shadowHeight = shadowBotRight.svgY - shadowTopLeft.svgY;

  // 3x3 inner grid split lines
  const szCol1 = szTopLeft.svgX + szWidth / 3;
  const szCol2 = szTopLeft.svgX + (2 * szWidth) / 3;
  const szRow1 = szTopLeft.svgY + szHeight / 3;
  const szRow2 = szTopLeft.svgY + (2 * szHeight) / 3;

  // Home plate outline at Z = 0.0 (ground)
  const hpCornerLeft = statcastToSvg(-0.708, 0.40, SVG_WIDTH, SVG_HEIGHT);
  const hpCornerRight = statcastToSvg(0.708, 0.40, SVG_WIDTH, SVG_HEIGHT);
  const hpPoint = statcastToSvg(0.0, 0.05, SVG_WIDTH, SVG_HEIGHT);
  const hpMidLeft = statcastToSvg(-0.708, 0.25, SVG_WIDTH, SVG_HEIGHT);
  const hpMidRight = statcastToSvg(0.708, 0.25, SVG_WIDTH, SVG_HEIGHT);
  const platePoints = `${hpCornerLeft.svgX},${hpCornerLeft.svgY} ${hpCornerRight.svgX},${hpCornerRight.svgY} ${hpMidRight.svgX},${hpMidRight.svgY} ${hpPoint.svgX},${hpPoint.svgY} ${hpMidLeft.svgX},${hpMidLeft.svgY}`;

  // Target coordinates (custom override or packet intent)
  const activeTargetX = customTarget ? customTarget.x : packet ? packet.intent.targetX : 0.0;
  const activeTargetZ = customTarget ? customTarget.z : packet ? packet.intent.targetZ : 2.5;
  const targetSvg = statcastToSvg(activeTargetX, activeTargetZ, SVG_WIDTH, SVG_HEIGHT);

  // Realized pitch delivery coordinates
  const realizedSvg = packet
    ? statcastToSvg(packet.execution.realizedX, packet.execution.realizedZ, SVG_WIDTH, SVG_HEIGHT)
    : null;

  // Pitch colors
  const pitchColor = packet ? getPitchTypeColor(packet.strategy.selectedPitch) : Colors.cyan;
  const ringColor = packet ? getResultRingColor(packet.result.call) : Colors.blue;

  // Handle interactive touch to set custom target
  function handleSvgTouch(event: GestureResponderEvent) {
    const { locationX, locationY } = event.nativeEvent;
    const statcast = svgToStatcast(locationX, locationY, SVG_WIDTH, SVG_HEIGHT);
    onSetCustomTarget({ x: statcast.statcastX, z: statcast.statcastZ });
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.headerBox}>
        <Text style={styles.columnTitle}>COLUMN 2: GAMEDAY 2D TARGET ZONE</Text>
        {customTarget ? (
          <TouchableOpacity onPress={() => onSetCustomTarget(null)} style={styles.clearTargetBtn}>
            <Text style={styles.clearTargetText}>Reset Target</Text>
          </TouchableOpacity>
        ) : (
          <Text style={styles.hintText}>Tap plate to aim</Text>
        )}
      </View>

      {/* SVG Canvas Cross Section */}
      <TouchableOpacity activeOpacity={0.95} onPress={handleSvgTouch} style={styles.svgWrapper}>
        <Svg width={SVG_WIDTH} height={SVG_HEIGHT}>
          {/* Ground Baseline Z = 0 */}
          <Line x1={0} y1={statcastToSvg(0, 0, SVG_WIDTH, SVG_HEIGHT).svgY} x2={SVG_WIDTH} y2={statcastToSvg(0, 0, SVG_WIDTH, SVG_HEIGHT).svgY} stroke="rgba(144,164,174,0.3)" strokeWidth={1} />

          {/* Home Plate Outline */}
          <Polygon points={platePoints} fill="rgba(236,239,241,0.25)" stroke="rgba(236,239,241,0.7)" strokeWidth={1.5} />
          <SvgText x={SVG_WIDTH / 2} y={hpCornerLeft.svgY - 4} fill="rgba(144,164,174,0.6)" fontSize="8" fontWeight="bold" textAnchor="middle">
            HOME PLATE (17 IN)
          </SvgText>

          {/* Shadow Zone Outer Margin (Dashed) */}
          <Rect
            x={shadowTopLeft.svgX}
            y={shadowTopLeft.svgY}
            width={shadowWidth}
            height={shadowHeight}
            fill="rgba(2, 119, 189, 0.04)"
            stroke="rgba(2, 119, 189, 0.35)"
            strokeWidth={1}
            strokeDasharray="4,4"
          />

          {/* 17" Rulebook Strike Zone Rectangle */}
          <Rect
            x={szTopLeft.svgX}
            y={szTopLeft.svgY}
            width={szWidth}
            height={szHeight}
            fill="rgba(13, 27, 42, 0.75)"
            stroke="#ECEFF1"
            strokeWidth={2}
          />

          {/* 3x3 Inner Zone Dividing Lines */}
          <Line x1={szCol1} y1={szTopLeft.svgY} x2={szCol1} y2={szBotRight.svgY} stroke="rgba(236,239,241,0.3)" strokeWidth={1} strokeDasharray="3,3" />
          <Line x1={szCol2} y1={szTopLeft.svgY} x2={szCol2} y2={szBotRight.svgY} stroke="rgba(236,239,241,0.3)" strokeWidth={1} strokeDasharray="3,3" />
          <Line x1={szTopLeft.svgX} y1={szRow1} x2={szBotRight.svgX} y2={szRow1} stroke="rgba(236,239,241,0.3)" strokeWidth={1} strokeDasharray="3,3" />
          <Line x1={szTopLeft.svgX} y1={szRow2} x2={szBotRight.svgX} y2={szRow2} stroke="rgba(236,239,241,0.3)" strokeWidth={1} strokeDasharray="3,3" />

          {/* Heart Zone (Inner 50% rectangle) */}
          <Rect
            x={heartTopLeft.svgX}
            y={heartTopLeft.svgY}
            width={heartWidth}
            height={heartHeight}
            fill="rgba(239, 68, 68, 0.08)"
            stroke="rgba(239, 68, 68, 0.45)"
            strokeWidth={1}
            strokeDasharray="2,2"
          />
          <SvgText x={heartTopLeft.svgX + heartWidth / 2} y={heartTopLeft.svgY + heartHeight / 2 + 3} fill="rgba(239,68,68,0.5)" fontSize="9" fontWeight="800" textAnchor="middle">
            HEART (50%)
          </SvgText>

          {/* Execution Vector Line (Target -> Realized) */}
          {realizedSvg && (
            <G>
              <Line
                x1={targetSvg.svgX}
                y1={targetSvg.svgY}
                x2={realizedSvg.svgX}
                y2={realizedSvg.svgY}
                stroke="rgba(255, 215, 0, 0.8)"
                strokeWidth={1.5}
                strokeDasharray="2,2"
              />
              {/* Radial Miss Distance Label */}
              <SvgText
                x={(targetSvg.svgX + realizedSvg.svgX) / 2 + 6}
                y={(targetSvg.svgY + realizedSvg.svgY) / 2 - 4}
                fill="#FFD54F"
                fontSize="10"
                fontWeight="bold"
              >
                {packet?.execution.radialMissInches}"
              </SvgText>
            </G>
          )}

          {/* Intended Target Reticle (Dashed Circle + Crosshairs) */}
          <G>
            <Circle cx={targetSvg.svgX} cy={targetSvg.svgY} r={11} fill="none" stroke="#FFD54F" strokeWidth={1.5} strokeDasharray="3,2" />
            <Line x1={targetSvg.svgX - 14} y1={targetSvg.svgY} x2={targetSvg.svgX + 14} y2={targetSvg.svgY} stroke="#FFD54F" strokeWidth={1.2} />
            <Line x1={targetSvg.svgX} y1={targetSvg.svgY - 14} x2={targetSvg.svgX} y2={targetSvg.svgY + 14} stroke="#FFD54F" strokeWidth={1.2} />
            <SvgText x={targetSvg.svgX} y={targetSvg.svgY - 16} fill="#FFD54F" fontSize="9" fontWeight="800" textAnchor="middle">
              {customTarget ? '○ CUSTOM' : '○ TARGET'}
            </SvgText>
          </G>

          {/* Realized Delivery Pitch Dot */}
          {realizedSvg && (
            <G>
              <Circle
                cx={realizedSvg.svgX}
                cy={realizedSvg.svgY}
                r={9}
                fill={pitchColor}
                stroke={ringColor}
                strokeWidth={2.5}
              />
              <SvgText
                x={realizedSvg.svgX}
                y={realizedSvg.svgY + 18}
                fill="#FFFFFF"
                fontSize="9"
                fontWeight="900"
                textAnchor="middle"
              >
                #{packet?.meta.pitchNumber} {packet?.execution.realizedSpeedMph}
              </SvgText>
            </G>
          )}
        </Svg>
      </TouchableOpacity>

      {/* Coordinate & Execution Telemetry Readout */}
      <View style={styles.telemetryCard}>
        <View style={styles.telemetryRow}>
          <Text style={styles.telemetryKey}>Target (X*, Z*):</Text>
          <Text style={[styles.telemetryVal, { color: Colors.amberLight }]}>
            ({activeTargetX > 0 ? `+${activeTargetX.toFixed(2)}` : activeTargetX.toFixed(2)}, {activeTargetZ.toFixed(2)} ft)
          </Text>
        </View>

        {packet && (
          <>
            <View style={styles.telemetryRow}>
              <Text style={styles.telemetryKey}>Actual (X_real, Z_real):</Text>
              <Text style={[styles.telemetryVal, { color: Colors.greenLight }]}>
                ({packet.execution.realizedX > 0 ? `+${packet.execution.realizedX.toFixed(2)}` : packet.execution.realizedX.toFixed(2)}, {packet.execution.realizedZ.toFixed(2)} ft)
              </Text>
            </View>

            <View style={styles.telemetryRow}>
              <Text style={styles.telemetryKey}>Radial Miss (Δ):</Text>
              <Text style={[styles.telemetryVal, { color: packet.execution.radialMissInches > 4.5 ? Colors.redLight : '#FFF' }]}>
                {packet.execution.radialMissInches}" (ΔX: {packet.execution.deltaXInches}", ΔZ: {packet.execution.deltaZInches}")
              </Text>
            </View>

            <View style={styles.telemetryRow}>
              <Text style={styles.telemetryKey}>Zone Classification:</Text>
              <Text style={[styles.telemetryVal, { color: Colors.blueSky }]}>
                {packet.execution.realizedZoneCategory} ({packet.result.isStrike ? 'STRIKE' : 'BALL'})
              </Text>
            </View>

            {packet.execution.isHeartZoneLeak && (
              <View style={styles.alertBanner}>
                <Text style={styles.alertText}>*ALERT: Leaking over middle of plate!</Text>
              </View>
            )}
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bgDeep, padding: 10, gap: 10 },
  headerBox: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  columnTitle: { color: Colors.textSecondary, fontSize: 10, fontWeight: '800', letterSpacing: 0.8 },
  clearTargetBtn: { backgroundColor: 'rgba(255, 179, 0, 0.2)', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, borderWidth: 1, borderColor: '#FFB300' },
  clearTargetText: { color: '#FFD54F', fontSize: 9, fontWeight: '800' },
  hintText: { color: Colors.textMuted, fontSize: 9 },
  svgWrapper: {
    backgroundColor: '#070B10',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 6,
  },
  telemetryCard: {
    backgroundColor: Colors.bgSurface,
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    gap: 4,
  },
  telemetryRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  telemetryKey: { color: Colors.textSecondary, fontSize: 11 },
  telemetryVal: { fontSize: 11, fontWeight: '700' },
  alertBanner: { backgroundColor: 'rgba(239, 68, 68, 0.15)', borderWidth: 1, borderColor: '#EF4444', borderRadius: 4, padding: 6, marginTop: 4, alignItems: 'center' },
  alertText: { color: '#FCA5A5', fontSize: 10, fontWeight: '800' },
});
