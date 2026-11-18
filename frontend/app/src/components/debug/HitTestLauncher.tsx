import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import {
  HIT_PRESETS,
  buildActiveBattedBallFromPreset,
  calculateRemainingLifecycleMs,
  type HitPreset,
} from './hitPresets';
import type { ActiveBattedBallData, GameCameraMode } from '../gamefield/types';
import { useGameStore } from '../../store/gameStore';
import { Colors } from '../../theme/colors';

export interface HitTestLauncherProps {
  onLaunchBattedBall: (battedBall: ActiveBattedBallData) => void;
  onSetCameraMode?: (mode: GameCameraMode | null) => void;
  onSetCameraHold?: (hold: boolean) => void;
  onReset: () => void;
}

const CONTACT_DELAY_MS = 160;
const LANDING_HOLD_MS = 1200;

function categoryBadge(category: HitPreset['category']) {
  switch (category) {
    case 'grounder':
      return { label: '⚡ GROUNDER', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.18)' };
    case 'line_drive':
      return { label: '🚀 LINE DRIVE', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.18)' };
    case 'fly_ball':
      return { label: '🦅 FLY BALL', color: '#a855f7', bg: 'rgba(168, 85, 247, 0.18)' };
    case 'home_run':
      return { label: '💥 HOME RUN', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.18)' };
    default:
      return { label: 'HIT', color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.18)' };
  }
}

/**
 * Floating, plug-and-play debug launcher to activate different hit trajectories
 * and test camera tracking, physics, and catch framing.
 */
