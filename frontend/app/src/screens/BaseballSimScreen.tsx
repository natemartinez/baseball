import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Text,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
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
import { BattedBallMetricsWidget } from '../components/BattedBallMetricsWidget';
import type {
  ActiveBattedBallData,
  ActivePitchData,
  GameCameraMode,
  ProjectedPlatePosition,
} from '../components/gamefield/types';
import type {
  BattedBallTelemetry,
  PitchDetails,
  SwingContactReport,
} from '../types/api';
import { CAMERA_SEQUENCE_ENABLED } from '../components/gamefield/cameraShots';
import { LineupDialogWidget } from '../components/LineupDialogWidget';
import { RotationBullpenDialogWidget } from '../components/RotationBullpenDialogWidget';
import { PitchSelectorWidget } from '../components/PitchSelectorWidget';
import { StrategyMenuModal } from '../components/StrategyMenuModal';
import { PitchFeedModal } from '../components/PitchFeedModal';
import { PitchTrajectoryModal } from '../components/PitchTrajectoryModal';
import { SettingsMenuModal } from '../components/SettingsMenuModal';
import { SwingMeterWidget } from '../components/SwingMeterWidget';
import { BattingDrillHud } from '../components/BattingDrillHud';
import { BattingDrillModal } from '../components/BattingDrillModal';
import { GamedayDevMenuModal } from '../components/debug/GamedayDevMenuModal';
import { getZoneNominalTarget } from '../services/gamedayMath';
import { movementForPitch } from '../services/pitchTrajectory';
import { Colors } from '../theme/colors';

const MOCK_RELEASE: [number, number, number] = [-1.5, 6.0, -59.5];

const RESULT_CAMERA_HOLD_MS = 1600;

