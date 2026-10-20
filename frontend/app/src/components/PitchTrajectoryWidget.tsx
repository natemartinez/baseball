import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, {
  Circle,
  Ellipse,
  G,
  Line,
  Path,
  Polygon,
  Rect,
  Text as SvgText,
} from 'react-native-svg';
import type { PitchDetails } from '../types/api';
import type { Gameday2DPitchPacket } from '../types/gameday';
import { Colors } from '../theme/colors';
import {
  calculatePitchPoint,
  defaultRelease,
  movementForPitch,
  type PitcherHand,
  type PitchPoint3D,
} from '../services/pitchTrajectory';

interface PitchTrajectoryWidgetProps {
  pitch?: PitchDetails | null;
  /** Fallback when the packet has no meta.pitcherHand. */
  throws?: 'R' | 'L';
  width?: number;
  /** Bump this to replay the animation for the same pitch. */
  replayToken?: number;
}

// ─── World setup (feet) ──────────────────────────────────────────────────────
const VIEW_W = 480;
const VIEW_H = 360;
const FOCAL = 320;

/** Camera sits ~4 ft behind home plate at 3.5 ft eye level. */
const CAMERA: PitchPoint3D = { x: 0, y: -4.0, z: 3.5 };
/** Front edge of home plate. */
const PLATE_Y = 1.417;

const STRIKE_HALF_WIDTH = 0.71; // 17" plate
const STRIKE_TOP = 3.5;
const STRIKE_BOTTOM = 1.5;

/** Fallback plate location (feet) for a zone when no gameday packet exists. */
function zoneTarget(zone?: string): { x: number; z: number } {
  const map: Record<string, { x: number; z: number }> = {
    'upper-in': { x: -0.45, z: 3.15 },
    'upper-middle': { x: 0, z: 3.2 },
    'upper-away': { x: 0.45, z: 3.15 },
    'middle-in': { x: -0.5, z: 2.5 },
    heart: { x: 0, z: 2.5 },
    'middle-away': { x: 0.5, z: 2.5 },
    'lower-in': { x: -0.45, z: 1.85 },
    'lower-middle': { x: 0, z: 1.8 },
    'lower-away': { x: 0.45, z: 1.85 },
    'chase-high': { x: 0, z: 4.2 },
    'chase-low': { x: 0, z: 1.0 },
    'chase-in': { x: -1.1, z: 2.5 },
    'chase-away': { x: 1.1, z: 2.5 },
  };
  return map[zone ?? 'heart'] ?? { x: 0, z: 2.5 };
}

function project(point: PitchPoint3D) {
  const depth = Math.max(point.y - CAMERA.y, 0.5);
  const relativeZ = point.z - CAMERA.z;
  return {
    x: VIEW_W / 2 + (point.x / depth) * FOCAL,
    y: VIEW_H / 2 - (relativeZ / depth) * FOCAL,
  };
}

