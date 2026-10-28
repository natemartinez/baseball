import React, { useEffect, useState } from 'react';
import {
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { useGameStore } from '../store/gameStore';
import { Colors } from '../theme/colors';
import type { BattingDrillEntry } from '../types/api';
import { STRIKE_ZONES } from '../types/api';
import { getZoneNominalTarget } from '../services/gamedayMath';
import { StrikeZoneGridWidget } from './StrikeZoneGridWidget';

const ZONE_NAMES = Object.values(STRIKE_ZONES);
const INTERVALS = [2000, 2500, 3500, 4500];

function nearestZone(x: number, z: number): string {
  let best: string = STRIKE_ZONES.HEART;
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const zone of ZONE_NAMES) {
    const nominal = getZoneNominalTarget(zone);
    const distance = (nominal.x - x) ** 2 + (nominal.z - z) ** 2;
    if (distance < bestDistance) {
      bestDistance = distance;
      best = zone;
    }
  }
  return best;
}

function newEntry(
  pitchName: string,
  targetX: number,
  targetZ: number,
  targetZone: string,
  index: number,
): BattingDrillEntry {
  return {
    id: `drill-${Date.now()}-${index}`,
    pitchName,
    targetX,
    targetZ,
    targetZone,
  };
}

/**
 * Batting Practice setup. The batter never chooses pitches during an at-bat;
 * this modal builds the exact pitch/location playlist before the drill and
 * pauses the auto-feed while open.
 */
