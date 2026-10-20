import React, { useMemo } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  type GestureResponderEvent,
} from 'react-native';
import Svg, { Circle, Image as SvgImage } from 'react-native-svg';
import type { BatterInfo, PitchDetails, PitchResultType } from '../types/api';
import { STRIKE_ZONES } from '../types/api';
import { buildSprayCloud, CHASE_BORDER_FT, SHADOW_BORDER_FT } from '../services/gamedayMath';
import { Colors } from '../theme/colors';

const GLOVE_ICON = require('../../assets/glove-icon.png');

interface StrikeZoneGridWidgetProps {
  selectedZone: string;
  onSelectZone: (zone: string) => void;
  currentBatter: BatterInfo;
  latestPitch?: PitchDetails | null;
  /** All pitches in the current at-bat, oldest first (numbered 1..n). */
  atBatPitches?: PitchDetails[];
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
}

interface NumberedPitch {
  pitch: PitchDetails;
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
    const lx = Math.max(0, Math.min(GRID_WIDTH, e.nativeEvent.locationX));
    const ly = Math.max(0, Math.min(GRID_HEIGHT, e.nativeEvent.locationY));
    onSetGloveTarget(gridToStatcastX(lx), gridToStatcastZ(ly));
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
          />
          <InnerStrikeZone3x3
            selectedZone={selectedZone}
            onSelectZone={onSelectZone}
            currentBatter={currentBatter}
            pitches={numberedPitches}
            gloveTarget={gloveTarget}
            commandRating={commandRating}
            showZoneLabels={showZoneLabels}
          />
          <ChaseZonePill
            zoneId={STRIKE_ZONES.CHASE_AWAY}
            label={'CHASE\nAWAY'}
            isSelected={selectedZone === STRIKE_ZONES.CHASE_AWAY}
            pitches={numberedPitches}
            onSelect={onSelectZone}
            transparent={chaseTransparent}
            horizontal={false}
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
const GRID_PAD_PX = 2;
const GRID_CONTENT_PX = STRIKE_ZONE_SIZE - GRID_PAD_PX * 2;
const CLOUD_PAD_PX = 64;
const CLOUD_SIZE = STRIKE_ZONE_SIZE + CLOUD_PAD_PX * 2;
const PX_PER_INCH = GRID_CONTENT_PX / 17;

/**
 * The visible layout has three bands on each side:
 *   padding (waste) -> chase strip -> 4px shadow gap -> strike zone.
 * These functions map each band independently so the chase strips represent
 * the real 1-2 ball-width chase band and never collapse into the shadow edge.
 */
function gridToStatcastX(lx: number): number {
  const stripOuter = GRID_BOX_PAD;
  const stripInner = GRID_BOX_PAD + CHASE_V;
  const shadowInner = INNER_LEFT;

  if (lx < stripOuter) {
    const t = (stripOuter - lx) / GRID_BOX_PAD;
    return ZONE_X_MIN - CHASE_BORDER_FT - t * SHADOW_BORDER_FT;
  }
  if (lx < stripInner) {
    const t = (lx - stripOuter) / CHASE_V;
    return ZONE_X_MIN - CHASE_BORDER_FT + t * (CHASE_BORDER_FT - SHADOW_BORDER_FT);
  }
  if (lx < shadowInner) {
    const t = (lx - stripInner) / GRID_BOX_GAP;
    return ZONE_X_MIN - SHADOW_BORDER_FT + t * SHADOW_BORDER_FT;
  }
  if (lx <= INNER_LEFT + STRIKE_ZONE_SIZE) {
    return ZONE_X_MIN + ((lx - INNER_LEFT) / STRIKE_ZONE_SIZE) * (ZONE_X_MAX - ZONE_X_MIN);
  }

  const rightShadowStart = INNER_LEFT + STRIKE_ZONE_SIZE;
  const rightStripStart = rightShadowStart + GRID_BOX_GAP;
  const rightStripEnd = rightStripStart + CHASE_V;
  if (lx < rightStripStart) {
    const t = (lx - rightShadowStart) / GRID_BOX_GAP;
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
  const shadowInner = INNER_TOP;

  if (ly < stripOuter) {
    const t = (stripOuter - ly) / GRID_BOX_PAD;
    return ZONE_Z_TOP + CHASE_BORDER_FT + t * SHADOW_BORDER_FT;
  }
  if (ly < stripInner) {
    const t = (ly - stripOuter) / CHASE_H;
    return ZONE_Z_TOP + CHASE_BORDER_FT - t * (CHASE_BORDER_FT - SHADOW_BORDER_FT);
  }
  if (ly < shadowInner) {
    const t = (ly - stripInner) / GRID_BOX_GAP;
    return ZONE_Z_TOP + SHADOW_BORDER_FT - t * SHADOW_BORDER_FT;
  }
  if (ly <= INNER_TOP + STRIKE_ZONE_SIZE) {
    return ZONE_Z_TOP - ((ly - INNER_TOP) / STRIKE_ZONE_SIZE) * (ZONE_Z_TOP - ZONE_Z_BOT);
  }

  const bottomShadowStart = INNER_TOP + STRIKE_ZONE_SIZE;
  const bottomStripStart = bottomShadowStart + GRID_BOX_GAP;
  const bottomStripEnd = bottomStripStart + CHASE_H;
  if (ly < bottomStripStart) {
    const t = (ly - bottomShadowStart) / GRID_BOX_GAP;
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
}: {
  selectedZone: string;
  onSelectZone: (z: string) => void;
  currentBatter: BatterInfo;
  pitches: NumberedPitch[];
  gloveTarget?: { x: number; z: number } | null;
  commandRating?: number;
  showZoneLabels: boolean;
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
            />
          ))}
        </View>
      ))}

      {/* Spray cloud + glove marker, drawn over the grid */}
      {cloud && glovePx && (
        <View style={styles.cloudOverlay} pointerEvents="none">
          <Svg width={CLOUD_SIZE} height={CLOUD_SIZE}>
            {cloud.points.map((point, index) => {
              const px = statcastToGrid(point.x, point.z);
              return (
                <Circle
                  key={`cloud-${index}`}
                  cx={px.x + CLOUD_PAD_PX}
                  cy={px.y + CLOUD_PAD_PX}
                  r={1.5}
                  fill={cloudDotColor(point.zone)}
                />
              );
            })}
            {/* Catcher's glove asset — fills the old error-circle area */}
            <SvgImage
              href={GLOVE_ICON}
              x={glovePx.x + CLOUD_PAD_PX - gloveSize / 2}
              y={glovePx.y + CLOUD_PAD_PX - gloveSize / 2}
              width={gloveSize}
              height={gloveSize}
              preserveAspectRatio="xMidYMid meet"
            />
          </Svg>
        </View>
      )}
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
}: {
  zoneId: string;
  displayLabel: string;
  selectedZone: string;
  currentBatter: BatterInfo;
  pitches: NumberedPitch[];
  showZoneLabels: boolean;
  onSelect: (z: string) => void;
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
      <ZonePitchMarkers pitches={zonePitches} />
    </TouchableOpacity>
  );
}

