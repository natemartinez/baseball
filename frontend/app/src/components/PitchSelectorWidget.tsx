import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  Animated,
  Easing,
  Platform,
  StyleSheet,
} from 'react-native';

/** Hold duration; also drives the background fill progress. */
const HOLD_DURATION_MS = 500;
/** Native driver isn't available on react-native-web. */
const USE_NATIVE_DRIVER = Platform.OS !== 'web';
import type {
  PitchArsenalItem,
  PitcherInfo,
  StrategyIntentDecision,
} from '../types/api';
import { Colors } from '../theme/colors';

interface PitchSelectorWidgetProps {
  pitcher: PitcherInfo;
  selectedPitchIntent: string;
  recommendedPitch?: string;
  strategyIntent?: StrategyIntentDecision;
  onSelectPitchIntent: (name: string) => void;
  onThrowPitch: () => void;
  isActionPending?: boolean;
}

/**
 * PitchSelectorWidget — Standalone container for selecting pitch intent.
 * Placed directly above the Strike Zone Grid.
 *
 * Hosts the arsenal chips and the strategy summary (situation tag, recommended
 * target, and pitch probability percentages).
 *
 * Interaction model: tap a pitch chip to select it; press and hold a chip to
 * select and immediately throw that pitch (no separate throw button).
 */
export function PitchSelectorWidget({
  pitcher,
  selectedPitchIntent,
  recommendedPitch,
  strategyIntent,
  onSelectPitchIntent,
  onThrowPitch,
  isActionPending = false,
}: PitchSelectorWidgetProps) {
  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.sectionLabel}>PITCH SELECTOR</Text>
        <Text style={styles.headerHint}>TAP TO SELECT • HOLD TO THROW</Text>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.arsenalRow}
      >
        {pitcher.arsenal.map((item) => (
          <ArsenalChip
            key={item.name}
            item={item}
            isSelected={item.name === selectedPitchIntent}
            isRecommended={item.name === recommendedPitch}
            disabled={isActionPending}
            onSelect={() => onSelectPitchIntent(item.name)}
            onThrow={() => {
              onSelectPitchIntent(item.name);
              onThrowPitch();
            }}
          />
        ))}
      </ScrollView>

      {/* Strategy summary: situation, recommended target, pitch percentages */}
      {strategyIntent && (
        <CollapsibleStrategySummary
          strategyIntent={strategyIntent}
          onSelectPitchIntent={onSelectPitchIntent}
        />
      )}
    </View>
  );
}

// ─── Collapsible Strategy Summary ────────────────────────────────────────────

function CollapsibleStrategySummary({
  strategyIntent,
  onSelectPitchIntent,
}: {
  strategyIntent: StrategyIntentDecision;
  onSelectPitchIntent: (name: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [contentHeight, setContentHeight] = useState(0);
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(progress, {
      toValue: expanded ? 1 : 0,
      duration: expanded ? 220 : 160,
      easing: Easing.out(Easing.cubic),
      // Height can't use the native driver.
      useNativeDriver: false,
    }).start();
  }, [expanded, progress]);

  const height = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [0, contentHeight],
  });

  return (
    <View>
      {/* Clipped panel: content is bottom-anchored so it rises from the bottom */}
      <Animated.View style={[styles.strategyCollapse, { height }]}>
        <Animated.View
          onLayout={(e) => setContentHeight(e.nativeEvent.layout.height)}
          style={[styles.strategyCollapseInner, { opacity: progress }]}
        >
          <StrategySummaryStrip
            strategyIntent={strategyIntent}
            onSelectPitchIntent={onSelectPitchIntent}
          />
        </Animated.View>
      </Animated.View>

      <TouchableOpacity
        onPress={() => setExpanded((v) => !v)}
        activeOpacity={0.7}
        style={styles.strategyToggle}
        accessibilityLabel={
          expanded ? 'Hide strategy summary' : 'Show strategy summary'
        }
      >
        <Text style={styles.strategyToggleTriangle}>{expanded ? '▼' : '▲'}</Text>
      </TouchableOpacity>
    </View>
  );
}