function buildGeometry(pitch: PitchDetails | null | undefined, fallbackHand: PitcherHand) {
  const packet: Gameday2DPitchPacket | undefined = pitch?.gameday_packet;
  const pitcherHand: PitcherHand =
    packet?.meta?.pitcherHand ?? fallbackHand ?? 'R';

  const release: PitchPoint3D =
    packet?.release ?? defaultRelease(pitcherHand);

  const fallbackTarget = zoneTarget(pitch?.actual_zone);
  const target: PitchPoint3D = {
    x: packet?.execution?.realizedX ?? fallbackTarget.x,
    y: PLATE_Y,
    z: packet?.execution?.realizedZ ?? fallbackTarget.z,
  };

  const fallbackMovement = movementForPitch(pitch?.pitch_name);
  const hbInches =
    packet?.execution?.horizontalBreakInches ?? fallbackMovement.hb;
  const ivbInches =
    packet?.execution?.inducedVerticalBreakInches ?? fallbackMovement.ivb;

  const steps = 48;
  const projected: Array<{ x: number; y: number }> = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const point = calculatePitchPoint(
      t,
      release,
      target,
      hbInches,
      ivbInches,
      pitcherHand,
    );
    projected.push(project(point));
  }

  const pathD = projected
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ');

  const zoneCorners = [
    project({ x: -STRIKE_HALF_WIDTH, y: PLATE_Y, z: STRIKE_TOP }),
    project({ x: STRIKE_HALF_WIDTH, y: PLATE_Y, z: STRIKE_TOP }),
    project({ x: STRIKE_HALF_WIDTH, y: PLATE_Y, z: STRIKE_BOTTOM }),
    project({ x: -STRIKE_HALF_WIDTH, y: PLATE_Y, z: STRIKE_BOTTOM }),
  ];

  const releaseProj = project(release);
  const bodyCenter = project({ x: 0, y: release.y, z: 5.5 });
  const feet = project({ x: 0, y: release.y, z: 0 });
  const moundCorners = [
    project({ x: -3.2, y: release.y, z: 0 }),
    project({ x: 3.2, y: release.y, z: 0 }),
    project({ x: 3.2, y: release.y, z: 0.8 }),
    project({ x: -3.2, y: release.y, z: 0.8 }),
  ];

  const speedMph =
    packet?.execution?.releaseSpeedMph ??
    packet?.execution?.realizedSpeedMph ??
    pitch?.velocity_mph ??
    93;
  const flightMs = Math.max(
    300,
    ((release.y - PLATE_Y) / (speedMph * 1.4667)) * 1000,
  );

  return {
    projected,
    pathD,
    zonePoints: zoneCorners.map((p) => `${p.x},${p.y}`).join(' '),
    releaseProj,
    bodyCenter,
    feet,
    moundPoints: moundCorners.map((p) => `${p.x},${p.y}`).join(' '),
    pitcherHand,
    armSide: pitcherHand === 'L' ? 1 : -1,
    flightMs,
  };
}

/**
 * PitchTrajectoryWidget — 3D-perspective pitch path with a pitcher figure.
 *
 * Consumes the engine's gameday packet: release slot, handedness, realized
 * plate coordinates, HB, IVB, and release speed. The path uses the
 * boundary-constrained constant-acceleration model (see pitchTrajectory.ts):
 * starts at release, ends exactly at the realized target, and keeps the plate
 * tangent in the break direction so breaking pitches do not hook back.
 */
export function PitchTrajectoryWidget({
  pitch,
  throws = 'R',
  width = 320,
  replayToken = 0,
}: PitchTrajectoryWidgetProps) {
  const height = Math.round(width * (VIEW_H / VIEW_W));
  const geometry = useMemo(
    () => buildGeometry(pitch, throws),
    [pitch, throws],
  );
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    setProgress(0);
    if (!pitch) return;

    let start: number | null = null;
    const duration = Math.max(300, geometry.flightMs);

    const step = (timestamp: number) => {
      if (start === null) start = timestamp;
      const p = Math.min((timestamp - start) / duration, 1);
      setProgress(p);
      if (p < 1) {
        rafRef.current = requestAnimationFrame(step);
      }
    };
    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [pitch, throws, replayToken, geometry.flightMs]);

  const lastIndex = geometry.projected.length - 1;
  const ballIndex = Math.min(Math.floor(progress * lastIndex), lastIndex);
  const ball = geometry.projected[ballIndex];
  const ballRadius = 3 + progress * 6;

  return (
    <View style={styles.wrap}>
      <Svg width={width} height={height} viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}>
        <Rect x={0} y={0} width={VIEW_W} height={VIEW_H} rx={10} fill="#1A202C" />

        {/* Mound */}
        <Polygon points={geometry.moundPoints} fill="#2D3748" />

        {/* Horizon / ground */}
        <Line
          x1={0}
          y1={geometry.feet.y}
          x2={VIEW_W}
          y2={geometry.feet.y}
          stroke="#2D3748"
          strokeWidth={1}
        />

        {/* Low-detail pitcher figure, handedness-aware */}
        <PitcherFigure
          body={geometry.bodyCenter}
          feet={geometry.feet}
          hand={geometry.releaseProj}
          armSide={geometry.armSide}
        />
        <SvgText
          x={geometry.bodyCenter.x + 16}
          y={geometry.bodyCenter.y - 18}
          fill="#A0AEC0"
          fontSize={11}
          fontWeight="700"
        >
          {geometry.pitcherHand}HP
        </SvgText>
        <SvgText
          x={geometry.bodyCenter.x + 16}
          y={geometry.bodyCenter.y - 6}
          fill="#64748B"
          fontSize={9}
        >
          PITCHER
        </SvgText>

        {/* Strike zone box */}
        <Polygon
          points={geometry.zonePoints}
          fill="rgba(255,255,255,0.04)"
          stroke="#FFFFFF"
          strokeWidth={2}
        />

        {/* Pitch trajectory (drawn behind the ball) */}
        <Path
          d={geometry.pathD}
          stroke="rgba(66,153,225,0.75)"
          strokeWidth={3}
          fill="none"
        />

        {/* Moving baseball */}
        {ball && (
          <Circle
            cx={ball.x}
            cy={ball.y}
            r={ballRadius}
            fill="#ECC94B"
            stroke="#D69E2E"
            strokeWidth={1.5}
          />
        )}
      </Svg>

      <Text style={styles.caption}>
        {pitch
          ? `${geometry.pitcherHand}HP • ${pitch.pitch_name} • ${pitch.velocity_mph} mph → ${pitch.actual_zone}`
          : 'No pitch yet'}
      </Text>
    </View>
  );
}

