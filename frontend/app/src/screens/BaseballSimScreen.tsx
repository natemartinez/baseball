import React, { useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Text,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { useGameStore } from '../store/gameStore';
import { ErrorEnvelopeBanner } from '../components/ErrorEnvelopeBanner';
import { ScoreboardControlsWidget } from '../components/ScoreboardControlsWidget';
import { StrikeZoneGridWidget } from '../components/StrikeZoneGridWidget';
import { LineupDialogWidget } from '../components/LineupDialogWidget';
import { RotationBullpenDialogWidget } from '../components/RotationBullpenDialogWidget';
import { PitchSelectorWidget } from '../components/PitchSelectorWidget';
import { StrategyMenuModal } from '../components/StrategyMenuModal';
import { PitchFeedModal } from '../components/PitchFeedModal';
import { PitchTrajectoryModal } from '../components/PitchTrajectoryModal';
import { SettingsMenuModal } from '../components/SettingsMenuModal';
import { GamedayDevMenuModal } from '../components/debug/GamedayDevMenuModal';
import { getZoneNominalTarget } from '../services/gamedayMath';
import { Colors } from '../theme/colors';

/**
 * BaseballSimScreen — Root screen of the simulation client.
 * Ported from BaseballSimScreen.kt / GameViewModel.
 *
 * Assembles all 7 widgets into a scrollable vertical layout matching the
 * original Jetpack Compose scaffold.
 */
export function BaseballSimScreen() {
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
  const gloveTarget = customTargetCoords ?? { x: defaultGlove.x, z: defaultGlove.z };
  const commandRating = currentPitcher?.control ?? 82;

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.bgDeep} />

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

      {/* Strike Zone — dead-centered in the viewport so the HEART cell is centered */}
      {currentBatter && (
        <View style={styles.strikeZoneOverlay} pointerEvents="box-none">
          <StrikeZoneGridWidget
            selectedZone={selectedTargetZone ?? ''}
            onSelectZone={setSelectedTargetZone}
            currentBatter={currentBatter}
            latestPitch={latestPitch ?? pitchFeed[0]}
            atBatPitches={currentAtBatPitches}
            gloveTarget={gloveTarget}
            commandRating={commandRating}
            onSetGloveTarget={setGloveTarget}
            showZoneLabels={false}
            chaseTransparent
            showPitchSummary={false}
          />
        </View>
      )}

      {/* Pitch Selector — pinned to the bottom of the screen */}
      {currentPitcher && (
        <View style={styles.pitchFooter}>
          <PitchSelectorWidget
            pitcher={currentPitcher}
            selectedPitchIntent={selectedPitchIntent}
            recommendedPitch={gameState?.strategy_intent?.recommended_pitch}
            strategyIntent={gameState?.strategy_intent}
            onSelectPitchIntent={setSelectedPitchIntent}
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
    </SafeAreaView>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.bgDeep },
  loadingContainer: { flex: 1, backgroundColor: Colors.bgDeep, alignItems: 'center', justifyContent: 'center', gap: 16 },
  loadingText: { color: Colors.textSecondary, fontSize: 14 },
  scroll: { flex: 1 },
  scrollContent: { padding: 12, gap: 12 },
  bottomPad: { height: 12 },
  strikeZoneOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pitchFooter: { paddingHorizontal: 12, paddingBottom: 8 },
});
