import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
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

/** Target charging sweet spot in milliseconds. */
const TARGET_SWEET_SPOT_MS = 1000.0;
/** Max charging hold duration before auto-release. */
const MAX_HOLD_MS = 1500.0;
/** Native driver isn't available on react-native-web. */
const USE_NATIVE_DRIVER = Platform.OS !== 'web';
import type {
  PitchArsenalItem,
  PitcherInfo,
  StrategyIntentDecision,
  TimingTier,
} from '../../types/api';
import { Colors } from '../../theme/colors';
import {
  evaluateChargingTiming,
  getAbilityTier,
  getAbilityTierColor,
} from '../../services/gamedayMath';
import {
  computeBaselineEffectiveness,
  calculateCombinedEffectiveCommand,
} from '../../services/effectivenessModel';
import {
  resolveInitialWidgetViewMode,
  resolveUpdatedWidgetViewMode,
  canSwitchOrSelectPitch,
  shouldResetToChipsOnPitchComplete,
  type WidgetViewMode,
} from './pitchSelectorState';

export {
  resolveInitialWidgetViewMode,
  resolveUpdatedWidgetViewMode,
  canSwitchOrSelectPitch,
  shouldResetToChipsOnPitchComplete,
  type WidgetViewMode,
};


interface PitchSelectorWidgetProps {
  pitcher: PitcherInfo;
  selectedPitchName: string;
  recommendedPitch?: string;
  strategyIntent?: StrategyIntentDecision;
  onSelectPitchName: (name: string) => void;
  onThrowPitch: (timingTier: TimingTier, timingLabel: string) => void;
  isActionPending?: boolean;
  disabled?: boolean;
  /** Horizontal footer layout (default) or a vertical side-panel stack. */
  layout?: 'horizontal' | 'vertical';
  /** Callback reporting charging progress (0.0 to 1.5) or null when not charging. */
  onChargingProgress?: (progress: number | null) => void;
  /** Current pitcher stamina percentage (0 to 100, defaults to 100). */
  staminaPct?: number;
  /** Current confidence percentage for the selected pitch (0 to 100, defaults to 50). */
  confidencePct?: number;
  /** Individual confidence percentages for pitches in the arsenal. */
  pitchConfidences?: Record<string, number>;
  /** Current effectiveness percentage for the selected pitch (0 to 100). */
  effectivenessPct?: number;
  /** Individual effectiveness percentages for pitches in the arsenal. */
  pitchEffectiveness?: Record<string, number>;
}

function getStaminaColor(pct: number): string {
  if (pct > 60) return '#10B981'; // Green
  if (pct > 30) return '#F59E0B'; // Amber
  return '#EF4444'; // Red
}

function getConfidenceColor(pct: number): string {
  if (pct >= 65) return '#00E5FF'; // Electric Cyan
  if (pct >= 45) return '#3B82F6'; // Royal Blue
  if (pct >= 25) return '#F59E0B'; // Amber
  return '#EF4444'; // Red
}

function getEffectivenessColor(pct: number): string {
  if (pct >= 85) return '#A855F7'; // Purple (elite stuff)
  if (pct >= 75) return '#10B981'; // Emerald Green (sharp)
  if (pct >= 60) return '#F59E0B'; // Amber (flattening)
  return '#EF4444'; // Red (flat/hittable)
}

interface PitcherMetersSectionProps {
  staminaPct: number;
  confidencePct: number;
  layout?: 'horizontal' | 'vertical';
}