// ─── Pitcher figure ──────────────────────────────────────────────────────────

function PitcherFigure({
  body,
  feet,
  hand,
  armSide,
}: {
  body: { x: number; y: number };
  feet: { x: number; y: number };
  hand: { x: number; y: number };
  armSide: number;
}) {
  const bodyX = body.x;
  const groundY = feet.y;

  // Anchor the throwing hand at the release, then build an intentionally
  // exaggerated (readable) body down to the mound.
  const headR = 8;
  const headY = hand.y - 16;
  const shoulderY = hand.y - 4;
  const hipY = hand.y + 24;
  const gloveHand = { x: bodyX - armSide * 16, y: shoulderY + 14 };

  return (
    <G>
      {/* Ground shadow */}
      <Ellipse
        cx={bodyX}
        cy={groundY}
        rx={15}
        ry={3.5}
        fill="rgba(0,0,0,0.45)"
      />

      {/* Legs */}
      <Line
        x1={bodyX - 3}
        y1={hipY}
        x2={bodyX - 9}
        y2={groundY - 1}
        stroke="#CBD5E1"
        strokeWidth={5}
        strokeLinecap="round"
      />
      <Line
        x1={bodyX + 3}
        y1={hipY}
        x2={bodyX + 9}
        y2={groundY - 1}
        stroke="#CBD5E1"
        strokeWidth={5}
        strokeLinecap="round"
      />

      {/* Torso / jersey */}
      <Line
        x1={bodyX}
        y1={shoulderY}
        x2={bodyX}
        y2={hipY}
        stroke="#3B82F6"
        strokeWidth={12}
        strokeLinecap="round"
      />

      {/* Glove arm (opposite the throwing arm) */}
      <Line
        x1={bodyX - armSide * 4}
        y1={shoulderY + 2}
        x2={gloveHand.x}
        y2={gloveHand.y}
        stroke="#CBD5E1"
        strokeWidth={4}
        strokeLinecap="round"
      />

      {/* Throwing arm — connects the shoulder to the actual release point */}
      <Line
        x1={bodyX + armSide * 2}
        y1={shoulderY + 2}
        x2={hand.x}
        y2={hand.y}
        stroke="#F5CBA7"
        strokeWidth={5}
        strokeLinecap="round"
      />

      {/* Head */}
      <Circle cx={bodyX} cy={headY} r={headR} fill="#F5CBA7" />
      <Circle cx={bodyX} cy={headY} r={headR} fill="none" stroke="#8D6E63" strokeWidth={1.5} />
    </G>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: 8 },
  caption: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '600',
  },
});
