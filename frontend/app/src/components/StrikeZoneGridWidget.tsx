import React, { useMemo } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
  type GestureResponderEvent,
} from 'react-native';
import Svg, { Ellipse, Image as SvgImage } from 'react-native-svg';
import type { BatterInfo, PitchResultType, ResolvedPitchDetails } from '../types/api';
import { STRIKE_ZONES } from '../types/api';
import {
  buildSprayCloud,
  CHASE_BORDER_FT,
  SHADOW_BORDER_FT,
  getZoneNominalTarget,
} from '../services/gamedayMath';
import { Colors } from '../theme/colors';

const GLOVE_ICON = require('../../assets/glove-icon.png');

interface StrikeZoneGridWidgetProps {
  selectedZone: string;
  onSelectZone: (zone: string) => void;
  currentBatter: BatterInfo;
  latestPitch?: ResolvedPitchDetails | null;
  /** All pitches in the current at-bat, oldest first (numbered 1..n). */
  atBatPitches?: ResolvedPitchDetails[];
  /** Exact catcher's glove target (Statcast feet). */
  gloveTarget?: { x: number; z: number } | null;
  /** Pitcher command rating used to size the spray cloud. */
  commandRating?: number;
  /** Place the glove at an exact x/z (enables tap/drag targeting). */
  onSetGloveTarget?: (x: number, z: number) => void;
  /** Show the zone name + SLG labels inside each cell (default true). */
  showZoneLabels?: boolean;
  /** Render the surrounding chase elements fully invisible (default false). */
  chaseTransparent?: boolean;
  /** Show the latest-pitch summary below the grid (default true). */
  showPitchSummary?: boolean;
  /** Visual scale applied by the parent overlay; corrects web responder coordinates. */
  coordinateScaleX?: number;
  coordinateScaleY?: number;
  /**
   * 'selector' keeps the 3x3 + chase picker used by the Strategy menu.
   * 'field' renders one strike rectangle with exact-coordinate pitch dots.
   */
  variant?: 'field' | 'selector';
}