// ─── Chase Zone Pill ──────────────────────────────────────────────────────────

function ChaseZonePill({
  zoneId, label, isSelected, pitches, onSelect, horizontal, transparent = false,
}: {
  zoneId: string;
  label: string;
  isSelected: boolean;
  pitches: NumberedPitch[];
  onSelect: (z: string) => void;
  horizontal: boolean;
  transparent?: boolean;
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
        <ZonePitchMarkers pitches={zonePitches} />
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
      <ZonePitchMarkers pitches={zonePitches} />
    </TouchableOpacity>
  );
}

// ─── Pitch Markers ────────────────────────────────────────────────────────────

function ZonePitchMarkers({ pitches }: { pitches: NumberedPitch[] }) {
  if (pitches.length === 0) return null;

  return (
    <View style={styles.pitchMarkersOverlay} pointerEvents="none">
      {pitches.map(({ pitch, number }) => (
        <View
          key={`${number}-${pitch.pitch_name}`}
          style={[
            styles.pitchNumberMarker,
            { backgroundColor: pitchMarkerColor(pitch.pitch_result) },
          ]}
        >
          <Text style={styles.pitchNumberText}>{number}</Text>
        </View>
      ))}
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
    backgroundColor: 'transparent',
    padding: 14,
    gap: 10,
    alignItems: 'center',
  },
  gridOuter: { position: 'relative' },
  // Grid outer box
  gridBox: {
    backgroundColor: Colors.bgInput,
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
    backgroundColor: '#1B2430',
    padding: 2,
    gap: 2,
  },
  cloudOverlay: {
    position: 'absolute',
    left: -CLOUD_PAD_PX,
    top: -CLOUD_PAD_PX,
    width: CLOUD_SIZE,
    height: CLOUD_SIZE,
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
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'center',
    alignContent: 'center',
    gap: 2,
    padding: 2,
  },
  pitchNumberMarker: {
    width: 18,
    height: 18,
    borderRadius: 9,
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
