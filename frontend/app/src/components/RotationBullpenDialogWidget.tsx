import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  ScrollView,
  StyleSheet,
} from 'react-native';
import type { TeamRotation, PlayerSummary } from '../types/api';
import { Colors } from '../theme/colors';

interface RotationBullpenDialogWidgetProps {
  rotations: TeamRotation[];
  visible: boolean;
  onSwapRotation: (teamId: number, pos1: number, pos2: number) => void;
  onDismiss: () => void;
}

/**
 * Rotation & Bullpen Management Dialog
 * Visualizes each team's starting rotation (with order-swap support backed by
 * POST /api/swap_rotation) and the bullpen depth chart.
 */
export function RotationBullpenDialogWidget({
  rotations,
  visible,
  onSwapRotation,
  onDismiss,
}: RotationBullpenDialogWidgetProps) {
  const [selectedTeamTab, setSelectedTeamTab] = useState(0);
  const [selectedFirstPos, setSelectedFirstPos] = useState<number | null>(null);
  const [selectedSecondPos, setSelectedSecondPos] = useState<number | null>(null);

  const activeRotation = rotations[selectedTeamTab];

  function handleTabChange(index: number) {
    setSelectedTeamTab(index);
    setSelectedFirstPos(null);
    setSelectedSecondPos(null);
  }

  function handleStarterTap(pos: number) {
    if (selectedFirstPos === null) {
      setSelectedFirstPos(pos);
    } else if (selectedFirstPos === pos) {
      setSelectedFirstPos(null);
    } else if (selectedSecondPos === null) {
      setSelectedSecondPos(pos);
    } else if (selectedSecondPos === pos) {
      setSelectedSecondPos(null);
    } else {
      setSelectedFirstPos(pos);
      setSelectedSecondPos(null);
    }
  }

  function handleConfirmSwap() {
    if (selectedFirstPos !== null && selectedSecondPos !== null && activeRotation) {
      onSwapRotation(activeRotation.team_id, selectedFirstPos, selectedSecondPos);
      setSelectedFirstPos(null);
      setSelectedSecondPos(null);
    }
  }

  const swapReady = selectedFirstPos !== null && selectedSecondPos !== null;
  const swapHint =
    selectedFirstPos !== null && selectedSecondPos !== null
      ? `Ready to swap SP${selectedFirstPos} and SP${selectedSecondPos}`
      : selectedFirstPos !== null
        ? `Selected SP${selectedFirstPos}. Tap a second starter to swap.`
        : 'Tap two starters to reorder the rotation';

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onDismiss}>
      <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={onDismiss}>
        <TouchableOpacity activeOpacity={1} style={styles.dialog}>
          <Text style={styles.title}>ROTATION & BULLPEN</Text>
          <Text style={styles.subtitle}>
            Tap two starters to reorder (POST /api/swap_rotation)
          </Text>

          {/* Team tabs */}
          <View style={styles.tabRow}>
            {rotations.map((rotation, idx) => (
              <TouchableOpacity
                key={rotation.team_id}
                onPress={() => handleTabChange(idx)}
                style={[styles.tab, selectedTeamTab === idx && styles.tabActive]}
              >
                <Text style={[styles.tabText, selectedTeamTab === idx && styles.tabTextActive]}>
                  {rotation.team_name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent}>
            {activeRotation ? (
              <>
                <Text style={styles.sectionLabel}>STARTING ROTATION</Text>

                <View style={styles.hintPill}>
                  <Text style={[styles.hintText, swapReady && { color: Colors.amberLight }]}>
                    {swapHint}
                  </Text>
                </View>

                {activeRotation.starters.map((pitcher, idx) => {
                  const pos = idx + 1;
                  const isHighlighted = selectedFirstPos === pos || selectedSecondPos === pos;
                  return (
                    <PitcherRow
                      key={`sp-${pitcher.id}-${idx}`}
                      pitcher={pitcher}
                      badge={`SP${pos}`}
                      badgeColor={isHighlighted ? Colors.blue : Colors.metsBlue}
                      highlighted={isHighlighted}
                      onPress={() => handleStarterTap(pos)}
                    />
                  );
                })}

                <Text style={[styles.sectionLabel, styles.bullpenLabel]}>BULLPEN</Text>
                {activeRotation.bullpen && activeRotation.bullpen.length > 0 ? (
                  activeRotation.bullpen.map((pitcher, idx) => (
                    <PitcherRow
                      key={`rp-${pitcher.id}-${idx}`}
                      pitcher={pitcher}
                      badge={pitcher.position}
                      badgeColor={Colors.amber}
                      highlighted={false}
                    />
                  ))
                ) : (
                  <View style={styles.emptyBullpen}>
                    <Text style={styles.emptyBullpenText}>No bullpen data available.</Text>
                  </View>
                )}
              </>
            ) : (
              <View style={styles.emptyBullpen}>
                <Text style={styles.emptyBullpenText}>No rotation data available.</Text>
              </View>
            )}
          </ScrollView>

          {/* Buttons */}
          <View style={styles.buttonRow}>
            <TouchableOpacity onPress={onDismiss} style={styles.cancelBtn}>
              <Text style={styles.cancelText}>Close</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={handleConfirmSwap}
              disabled={!swapReady}
              style={[styles.confirmBtn, !swapReady && styles.confirmBtnDisabled]}
            >
              <Text style={styles.confirmText}>Confirm Swap</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </TouchableOpacity>
    </Modal>
  );
}

// ─── Pitcher Row ─────────────────────────────────────────────────────────────

function PitcherRow({
  pitcher,
  badge,
  badgeColor,
  highlighted,
  onPress,
}: {
  pitcher: PlayerSummary;
  badge: string;
  badgeColor: string;
  highlighted: boolean;
  onPress?: () => void;
}) {
  const content = (
    <>
      <View style={styles.pitcherRowLeft}>
        <View style={[styles.pitcherBadge, { backgroundColor: badgeColor }]}>
          <Text style={styles.pitcherBadgeText}>{badge}</Text>
        </View>
        <View>
          <Text style={styles.pitcherName}>
            {pitcher.name} (#{pitcher.jersey_number})
          </Text>
          <Text style={styles.pitcherMeta}>{pitcher.position} • {pitcher.team}</Text>
        </View>
      </View>
      {onPress && (
        <View style={styles.swapPill}>
          <Text style={styles.swapPillText}>{highlighted ? 'SELECTED' : 'SWAP'}</Text>
        </View>
      )}
    </>
  );

  if (!onPress) {
    return (
      <View
        style={[
          styles.pitcherRow,
          { backgroundColor: Colors.bgListItem, borderColor: Colors.borderPrimary },
        ]}
      >
        {content}
      </View>
    );
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.75}
      style={[
        styles.pitcherRow,
        {
          backgroundColor: highlighted ? 'rgba(2, 119, 189, 0.4)' : Colors.bgListItem,
          borderColor: highlighted ? Colors.blue : Colors.borderPrimary,
        },
      ]}
    >
      {content}
    </TouchableOpacity>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center', padding: 16 },
  dialog: { backgroundColor: Colors.bgSurface, borderRadius: 16, width: '100%', maxWidth: 480, maxHeight: '88%', padding: 16, gap: 10 },
  title: { fontSize: 16, fontWeight: '900', color: '#FFF' },
  subtitle: { fontSize: 11, color: Colors.textSecondary },
  tabRow: { flexDirection: 'row', backgroundColor: Colors.bgInput, borderRadius: 8, overflow: 'hidden' },
  tab: { flex: 1, paddingVertical: 8, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: Colors.green },
  tabText: { fontSize: 12, color: Colors.textMuted, fontWeight: '500' },
  tabTextActive: { color: '#FFF', fontWeight: '700' },
  body: { flexShrink: 1 },
  bodyContent: { gap: 6, paddingBottom: 4 },
  sectionLabel: { fontSize: 10, fontWeight: '800', color: Colors.textSecondary, letterSpacing: 1.0, marginTop: 2 },
  bullpenLabel: { marginTop: 10 },
  hintPill: { backgroundColor: Colors.bgCard, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 6, marginBottom: 2 },
  hintText: { fontSize: 11, fontWeight: '600', color: Colors.textSecondary },
  pitcherRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderRadius: 6, borderWidth: 1, paddingHorizontal: 8, paddingVertical: 6 },
  pitcherRowLeft: { flexDirection: 'row', alignItems: 'center', gap: 8, flexShrink: 1 },
  pitcherBadge: { minWidth: 30, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 6 },
  pitcherBadgeText: { fontSize: 10, fontWeight: '900', color: '#FFF' },
  pitcherName: { fontSize: 12, fontWeight: '700', color: '#FFF' },
  pitcherMeta: { fontSize: 10, color: Colors.textSecondary },
  swapPill: { backgroundColor: Colors.bgInput, borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  swapPillText: { color: Colors.amberLight, fontSize: 9, fontWeight: '700' },
  emptyBullpen: { backgroundColor: Colors.bgInput, borderRadius: 6, padding: 12, alignItems: 'center' },
  emptyBullpenText: { color: Colors.textMuted, fontSize: 11, fontStyle: 'italic' },
  buttonRow: { flexDirection: 'row', gap: 8, justifyContent: 'flex-end', marginTop: 4 },
  cancelBtn: { borderWidth: 1, borderColor: Colors.textSecondary, borderRadius: 8, paddingHorizontal: 16, paddingVertical: 8 },
  cancelText: { color: Colors.textSecondary, fontWeight: '600' },
  confirmBtn: { backgroundColor: Colors.green, borderRadius: 8, paddingHorizontal: 16, paddingVertical: 8 },
  confirmBtnDisabled: { opacity: 0.4 },
  confirmText: { color: '#000', fontWeight: '900', fontSize: 13 },
});