interface NumberedPitch {
  pitch: ResolvedPitchDetails;
  number: number;
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
  atBatPitches,
  gloveTarget,
  commandRating,
  onSetGloveTarget,
  showZoneLabels = true,
  chaseTransparent = false,
  showPitchSummary = true,
  coordinateScaleX = 1,
  coordinateScaleY = 1,
  variant = 'selector',
}: StrikeZoneGridWidgetProps) {
  const sourcePitches =
    atBatPitches !== undefined
      ? atBatPitches
      : latestPitch
        ? [latestPitch]
        : [];
  const numberedPitches: NumberedPitch[] = sourcePitches.map((pitch, i) => ({
    pitch,
    number: i + 1,
  }));

  // The responder lives on a transparent overlay that exactly covers the grid
  // box. This keeps locationX/locationY in the grid's coordinate space instead
  // of the touched child's space, and it maps the chase strips to the full
  // chase band rather than a few pixels just outside the zone.
  function handleGridGlove(e: GestureResponderEvent) {
    if (!onSetGloveTarget) return;
    // react-native-web derives locationX/Y from getBoundingClientRect, which
    // includes the overlay's CSS scale, so undo that scale before mapping.
    // Native responders already report layout coordinates.
    const scaleX = Platform.OS === 'web' && coordinateScaleX > 0 ? coordinateScaleX : 1;
    const scaleY = Platform.OS === 'web' && coordinateScaleY > 0 ? coordinateScaleY : 1;
    const lx = Math.max(0, Math.min(GRID_WIDTH, e.nativeEvent.locationX / scaleX));
    const ly = Math.max(0, Math.min(GRID_HEIGHT, e.nativeEvent.locationY / scaleY));
    onSetGloveTarget(gridToStatcastX(lx), gridToStatcastZ(ly));
  }

  if (variant === 'field') {
    return (
      <View style={styles.container}>
        <View style={styles.fieldBox}>
          {/* One visible rectangle: the rulebook strike zone, edge inclusive. */}
          <View style={styles.strikeZoneRect} />

          <View style={styles.fieldGloveLayer}>
            <GloveCloudOverlay
              gloveTarget={gloveTarget}
              commandRating={commandRating}
              markerScaleX={coordinateScaleX}
              markerScaleY={coordinateScaleY}
            />
          </View>

          <FieldPitchDots
            pitches={numberedPitches}
            scaleX={coordinateScaleX}
            scaleY={coordinateScaleY}
          />

          {onSetGloveTarget && (
            <View
              style={StyleSheet.absoluteFill}
              onStartShouldSetResponder={() => true}
              onMoveShouldSetResponder={() => true}
              onStartShouldSetResponderCapture={() => true}
              onMoveShouldSetResponderCapture={() => true}
              onResponderGrant={handleGridGlove}
              onResponderMove={handleGridGlove}
            />
          )}
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Grid Box */}
      <View style={styles.gridOuter}>
      <View style={styles.gridBox}>
        {/* Chase High */}
        <ChaseZonePill
          zoneId={STRIKE_ZONES.CHASE_HIGH}
          label="CHASE HIGH"
          isSelected={selectedZone === STRIKE_ZONES.CHASE_HIGH}
          pitches={numberedPitches}
          onSelect={onSelectZone}
          transparent={chaseTransparent}
          horizontal
          markerScaleX={coordinateScaleX}
          markerScaleY={coordinateScaleY}
        />

        {/* Middle row: Chase In + 3×3 + Chase Away */}
        <View style={styles.middleRow}>
          <ChaseZonePill
            zoneId={STRIKE_ZONES.CHASE_IN}
            label={'CHASE\nIN'}
            isSelected={selectedZone === STRIKE_ZONES.CHASE_IN}
            pitches={numberedPitches}
            onSelect={onSelectZone}
            transparent={chaseTransparent}
            horizontal={false}
            markerScaleX={coordinateScaleX}
            markerScaleY={coordinateScaleY}
          />
          <InnerStrikeZone3x3
            selectedZone={selectedZone}
            onSelectZone={onSelectZone}
            currentBatter={currentBatter}
            pitches={numberedPitches}
            gloveTarget={gloveTarget}
            commandRating={commandRating}
            showZoneLabels={showZoneLabels}
            markerScaleX={coordinateScaleX}
            markerScaleY={coordinateScaleY}
          />
          <ChaseZonePill
            zoneId={STRIKE_ZONES.CHASE_AWAY}
            label={'CHASE\nAWAY'}
            isSelected={selectedZone === STRIKE_ZONES.CHASE_AWAY}
            pitches={numberedPitches}
            onSelect={onSelectZone}
            transparent={chaseTransparent}
            horizontal={false}
            markerScaleX={coordinateScaleX}
            markerScaleY={coordinateScaleY}
          />
        </View>

        {/* Chase Low */}
        <ChaseZonePill
          zoneId={STRIKE_ZONES.CHASE_LOW}
          label="CHASE LOW"
          isSelected={selectedZone === STRIKE_ZONES.CHASE_LOW}
          pitches={numberedPitches}
          onSelect={onSelectZone}
          transparent={chaseTransparent}
          horizontal
          markerScaleX={coordinateScaleX}
          markerScaleY={coordinateScaleY}
        />
      </View>
      {onSetGloveTarget && (
        <View
          style={StyleSheet.absoluteFill}
          onStartShouldSetResponder={() => true}
          onMoveShouldSetResponder={() => true}
          onStartShouldSetResponderCapture={() => true}
          onMoveShouldSetResponderCapture={() => true}
          onResponderGrant={handleGridGlove}
          onResponderMove={handleGridGlove}
        />
      )}
      </View>

      {/* Latest pitch summary */}
      {showPitchSummary && latestPitch && (
        <PitchOutcomeSummaryBadge latestPitch={latestPitch} />
      )}
    </View>
  );
}

// ─── Inner 3×3 Strike Zone ───────────────────────────────────────────────────

/** Square edge length of the 3×3 strike zone (kept 1:1). */
const STRIKE_ZONE_SIZE = 190;
const GRID_PAD_PX = 2;

/** Semi-transparent panel backing so the 3D field shows through the HUD. */
const GRID_PANEL_BG = 'rgba(13, 19, 26, 0.45)';
const GRID_INNER_BG = 'rgba(27, 36, 48, 0.3)';

