import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Text,
  SafeAreaView,
  StatusBar,
  useWindowDimensions,
} from 'react-native';
import { useGameStore } from '../store/gameStore';
import { ErrorEnvelopeBanner } from '../components/ErrorEnvelopeBanner';
import { ScoreboardControlsWidget } from '../components/ScoreboardControlsWidget';
import {
  StrikeZoneGridWidget,
  STRIKE_ZONE_GRID_CONTENT_SIZE,
  STRIKE_ZONE_GRID_CONTENT_TOP,
  STRIKE_ZONE_WIDGET_SIZE,
  STRIKE_ZONE_WIDGET_WIDTH,
} from '../components/StrikeZoneGridWidget';
import { GameField } from '../components/GameField';
import type {
  ActivePitchData,
  ProjectedPlatePosition,
} from '../components/gamefield/types';
import type { PitchDetails } from '../types/api';
import { LineupDialogWidget } from '../components/LineupDialogWidget';
import { RotationBullpenDialogWidget } from '../components/RotationBullpenDialogWidget';
import { PitchSelectorWidget } from '../components/PitchSelectorWidget';
import { StrategyMenuModal } from '../components/StrategyMenuModal';
import { PitchFeedModal } from '../components/PitchFeedModal';
import { PitchTrajectoryModal } from '../components/PitchTrajectoryModal';
import { SettingsMenuModal } from '../components/SettingsMenuModal';
import { GamedayDevMenuModal } from '../components/debug/GamedayDevMenuModal';
import { getZoneNominalTarget } from '../services/gamedayMath';
import { movementForPitch } from '../services/pitchTrajectory';
import { Colors } from '../theme/colors';

const MOCK_RELEASE: [number, number, number] = [-1.5, 6.0, -59.5];

/**
 * BaseballSimScreen — Root screen of the simulation client.
 * Ported from BaseballSimScreen.kt / GameViewModel.
 *
 * Assembles all 7 widgets into a scrollable vertical layout matching the
 * original Jetpack Compose scaffold.
 */
