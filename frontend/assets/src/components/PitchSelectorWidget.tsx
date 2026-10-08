import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import type { PitchArsenalItem, PitcherInfo } from '../types/api';
import { Colors } from '../theme/colors';

interface PitchSelectorWidgetProps {
  pitcher: PitcherInfo;
  selectedPitchIntent: string;
  recommendedPitch?: string;
  onSelectPitchIntent: (name: string) => void;
}

/**
 * PitchSelectorWidget — Standalone container for selecting pitch intent.
 * Placed directly above the Strike Zone Grid.
 */
export function PitchSelectorWidget({
  pitcher,
  selectedPitchIntent,
  recommendedPitch,
  onSelectPitchIntent,
}: PitchSelectorWidgetProps) {
  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.sectionLabel}>PITCH SELECTOR</Text>
        <Text style={styles.headerHint}>TAP TO SELECT INTENT</Text>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.arsenalRow}
      >
        {pitcher.arsenal.map((item) => (
          <ArsenalChip
            key={item.name}
            item={item}
            isSelected={item.name === selectedPitchIntent}
            isRecommended={item.name === recommendedPitch}
            onSelect={() => onSelectPitchIntent(item.name)}
          />
        ))}
      </ScrollView>
    </View>
  );
}

function ArsenalChip({
  item,
  isSelected,
  isRecommended,
  onSelect,
}: {
  item: PitchArsenalItem;
  isSelected: boolean;
  isRecommended?: boolean;
  onSelect: () => void;
}) {
  return (
    <TouchableOpacity
      onPress={onSelect}
      activeOpacity={0.75}
      style={[
        styles.arsenalChip,
        {
          backgroundColor: isSelected ? Colors.blueMid : '#141C24',
          borderColor: isSelected
            ? Colors.blue
            : isRecommended
              ? 'rgba(16, 185, 129, 0.6)'
              : Colors.borderSecondary,
        },
      ]}
    >
      {isRecommended && (
        <View style={styles.recBadge}>
          <Text style={styles.recBadgeText}>★ PRIMARY</Text>
        </View>
      )}
      {isSelected && <View style={styles.arsenalDot} />}
      <Text
        style={[
          styles.arsenalName,
          {
            fontWeight: isSelected ? '700' : '500',
            color: isSelected
              ? '#FFF'
              : isRecommended
                ? '#34D399'
                : Colors.textPrimary,
          },
        ]}
      >
        {item.name}
      </Text>
      <Text
        style={[
          styles.arsenalVelo,
          { color: isSelected ? Colors.yellow : Colors.textSecondary },
        ]}
      >
        {item.velocity_mph} mph
      </Text>
      {item.spin_rpm > 2800 && (
        <Text style={styles.arsenalSpin}>{item.spin_rpm} RPM</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bgSurface,
    borderRadius: 12,
    padding: 14,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.borderPrimary,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 1.0,
    textTransform: 'uppercase',
  },
  headerHint: {
    fontSize: 9,
    fontWeight: '600',
    color: Colors.textMuted,
    letterSpacing: 0.5,
  },
  arsenalRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 2,
  },
  arsenalChip: {
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
    alignItems: 'center',
    minWidth: 100,
    gap: 2,
  },
  arsenalDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.yellow,
    marginBottom: 2,
  },
  arsenalName: {
    fontSize: 11,
    textAlign: 'center',
  },
  arsenalVelo: {
    fontSize: 12,
    fontWeight: '700',
  },
  arsenalSpin: {
    fontSize: 9,
    color: '#E040FB',
    fontWeight: '700',
  },
  recBadge: {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.4)',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 4,
    marginBottom: 2,
  },
  recBadgeText: {
    fontSize: 7,
    fontWeight: '800',
    color: '#34D399',
    letterSpacing: 0.3,
  },
});
