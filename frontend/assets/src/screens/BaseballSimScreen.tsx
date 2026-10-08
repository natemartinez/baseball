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
import { MatchupCardWidget } from '../components/MatchupCardWidget';
import { PitchOutcomeFeedWidget } from '../components/PitchOutcomeFeedWidget';
import { LineupDialogWidget } from '../components/LineupDialogWidget';
import { PitchSelectorWidget } from '../components/PitchSelectorWidget';
import { StrategyDeciderWidget } from '../components/StrategyDeciderWidget';
import { GamedayDevMenuModal } from '../components/debug/GamedayDevMenuModal';
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
    latestPitch,
    lineups,
    selectedPitchIntent,
    selectedTargetZone,
    isLineupDialogOpen,
    isMockMode,
    gamedayLog,
    loadingState,
    isPitching,
    errorMessage,
    errorEnvelope,
    // Actions
    loadInitialState,
    startNewGame,
    resetGame,
    throwPitch,
    simAtBat,
    swapLineup,
    toggleMockMode,
    toggleDevMenu,
    setSelectedPitchIntent,
    setSelectedTargetZone,
    setLineupDialogOpen,
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
          isActionPending={isPitching || loadingState === 'loading'}
          isMockMode={isMockMode}
          selectedPitchIntent={selectedPitchIntent}
          selectedTargetZone={selectedTargetZone}
          gamedayCount={gamedayLog.length}
          onThrowPitch={throwPitch}
          onSimAtBat={simAtBat}
          onResetGame={resetGame}
          onOpenLineup={() => setLineupDialogOpen(true)}
          onOpenDevMenu={() => toggleDevMenu(true)}
          onToggleMock={toggleMockMode}
        />

        {/* Step 3: AI Strategy & Pitch Decider below scoreboard controls */}
        {gameState?.strategy_intent && (
          <StrategyDeciderWidget
            strategyIntent={gameState.strategy_intent}
            selectedPitchIntent={selectedPitchIntent}
            selectedTargetZone={selectedTargetZone}
            onSelectPitchIntent={setSelectedPitchIntent}
            onSelectTargetZone={setSelectedTargetZone}
          />
        )}

        {/* Step 1: Pitch Selector above strike zone box */}
        {currentPitcher && (
          <PitchSelectorWidget
            pitcher={currentPitcher}
            selectedPitchIntent={selectedPitchIntent}
            recommendedPitch={gameState?.strategy_intent?.recommended_pitch}
            onSelectPitchIntent={setSelectedPitchIntent}
          />
        )}

        {/* Strike Zone Grid */}
        {currentBatter && (
          <StrikeZoneGridWidget
            selectedZone={selectedTargetZone ?? ''}
            onSelectZone={setSelectedTargetZone}
            currentBatter={currentBatter}
            latestPitch={latestPitch ?? pitchFeed[0]}
          />
        )}

        {/* Pitch Outcome Feed */}
        <PitchOutcomeFeedWidget pitches={pitchFeed} />

        {/* Step 2: Plate Matchup Container at bottom of screen */}
        {currentBatter && currentPitcher && (
          <MatchupCardWidget
            batter={currentBatter}
            pitcher={currentPitcher}
          />
        )}

        <View style={styles.bottomPad} />
      </ScrollView>

      {/* Lineup Dialog */}
      <LineupDialogWidget
        lineups={lineups}
        visible={isLineupDialogOpen}
        onSwapLineup={swapLineup}
        onDismiss={() => setLineupDialogOpen(false)}
      />

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
  bottomPad: { height: 24 },
});