function PitcherMetersSection({
  staminaPct,
  confidencePct,
  layout = 'horizontal',
}: PitcherMetersSectionProps) {
  const isVertical = layout === 'vertical';
  const clampedStamina = Math.max(0, Math.min(100, staminaPct));
  const clampedConfidence = Math.max(0, Math.min(100, confidencePct));
  const staminaColor = getStaminaColor(clampedStamina);
  const confidenceColor = getConfidenceColor(clampedConfidence);

  return (
    <View style={isVertical ? styles.metersColumn : styles.metersRow}>
      {/* Stamina Meter */}
      <View
        style={styles.meterContainer}
        accessibilityRole="progressbar"
        accessibilityLabel="Pitcher stamina"
        accessibilityValue={{ min: 0, max: 100, now: Math.round(clampedStamina) }}
      >
        <View style={styles.meterLabelRow}>
          <Text style={styles.meterTitle}>STAMINA</Text>
          <Text style={[styles.meterValue, { color: staminaColor }]}>
            {Math.round(clampedStamina)}%
          </Text>
        </View>
        <View style={styles.meterTrack}>
          <View
            style={[
              styles.meterFill,
              { width: `${clampedStamina}%`, backgroundColor: staminaColor },
            ]}
          />
        </View>
      </View>

      {/* Confidence Meter (Mental) */}
      <View
        style={styles.meterContainer}
        accessibilityRole="progressbar"
        accessibilityLabel="Pitcher confidence"
        accessibilityValue={{ min: 0, max: 100, now: Math.round(clampedConfidence) }}
      >
        <View style={styles.meterLabelRow}>
          <Text style={styles.meterTitle} numberOfLines={1}>
            CONFIDENCE
          </Text>
          <Text style={[styles.meterValue, { color: confidenceColor }]}>
            {Math.round(clampedConfidence)}%
          </Text>
        </View>
        <View style={styles.meterTrack}>
          <View
            style={[
              styles.meterFill,
              { width: `${clampedConfidence}%`, backgroundColor: confidenceColor },
            ]}
          />
        </View>
      </View>
    </View>
  );
}

/**
 * PitchSelectorWidget — Standalone container for selecting and throwing a pitch.
 * Placed directly above or beside the Strike Zone Grid.
 *
 * Hosts the arsenal chips, dedicated press-and-release THROW button,
 * and the strategy summary (situation tag, recommended target, and pitch probability percentages).
 */