// Fixed grid-box layout. The unified glove responder maps the whole box,
// including the chase strips, so these offsets must stay in sync with styles.
const GRID_BOX_PAD = 6;
const GRID_BOX_GAP = 4;
const CHASE_H = 26;
const CHASE_V = 28;
const INNER_LEFT = GRID_BOX_PAD + CHASE_V + GRID_BOX_GAP;
const INNER_TOP = GRID_BOX_PAD + CHASE_H + GRID_BOX_GAP;
const GRID_WIDTH = GRID_BOX_PAD * 2 + CHASE_V * 2 + GRID_BOX_GAP * 2 + STRIKE_ZONE_SIZE;
const GRID_HEIGHT = GRID_BOX_PAD * 2 + CHASE_H * 2 + GRID_BOX_GAP * 2 + STRIKE_ZONE_SIZE;
const CHASE_LEFT_PX = INNER_LEFT;
const CHASE_TOP_PX = INNER_TOP;
const CHASE_RIGHT_PX = GRID_WIDTH - INNER_LEFT - STRIKE_ZONE_SIZE;
const CHASE_BOTTOM_PX = GRID_HEIGHT - INNER_TOP - STRIKE_ZONE_SIZE;

/** Outer container padding, shared by the style and the exported rendered size. */
const CONTAINER_PAD = 14;

/** Rendered height while the pitch summary is hidden: grid box plus container padding. */
export const STRIKE_ZONE_WIDGET_SIZE = GRID_HEIGHT + CONTAINER_PAD * 2;

/** Rendered width of the 3x3 strike zone before any overlay scale. */
export const STRIKE_ZONE_GRID_SIZE = STRIKE_ZONE_SIZE;

/** Rendered width of the whole widget, including chase strips and container padding. */
export const STRIKE_ZONE_WIDGET_WIDTH = GRID_WIDTH + CONTAINER_PAD * 2;

/** Distance from the widget's top to the bottom edge of the 3x3 grid (unscaled). */
export const STRIKE_ZONE_GRID_BOTTOM_OFFSET =
  CONTAINER_PAD + INNER_TOP + STRIKE_ZONE_SIZE;

/** Inner 3x3 content size, excluding the 2px inner padding. */
export const STRIKE_ZONE_GRID_CONTENT_SIZE =
  STRIKE_ZONE_SIZE - GRID_PAD_PX * 2;

/** Distance from the widget's top to the 3x3 content top (unscaled). */
export const STRIKE_ZONE_GRID_CONTENT_TOP =
  CONTAINER_PAD + INNER_TOP + GRID_PAD_PX;

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

// Statcast strike-zone bounds used by the spray cloud overlay.
const ZONE_X_MIN = -0.7083;
const ZONE_X_MAX = 0.7083;
const ZONE_Z_BOT = 1.5;
const ZONE_Z_TOP = 3.5;
const GRID_CONTENT_PX = STRIKE_ZONE_GRID_CONTENT_SIZE;
const CONTENT_LEFT = INNER_LEFT + GRID_PAD_PX;
const CONTENT_RIGHT = CONTENT_LEFT + GRID_CONTENT_PX;
const CONTENT_TOP = INNER_TOP + GRID_PAD_PX;
const CONTENT_BOTTOM = CONTENT_TOP + GRID_CONTENT_PX;
const EDGE_BAND_PX = GRID_PAD_PX + GRID_BOX_GAP;
const CLOUD_PAD_PX = 64;
const CLOUD_SIZE = STRIKE_ZONE_SIZE + CLOUD_PAD_PX * 2;
const PX_PER_INCH = GRID_CONTENT_PX / 17;

/**
 * The visible layout has three bands on each side:
 *   padding (waste) -> chase strip -> shadow gap -> strike zone.
 * The strike boundary is the visible content rectangle, so taps exactly on
 * its border map to the inclusive rulebook edge and taps outside map to balls.
 */
function gridToStatcastX(lx: number): number {
  const stripOuter = GRID_BOX_PAD;
  const stripInner = GRID_BOX_PAD + CHASE_V;

  if (lx < stripOuter) {
    const t = (stripOuter - lx) / GRID_BOX_PAD;
    return ZONE_X_MIN - CHASE_BORDER_FT - t * SHADOW_BORDER_FT;
  }
  if (lx < stripInner) {
    const t = (lx - stripOuter) / CHASE_V;
    return ZONE_X_MIN - CHASE_BORDER_FT + t * (CHASE_BORDER_FT - SHADOW_BORDER_FT);
  }
  if (lx < CONTENT_LEFT) {
    const t = (lx - stripInner) / EDGE_BAND_PX;
    return ZONE_X_MIN - SHADOW_BORDER_FT + t * SHADOW_BORDER_FT;
  }
  if (lx <= CONTENT_RIGHT) {
    return ZONE_X_MIN + ((lx - CONTENT_LEFT) / GRID_CONTENT_PX) * (ZONE_X_MAX - ZONE_X_MIN);
  }

  const rightShadowStart = CONTENT_RIGHT;
  const rightStripStart = rightShadowStart + EDGE_BAND_PX;
  const rightStripEnd = rightStripStart + CHASE_V;
  if (lx < rightStripStart) {
    const t = (lx - rightShadowStart) / EDGE_BAND_PX;
    return ZONE_X_MAX + t * SHADOW_BORDER_FT;
  }
  if (lx < rightStripEnd) {
    const t = (lx - rightStripStart) / CHASE_V;
    return ZONE_X_MAX + SHADOW_BORDER_FT + t * (CHASE_BORDER_FT - SHADOW_BORDER_FT);
  }
  const t = (lx - rightStripEnd) / GRID_BOX_PAD;
  return ZONE_X_MAX + CHASE_BORDER_FT + t * SHADOW_BORDER_FT;
}

