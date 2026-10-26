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
    pitchPhase,
    pendingThrow,
    pendingResolution,
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
    resolvePitch,
    revealPitch,
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
  const lastAnimatedPitchRef = useRef<PitchDetails | null>(null);
  const revealedResolutionRef = useRef<unknown>(null);

  // Animate the ball flight from the throw response, before any reaction or
  // outcome is published. The ball ends at the packet's realized location, not
  // a zone center, so the 3D endpoint and the 2D marker always agree.
  useEffect(() => {
    const pitch = pendingThrow?.pitch_details;
    if (!pitch || lastAnimatedPitchRef.current === pitch) return;
    lastAnimatedPitchRef.current = pitch;

    const packet = pitch.gameday_packet;
    const execution = packet?.execution;
    if (!execution) return;

    const fallbackMovement = movementForPitch(pitch.pitch_name);
    const horizontalBreakIn =
      execution.horizontalBreakInches ?? fallbackMovement.hb;
    const inducedVerticalBreakIn =
      execution.inducedVerticalBreakInches ?? fallbackMovement.ivb;
    const speedMph = execution.releaseSpeedMph ?? pitch.velocity_mph;
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
  }, [pendingThrow]);

  // The ball reached the plate: resolve contact, but do not publish the result
  // yet. The reaction beat below controls the reveal.
  const handlePitchComplete = useCallback(() => {
    if (pitchPhase !== 'IN_FLIGHT') return;
    setActivePitch(null);
    void resolvePitch();
  }, [pitchPhase, resolvePitch]);

  // Reaction beat: after the SWING/TAKE indicator has played, publish the
  // result, count, feed, zone markers, and gameday log together.
  useEffect(() => {
    if (pitchPhase !== 'REACTING' || !pendingResolution) return;
    if (!pendingResolution.pitch_details) return;
    if (revealedResolutionRef.current === pendingResolution) return;
    revealedResolutionRef.current = pendingResolution;

    const timer = setTimeout(() => {
      revealPitch();
    }, 650);
    return () => clearTimeout(timer);
  }, [pitchPhase, pendingResolution, revealPitch]);

  const handleSelectPitchIntent = useCallback(
    (name: string) => {
      setSelectedPitchIntent(name);
    },
    [setSelectedPitchIntent],
  );

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
  const packetAim = pendingThrow?.pitch_details.gameday_packet?.intent ?? latestPitch?.gameday_packet?.intent;
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
  const reactionDecision =
    pitchPhase === 'REACTING'
      ? pendingResolution?.pitch_details?.batter_decision ?? null
      : null;
  const resultVisible = pitchPhase === 'IDLE';

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

  // Place the pitch selector beside the strike zone when the viewport leaves
  // enough room; otherwise keep the bottom footer as the narrow-screen fallback.
  const strikeZoneRight = screenWidth / 2 + scaledStrikeZoneWidth / 2;
  const sidePitchSelectorWidth = Math.min(260, screenWidth - strikeZoneRight - 24);
  const showSidePitchSelector =
    Boolean(currentPitcher) && sidePitchSelectorWidth >= 180;
  const sidePitchSelectorTop = Math.max(12, strikeZoneTop - 12);

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

      {/* Reaction beat: SWING/TAKE appears at the plate before the reveal. */}
      {reactionDecision && (
        <View pointerEvents="none" style={styles.reactionOverlay}>
          <Text
            style={[
              styles.reactionText,
              reactionDecision === 'SWING' ? styles.reactionSwing : styles.reactionTake,
            ]}
          >
            {reactionDecision}
          </Text>
        </View>
      )}

      {/* Neutral in-flight state: never expose the previous result. */}
      {(pitchPhase === 'IN_FLIGHT' || pitchPhase === 'RESOLVING') && (
        <View pointerEvents="none" style={styles.flightOverlay}>
          <Text style={styles.flightText}>
            {pitchPhase === 'IN_FLIGHT' ? 'PITCH IN FLIGHT' : 'AT THE PLATE'}
          </Text>
        </View>
      )}

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
            latestPitch={resultVisible ? latestPitch : null}
            isMockMode={isMockMode}
            onOpenSettings={() => toggleSettingsMenu(true)}
            onToggleMock={toggleMockMode}
          />

          <View style={styles.bottomPad} />
        </ScrollView>

        {/* Pitch Selector — bottom fallback for narrow screens */}
        {currentPitcher && !showSidePitchSelector && (
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
                latestPitch={resultVisible ? latestPitch ?? pitchFeed[0] : null}
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

      {/* Pitch Selector — stacked vertically beside the strike zone */}
      {currentPitcher && showSidePitchSelector && (
        <View
          style={[
            styles.pitchSelectorSide,
            {
              top: sidePitchSelectorTop,
              left: strikeZoneRight + 12,
              width: sidePitchSelectorWidth,
            },
          ]}
        >
          <PitchSelectorWidget
            layout="vertical"
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
  pitchSelectorSide: {
    position: 'absolute',
    zIndex: 10,
  },
  reactionOverlay: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: '48%',
    alignItems: 'center',
  },
  reactionText: {
    fontSize: 34,
    fontWeight: '900',
    letterSpacing: 4,
    textShadowColor: 'rgba(0, 0, 0, 0.8)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 6,
  },
  reactionSwing: { color: Colors.amber },
  reactionTake: { color: Colors.blueSky },
  flightOverlay: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: '42%',
    alignItems: 'center',
  },
  flightText: {
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 2,
    color: Colors.textSecondary,
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 4,
    overflow: 'hidden',
  },
});