function PitchSelectorWidgetComponent({
  pitcher,
  selectedPitchName,
  recommendedPitch,
  strategyIntent,
  onSelectPitchName,
  onThrowPitch,
  isActionPending = false,
  disabled = false,
  layout = 'horizontal',
  onChargingProgress,
  staminaPct = 100,
  confidencePct = 50,
  pitchConfidences,
  effectivenessPct,
  pitchEffectiveness,
}: PitchSelectorWidgetProps) {
  const isVertical = layout === 'vertical';

  const pitchNames = useMemo(
    () => (pitcher.arsenal ?? []).map((p) => p.name),
    [pitcher.arsenal],
  );
  const [viewMode, setViewMode] = useState<WidgetViewMode>(() =>
    resolveInitialWidgetViewMode(selectedPitchName, pitchNames)
  );

  const isMountedRef = useRef(true);
  const isTransitioningRef = useRef(false);
  const fadeAnim = useRef(new Animated.Value(1)).current;
  const prevActionPendingRef = useRef(isActionPending);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      fadeAnim.stopAnimation();
      if (rafIdRef.current != null) {
        cancelAnimationFrame(rafIdRef.current);
      }
      isChargingRef.current = false;
    };
  }, [fadeAnim]);

  useEffect(() => {
    if (shouldResetToChipsOnPitchComplete(prevActionPendingRef.current, isActionPending)) {
      setViewMode('chips');
      fadeAnim.setValue(1);
      isTransitioningRef.current = false;
    }
    prevActionPendingRef.current = isActionPending;
  }, [isActionPending, fadeAnim]);

  const switchView = useCallback(
    (nextMode: WidgetViewMode) => {
      if (viewMode === nextMode || isTransitioningRef.current || !isMountedRef.current) return;
      isTransitioningRef.current = true;
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 90,
        easing: Easing.out(Easing.quad),
        useNativeDriver: USE_NATIVE_DRIVER,
      }).start(({ finished }) => {
        if (!isMountedRef.current) return;
        if (finished) {
          setViewMode(nextMode);
          Animated.timing(fadeAnim, {
            toValue: 1,
            duration: 120,
            easing: Easing.out(Easing.cubic),
            useNativeDriver: USE_NATIVE_DRIVER,
          }).start(() => {
            if (isMountedRef.current) {
              isTransitioningRef.current = false;
            }
          });
        } else {
          fadeAnim.setValue(1);
          isTransitioningRef.current = false;
        }
      });
    },
    [viewMode, fadeAnim],
  );

  useEffect(() => {
    const nextMode = resolveUpdatedWidgetViewMode(viewMode, selectedPitchName, pitchNames);
    if (nextMode !== viewMode) {
      switchView(nextMode);
    }
  }, [selectedPitchName, pitchNames, viewMode, switchView]);

  const handleSelectPitch = useCallback(
    (name: string) => {
      if (!canSwitchOrSelectPitch(disabled, isActionPending)) return;
      onSelectPitchName(name);
      switchView('throw');
    },
    [disabled, isActionPending, onSelectPitchName, switchView],
  );

  const pressStartTimeRef = useRef<number | null>(null);
  const rafIdRef = useRef<number | null>(null);
  const isChargingRef = useRef(false);
  const [isCharging, setIsCharging] = useState(false);
  const [chargeRatio, setChargeRatio] = useState(0);

  const handlePressIn = useCallback(() => {
    if (disabled || isActionPending || !selectedPitchName) return;
    pressStartTimeRef.current = performance.now();
    isChargingRef.current = true;
    setIsCharging(true);
    setChargeRatio(0);
    onChargingProgress?.(0);

    const loop = () => {
      if (!isChargingRef.current || pressStartTimeRef.current == null) return;
      const now = performance.now();
      const elapsed = now - pressStartTimeRef.current;
      const ratio = elapsed / TARGET_SWEET_SPOT_MS;
      setChargeRatio(ratio);
      onChargingProgress?.(Math.min(ratio, 1.5));

      if (elapsed >= MAX_HOLD_MS) {
        // Auto-release at 1500ms max hold (LATE • POOR)
        if (rafIdRef.current != null) {
          cancelAnimationFrame(rafIdRef.current);
          rafIdRef.current = null;
        }
        isChargingRef.current = false;
        setIsCharging(false);
        setChargeRatio(0);
        pressStartTimeRef.current = null;
        onChargingProgress?.(null);
        onThrowPitch('POOR', 'LATE • POOR');
        return;
      }
      rafIdRef.current = requestAnimationFrame(loop);
    };
    rafIdRef.current = requestAnimationFrame(loop);
  }, [disabled, isActionPending, selectedPitchName, onChargingProgress, onThrowPitch]);

  const handlePressOut = useCallback(() => {
    if (!isChargingRef.current || pressStartTimeRef.current == null) return;
    if (rafIdRef.current != null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
    const now = performance.now();
    const elapsed = now - pressStartTimeRef.current;
    isChargingRef.current = false;
    setIsCharging(false);
    setChargeRatio(0);
    pressStartTimeRef.current = null;
    onChargingProgress?.(null);

    const selectedPitchItem = (pitcher.arsenal ?? []).find((p) => p.name === selectedPitchName);
    const selectedPitchEff =
      (selectedPitchName && pitchEffectiveness?.[selectedPitchName] != null)
        ? pitchEffectiveness[selectedPitchName]
        : (selectedPitchItem
          ? computeBaselineEffectiveness(
            selectedPitchItem.velocity_mph ?? 93,
            selectedPitchItem.break_rating ?? 75,
            selectedPitchItem.spin_rpm ?? 2400,
            selectedPitchItem.control_rating ?? 75,
          )
          : 80.0);

    const result = evaluateChargingTiming(elapsed, TARGET_SWEET_SPOT_MS, selectedPitchEff);
    onThrowPitch(result.timingTier, result.timingLabel);
  }, [pitcher.arsenal, selectedPitchName, pitchEffectiveness, onChargingProgress, onThrowPitch]);

  const pitcherControl = pitcher.control ?? 75;

  const chips = useMemo(() => {
    return (pitcher.arsenal ?? []).map((item) => {
      const itemEff =
        pitchEffectiveness?.[item.name] ??
        computeBaselineEffectiveness(
          item.velocity_mph ?? 93,
          item.break_rating ?? 75,
          item.spin_rpm ?? 2400,
          item.control_rating ?? 75,
        );
      return (
        <ArsenalChip
          key={item.name}
          item={item}
          layout={layout}
          isSelected={item.name === selectedPitchName}
          isRecommended={item.name === recommendedPitch}
          disabled={isActionPending || disabled}
          onSelect={() => handleSelectPitch(item.name)}
          effectiveness={itemEff}
          confidencePct={confidencePct}
          pitcherControl={pitcherControl}
        />
      );
    });
  }, [
    pitcher.arsenal,
    pitchEffectiveness,
    layout,
    selectedPitchName,
    recommendedPitch,
    isActionPending,
    disabled,
    handleSelectPitch,
    confidencePct,
    pitcherControl,
  ]);

  const buttonDisabled = disabled || isActionPending || !selectedPitchName;

  const renderPitchNameHeader = (vertical: boolean) => (
    <View style={[styles.pitchNameHeader, vertical && styles.pitchNameHeaderVertical]}>
      <Text
        style={styles.pitchNameText}
        numberOfLines={1}
        accessibilityRole="header"
        accessibilityLabel={`Selected pitch: ${selectedPitchName || 'None'}`}
      >
        {selectedPitchName || 'PITCH'}
      </Text>
      <TouchableOpacity
        onPress={() => switchView('chips')}
        disabled={disabled || isActionPending}
        style={[
          styles.changePitchButton,
          (disabled || isActionPending) && styles.changePitchButtonDisabled,
        ]}
        activeOpacity={0.75}
        accessibilityRole="button"
        accessibilityLabel="Change selected pitch"
        accessibilityState={{ disabled: disabled || isActionPending }}
      >
        <Text style={styles.changePitchButtonText}>Change Pitch</Text>
      </TouchableOpacity>
    </View>
  );

  // During pitch execution (isActionPending is true), hide the widget completely.
  if (isActionPending) {
    return null;
  }

  return (
    <View style={[styles.container, isVertical && styles.containerVertical]}>

      {/* Stamina & Confidence Status Bars Above the Pitches */}
      <PitcherMetersSection
        staminaPct={staminaPct}
        confidencePct={confidencePct}
        layout={layout}
      />

      {/* Animated view switch container */}
      <Animated.View
        style={[
          styles.viewTransitionContainer,
          {
            opacity: fadeAnim,
            transform: [
              {
                scale: fadeAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.98, 1],
                }),
              },
            ],
          },
        ]}
      >
        {viewMode === 'throw' ? (
          isVertical ? (
            <View style={styles.throwViewColumn}>
              {renderPitchNameHeader(true)}
              <ThrowButton
                disabled={buttonDisabled}
                isCharging={isCharging}
                chargeRatio={chargeRatio}
                onPressIn={handlePressIn}
                onPressOut={handlePressOut}
                layout="vertical"
              />
            </View>
          ) : (
            <View style={styles.throwViewRow}>
              {renderPitchNameHeader(false)}
              <View style={styles.throwButtonHorizontalWrapper}>
                <ThrowButton
                  disabled={buttonDisabled}
                  isCharging={isCharging}
                  chargeRatio={chargeRatio}
                  onPressIn={handlePressIn}
                  onPressOut={handlePressOut}
                  layout="horizontal"
                />
              </View>
            </View>
          )
        ) : (
          isVertical ? (
            <View style={styles.chipsViewColumn}>
              <View style={styles.arsenalColumn}>
                {chips}
              </View>
            </View>
          ) : (
            <View style={styles.chipsViewRow}>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.arsenalRow}
              >
                {chips}
              </ScrollView>
            </View>
          )
        )}
      </Animated.View>

      {/* Strategy summary: situation, recommended target, pitch percentages */}
      {strategyIntent && (
        <CollapsibleStrategySummary
          strategyIntent={strategyIntent}
          onSelectPitchName={handleSelectPitch}
          disabled={disabled || isActionPending}
        />
      )}
    </View>
  );
}