/** Maps a grid-box touch Y to Statcast Z with the same band structure. */
function gridToStatcastZ(ly: number): number {
  const stripOuter = GRID_BOX_PAD;
  const stripInner = GRID_BOX_PAD + CHASE_H;

  if (ly < stripOuter) {
    const t = (stripOuter - ly) / GRID_BOX_PAD;
    return ZONE_Z_TOP + CHASE_BORDER_FT + t * SHADOW_BORDER_FT;
  }
  if (ly < stripInner) {
    const t = (ly - stripOuter) / CHASE_H;
    return ZONE_Z_TOP + CHASE_BORDER_FT - t * (CHASE_BORDER_FT - SHADOW_BORDER_FT);
  }
  if (ly < CONTENT_TOP) {
    const t = (ly - stripInner) / EDGE_BAND_PX;
    return ZONE_Z_TOP + SHADOW_BORDER_FT - t * SHADOW_BORDER_FT;
  }
  if (ly <= CONTENT_BOTTOM) {
    return ZONE_Z_TOP - ((ly - CONTENT_TOP) / GRID_CONTENT_PX) * (ZONE_Z_TOP - ZONE_Z_BOT);
  }

  const bottomShadowStart = CONTENT_BOTTOM;
  const bottomStripStart = bottomShadowStart + EDGE_BAND_PX;
  const bottomStripEnd = bottomStripStart + CHASE_H;
  if (ly < bottomStripStart) {
    const t = (ly - bottomShadowStart) / EDGE_BAND_PX;
    return ZONE_Z_BOT - t * SHADOW_BORDER_FT;
  }
  if (ly < bottomStripEnd) {
    const t = (ly - bottomStripStart) / CHASE_H;
    return ZONE_Z_BOT - SHADOW_BORDER_FT - t * (CHASE_BORDER_FT - SHADOW_BORDER_FT);
  }
  const t = (ly - bottomStripEnd) / GRID_BOX_PAD;
  return ZONE_Z_BOT - CHASE_BORDER_FT - t * SHADOW_BORDER_FT;
}