export function BattingDrillModal() {
  const {
    isBattingDrillOpen,
    battingDrill,
    gameState,
    isPitching,
    pitchPhase,
    startBattingDrill,
    updateBattingDrill,
    resumeBattingDrill,
    endBattingDrill,
    setBattingDrillOpen,
  } = useGameStore();

  const arsenal = gameState?.current_pitcher?.arsenal ?? [];
  const active = Boolean(battingDrill?.active);
  const canStart = !isPitching && pitchPhase === 'IDLE';
  const [entries, setEntries] = useState<BattingDrillEntry[]>([]);
  const [draftPitch, setDraftPitch] = useState('');
  const [draftTarget, setDraftTarget] = useState({ x: 0, z: 2.5 });
  const [draftZone, setDraftZone] = useState<string>(STRIKE_ZONES.HEART);
  const [loop, setLoop] = useState(true);
  const [intervalMs, setIntervalMs] = useState(2500);

  useEffect(() => {
    if (!isBattingDrillOpen) return;

    const activeEntries =
      battingDrill?.entries?.length
        ? battingDrill.entries.map((entry) => ({ ...entry }))
        : [];
    const nextEntries =
      activeEntries.length > 0
        ? activeEntries
        : arsenal[0]
          ? [
              newEntry(
                arsenal[0].name,
                0,
                2.5,
                STRIKE_ZONES.HEART,
                0,
              ),
            ]
          : [];
    const first = nextEntries[0];

    setEntries(nextEntries);
    setDraftPitch(first?.pitchName ?? arsenal[0]?.name ?? '');
    setDraftTarget(
      first ? { x: first.targetX, z: first.targetZ } : { x: 0, z: 2.5 },
    );
    setDraftZone(first?.targetZone ?? STRIKE_ZONES.HEART);
    setLoop(battingDrill?.loop ?? true);
    setIntervalMs(battingDrill?.intervalMs ?? 2500);
    // Re-sync only when the modal opens; edits remain local while open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isBattingDrillOpen]);

  if (Platform.OS !== 'web') return null;

  const addEntry = () => {
    if (!draftPitch) return;
    setEntries((prev) => [
      ...prev,
      newEntry(draftPitch, draftTarget.x, draftTarget.z, draftZone, prev.length),
    ]);
  };

  const removeEntry = (id: string) => {
    setEntries((prev) => prev.filter((entry) => entry.id !== id));
  };

  const moveEntry = (index: number, direction: -1 | 1) => {
    setEntries((prev) => {
      const next = [...prev];
      const target = index + direction;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const applyAndStart = () => {
    if (entries.length === 0 || !canStart) return;
    if (active) {
      updateBattingDrill(entries, { loop, intervalMs });
      resumeBattingDrill();
      setBattingDrillOpen(false);
      return;
    }
    void startBattingDrill(entries, { loop, intervalMs });
  };

  const close = () => setBattingDrillOpen(false);

  return (
    <Modal
      visible={isBattingDrillOpen}
      transparent
      animationType="slide"
      onRequestClose={close}
    >
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>BATTING DRILL</Text>
              <Text style={styles.subtitle}>
                Build the exact pitches and locations the AI will throw.
              </Text>
            </View>
            <TouchableOpacity onPress={close} style={styles.closeButton}>
              <Text style={styles.closeText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.scroll}>
            <Text style={styles.sectionLabel}>PITCH</Text>
            <View style={styles.chipWrap}>
              {arsenal.map((pitch) => {
                const selected = draftPitch === pitch.name;
                return (
                  <TouchableOpacity
                    key={pitch.name}
                    style={[styles.pitchChip, selected && styles.pitchChipSelected]}
                    onPress={() => setDraftPitch(pitch.name)}
                    activeOpacity={0.75}
                  >
                    <Text
                      style={[
                        styles.pitchChipName,
                        selected && styles.pitchChipNameSelected,
                      ]}
                    >
                      {pitch.name}
                    </Text>
                    <Text style={styles.pitchChipMeta}>
                      {pitch.velocity_mph.toFixed(1)} mph
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            <Text style={styles.sectionLabel}>EXACT LOCATION</Text>
            <Text style={styles.locationText}>
              {draftZone.toUpperCase()} · {draftTarget.x.toFixed(2)} ft /{' '}
              {draftTarget.z.toFixed(2)} ft
            </Text>
            {gameState?.current_batter ? (
              <View style={styles.gridWrap}>
                <StrikeZoneGridWidget
                  variant="field"
                  selectedZone={draftZone}
                  onSelectZone={(zone) => {
                    const nominal = getZoneNominalTarget(zone);
                    setDraftZone(zone);
                    setDraftTarget({ x: nominal.x, z: nominal.z });
                  }}
                  currentBatter={gameState.current_batter}
                  latestPitch={null}
                  atBatPitches={[]}
                  gloveTarget={draftTarget}
                  commandRating={gameState.current_pitcher?.control ?? 70}
                  onSetGloveTarget={(x, z) => {
                    setDraftTarget({ x, z });
                    setDraftZone(nearestZone(x, z));
                  }}
                  showZoneLabels={false}
                  showPitchSummary={false}
                />
              </View>
            ) : (
              <Text style={styles.emptyText}>Load a game to configure a drill.</Text>
            )}

            <TouchableOpacity
              style={[styles.addButton, !draftPitch && styles.disabled]}
              onPress={addEntry}
              disabled={!draftPitch}
              activeOpacity={0.75}
            >
              <Text style={styles.addButtonText}>+ ADD TO PLAYLIST</Text>
            </TouchableOpacity>

            <View style={styles.playlistHeader}>
              <Text style={styles.sectionLabel}>PLAYLIST</Text>
              <Text style={styles.playlistCount}>
                {entries.length} {entries.length === 1 ? 'entry' : 'entries'}
              </Text>
            </View>

            {entries.length === 0 && (
              <Text style={styles.emptyText}>
                Add at least one pitch/location entry to start.
              </Text>
            )}

            {entries.map((entry, index) => (
              <View key={entry.id} style={styles.entryRow}>
                <Text style={styles.entryIndex}>{index + 1}</Text>
                <View style={styles.entryInfo}>
                  <Text style={styles.entryName}>{entry.pitchName}</Text>
                  <Text style={styles.entryMeta}>
                    {entry.targetZone ?? 'point'} · {entry.targetX.toFixed(2)} /{' '}
                    {entry.targetZ.toFixed(2)} ft
                  </Text>
                </View>
                <TouchableOpacity
                  style={styles.iconButton}
                  onPress={() => moveEntry(index, -1)}
                  disabled={index === 0}
                >
                  <Text style={styles.iconText}>↑</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.iconButton}
                  onPress={() => moveEntry(index, 1)}
                  disabled={index === entries.length - 1}
                >
                  <Text style={styles.iconText}>↓</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.iconButton}
                  onPress={() => removeEntry(entry.id)}
                >
                  <Text style={styles.removeText}>✕</Text>
                </TouchableOpacity>
              </View>
            ))}

            <View style={styles.optionsRow}>
              <TouchableOpacity
                style={[styles.optionPill, loop && styles.optionPillActive]}
                onPress={() => setLoop((value) => !value)}
                activeOpacity={0.75}
              >
                <Text
                  style={[styles.optionText, loop && styles.optionTextActive]}
                >
                  LOOP {loop ? 'ON' : 'OFF'}
                </Text>
              </TouchableOpacity>
              {INTERVALS.map((value) => (
                <TouchableOpacity
                  key={value}
                  style={[
                    styles.optionPill,
                    intervalMs === value && styles.optionPillActive,
                  ]}
                  onPress={() => setIntervalMs(value)}
                  activeOpacity={0.75}
                >
                  <Text
                    style={[
                      styles.optionText,
                      intervalMs === value && styles.optionTextActive,
                    ]}
                  >
                    {(value / 1000).toFixed(1)}s
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          <View style={styles.footer}>
            {!canStart && (
              <Text style={styles.waitText}>
                Finish the current pitch before starting or resuming the drill.
              </Text>
            )}
            <View style={styles.actions}>
              {active && (
                <TouchableOpacity
                  style={styles.endButton}
                  onPress={() => void endBattingDrill()}
                  activeOpacity={0.75}
                >
                  <Text style={styles.endButtonText}>END PRACTICE</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity
                style={[
                  styles.startButton,
                  (entries.length === 0 || !canStart) && styles.disabled,
                ]}
                onPress={applyAndStart}
                disabled={entries.length === 0 || !canStart}
                activeOpacity={0.75}
              >
                <Text style={styles.startButtonText}>
                  {active ? 'SAVE & RESUME' : 'START DRILL'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.72)',
    justifyContent: 'flex-end',
  },
  sheet: {
    maxHeight: '92%',
    backgroundColor: '#070D1A',
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    borderWidth: 1,
    borderColor: '#1E293B',
    paddingBottom: 20,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
    gap: 12,
  },
  title: {
    color: '#F8FAFC',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
  },
  subtitle: {
    color: '#94A3B8',
    fontSize: 11,
    marginTop: 2,
    maxWidth: 280,
  },
  closeButton: {
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1E293B',
  },
  closeText: {
    color: '#E2E8F0',
    fontSize: 14,
    fontWeight: '800',
  },
  scroll: {
    paddingHorizontal: 16,
    paddingBottom: 24,
    gap: 8,
  },
  sectionLabel: {
    color: Colors.gameday.accentCyan,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1,
    marginTop: 8,
  },
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  pitchChip: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#1E293B',
    backgroundColor: '#0F172A',
    paddingHorizontal: 9,
    paddingVertical: 6,
    minWidth: 134,
  },
  pitchChipSelected: {
    borderColor: Colors.gameday.accentCyan,
    backgroundColor: 'rgba(6, 182, 212, 0.14)',
  },
  pitchChipName: {
    color: '#CBD5E1',
    fontSize: 10,
    fontWeight: '800',
  },
  pitchChipNameSelected: {
    color: '#E0F2FE',
  },
  pitchChipMeta: {
    color: '#64748B',
    fontSize: 9,
    marginTop: 1,
  },
  locationText: {
    color: '#94A3B8',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
  gridWrap: {
    alignItems: 'center',
    marginVertical: 4,
  },
  addButton: {
    marginTop: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.gameday.accentCyan,
    backgroundColor: 'rgba(6, 182, 212, 0.12)',
    paddingVertical: 9,
    alignItems: 'center',
  },
  addButtonText: {
    color: Colors.gameday.accentCyan,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0.6,
  },
  playlistHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  playlistCount: {
    color: '#64748B',
    fontSize: 9,
    fontWeight: '700',
  },
  entryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#1E293B',
    backgroundColor: '#0F172A',
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
  entryIndex: {
    width: 16,
    color: Colors.gameday.accentCyan,
    fontSize: 10,
    fontWeight: '900',
  },
  entryInfo: {
    flex: 1,
  },
  entryName: {
    color: '#E2E8F0',
    fontSize: 10,
    fontWeight: '800',
  },
  entryMeta: {
    color: '#64748B',
    fontSize: 9,
    marginTop: 1,
  },
  iconButton: {
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: {
    color: '#94A3B8',
    fontSize: 13,
    fontWeight: '800',
  },
  removeText: {
    color: '#F87171',
    fontSize: 12,
    fontWeight: '800',
  },
  optionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 8,
  },
  optionPill: {
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#1E293B',
    backgroundColor: '#0F172A',
    paddingHorizontal: 9,
    paddingVertical: 6,
  },
  optionPillActive: {
    borderColor: Colors.gameday.accentCyan,
    backgroundColor: 'rgba(6, 182, 212, 0.14)',
  },
  optionText: {
    color: '#94A3B8',
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0.4,
  },
  optionTextActive: {
    color: Colors.gameday.accentCyan,
  },
  actions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 0,
  },
  footer: {
    paddingHorizontal: 16,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#1E293B',
    backgroundColor: '#070D1A',
    gap: 6,
  },
  waitText: {
    color: '#FBBF24',
    fontSize: 9,
    fontWeight: '700',
    lineHeight: 13,
  },
  endButton: {
    flex: 1,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#7F1D1D',
    backgroundColor: 'rgba(127, 29, 29, 0.25)',
    paddingVertical: 10,
    alignItems: 'center',
  },
  endButtonText: {
    color: '#FCA5A5',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0.6,
  },
  startButton: {
    flex: 1.4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.gameday.accentCyan,
    backgroundColor: 'rgba(6, 182, 212, 0.18)',
    paddingVertical: 10,
    alignItems: 'center',
  },
  startButtonText: {
    color: Colors.gameday.accentCyan,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0.6,
  },
  disabled: {
    opacity: 0.4,
  },
  emptyText: {
    color: '#64748B',
    fontSize: 10,
    lineHeight: 15,
    marginTop: 4,
  },
});