export const HitTestLauncher = React.memo(function HitTestLauncher({
  onLaunchBattedBall,
  onSetCameraMode,
  onSetCameraHold,
  onReset,
}: HitTestLauncherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activePresetId, setActivePresetId] = useState<string | null>(null);

  const isPaused = useGameStore((s) => s.isBattedBallPaused);
  const toggleBattedBallPaused = useGameStore((s) => s.toggleBattedBallPaused);
  const setBattedBallPaused = useGameStore((s) => s.setBattedBallPaused);

  const seqRef = useRef(0);
  const timer1Ref = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timer2Ref = useRef<ReturnType<typeof setTimeout> | null>(null);
  const launchStartTimeRef = useRef(0);
  const remainingMsRef = useRef(0);

  const clearAllTimers = useCallback(() => {
    if (timer1Ref.current) {
      clearTimeout(timer1Ref.current);
      timer1Ref.current = null;
    }
    if (timer2Ref.current) {
      clearTimeout(timer2Ref.current);
      timer2Ref.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      clearAllTimers();
      setBattedBallPaused(false);
      onSetCameraMode?.(null);
      onSetCameraHold?.(false);
      onReset();
    };
  }, [clearAllTimers, setBattedBallPaused, onSetCameraMode, onSetCameraHold, onReset]);

  const handleLaunchPreset = useCallback(
    (preset: HitPreset) => {
      clearAllTimers();
      setBattedBallPaused(false);
      setActivePresetId(preset.id);
      seqRef.current += 1;

      const battedBall = buildActiveBattedBallFromPreset(preset, seqRef.current);

      // Stage 1: Contact Impact Beat (0 - 160ms)
      // Camera holds in batting view (PITCH)
      onSetCameraMode?.('PITCH');
      onSetCameraHold?.(false);

      // Stage 2: Adaptive Follow Camera Tracking & Ball Flight (at 160ms)
      // Synchronized handoff: ball takes flight as follow camera begins tracking
      timer1Ref.current = setTimeout(() => {
        onLaunchBattedBall(battedBall);
        onSetCameraMode?.(preset.isGrounder ? 'GROUNDER' : 'TRACKING');
        onSetCameraHold?.(true);
      }, CONTACT_DELAY_MS);

      // Stage 3 & 4: Landing zone hold and return to batter view
      const flightDurationMs = preset.hangTime * 1000;
      const totalLifecycleMs = CONTACT_DELAY_MS + flightDurationMs + LANDING_HOLD_MS;
      launchStartTimeRef.current = Date.now();
      remainingMsRef.current = totalLifecycleMs;

      timer2Ref.current = setTimeout(() => {
        setActivePresetId(null);
        setBattedBallPaused(false);
        onSetCameraMode?.(null);
        onSetCameraHold?.(false);
        onReset();
      }, totalLifecycleMs);
    },
    [clearAllTimers, setBattedBallPaused, onLaunchBattedBall, onSetCameraMode, onSetCameraHold, onReset],
  );

  const handleReset = useCallback(() => {
    clearAllTimers();
    setBattedBallPaused(false);
    setActivePresetId(null);
    onSetCameraMode?.(null);
    onSetCameraHold?.(false);
    onReset();
  }, [clearAllTimers, setBattedBallPaused, onSetCameraMode, onSetCameraHold, onReset]);

  const handleTogglePause = useCallback(() => {
    if (!activePresetId) return;

    if (!isPaused) {
      if (timer2Ref.current) {
        clearTimeout(timer2Ref.current);
        timer2Ref.current = null;
      }
      const elapsedMs = Date.now() - launchStartTimeRef.current;
      remainingMsRef.current = calculateRemainingLifecycleMs(remainingMsRef.current, elapsedMs);
      toggleBattedBallPaused();
    } else {
      launchStartTimeRef.current = Date.now();
      timer2Ref.current = setTimeout(() => {
        setActivePresetId(null);
        setBattedBallPaused(false);
        onSetCameraMode?.(null);
        onSetCameraHold?.(false);
        onReset();
      }, remainingMsRef.current);
      toggleBattedBallPaused();
    }
  }, [
    activePresetId,
    isPaused,
    toggleBattedBallPaused,
    setBattedBallPaused,
    onSetCameraMode,
    onSetCameraHold,
    onReset,
  ]);

  return (
    <View pointerEvents="box-none" style={styles.container}>
      {/* Floating Trigger Row */}
      {!isOpen && (
        <View style={styles.floatingRow}>
          {activePresetId !== null && (
            <TouchableOpacity
              style={[styles.pausePillButton, isPaused && styles.pausePillButtonActive]}
              onPress={handleTogglePause}
              activeOpacity={0.8}
            >
              <Text style={styles.pausePillIcon}>{isPaused ? '▶' : '⏸'}</Text>
              <Text style={styles.pausePillText}>{isPaused ? 'RESUME' : 'PAUSE'}</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            style={styles.pillButton}
            onPress={() => setIsOpen(true)}
            activeOpacity={0.8}
          >
            <Text style={styles.pillIcon}>🎯</Text>
            <Text style={styles.pillText}>TEST HITS</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Expandable Debug Panel */}
      {isOpen && (
        <View style={styles.panel}>
          <View style={styles.panelHeader}>
            <View>
              <Text style={styles.panelTitle}>🎯 Hit Debugger</Text>
              <Text style={styles.panelSubtitle}>Test camera tracking & physics</Text>
            </View>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setIsOpen(false)}
              activeOpacity={0.7}
            >
              <Text style={styles.closeButtonText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.presetList} showsVerticalScrollIndicator={false}>
            {HIT_PRESETS.map((preset) => {
              const badge = categoryBadge(preset.category);
              const isSelected = activePresetId === preset.id;
              return (
                <TouchableOpacity
                  key={preset.id}
                  style={[styles.presetCard, isSelected && styles.presetCardActive]}
                  onPress={() => handleLaunchPreset(preset)}
                  activeOpacity={0.75}
                >
                  <View style={styles.presetCardHeader}>
                    <Text style={styles.presetName}>{preset.name}</Text>
                    <View style={[styles.badge, { backgroundColor: badge.bg }]}>
                      <Text style={[styles.badgeText, { color: badge.color }]}>
                        {badge.label}
                      </Text>
                    </View>
                  </View>

                  <Text style={styles.presetMetrics}>
                    {preset.exitVelocity} mph • {preset.launchAngle}° LA • {preset.hangTime}s flight
                  </Text>

                  <Text style={styles.presetDesc} numberOfLines={2}>
                    {preset.description}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          <View style={styles.panelFooter}>
            {activePresetId !== null && (
              <TouchableOpacity
                style={[styles.pauseButton, isPaused && styles.pauseButtonActive]}
                onPress={handleTogglePause}
                activeOpacity={0.75}
              >
                <Text style={styles.pauseButtonText}>
                  {isPaused ? '▶ Resume Flight' : '⏸ Pause Flight'}
                </Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity
              style={styles.resetButton}
              onPress={handleReset}
              activeOpacity={0.75}
            >
              <Text style={styles.resetButtonText}>↺ Reset Camera & Ball</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
});

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 60,
    right: 12,
    zIndex: 9999,
  },
  floatingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  pausePillButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(15, 23, 42, 0.88)',
    borderWidth: 1.5,
    borderColor: '#f59e0b',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 7,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.35,
    shadowRadius: 4,
    elevation: 5,
  },
  pausePillButtonActive: {
    borderColor: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
  },
  pausePillIcon: {
    fontSize: 12,
    marginRight: 5,
    color: '#f59e0b',
  },
  pausePillText: {
    color: '#f59e0b',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.6,
  },
  pauseButton: {
    backgroundColor: 'rgba(245, 158, 11, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.6)',
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: 'center',
    marginBottom: 8,
  },
  pauseButtonActive: {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    borderColor: 'rgba(16, 185, 129, 0.6)',
  },
  pauseButtonText: {
    color: '#fbbf24',
    fontSize: 11,
    fontWeight: '700',
  },
  pillButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(15, 23, 42, 0.88)',
    borderWidth: 1.5,
    borderColor: '#38bdf8',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 7,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.35,
    shadowRadius: 4,
    elevation: 5,
  },
  pillIcon: {
    fontSize: 14,
    marginRight: 6,
  },
  pillText: {
    color: '#38bdf8',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.6,
  },
  panel: {
    width: 290,
    maxHeight: 460,
    backgroundColor: 'rgba(15, 23, 42, 0.94)',
    borderWidth: 1.5,
    borderColor: 'rgba(56, 189, 248, 0.5)',
    borderRadius: 14,
    padding: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 8,
  },
  panelHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  panelTitle: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  panelSubtitle: {
    color: '#94a3b8',
    fontSize: 11,
    marginTop: 2,
  },
  closeButton: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  closeButtonText: {
    color: '#cbd5e1',
    fontSize: 12,
    fontWeight: 'bold',
  },
  presetList: {
    maxHeight: 320,
  },
  presetCard: {
    backgroundColor: 'rgba(30, 41, 59, 0.75)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 8,
    padding: 9,
    marginBottom: 8,
  },
  presetCardActive: {
    borderColor: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
  },
  presetCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  presetName: {
    color: '#f8fafc',
    fontSize: 12,
    fontWeight: '700',
    flex: 1,
  },
  badge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginLeft: 6,
  },
  badgeText: {
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0.4,
  },
  presetMetrics: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '600',
    marginBottom: 3,
  },
  presetDesc: {
    color: '#cbd5e1',
    fontSize: 10,
    lineHeight: 14,
  },
  panelFooter: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  resetButton: {
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.5)',
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: 'center',
  },
  resetButtonText: {
    color: '#fca5a5',
    fontSize: 11,
    fontWeight: '700',
  },
});