/** Inverse of the mapping above, in inner-grid local SVG pixels. */
function statcastToGrid(x: number, z: number) {
  const leftChaseOuter = ZONE_X_MIN - CHASE_BORDER_FT;
  const leftShadowOuter = ZONE_X_MIN - SHADOW_BORDER_FT;
  let px: number;
  if (x < leftChaseOuter) {
    const t = Math.max(0, Math.min(1, (x - (leftChaseOuter - SHADOW_BORDER_FT)) / SHADOW_BORDER_FT));
    px = -INNER_LEFT + t * GRID_BOX_PAD;
  } else if (x < leftShadowOuter) {
    const t = (x - leftChaseOuter) / (CHASE_BORDER_FT - SHADOW_BORDER_FT);
    px = -INNER_LEFT + GRID_BOX_PAD + t * CHASE_V;
  } else if (x < ZONE_X_MIN) {
    const t = (x - leftShadowOuter) / SHADOW_BORDER_FT;
    px = -GRID_BOX_GAP + t * GRID_BOX_GAP;
  } else if (x <= ZONE_X_MAX) {
    px = GRID_PAD_PX + ((x - ZONE_X_MIN) / (ZONE_X_MAX - ZONE_X_MIN)) * GRID_CONTENT_PX;
  } else {
    const rightShadowOuter = ZONE_X_MAX + SHADOW_BORDER_FT;
    const rightChaseOuter = ZONE_X_MAX + CHASE_BORDER_FT;
    if (x < rightShadowOuter) {
      const t = (x - ZONE_X_MAX) / SHADOW_BORDER_FT;
      px = STRIKE_ZONE_SIZE + t * GRID_BOX_GAP;
    } else if (x < rightChaseOuter) {
      const t = (x - rightShadowOuter) / (CHASE_BORDER_FT - SHADOW_BORDER_FT);
      px = STRIKE_ZONE_SIZE + GRID_BOX_GAP + t * CHASE_V;
    } else {
      const t = Math.max(0, Math.min(1, (x - rightChaseOuter) / SHADOW_BORDER_FT));
      px = STRIKE_ZONE_SIZE + GRID_BOX_GAP + CHASE_V + t * GRID_BOX_PAD;
    }
  }

  const topChaseOuter = ZONE_Z_TOP + CHASE_BORDER_FT;
  const topShadowOuter = ZONE_Z_TOP + SHADOW_BORDER_FT;
  const bottomShadowOuter = ZONE_Z_BOT - SHADOW_BORDER_FT;
  const bottomChaseOuter = ZONE_Z_BOT - CHASE_BORDER_FT;
  let py: number;
  if (z > topChaseOuter) {
    const t = Math.max(0, Math.min(1, (z - topChaseOuter) / SHADOW_BORDER_FT));
    py = -INNER_TOP + GRID_BOX_PAD - t * GRID_BOX_PAD;
  } else if (z > topShadowOuter) {
    const t = (topChaseOuter - z) / (CHASE_BORDER_FT - SHADOW_BORDER_FT);
    py = -INNER_TOP + GRID_BOX_PAD + t * CHASE_H;
  } else if (z > ZONE_Z_TOP) {
    const t = (topShadowOuter - z) / SHADOW_BORDER_FT;
    py = -GRID_BOX_GAP + t * GRID_BOX_GAP;
  } else if (z >= ZONE_Z_BOT) {
    py = GRID_PAD_PX + ((ZONE_Z_TOP - z) / (ZONE_Z_TOP - ZONE_Z_BOT)) * GRID_CONTENT_PX;
  } else if (z > bottomShadowOuter) {
    const t = (ZONE_Z_BOT - z) / SHADOW_BORDER_FT;
    py = STRIKE_ZONE_SIZE + t * GRID_BOX_GAP;
  } else if (z > bottomChaseOuter) {
    const t = (bottomShadowOuter - z) / (CHASE_BORDER_FT - SHADOW_BORDER_FT);
    py = STRIKE_ZONE_SIZE + GRID_BOX_GAP + t * CHASE_H;
  } else {
    const t = Math.max(0, Math.min(1, (bottomChaseOuter - z) / SHADOW_BORDER_FT));
    py = STRIKE_ZONE_SIZE + GRID_BOX_GAP + CHASE_H + t * GRID_BOX_PAD;
  }

  return { x: px, y: py };
}

function cloudDotColor(zone: string): string {
  if (zone === 'HEART') return 'rgba(239, 68, 68, 0.55)';
  if (zone === 'SHADOW') return 'rgba(64, 196, 255, 0.45)';
  if (zone === 'CHASE') return 'rgba(255, 179, 0, 0.5)';
  return 'rgba(148, 163, 184, 0.4)';
}

function InnerStrikeZone3x3({
  selectedZone,
  onSelectZone,
  currentBatter,
  pitches,
  gloveTarget,
  commandRating,
  showZoneLabels,
  markerScaleX,
  markerScaleY,
}: {
  selectedZone: string;
  onSelectZone: (z: string) => void;
  currentBatter: BatterInfo;
  pitches: NumberedPitch[];
  gloveTarget?: { x: number; z: number } | null;
  commandRating?: number;
  showZoneLabels: boolean;
  markerScaleX: number;
  markerScaleY: number;
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
              pitches={pitches}
              showZoneLabels={showZoneLabels}
              onSelect={onSelectZone}
              markerScaleX={markerScaleX}
              markerScaleY={markerScaleY}
            />
          ))}
        </View>
      ))}

      {/* Spray cloud + glove marker, drawn over the grid */}
      <GloveCloudOverlay
        gloveTarget={gloveTarget}
        commandRating={commandRating}
        markerScaleX={markerScaleX}
        markerScaleY={markerScaleY}
      />
    </View>
  );
}

