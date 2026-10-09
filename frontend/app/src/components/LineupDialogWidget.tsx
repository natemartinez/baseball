import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  FlatList,
  StyleSheet,
  ScrollView,
} from 'react-native';
import type { TeamLineup, LineupPlayer } from '../types/api';
import { Colors } from '../theme/colors';

interface LineupDialogWidgetProps {
  lineups: TeamLineup[];
  visible: boolean;
  onSwapLineup: (teamId: number, pos1: number, pos2: number) => void;
  onDismiss: () => void;
}

/**
 * Lineup Management Dialog
 * Visualizes 9-man batting orders and supports POST /api/swap_lineup.
 *
 * Ported from LineupDialogWidget.kt.
 */
export function LineupDialogWidget({
  lineups,
  visible,
  onSwapLineup,
  onDismiss,
}: LineupDialogWidgetProps) {
  const [selectedTeamTab, setSelectedTeamTab] = useState(0);
  const [selectedFirstPos, setSelectedFirstPos] = useState<number | null>(null);
  const [selectedSecondPos, setSelectedSecondPos] = useState<number | null>(null);

  const activeLineup = lineups[selectedTeamTab];

  function handleTabChange(index: number) {
    setSelectedTeamTab(index);
    setSelectedFirstPos(null);
    setSelectedSecondPos(null);
  }

  function handlePlayerTap(battingOrder: number) {
    if (selectedFirstPos === null) {
      setSelectedFirstPos(battingOrder);
    } else if (selectedFirstPos === battingOrder) {
      setSelectedFirstPos(null);
    } else if (selectedSecondPos === null) {
      setSelectedSecondPos(battingOrder);
    } else if (selectedSecondPos === battingOrder) {
      setSelectedSecondPos(null);
    } else {
      setSelectedFirstPos(battingOrder);
      setSelectedSecondPos(null);
    }
  }

  function handleConfirmSwap() {
    if (selectedFirstPos !== null && selectedSecondPos !== null && activeLineup) {
      onSwapLineup(activeLineup.team_id, selectedFirstPos, selectedSecondPos);
      setSelectedFirstPos(null);
      setSelectedSecondPos(null);
    }
  }

  const swapHint =
    selectedFirstPos !== null && selectedSecondPos !== null
      ? `Ready to swap #${selectedFirstPos} and #${selectedSecondPos}`
      : selectedFirstPos !== null
        ? `Selected #${selectedFirstPos}. Tap a second player to swap.`
        : 'Tap a player to begin swap';

  const swapReady = selectedFirstPos !== null && selectedSecondPos !== null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onDismiss}
    >
      <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={onDismiss}>
        <TouchableOpacity activeOpacity={1} style={styles.dialog}>
          {/* Title */}
          <Text style={styles.title}>ROSTER & BATTING ORDER</Text>
          <Text style={styles.subtitle}>
            Tap two positions to swap batting orders (POST /api/swap_lineup)
          </Text>

          {/* Team tabs */}
          <View style={styles.tabRow}>
            {lineups.map((lineup, idx) => (
              <TouchableOpacity
                key={lineup.team_id}
                onPress={() => handleTabChange(idx)}
                style={[styles.tab, selectedTeamTab === idx && styles.tabActive]}
              >
                <Text style={[styles.tabText, selectedTeamTab === idx && styles.tabTextActive]}>
                  {lineup.team_name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Swap hint pill */}
          <View style={styles.hintPill}>
            <Text style={[styles.hintText, swapReady && { color: Colors.amberLight }]}>
              {swapHint}
            </Text>
          </View>

          {/* Lineup list */}
          {activeLineup && (
            <FlatList
              data={activeLineup.lineup}
              keyExtractor={(item) => String(item.batting_order)}
              style={styles.lineupList}
              contentContainerStyle={{ gap: 4 }}
              renderItem={({ item }) => {
                const isPos1 = selectedFirstPos === item.batting_order;
                const isPos2 = selectedSecondPos === item.batting_order;
                const isHighlighted = isPos1 || isPos2;
                return (
                  <LineupRowItem
                    item={item}
                    isHighlighted={isHighlighted}
                    onPress={() => handlePlayerTap(item.batting_order)}
                  />
                );
              }}
            />
          )}

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

// ─── Lineup Row Item ─────────────────────────────────────────────────────────

function LineupRowItem({
  item,
  isHighlighted,
  onPress,
}: { item: LineupPlayer; isHighlighted: boolean; onPress: () => void }) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.75}
      style={[
        styles.lineupRow,
        {
          backgroundColor: isHighlighted ? 'rgba(2, 119, 189, 0.4)' : Colors.bgListItem,
          borderColor: isHighlighted ? Colors.blue : Colors.borderPrimary,
        },
      ]}
    >
      <View style={styles.lineupRowLeft}>
        <View style={[styles.orderCircle, { backgroundColor: isHighlighted ? Colors.blue : Colors.baseDefault }]}>
          <Text style={[styles.orderNumber, { color: isHighlighted ? '#000' : '#FFF' }]}>
            {item.batting_order}
          </Text>
        </View>
        <View>
          <Text style={styles.lineupPlayerName}>
            {item.player.name} (#{item.player.jersey_number})
          </Text>
          <Text style={styles.lineupPlayerMeta}>
            {item.player.position} • {item.ratings}
          </Text>
        </View>
      </View>
      <View style={styles.positionBadge}>
        <Text style={styles.positionText}>{item.player.position}</Text>
      </View>
    </TouchableOpacity>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center', padding: 16 },
  dialog: { backgroundColor: Colors.bgSurface, borderRadius: 16, width: '100%', maxWidth: 480, padding: 16, gap: 10 },
  title: { fontSize: 16, fontWeight: '900', color: '#FFF' },
  subtitle: { fontSize: 11, color: Colors.textSecondary },
  tabRow: { flexDirection: 'row', backgroundColor: Colors.bgInput, borderRadius: 8, overflow: 'hidden' },
  tab: { flex: 1, paddingVertical: 8, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: Colors.green },
  tabText: { fontSize: 12, color: Colors.textMuted, fontWeight: '500' },
  tabTextActive: { color: '#FFF', fontWeight: '700' },
  hintPill: { backgroundColor: Colors.bgCard, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 6 },
  hintText: { fontSize: 11, fontWeight: '600', color: Colors.textSecondary },
  lineupList: { maxHeight: 300 },
  lineupRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderRadius: 6, borderWidth: 1, paddingHorizontal: 8, paddingVertical: 6 },
  lineupRowLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  orderCircle: { width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  orderNumber: { fontSize: 11, fontWeight: '900' },
  lineupPlayerName: { fontSize: 12, fontWeight: '700', color: '#FFF' },
  lineupPlayerMeta: { fontSize: 10, color: Colors.textSecondary },
  positionBadge: { backgroundColor: Colors.bgInput, borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  positionText: { color: Colors.amberLight, fontSize: 10, fontWeight: '700' },
  buttonRow: { flexDirection: 'row', gap: 8, justifyContent: 'flex-end', marginTop: 4 },
  cancelBtn: { borderWidth: 1, borderColor: Colors.textSecondary, borderRadius: 8, paddingHorizontal: 16, paddingVertical: 8 },
  cancelText: { color: Colors.textSecondary, fontWeight: '600' },
  confirmBtn: { backgroundColor: Colors.green, borderRadius: 8, paddingHorizontal: 16, paddingVertical: 8 },
  confirmBtnDisabled: { opacity: 0.4 },
  confirmText: { color: '#000', fontWeight: '900', fontSize: 13 },
});