/** A trace is only playable when it has a finite hang time and 3D samples. */
function isValidBattedBallTrace(trace: unknown): trace is BattedBallTelemetry {
  if (!trace || typeof trace !== 'object') return false;
  const candidate = trace as Partial<BattedBallTelemetry>;
  if (!Number.isFinite(candidate.hang_time_s)) return false;

  const samples = candidate.samples;
  if (!Array.isArray(samples) || samples.length < 2) return false;

  return samples.every(
    (sample) =>
      Array.isArray(sample) &&
      sample.length === 3 &&
      sample.every((value) => Number.isFinite(value)),
  );
}

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
    activeSeed,
    controlMode,
    battingDrill,
    isBattingDrillOpen,
    isSettingsMenuOpen,
    isDevMenuOpen,
    isPitchFeedOpen,
    isStrategyMenuOpen,
    isTrajectoryOpen,
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
    beginBattedBall,
    completeBattedBall,
    swapLineup,
    swapRotation,
    toggleSettingsMenu,
    throwDrillPitch,
    setBattingDrillOpen,
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
  const [activeBattedBall, setActiveBattedBall] =
    useState<ActiveBattedBallData | null>(null);
  const pitchSequence = useRef(0);
  const battedBallSequence = useRef(0);
  const lastAnimatedPitchRef = useRef<PitchDetails | null>(null);
  const revealedResolutionRef = useRef<unknown>(null);
  const animatedBattedBallTraceRef = useRef<BattedBallTelemetry | null>(null);
  const battingChargeRef = useRef(0);
  const [resultCameraHold, setResultCameraHold] = useState(false);

  const pendingBattedBall = pendingResolution?.pitch_details?.batted_ball;
  const hasPendingBattedBall = isValidBattedBallTrace(pendingBattedBall);

  // Pitch -> Contact -> Result. The bird's-eye cut starts at contact (the
  // REACTING beat) and lasts through the flight, reveal, and result hold.
  const birdseyeActive =
    CAMERA_SEQUENCE_ENABLED &&
    ((pitchPhase === 'REACTING' && hasPendingBattedBall) ||
      pitchPhase === 'BATTED_BALL' ||
      (pitchPhase === 'IDLE' && resultCameraHold));
  const cameraMode: GameCameraMode = birdseyeActive ? 'BIRDSEYE' : 'PITCH';
  const battingMode = controlMode === 'BATTING';
  const battingModalOpen =
    isBattingDrillOpen ||
    isSettingsMenuOpen ||
    isDevMenuOpen ||
    isPitchFeedOpen ||
    isStrategyMenuOpen ||
    isTrajectoryOpen ||
    isLineupDialogOpen ||
    isRotationDialogOpen;
  const battingInputEnabled = battingMode && !birdseyeActive && !battingModalOpen;

  // Batting Practice auto-feed: the playlist is thrown without the player
  // touching the pitch selector. Wait for the result/camera hold, and never
  // fire while paused, in a modal, or during another pitch.
  useEffect(() => {
    if (!battingMode || !battingDrill?.active || !battingDrill.playing) return;
    if (battingDrill.entries.length === 0) return;
    if (pitchPhase !== 'IDLE' || isPitching || resultCameraHold) return;
    if (battingModalOpen) return;

    const delay =
      battingDrill.pitchesThrown === 0 ? 3000 : battingDrill.intervalMs;
    const timer = setTimeout(() => {
      void throwDrillPitch();
    }, delay);
    return () => clearTimeout(timer);
  }, [
    battingMode,
    battingDrill,
    pitchPhase,
    isPitching,
    resultCameraHold,
    battingModalOpen,
    throwDrillPitch,
  ]);

  // Leaving practice must also clear any screen-local practice pitch/result
  // before the real pitching flow renders.
  useEffect(() => {
    if (controlMode === 'BATTING' && battingDrill?.active) return;
    setActivePitch(null);
    setActiveBattedBall(null);
    setResultCameraHold(false);
    animatedBattedBallTraceRef.current = null;
  }, [controlMode, battingDrill?.active]);

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

  // Reaction beat: after the SWING/TAKE indicator has played, either start the
  // batted-ball flight or publish the result immediately when there is no trace.
  useEffect(() => {
    if (pitchPhase !== 'REACTING' || !pendingResolution) return;
    if (!pendingResolution.pitch_details) return;
    if (revealedResolutionRef.current === pendingResolution) return;
    revealedResolutionRef.current = pendingResolution;

    const timer = setTimeout(() => {
      if (isValidBattedBallTrace(pendingResolution.pitch_details?.batted_ball)) {
        animatedBattedBallTraceRef.current =
          pendingResolution.pitch_details?.batted_ball ?? null;
        beginBattedBall();
      } else {
        revealPitch();
      }
    }, 650);
    return () => clearTimeout(timer);
  }, [pitchPhase, pendingResolution, revealPitch, beginBattedBall]);

  useEffect(() => {
    if (pitchPhase !== 'BATTED_BALL') return;
    const trace = pendingResolution?.pitch_details?.batted_ball;
    if (!isValidBattedBallTrace(trace)) {
      completeBattedBall();
      return;
    }

    battedBallSequence.current += 1;
    setActiveBattedBall({
      id: `batted-${battedBallSequence.current}`,
      hangTime: trace.hang_time_s,
      samples: trace.samples,
    });

    const timeoutMs = Math.min(
      8000,
      Math.max(500, (trace.hang_time_s + 1.0) * 1000),
    );
    const timer = setTimeout(() => {
      // The canvas is not trusted to report completion; hold the bird's-eye
      // shot through the reveal anyway. Read the live phase so a completion
      // that already ran does not unmount the retained visual.
      if (useGameStore.getState().pitchPhase !== 'BATTED_BALL') return;
      setResultCameraHold(true);
      setActiveBattedBall(null);
      completeBattedBall();
    }, timeoutMs);

    return () => clearTimeout(timer);
  }, [pitchPhase, pendingResolution, completeBattedBall]);

  // One-shot result hold after the reveal, then back to the pitch camera.
  useEffect(() => {
    if (pitchPhase !== 'IDLE' || !resultCameraHold) return;
    const timer = setTimeout(() => {
      setResultCameraHold(false);
      setActiveBattedBall(null);
    }, RESULT_CAMERA_HOLD_MS);
    return () => clearTimeout(timer);
  }, [pitchPhase, resultCameraHold]);

  // A new pitch always returns to the pitch camera and drops any retained
  // batted-ball visual. Reset/clear paths also land here.
  useEffect(() => {
    if (pitchPhase !== 'IN_FLIGHT' && pitchPhase !== 'RESOLVING') return;
    setResultCameraHold(false);
    setActiveBattedBall(null);
    animatedBattedBallTraceRef.current = null;
  }, [pitchPhase]);

  // simAtBat and reset swap latestPitch without playing a flight, so a hold
  // must not survive a trace that is not the one that was animated.
  useEffect(() => {
    const trace = latestPitch?.batted_ball ?? null;
    if (trace === animatedBattedBallTraceRef.current) return;
    setResultCameraHold(false);
    setActiveBattedBall(null);
    animatedBattedBallTraceRef.current = null;
  }, [latestPitch]);

  // Clear a retained visual if the phase drops to IDLE without a hold
  // (for example clearPendingPitch).
  useEffect(() => {
    if (pitchPhase !== 'IDLE' || resultCameraHold) return;
    if (activeBattedBall) setActiveBattedBall(null);
  }, [pitchPhase, resultCameraHold, activeBattedBall]);

  const handleBattedBallComplete = useCallback(() => {
    // Read the live phase: a stale completion callback can arrive after the
    // store has already moved on (reveal, reset, or a new pitch).
    if (useGameStore.getState().pitchPhase !== 'BATTED_BALL') return;
    // Set the hold before the store flips to IDLE; the derived camera mode is
    // evaluated on the next render and would otherwise flicker to PITCH.
    setResultCameraHold(true);
    // Keep the ball, arc, and ring mounted through the hold.
    completeBattedBall();
  }, [completeBattedBall]);

  const handleBattingContact = useCallback((contact: SwingContactReport) => {
    if (useGameStore.getState().pitchPhase !== 'IN_FLIGHT') return;
    setActivePitch(null);
    void resolvePitch({ batterDecision: 'SWING', contact });
  }, [resolvePitch]);

  const handleBattingPitchArrival = useCallback((swingAttempted: boolean) => {
    if (useGameStore.getState().pitchPhase !== 'IN_FLIGHT') return;
    setActivePitch(null);
    if (swingAttempted) {
      void resolvePitch({
        batterDecision: 'SWING',
        contact: { contacted: false },
      });
      return;
    }
    void resolvePitch({ batterDecision: 'TAKE' });
  }, [resolvePitch]);

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

  if (!gameState && loadingState === 'error') {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.disconnectedTitle}>⚠️ Simulation Backend Offline</Text>
        <Text style={styles.disconnectedSubtitle}>
          {errorMessage || 'Unable to connect to Flask backend on port 5050.'}
        </Text>
        <TouchableOpacity
          style={styles.reconnectBtn}
          onPress={() => loadInitialState()}
          activeOpacity={0.8}
        >
          <Text style={styles.reconnectBtnText}>🔄 RECONNECT TO BACKEND</Text>
        </TouchableOpacity>
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
  const battedBallTelemetry: BattedBallTelemetry | null =
    (pitchPhase === 'REACTING' || pitchPhase === 'BATTED_BALL') &&
    hasPendingBattedBall
      ? pendingBattedBall ?? null
      : pitchPhase === 'IDLE'
        ? latestPitch?.batted_ball ?? null
        : null;

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
        activeBattedBall={activeBattedBall}
        onBattedBallComplete={handleBattedBallComplete}
        cameraMode={cameraMode}
        controlMode={controlMode}
        pitchPhase={pitchPhase}
        battingInputEnabled={battingInputEnabled}
        battingChargeRef={battingChargeRef}
        onBattingContact={handleBattingContact}
        onBattingPitchArrival={handleBattingPitchArrival}
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

      {battedBallTelemetry && (
        <View pointerEvents="none" style={styles.battedBallOverlay}>
          <BattedBallMetricsWidget telemetry={battedBallTelemetry} />
        </View>
      )}

      <SafeAreaView style={styles.safeArea}>
        {/* Error Banner */}
        {errorMessage && (
          <ErrorEnvelopeBanner
            message={errorMessage}
            errorEnvelope={errorEnvelope}
            onDismiss={clearError}
            onRetry={loadInitialState}
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
            onOpenSettings={() => toggleSettingsMenu(true)}
            activeSeed={activeSeed}
            controlMode={controlMode}
            onOpenBattingDrill={() => setBattingDrillOpen(true)}
          />

          <View style={styles.bottomPad} />
        </ScrollView>

        {/* Pitch Selector — bottom fallback for narrow screens */}
        {currentPitcher && !showSidePitchSelector && !birdseyeActive && !battingMode && (
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
      {currentBatter && !birdseyeActive && (
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
                gloveTarget={battingMode ? null : gloveTarget}
                commandRating={commandRating}
                onSetGloveTarget={battingMode ? undefined : setGloveTarget}
                coordinateScaleX={strikeZoneScaleX}
                coordinateScaleY={strikeZoneScaleY}
                variant="field"
              />
            </View>
          </View>
        </View>
      )}

      {/* Pitch Selector — stacked vertically beside the strike zone */}
      {currentPitcher && showSidePitchSelector && !birdseyeActive && !battingMode && (
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

      <BattingDrillHud />

      <SwingMeterWidget
        chargeRef={battingChargeRef}
        visible={battingMode && pitchPhase === 'IN_FLIGHT' && !birdseyeActive}
      />

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

      {/* Batting Practice drill playlist setup */}
      <BattingDrillModal />

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
  disconnectedTitle: { color: '#FF8A80', fontSize: 18, fontWeight: '800' },
  disconnectedSubtitle: { color: Colors.textSecondary, fontSize: 13, textAlign: 'center', maxWidth: 320 },
  reconnectBtn: {
    backgroundColor: Colors.green,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    marginTop: 8,
  },
  reconnectBtnText: { color: '#000', fontSize: 13, fontWeight: '800' },
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
  battedBallOverlay: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 132,
    alignItems: 'center',
    zIndex: 20,
  },
});