function GloveCloudOverlay({
  gloveTarget,
  commandRating,
  markerScaleX,
  markerScaleY,
}: {
  gloveTarget?: { x: number; z: number } | null;
  commandRating?: number;
  markerScaleX: number;
  markerScaleY: number;
}) {
  const cloud = useMemo(
    () =>
      gloveTarget && commandRating != null
        ? buildSprayCloud(gloveTarget.x, gloveTarget.z, commandRating)
        : null,
    [gloveTarget?.x, gloveTarget?.z, commandRating],
  );
  const glovePx = gloveTarget ? statcastToGrid(gloveTarget.x, gloveTarget.z) : null;
  // The asset has ~9% padding inside its 512 viewBox; compensate so the
  // visible glove fills the old error-circle diameter.
  const gloveSize = cloud
    ? Math.max(18, (2 * cloud.radiusInches * PX_PER_INCH) / 0.81)
    : 0;
  const markerSx = Math.max(markerScaleX, 0.01);
  const markerSy = Math.max(markerScaleY, 0.01);
  const gloveWidth = gloveSize / markerSx;
  const gloveHeight = gloveSize / markerSy;

  if (!cloud || !glovePx) return null;

  return (
    <View style={styles.cloudOverlay}>
      <Svg width={CLOUD_SIZE} height={CLOUD_SIZE}>
        {cloud.points.map((point, index) => {
          const px = statcastToGrid(point.x, point.z);
          return (
            <Ellipse
              key={`cloud-${index}`}
              cx={px.x + CLOUD_PAD_PX}
              cy={px.y + CLOUD_PAD_PX}
              rx={1.5 / markerSx}
              ry={1.5 / markerSy}
              fill={cloudDotColor(point.zone)}
            />
          );
        })}
        {/* Catcher's glove asset — counter-scaled so it stays square */}
        <SvgImage
          href={GLOVE_ICON}
          x={glovePx.x + CLOUD_PAD_PX - gloveWidth / 2}
          y={glovePx.y + CLOUD_PAD_PX - gloveHeight / 2}
          width={gloveWidth}
          height={gloveHeight}
          preserveAspectRatio="none"
        />
      </Svg>
    </View>
  );
}

/** Resolve the exact realized pitch location, with legacy fallbacks. */
function pitchRealizedLocation(pitch: ResolvedPitchDetails): { x: number; z: number } {
  const execution = pitch.gameday_packet?.execution;
  if (
    execution &&
    Number.isFinite(execution.realizedX) &&
    Number.isFinite(execution.realizedZ)
  ) {
    return { x: execution.realizedX, z: execution.realizedZ };
  }

  const intent = pitch.gameday_packet?.intent;
  if (intent && Number.isFinite(intent.targetX) && Number.isFinite(intent.targetZ)) {
    return { x: intent.targetX, z: intent.targetZ };
  }

  const nominal = getZoneNominalTarget(pitch.actual_zone || 'heart');
  return { x: nominal.x, z: nominal.z };
}

