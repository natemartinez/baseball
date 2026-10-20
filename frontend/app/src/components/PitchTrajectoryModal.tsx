import React, { useState } from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  StyleSheet,
  useWindowDimensions,
} from 'react-native';
import { useGameStore } from '../store/gameStore';
import { PitchTrajectoryWidget } from './PitchTrajectoryWidget';
import { Colors } from '../theme/colors';

/**
 * PitchTrajectoryModal — Full page hosting the 3D pitch-path viewer.
 *
 * Visibility is controlled by the store's isTrajectoryOpen / toggleTrajectory.
 * Opened from the Settings menu; "Replay" re-runs the animation for the latest
 * pitch.
 */
export function PitchTrajectoryModal() {
  const { isTrajectoryOpen, toggleTrajectory, latestPitch, gameState } =
    useGameStore();
  const [replayToken, setReplayToken] = useState(0);
  const { width } = useWindowDimensions();
  const chartWidth = Math.min(360, Math.max(260, width - 80));

  function close() {
    toggleTrajectory(false);
  }

  return (
    <Modal
      visible={isTrajectoryOpen}
      transparent
      animationType="fade"
      onRequestClose={close}
    >
      <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={close}>
        <TouchableOpacity activeOpacity={1} style={styles.dialog}>
          <View style={styles.headerRow}>
            <View style={styles.headerLeft}>
              <View style={styles.dot} />
              <Text style={styles.title}>PITCH TRAJECTORY</Text>
            </View>
            <TouchableOpacity
              onPress={close}
              style={styles.closeBtn}
              accessibilityLabel="Close pitch trajectory"
            >
              <Text style={styles.closeBtnText}>✕ CLOSE</Text>
            </TouchableOpacity>
          </View>

          <PitchTrajectoryWidget
            pitch={latestPitch}
            throws={gameState?.current_pitcher?.throws ?? 'R'}
            width={chartWidth}
            replayToken={replayToken}
          />

          <TouchableOpacity
            onPress={() => setReplayToken((t) => t + 1)}
            disabled={!latestPitch}
            activeOpacity={0.8}
            style={[styles.replayBtn, !latestPitch && styles.replayBtnDisabled]}
          >
            <Text style={styles.replayBtnText}>REPLAY PITCH</Text>
          </TouchableOpacity>
        </TouchableOpacity>
      </TouchableOpacity>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  dialog: {
    backgroundColor: Colors.bgDeep,
    borderRadius: 16,
    width: '100%',
    maxWidth: 480,
    padding: 14,
    gap: 12,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    alignItems: 'center',
  },
  headerRow: {
    width: '100%',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.blue },
  title: {
    fontSize: 13,
    fontWeight: '900',
    color: '#FFF',
    letterSpacing: 1.0,
  },
  closeBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
  },
  closeBtnText: {
    fontSize: 10,
    fontWeight: '800',
    color: Colors.textSecondary,
  },
  replayBtn: {
    backgroundColor: Colors.blue,
    borderRadius: 8,
    paddingHorizontal: 18,
    paddingVertical: 10,
  },
  replayBtnDisabled: { opacity: 0.4 },
  replayBtnText: { color: '#FFF', fontWeight: '800', fontSize: 12, letterSpacing: 0.5 },
});
