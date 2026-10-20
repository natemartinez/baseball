import React from 'react';
import { View, Text, Modal, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { useGameStore } from '../store/gameStore';
import { PitchFeedItemCard } from './PitchOutcomeFeedWidget';
import { Colors } from '../theme/colors';

/**
 * PitchFeedModal — Full page hosting the Pitch-by-Pitch feed & Statcast telemetry.
 *
 * Visibility is controlled by the store's isPitchFeedOpen / togglePitchFeed.
 * Opened from the Settings menu; the feed widget itself no longer renders inline
 * on the main screen.
 */
export function PitchFeedModal() {
  const { isPitchFeedOpen, togglePitchFeed, pitchFeed } = useGameStore();

  function close() {
    togglePitchFeed(false);
  }

  return (
    <Modal
      visible={isPitchFeedOpen}
      transparent
      animationType="fade"
      onRequestClose={close}
    >
      <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={close}>
        <TouchableOpacity activeOpacity={1} style={styles.dialog}>
          <View style={styles.headerRow}>
            <View style={styles.headerLeft}>
              <View style={styles.radarDot} />
              <Text style={styles.title}>PITCH-BY-PITCH FEED</Text>
            </View>
            <View style={styles.headerRight}>
              <Text style={styles.countLabel}>{pitchFeed.length} logged</Text>
              <TouchableOpacity
                onPress={close}
                style={styles.closeBtn}
                accessibilityLabel="Close pitch feed"
              >
                <Text style={styles.closeBtnText}>✕ CLOSE</Text>
              </TouchableOpacity>
            </View>
          </View>

          <ScrollView
            style={styles.body}
            contentContainerStyle={styles.bodyContent}
            showsVerticalScrollIndicator={false}
          >
            {pitchFeed.length === 0 ? (
              <View style={styles.emptyBox}>
                <Text style={styles.emptyText}>
                  Ready for first pitch. Press 'Throw Pitch' or 'Sim At-Bat'.
                </Text>
              </View>
            ) : (
              pitchFeed.map((item, index) => (
                <PitchFeedItemCard
                  key={`${pitchFeed.length - index}-${item.pitch_name}-${index}`}
                  pitch={item}
                  pitchIndex={pitchFeed.length - index}
                />
              ))
            )}
          </ScrollView>
        </TouchableOpacity>
      </TouchableOpacity>
    </Modal>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

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
    maxHeight: '88%',
    padding: 14,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  radarDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.green,
  },
  title: {
    fontSize: 13,
    fontWeight: '900',
    color: '#FFF',
    letterSpacing: 1.0,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  countLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: Colors.blueLight,
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
  body: {
    flexShrink: 1,
  },
  bodyContent: {
    gap: 8,
    paddingBottom: 4,
  },
  emptyBox: {
    backgroundColor: Colors.bgInput,
    borderRadius: 10,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    color: Colors.textMuted,
    fontSize: 12,
    textAlign: 'center',
  },
});