function FieldPitchDots({
  pitches,
  scaleX,
  scaleY,
}: {
  pitches: NumberedPitch[];
  scaleX: number;
  scaleY: number;
}) {
  if (pitches.length === 0) return null;

  const sx = Math.max(scaleX, 0.01);
  const sy = Math.max(scaleY, 0.01);
  const slotWidth = PITCH_MARKER_SIZE / sx;
  const slotHeight = PITCH_MARKER_SIZE / sy;

  return (
    <View style={styles.fieldDotsOverlay}>
      {pitches.map(({ pitch, number }) => {
        const location = pitchRealizedLocation(pitch);
        const px = statcastToGrid(location.x, location.z);
        return (
          <View
            key={`${number}-${pitch.pitch_name}`}
            style={[
              styles.fieldDotSlot,
              {
                left: INNER_LEFT + px.x - slotWidth / 2,
                top: INNER_TOP + px.y - slotHeight / 2,
                width: slotWidth,
                height: slotHeight,
              },
            ]}
          >
            <View
              style={[
                styles.pitchNumberMarker,
                {
                  backgroundColor: pitchMarkerColor(pitch.pitch_result),
                  transform: [{ scaleX: 1 / sx }, { scaleY: 1 / sy }],
                },
              ]}
            >
              <Text style={styles.pitchNumberText}>{number}</Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

function InnerZoneCell({
  zoneId,
  displayLabel,
  selectedZone,
  currentBatter,
  pitches,
  showZoneLabels,
  onSelect,
  markerScaleX,
  markerScaleY,
}: {
  zoneId: string;
  displayLabel: string;
  selectedZone: string;
  currentBatter: BatterInfo;
  pitches: NumberedPitch[];
  showZoneLabels: boolean;
  onSelect: (z: string) => void;
  markerScaleX: number;
  markerScaleY: number;
}) {
  const isSelected = selectedZone === zoneId;
  const zonePitches = pitches.filter((p) => p.pitch.actual_zone === zoneId);
  const slg = currentBatter.hot_zones[zoneId] ?? 0.35;

  const heatBg =
    slg >= 0.8
      ? 'rgba(183, 28, 28, 0.65)'
      : slg >= 0.6
        ? 'rgba(191, 54, 12, 0.62)'
        : slg >= 0.45
          ? 'rgba(255, 143, 0, 0.5)'
          : 'rgba(55, 71, 79, 0.28)';

  const slgLabel = '.' + String(Math.floor(slg * 1000)).padStart(3, '0');

  return (
    <TouchableOpacity
      onPress={() => onSelect(zoneId)}
      activeOpacity={0.75}
      style={[
        styles.innerCell,
        {
          backgroundColor: heatBg,
          borderColor: isSelected ? '#FFFFFF' : 'rgba(144, 164, 174, 0.27)',
          borderWidth: isSelected ? 2 : 1,
        },
      ]}
    >
      {showZoneLabels && (
        <>
          <Text style={[styles.cellLabel, { fontWeight: zoneId === STRIKE_ZONES.HEART ? '900' : '400' }]}>
            {displayLabel}
          </Text>
          <Text style={[styles.slgLabel, { color: slg >= 0.6 ? Colors.yellow : Colors.textSecondary }]}>
            {slgLabel}
          </Text>
        </>
      )}
      <ZonePitchMarkers
        pitches={zonePitches}
        scaleX={markerScaleX}
        scaleY={markerScaleY}
      />
    </TouchableOpacity>
  );
}

// ─── Chase Zone Pill ──────────────────────────────────────────────────────────

function ChaseZonePill({
  zoneId, label, isSelected, pitches, onSelect, horizontal, transparent = false,
  markerScaleX, markerScaleY,
}: {
  zoneId: string;
  label: string;
  isSelected: boolean;
  pitches: NumberedPitch[];
  onSelect: (z: string) => void;
  horizontal: boolean;
  transparent?: boolean;
  markerScaleX: number;
  markerScaleY: number;
}) {
  const zonePitches = pitches.filter((p) => p.pitch.actual_zone === zoneId);

  if (transparent) {
    return (
      <TouchableOpacity
        onPress={() => onSelect(zoneId)}
        activeOpacity={0.75}
        style={[
          styles.chasePill,
          horizontal ? styles.chasePillH : styles.chasePillV,
          isSelected
            ? {
                backgroundColor: 'rgba(64, 196, 255, 0.18)',
                borderColor: '#FFFFFF',
                borderWidth: 2,
              }
            : {
                backgroundColor: 'transparent',
                borderColor: 'transparent',
                borderWidth: 0,
              },
        ]}
      >
        <ZonePitchMarkers
          pitches={zonePitches}
          scaleX={markerScaleX}
          scaleY={markerScaleY}
        />
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      onPress={() => onSelect(zoneId)}
      activeOpacity={0.75}
      style={[
        styles.chasePill,
        horizontal ? styles.chasePillH : styles.chasePillV,
        {
          backgroundColor: isSelected ? 'rgba(2, 136, 209, 0.35)' : 'transparent',
          borderColor: isSelected ? Colors.blue : Colors.borderSecondary,
          borderWidth: isSelected ? 2 : 1,
        },
      ]}
    >
      <Text style={[styles.chaseLabel, { color: isSelected ? Colors.blueSky : Colors.textMuted }]}>
        {label}
      </Text>
      <ZonePitchMarkers
        pitches={zonePitches}
        scaleX={markerScaleX}
        scaleY={markerScaleY}
      />
    </TouchableOpacity>
  );
}

// ─── Pitch Markers ────────────────────────────────────────────────────────────

const PITCH_MARKER_SIZE = 18;

function ZonePitchMarkers({
  pitches,
  scaleX,
  scaleY,
}: {
  pitches: NumberedPitch[];
  scaleX: number;
  scaleY: number;
}) {
  if (pitches.length === 0) return null;

  const sx = Math.max(scaleX, 0.01);
  const sy = Math.max(scaleY, 0.01);

  return (
    <View style={styles.pitchMarkersOverlay}>
      {pitches.map(({ pitch, number }) => (
        <View
          key={`${number}-${pitch.pitch_name}`}
          style={[
            styles.pitchMarkerSlot,
            {
              width: PITCH_MARKER_SIZE / sx,
              height: PITCH_MARKER_SIZE / sy,
            },
          ]}
        >
          <View
            style={[
              styles.pitchNumberMarker,
              {
                backgroundColor: pitchMarkerColor(pitch.pitch_result),
                transform: [{ scaleX: 1 / sx }, { scaleY: 1 / sy }],
              },
            ]}
          >
            <Text style={styles.pitchNumberText}>{number}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

function PitchOutcomeSummaryBadge({ latestPitch }: { latestPitch: ResolvedPitchDetails }) {
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
    backgroundColor: 'transparent',
    padding: CONTAINER_PAD,
    gap: 10,
    alignItems: 'center',
  },
  gridOuter: { position: 'relative' },
  // Field variant: one visible rectangle, with the chase/waste bands kept as
  // invisible tap area and dot-rendering space.
  fieldBox: { position: 'relative', width: GRID_WIDTH, height: GRID_HEIGHT },
  strikeZoneRect: {
    position: 'absolute',
    left: CONTENT_LEFT,
    top: CONTENT_TOP,
    width: GRID_CONTENT_PX,
    height: GRID_CONTENT_PX,
    borderWidth: 2,
    borderColor: 'rgba(236, 240, 245, 0.9)',
    borderRadius: 2,
    backgroundColor: 'rgba(27, 36, 48, 0.14)',
    pointerEvents: 'none',
  },
  fieldGloveLayer: {
    position: 'absolute',
    left: INNER_LEFT,
    top: INNER_TOP,
    width: STRIKE_ZONE_SIZE,
    height: STRIKE_ZONE_SIZE,
    pointerEvents: 'none',
  },
  fieldDotsOverlay: {
    position: 'absolute',
    left: 0,
    top: 0,
    width: GRID_WIDTH,
    height: GRID_HEIGHT,
    pointerEvents: 'none',
  },
  fieldDotSlot: {
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Grid outer box
  gridBox: {
    backgroundColor: GRID_PANEL_BG,
    borderRadius: 8,
    padding: GRID_BOX_PAD,
    gap: GRID_BOX_GAP,
  },
  middleRow: {
    flexDirection: 'row',
    alignItems: 'stretch',
    justifyContent: 'center',
    gap: GRID_BOX_GAP,
    height: STRIKE_ZONE_SIZE,
  },
  // Inner 3×3 — fixed square so the strike zone holds a 1:1 ratio
  innerGrid: {
    position: 'relative',
    width: STRIKE_ZONE_SIZE,
    height: STRIKE_ZONE_SIZE,
    borderRadius: 4,
    backgroundColor: GRID_INNER_BG,
    padding: 2,
    gap: 2,
  },
  cloudOverlay: {
    position: 'absolute',
    left: -CLOUD_PAD_PX,
    top: -CLOUD_PAD_PX,
    width: CLOUD_SIZE,
    height: CLOUD_SIZE,
    pointerEvents: 'none',
  },
  innerRow: { flex: 1, flexDirection: 'row', gap: 2 },
  innerCell: { flex: 1, borderRadius: 3, alignItems: 'center', justifyContent: 'center', padding: 2 },
  cellLabel: { fontSize: 9, color: '#FFF', textAlign: 'center' },
  slgLabel: { fontSize: 8.5, fontWeight: '700', textAlign: 'center' },
  // Numbered pitch markers
  pitchMarkersOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    pointerEvents: 'none',
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'center',
    alignContent: 'center',
    gap: 2,
    padding: 2,
  },
  pitchMarkerSlot: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  pitchNumberMarker: {
    width: PITCH_MARKER_SIZE,
    height: PITCH_MARKER_SIZE,
    borderRadius: PITCH_MARKER_SIZE / 2,
    borderWidth: 1.5,
    borderColor: '#FFF',
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 4,
  },
  pitchNumberText: {
    color: '#000',
    fontSize: 9,
    fontWeight: '900',
    includeFontPadding: false,
  },
  // Chase pill
  chasePill: { borderRadius: 4, alignItems: 'center', justifyContent: 'center', padding: 4 },
  chasePillH: { height: CHASE_H },
  chasePillV: { width: CHASE_V },
  chaseLabel: { fontSize: 8.5, fontWeight: '700', textAlign: 'center' },
  // Summary badge
  summaryBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#0A0E13', borderRadius: 6, borderWidth: 1, paddingHorizontal: 8, paddingVertical: 4, width: '100%' },
  summaryDot: { width: 8, height: 8, borderRadius: 4 },
  summaryText: { flex: 1, fontSize: 11, fontWeight: '600', color: '#FFF' },
});