export const PitchSelectorWidget = React.memo(
  PitchSelectorWidgetComponent,
  (prev, next) => {
    return (
      prev.pitcher?.id === next.pitcher?.id &&
      prev.pitcher?.arsenal === next.pitcher?.arsenal &&
      prev.selectedPitchName === next.selectedPitchName &&
      prev.recommendedPitch === next.recommendedPitch &&
      prev.isActionPending === next.isActionPending &&
      prev.disabled === next.disabled &&
      prev.layout === next.layout &&
      prev.strategyIntent === next.strategyIntent &&
      prev.staminaPct === next.staminaPct &&
      prev.confidencePct === next.confidencePct &&
      prev.pitchConfidences === next.pitchConfidences &&
      prev.effectivenessPct === next.effectivenessPct &&
      prev.pitchEffectiveness === next.pitchEffectiveness &&
      prev.onChargingProgress === next.onChargingProgress &&
      prev.onSelectPitchName === next.onSelectPitchName &&
      prev.onThrowPitch === next.onThrowPitch
    );
  },
);

// ─── Collapsible Strategy Summary ────────────────────────────────────────────

function CollapsibleStrategySummary({
  strategyIntent,
  onSelectPitchName,
  disabled = false,
}: {
  strategyIntent: StrategyIntentDecision;
  onSelectPitchName: (name: string) => void;
  disabled?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [contentHeight, setContentHeight] = useState(0);
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const anim = Animated.timing(progress, {
      toValue: expanded ? 1 : 0,
      duration: expanded ? 220 : 160,
      easing: Easing.out(Easing.cubic),
      // Height can't use the native driver.
      useNativeDriver: false,
    });
    anim.start();
    return () => {
      anim.stop();
    };
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
            onSelectPitchName={onSelectPitchName}
            disabled={disabled}
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
  onSelectPitchName,
  disabled = false,
}: {
  strategyIntent: StrategyIntentDecision;
  onSelectPitchName: (name: string) => void;
  disabled?: boolean;
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
          onPress={() => onSelectPitchName(recommended_pitch)}
          disabled={disabled}
          style={[styles.recTargetPill, disabled && styles.changePitchButtonDisabled]}
          accessibilityRole="button"
          accessibilityLabel={`Recommended pitch ${recommended_pitch}, target ${recommended_zone}`}
          accessibilityState={{ disabled }}
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

// ─── Dedicated THROW Button ──────────────────────────────────────────────────

interface ThrowButtonProps {
  disabled?: boolean;
  isCharging: boolean;
  chargeRatio: number;
  onPressIn: () => void;
  onPressOut: () => void;
  layout?: 'horizontal' | 'vertical';
}

function ThrowButton({
  disabled = false,
  isCharging,
  chargeRatio,
  onPressIn,
  onPressOut,
  layout = 'horizontal',
}: ThrowButtonProps) {
  const isVertical = layout === 'vertical';

  let dynamicColor = '#2563EB'; // Base Blue
  let timingHint = 'HOLD TO THROW';
  if (isCharging) {
    if (chargeRatio < 0.65) {
      dynamicColor = '#EF4444'; // Red
      timingHint = 'EARLY • POOR';
    } else if (chargeRatio < 0.85) {
      dynamicColor = '#F59E0B'; // Amber
      timingHint = 'EARLY • OKAY';
    } else if (chargeRatio < 0.95) {
      dynamicColor = '#10B981'; // Green
      timingHint = 'EARLY • GOOD';
    } else if (chargeRatio <= 1.05) {
      dynamicColor = '#00E5FF'; // Cyan sweet spot!
      timingHint = 'PERFECT!';
    } else if (chargeRatio <= 1.15) {
      dynamicColor = '#10B981'; // Green
      timingHint = 'LATE • GOOD';
    } else if (chargeRatio <= 1.35) {
      dynamicColor = '#F59E0B'; // Amber
      timingHint = 'LATE • OKAY';
    } else {
      dynamicColor = '#EF4444'; // Red
      timingHint = 'LATE • POOR';
    }
  }

  const fillPercent = Math.min(100, Math.max(0, (chargeRatio / 1.0) * 100));

  return (
    <TouchableOpacity
      activeOpacity={0.9}
      onPressIn={onPressIn}
      onPressOut={onPressOut}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={
        isCharging
          ? (chargeRatio >= 0.95 && chargeRatio <= 1.05 ? 'Release now' : 'Charging pitch')
          : 'Throw pitch'
      }
      accessibilityHint="Press and hold to charge, release in the sweet spot"
      accessibilityState={{ disabled, busy: isCharging }}
      style={[
        styles.throwButton,
        isVertical ? styles.throwButtonVertical : styles.throwButtonHorizontal,
        disabled && styles.throwButtonDisabled,
        isCharging && { borderColor: dynamicColor },
      ]}
    >
      {/* Background Charging Fill */}
      {isCharging && (
        <View
          style={[
            styles.throwButtonFill,
            {
              width: `${fillPercent}%`,
              backgroundColor: dynamicColor,
              opacity: 0.35,
            },
          ]}
        />
      )}

      <View style={styles.throwButtonContent}>
        <Text
          style={[
            styles.throwButtonText,
            isCharging && { color: dynamicColor },
            disabled && { color: Colors.textMuted },
          ]}
        >
          {isCharging ? (chargeRatio >= 0.95 && chargeRatio <= 1.05 ? 'RELEASE NOW!' : 'CHARGING...') : 'THROW'}
        </Text>
        <Text
          style={[
            styles.throwButtonSubtext,
            isCharging && { color: dynamicColor },
          ]}
        >
          {isCharging
            ? `${(chargeRatio * 1000).toFixed(0)} ms • ${timingHint}`
            : disabled
              ? 'READY'
              : 'PRESS & HOLD'}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

// ─── Arsenal Chip ────────────────────────────────────────────────────────────

const ArsenalChip = React.memo(function ArsenalChip({
  item,
  layout = 'horizontal',
  isSelected,
  isRecommended,
  disabled = false,
  onSelect,
  effectiveness = 80,
  confidencePct = 50,
  pitcherControl = 75,
}: {
  item: PitchArsenalItem;
  layout?: 'horizontal' | 'vertical';
  isSelected: boolean;
  isRecommended?: boolean;
  disabled?: boolean;
  onSelect: () => void;
  effectiveness?: number;
  confidencePct?: number;
  pitcherControl?: number;
}) {
  const chipEffectiveness = Math.max(0, Math.min(100, effectiveness));
  const effColor = getEffectivenessColor(chipEffectiveness);
  const baseCmd = item.command ?? item.control_rating ?? pitcherControl;
  const effCmd = calculateCombinedEffectiveCommand(baseCmd, confidencePct, chipEffectiveness);
  const abilityTier = getAbilityTier(effCmd);
  const tierColor = getAbilityTierColor(abilityTier);

  return (
    <TouchableOpacity
      onPress={onSelect}
      disabled={disabled}
      activeOpacity={0.85}
      accessibilityRole="button"
      accessibilityLabel={`${item.name}, ${formatVelocityRange(item)}, effectiveness ${Math.round(chipEffectiveness)} percent${isRecommended ? ', recommended' : ''}`}
      accessibilityState={{ selected: isSelected, disabled }}
      style={[
        styles.arsenalChip,
        layout === 'vertical' && styles.arsenalChipVertical,
        disabled && styles.arsenalChipDisabled,
        {
          backgroundColor: isSelected ? 'rgba(37, 99, 235, 0.15)' : 'transparent',
          borderColor: isSelected
            ? Colors.blue
            : isRecommended
              ? 'rgba(16, 185, 129, 0.6)'
              : `${tierColor}55`,
        },
      ]}
    >
      {/* Tier Color Left Accent Bar */}
      <View style={[styles.chipTierAccent, { backgroundColor: tierColor }]} />

      {isRecommended && (
        <View style={styles.recBadge}>
          <Text style={styles.recBadgeText}>★ PRIMARY</Text>
        </View>
      )}

      {/* Side-by-side Pitch Name and Velocity Range */}
      <View style={styles.chipNameVeloRow}>
        {isSelected && <View style={styles.arsenalDot} />}
        <Text
          style={[
            styles.arsenalName,
            {
              fontWeight: isSelected ? '700' : '600',
              color: isSelected
                ? '#FFF'
                : isRecommended
                  ? '#34D399'
                  : Colors.textPrimary,
            },
          ]}
          numberOfLines={1}
        >
          {item.name}
        </Text>
        <Text
          style={[
            styles.arsenalVelo,
            { color: isSelected ? Colors.yellow : Colors.textSecondary },
          ]}
          numberOfLines={1}
        >
          {formatVelocityRange(item)}
        </Text>
      </View>

      {/* Effectiveness Metric on Chip */}
      <View style={styles.chipEffectivenessRow}>
        <Text style={styles.chipMeterTag}>EFF</Text>
        <View style={styles.chipMicroTrack}>
          <View
            style={[
              styles.chipMicroFill,
              { width: `${chipEffectiveness}%`, backgroundColor: effColor },
            ]}
          />
        </View>
        <Text style={[styles.chipMeterValText, { color: effColor }]}>
          {Math.round(chipEffectiveness)}%
        </Text>
      </View>
    </TouchableOpacity>
  );
});

function formatVelocityRange(item: PitchArsenalItem): string {
  if (item.velocity_display) {
    return item.velocity_display;
  }
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
  containerVertical: {
    padding: 10,
    gap: 8,
    backgroundColor: 'rgba(10, 18, 28, 0.92)',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
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
  metersRow: {
    flexDirection: 'row',
    gap: 12,
    paddingVertical: 2,
    marginBottom: 4,
  },
  metersColumn: {
    gap: 6,
    paddingVertical: 2,
    marginBottom: 4,
  },
  meterContainer: {
    flex: 1,
    gap: 3,
  },
  meterLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  meterTitle: {
    fontSize: 9,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    flex: 1,
    marginRight: 6,
  },
  meterValue: {
    fontSize: 10,
    fontWeight: '800',
  },
  meterTrack: {
    height: 5,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 3,
    overflow: 'hidden',
    borderWidth: 0.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  meterFill: {
    height: '100%',
    borderRadius: 3,
  },
  chipEffectivenessRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    width: '100%',
    marginTop: 4,
  },
  chipMeterTag: {
    fontSize: 7,
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.3,
    width: 20,
  },
  chipMicroTrack: {
    flex: 1,
    height: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 1.5,
    overflow: 'hidden',
  },
  chipMicroFill: {
    height: '100%',
    borderRadius: 1.5,
  },
  chipMeterValText: {
    fontSize: 7,
    fontWeight: '700',
    minWidth: 18,
    textAlign: 'right',
  },
  arsenalRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 2,
    flexGrow: 1,
  },
  horizontalSelectorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  throwButton: {
    position: 'relative',
    overflow: 'hidden',
    backgroundColor: 'rgba(37, 99, 235, 0.22)',
    borderWidth: 1.5,
    borderColor: '#3B82F6',
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  throwButtonHorizontal: {
    minWidth: 120,
    paddingHorizontal: 16,
    paddingVertical: 10,
    alignSelf: 'stretch',
  },
  throwButtonVertical: {
    width: '100%',
    paddingVertical: 12,
    marginTop: 4,
  },
  throwButtonDisabled: {
    opacity: 0.45,
    borderColor: Colors.borderSecondary,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
  },
  throwButtonFill: {
    position: 'absolute',
    top: 0,
    left: 0,
    bottom: 0,
    borderRadius: 6,
  },
  throwButtonContent: {
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  throwButtonText: {
    fontSize: 13,
    fontWeight: '900',
    color: '#FFF',
    letterSpacing: 1.0,
  },
  throwButtonSubtext: {
    fontSize: 9,
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.4,
    marginTop: 2,
  },
  arsenalColumn: {
    gap: 6,
  },
  arsenalChip: {
    position: 'relative',
    overflow: 'hidden',
    borderRadius: 8,
    borderWidth: 1,
    paddingLeft: 14,
    paddingRight: 10,
    paddingVertical: 8,
    alignItems: 'center',
    minWidth: 140,
    gap: 3,
  },
  chipTierAccent: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: 4,
    borderTopLeftRadius: 7,
    borderBottomLeftRadius: 7,
  },
  arsenalChipVertical: {
    width: '100%',
    minWidth: 0,
    paddingLeft: 12,
    paddingRight: 10,
    paddingVertical: 6,
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
  chipNameVeloRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    flexWrap: 'nowrap',
  },
  arsenalDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.yellow,
  },
  arsenalName: {
    fontSize: 12,
    textAlign: 'center',
  },
  arsenalVelo: {
    fontSize: 10.5,
    fontWeight: '600',
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
  gradeBanner: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 3,
    alignSelf: 'center',
  },
  gradeBannerText: {
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
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
  // ─── View transition & state manager styles ─────────────────────────────
  viewTransitionContainer: {
    width: '100%',
  },
  throwViewRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    width: '100%',
  },
  throwViewColumn: {
    width: '100%',
    gap: 6,
  },
  throwButtonHorizontalWrapper: {
    flex: 1,
  },
  pitchNameHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    minWidth: 170,
    gap: 12,
  },
  pitchNameHeaderVertical: {
    minWidth: 0,
    width: '100%',
    marginBottom: 4,
  },
  pitchNameText: {
    fontSize: 13,
    fontWeight: '800',
    color: '#FFF',
    letterSpacing: 0.5,
    flexShrink: 1,
  },
  changePitchButton: {
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 6,
    backgroundColor: 'rgba(37, 99, 235, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(59, 130, 246, 0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  changePitchButtonDisabled: {
    opacity: 0.45,
  },
  changePitchButtonText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#93C5FD',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  chipsViewRow: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
  },
  chipsViewColumn: {
    width: '100%',
    gap: 6,
  },
});