export function BaseballSimScreen() {
  const { height: screenHeight, width: screenWidth } = useWindowDimensions();
  const {
    // Data
    gameState,
    pitchFeed,
    currentAtBatPitches,
    latestPitch,
    lineups,
    rotations,
    selectedPitchIntent,
    selectedTargetZone,
    customTargetCoords,
    isLineupDialogOpen,
    isRotationDialogOpen,
    isMockMode,
    loadingState,
    isPitching,
    errorMessage,
    errorEnvelope,
    // Actions
    loadInitialState,
    startNewGame,
    throwPitch,
    swapLineup,
    swapRotation,
    toggleMockMode,
    toggleSettingsMenu,
    setSelectedPitchIntent,
    setSelectedTargetZone,
    setGloveTarget,
    setLineupDialogOpen,
    setRotationDialogOpen,
    clearError,
  } = useGameStore();

  useEffect(() => {
    loadInitialState();
  }, []);

  const [plateProjection, setPlateProjection] = useState<ProjectedPlatePosition | null>(null);
  const handlePlateProjected = useCallback((position: ProjectedPlatePosition) => {
    setPlateProjection(position);
  }, []);

  const [activePitch, setActivePitch] = useState<ActivePitchData | null>(null);
  const pitchSequence = useRef(0);
  const lastAnimatedPitchRef = useRef<PitchDetails | null>(latestPitch);

  // Animate the pitch that was actually resolved, for both mock and live
  // throws. The ball ends at the packet's realized location, not a zone
  // center, so the 3D endpoint and the 2D marker always agree.
  useEffect(() => {
    if (!latestPitch || lastAnimatedPitchRef.current === latestPitch) return;
    lastAnimatedPitchRef.current = latestPitch;

    const packet = latestPitch.gameday_packet;
    const execution = packet?.execution;
    if (!execution) return;

    const fallbackMovement = movementForPitch(latestPitch.pitch_name);
    const horizontalBreakIn =
      execution.horizontalBreakInches ?? fallbackMovement.hb;
    const inducedVerticalBreakIn =
      execution.inducedVerticalBreakInches ?? fallbackMovement.ivb;
    const speedMph = execution.releaseSpeedMph ?? latestPitch.velocity_mph;
    const flightTime = speedMph > 0 ? 59.5 / (speedMph * 1.4667) : 0.414;

    // Packet release uses [x, depth, height]; the 3D scene uses
    // [x, height, -depth].
    const release: [number, number, number] = packet?.release
      ? [packet.release.x, packet.release.z, -packet.release.y]
      : MOCK_RELEASE;

    pitchSequence.current += 1;
    setActivePitch({
      id: `pitch-${packet?.meta.pitchNumber ?? pitchSequence.current}-${pitchSequence.current}`,
      release,
      plate: [execution.realizedX, execution.realizedZ, 0],
      pfx: [horizontalBreakIn / 12, inducedVerticalBreakIn / 12],
      flightTime,
    });
  }, [latestPitch]);

  const handleSelectPitchIntent = useCallback(
    (name: string) => {
      setSelectedPitchIntent(name);
    },
    [setSelectedPitchIntent],
  );

  const handlePitchComplete = useCallback(() => {
    setActivePitch(null);
  }, []);

  const isLoading = loadingState === 'loading' && !isPitching && !gameState;

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={Colors.green} />
        <Text style={styles.loadingText}>Initializing Simulation Engine...</Text>
      </View>
    );
  }

  const currentBatter = gameState?.current_batter;
  const currentPitcher = gameState?.current_pitcher;
  const defaultGlove = getZoneNominalTarget(selectedTargetZone || 'heart');
  const packetAim = latestPitch?.gameday_packet?.intent;
  const resolvedAim =
    activePitch &&
    packetAim &&
    Number.isFinite(packetAim.targetX) &&
    Number.isFinite(packetAim.targetZ)
      ? { x: packetAim.targetX, z: packetAim.targetZ }
      : null;
  const gloveTarget =
    customTargetCoords ?? resolvedAim ?? { x: defaultGlove.x, z: defaultGlove.z };
  const commandRating = currentPitcher?.control ?? 82;

  // Project the HUD onto the 3D strike zone so the glove marker and the pitch
  // endpoint share the same screen position. The 3D zone is wider/taller in
  // perspective, so use independent horizontal/vertical scales.
  const zoneTopPx = (plateProjection?.zoneTopRatio ?? 0.536) * screenHeight;
  const zoneBottomPx = (plateProjection?.zoneBottomRatio ?? 0.782) * screenHeight;
  const zoneWidthPx = (plateProjection?.zoneWidthRatio ?? 0.38) * screenWidth;
  const rawStrikeZoneScaleX =
    zoneWidthPx > 0 ? zoneWidthPx / STRIKE_ZONE_GRID_CONTENT_SIZE : 1;
  const rawStrikeZoneScaleY =
    zoneBottomPx > zoneTopPx
      ? (zoneBottomPx - zoneTopPx) / STRIKE_ZONE_GRID_CONTENT_SIZE
      : 1;
  const strikeZoneScaleX = Number.isFinite(rawStrikeZoneScaleX) ? rawStrikeZoneScaleX : 1;
  const strikeZoneScaleY = Number.isFinite(rawStrikeZoneScaleY) ? rawStrikeZoneScaleY : 1;
  const scaledStrikeZoneHeight = STRIKE_ZONE_WIDGET_SIZE * strikeZoneScaleY;
  const scaledStrikeZoneWidth = STRIKE_ZONE_WIDGET_WIDTH * strikeZoneScaleX;
  const strikeZoneTop =
    zoneTopPx - STRIKE_ZONE_GRID_CONTENT_TOP * strikeZoneScaleY;

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.bgDeep} />
      <GameField
        batter={currentBatter}
        pitcher={currentPitcher}
        onPlateProjected={handlePlateProjected}
        activePitch={activePitch}
        onPitchComplete={handlePitchComplete}
      />

      <SafeAreaView style={styles.safeArea}>
        {/* Error Banner */}
        {errorMessage && (
          <ErrorEnvelopeBanner
            message={errorMessage}
            errorEnvelope={errorEnvelope}
            onDismiss={clearError}
          />
        )}

        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Step 4: Main Controls Container (contains Scorebug as uppermost element) */}
          <ScoreboardControlsWidget
            gameState={gameState}
            lineups={lineups}
            latestPitch={latestPitch}
            isMockMode={isMockMode}
            onOpenSettings={() => toggleSettingsMenu(true)}
            onToggleMock={toggleMockMode}
          />

          <View style={styles.bottomPad} />
        </ScrollView>

        {/* Pitch Selector — pinned to the bottom of the screen */}
        {currentPitcher && (
          <View style={styles.pitchFooter}>
            <PitchSelectorWidget
              pitcher={currentPitcher}
              selectedPitchIntent={selectedPitchIntent}
              recommendedPitch={gameState?.strategy_intent?.recommended_pitch}
              strategyIntent={gameState?.strategy_intent}
              onSelectPitchIntent={handleSelectPitchIntent}
              onThrowPitch={throwPitch}
              isActionPending={isPitching || loadingState === 'loading'}
            />
          </View>
        )}
      </SafeAreaView>

      {/* Strike Zone — pinned just above the plate in the GameField scene */}
      {currentBatter && (
        <View style={[styles.strikeZoneOverlay, { top: strikeZoneTop }]}>
          <View
            style={[
              styles.strikeZoneScaleBox,
              { width: scaledStrikeZoneWidth, height: scaledStrikeZoneHeight },
            ]}
          >
            <View
              style={{
                flexShrink: 0,
                transform: [
                  { scaleX: strikeZoneScaleX },
                  { scaleY: strikeZoneScaleY },
                ],
                transformOrigin: 'top center',
              }}
            >
              <StrikeZoneGridWidget
                selectedZone={selectedTargetZone ?? ''}
                onSelectZone={setSelectedTargetZone}
                currentBatter={currentBatter}
                latestPitch={latestPitch ?? pitchFeed[0]}
                atBatPitches={currentAtBatPitches}
                gloveTarget={gloveTarget}
                commandRating={commandRating}
                onSetGloveTarget={setGloveTarget}
                coordinateScaleX={strikeZoneScaleX}
                coordinateScaleY={strikeZoneScaleY}
                variant="field"
              />
            </View>
          </View>
        </View>
      )}

      {/* Lineup Dialog */}
      <LineupDialogWidget
        lineups={lineups}
        visible={isLineupDialogOpen}
        onSwapLineup={swapLineup}
        onDismiss={() => setLineupDialogOpen(false)}
      />

      {/* Rotation & Bullpen Dialog */}
      <RotationBullpenDialogWidget
        rotations={rotations}
        visible={isRotationDialogOpen}
        onSwapRotation={swapRotation}
        onDismiss={() => setRotationDialogOpen(false)}
      />

      {/* Settings Menu */}
      <SettingsMenuModal />

      {/* AI Strategy & Pitch Decider page */}
      <StrategyMenuModal />

      {/* Pitch-by-Pitch Feed page */}
      <PitchFeedModal />

      {/* Pitch Trajectory (3D) page */}
      <PitchTrajectoryModal />

      {/* Gameday Dev Menu Modal */}
      <GamedayDevMenuModal />
    </View>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.bgDeep },
  safeArea: { flex: 1, backgroundColor: 'transparent' },
  loadingContainer: { flex: 1, backgroundColor: Colors.bgDeep, alignItems: 'center', justifyContent: 'center', gap: 16 },
  loadingText: { color: Colors.textSecondary, fontSize: 14 },
  scroll: { flex: 1 },
  scrollContent: { padding: 12, gap: 12 },
  bottomPad: { height: 12 },
  strikeZoneOverlay: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
    pointerEvents: 'box-none',
  },
  strikeZoneScaleBox: {
    alignItems: 'center',
  },
  pitchFooter: { paddingHorizontal: 12, paddingBottom: 8 },
});
