import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { useGameStore } from '../store/gameStore';
import { Colors } from '../theme/colors';

/** Bottom drill status + pause/edit controls while batting practice is active. */
export function BattingDrillHud() {
  const {
    battingDrill,
    isPitching,
    pauseBattingDrill,
    resumeBattingDrill,
    setBattingDrillOpen,
  } = useGameStore();

  if (!battingDrill?.active) return null;

  const entries = battingDrill.entries;
  const next = entries[battingDrill.index] ?? entries[0];
  const ready = battingDrill.pitchesThrown === 0 && battingDrill.playing;
  const status = ready ? 'GET READY' : battingDrill.playing ? 'PLAYING' : 'PAUSED';
  const location = next
    ? next.targetZone ?? `${next.targetX.toFixed(2)} / ${next.targetZ.toFixed(2)}`
    : '—';

  return (
    <View style={styles.wrap}>
      <View style={styles.bar}>
        <View style={styles.info}>
          <Text style={styles.label}>BATTING DRILL · {status}</Text>
          <Text style={styles.next} numberOfLines={1}>
            NEXT: {next ? `${next.pitchName} · ${location}` : '—'}
          </Text>
          <Text style={styles.count}>
            PITCH {battingDrill.pitchesThrown} · ENTRY{' '}
            {Math.min(battingDrill.index + 1, Math.max(1, entries.length))}/
            {entries.length}
          </Text>
        </View>
        <TouchableOpacity
          style={[styles.btn, isPitching && styles.disabled]}
          onPress={() => setBattingDrillOpen(true)}
          disabled={isPitching}
          activeOpacity={0.75}
        >
          <Text style={styles.btnText}>EDIT</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.btnPrimary, isPitching && styles.disabled]}
          onPress={() =>
            battingDrill.playing ? pauseBattingDrill() : resumeBattingDrill()
          }
          disabled={isPitching}
          activeOpacity={0.75}
        >
          <Text style={styles.btnPrimaryText}>
            {battingDrill.playing ? 'PAUSE' : 'RESUME'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    left: 14,
    right: 14,
    bottom: 16,
  },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#1E293B',
    backgroundColor: 'rgba(3, 7, 18, 0.92)',
  },
  info: {
    flex: 1,
    gap: 1,
  },
  label: {
    color: Colors.gameday.accentCyan,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0.9,
  },
  next: {
    color: '#E2E8F0',
    fontSize: 11,
    fontWeight: '700',
  },
  count: {
    color: '#64748B',
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
  btn: {
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#334155',
    backgroundColor: '#1E293B',
    paddingHorizontal: 9,
    paddingVertical: 6,
  },
  btnText: {
    color: '#E2E8F0',
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  btnPrimary: {
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.gameday.accentCyan,
    backgroundColor: 'rgba(6, 182, 212, 0.16)',
    paddingHorizontal: 9,
    paddingVertical: 6,
  },
  btnPrimaryText: {
    color: Colors.gameday.accentCyan,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  disabled: {
    opacity: 0.4,
  },
});