// ─── Strategy Summary Strip ──────────────────────────────────────────────────

function StrategySummaryStrip({
  strategyIntent,
  onSelectPitchIntent,
}: {
  strategyIntent: StrategyIntentDecision;
  onSelectPitchIntent: (name: string) => void;
}) {
  const {
    situation_tag,
    recommended_pitch,
    recommended_zone,
    pitch_weights = [],
  } = strategyIntent;

  return (
    <View style={styles.strategyStrip}>
      <View style={styles.strategyStripHeader}>
        <View style={styles.situationBadge}>
          <Text style={styles.situationText}>{situation_tag.replace(/_/g, ' ')}</Text>
        </View>
        <TouchableOpacity
          activeOpacity={0.75}
          onPress={() => onSelectPitchIntent(recommended_pitch)}
          style={styles.recTargetPill}
        >
          <Text style={styles.recTargetLabel}>REC TARGET</Text>
          <Text style={styles.recTargetPitch}>{recommended_pitch}</Text>
          <Text style={styles.recTargetZone}>{recommended_zone}</Text>
        </TouchableOpacity>
      </View>

      {pitch_weights.length > 0 && (
        <View style={styles.pctList}>
          {pitch_weights.map((pw) => (
            <View key={pw.pitch_name} style={styles.pctRow}>
              <Text
                style={[
                  styles.pctName,
                  pw.is_most_likely && styles.pctNamePrimary,
                ]}
                numberOfLines={1}
              >
                {pw.pitch_name}
              </Text>
              <Text
                style={[
                  styles.pctValue,
                  pw.is_most_likely && styles.pctValuePrimary,
                ]}
              >
                {pw.probability_pct}%
              </Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

// ─── Arsenal Chip ────────────────────────────────────────────────────────────

function ArsenalChip({
  item,
  isSelected,
  isRecommended,
  disabled = false,
  onSelect,
  onThrow,
}: {
  item: PitchArsenalItem;
  isSelected: boolean;
  isRecommended?: boolean;
  disabled?: boolean;
  onSelect: () => void;
  onThrow: () => void;
}) {
  const holdProgress = useRef(new Animated.Value(0)).current;

  const scale = holdProgress.interpolate({
    inputRange: [0, 1],
    outputRange: [0.05, 1],
  });
  const fillOpacity = holdProgress.interpolate({
    inputRange: [0, 0.15, 1],
    outputRange: [0, 0.55, 0.55],
  });

  function startHold() {
    holdProgress.setValue(0);
    Animated.timing(holdProgress, {
      toValue: 1,
      duration: HOLD_DURATION_MS,
      useNativeDriver: USE_NATIVE_DRIVER,
    }).start();
  }

  function cancelHold() {
    holdProgress.stopAnimation(() => {
      Animated.timing(holdProgress, {
        toValue: 0,
        duration: 120,
        useNativeDriver: USE_NATIVE_DRIVER,
      }).start();
    });
  }

  return (
    <TouchableOpacity
      onPressIn={startHold}
      onPressOut={cancelHold}
      onPress={onSelect}
      onLongPress={() => {
        onThrow();
        cancelHold();
      }}
      delayLongPress={HOLD_DURATION_MS}
      disabled={disabled}
      activeOpacity={0.85}
      style={[
        styles.arsenalChip,
        disabled && styles.arsenalChipDisabled,
        {
          backgroundColor: 'transparent',
          borderColor: isSelected
            ? Colors.blue
            : isRecommended
              ? 'rgba(16, 185, 129, 0.6)'
              : Colors.borderSecondary,
        },
      ]}
    >
      {/* Hold-to-throw "breathing" fill: grows from a point to fill the chip */}
      <Animated.View
        style={[
          styles.holdFill,
          { opacity: fillOpacity, transform: [{ scale }] },
        ]}
      />

      {isRecommended && (
        <View style={styles.recBadge}>
          <Text style={styles.recBadgeText}>★ PRIMARY</Text>
        </View>
      )}
      {isSelected && <View style={styles.arsenalDot} />}
      <Text
        style={[
          styles.arsenalName,
          {
            fontWeight: isSelected ? '700' : '500',
            color: isSelected
              ? '#FFF'
              : isRecommended
                ? '#34D399'
                : Colors.textPrimary,
          },
        ]}
      >
        {item.name}
      </Text>
      <Text
        style={[
          styles.arsenalVelo,
          { color: isSelected ? Colors.yellow : Colors.textSecondary },
        ]}
      >
        {formatVelocityRange(item)}
      </Text>
    </TouchableOpacity>
  );
}

function formatVelocityRange(item: PitchArsenalItem): string {
  if (item.velocity_min_mph != null && item.velocity_max_mph != null) {
    return `${item.velocity_min_mph}–${item.velocity_max_mph} mph`;
  }
  return `${item.velocity_mph} mph`;
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'transparent',
    borderRadius: 12,
    padding: 14,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 1.0,
    textTransform: 'uppercase',
  },
  headerHint: {
    fontSize: 9,
    fontWeight: '600',
    color: Colors.textMuted,
    letterSpacing: 0.5,
  },
  arsenalRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 2,
  },
  arsenalChip: {
    position: 'relative',
    overflow: 'hidden',
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
    alignItems: 'center',
    minWidth: 132,
    gap: 2,
  },
  arsenalChipDisabled: { opacity: 0.45 },
  holdFill: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 200, 83, 0.5)',
    pointerEvents: 'none',
  },
  arsenalDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.yellow,
    marginBottom: 2,
  },
  arsenalName: {
    fontSize: 11,
    textAlign: 'center',
  },
  arsenalVelo: {
    fontSize: 12,
    fontWeight: '700',
  },
  recBadge: {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.4)',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 4,
    marginBottom: 2,
  },
  recBadgeText: {
    fontSize: 7,
    fontWeight: '800',
    color: '#34D399',
    letterSpacing: 0.3,
  },
  // ─── Collapsible strategy summary ───────────────────────────────────────
  strategyCollapse: {
    overflow: 'hidden',
  },
  strategyCollapseInner: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
  },
  strategyToggle: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 6,
  },
  strategyToggleTriangle: {
    color: Colors.blue,
    fontSize: 14,
    fontWeight: '900',
    lineHeight: 16,
  },
  // ─── Strategy summary strip ─────────────────────────────────────────────
  strategyStrip: {
    backgroundColor: Colors.bgInput,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    padding: 10,
    gap: 8,
  },
  strategyStripHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 6,
  },
  situationBadge: {
    backgroundColor: 'rgba(255, 179, 0, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(255, 179, 0, 0.4)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  situationText: {
    fontSize: 10,
    fontWeight: '800',
    color: Colors.amber,
    letterSpacing: 0.5,
  },
  recTargetPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.35)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  recTargetLabel: {
    fontSize: 8,
    fontWeight: '800',
    color: Colors.textMuted,
    letterSpacing: 0.4,
  },
  recTargetPitch: {
    fontSize: 10,
    fontWeight: '800',
    color: '#34D399',
  },
  recTargetZone: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: '800',
    color: Colors.amberLight,
  },
  pctList: {
    gap: 3,
  },
  pctRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  pctName: {
    flex: 1,
    fontSize: 10,
    color: Colors.textSecondary,
  },
  pctNamePrimary: {
    color: '#34D399',
    fontWeight: '800',
  },
  pctValue: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: '800',
    color: Colors.textMuted,
  },
  pctValuePrimary: {
    color: '#34D399',
  },
});
