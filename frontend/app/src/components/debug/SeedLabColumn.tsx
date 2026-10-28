import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { useGameStore } from '../../store/gameStore';
import { Colors } from '../../theme/colors';
import { createSeed, parseSeedInput, SEED_PRESETS } from '../../services/seeds';

/**
 * Seed Lab — starts a fresh game on the Flask API from a fixed or random seed.
 * All outcomes and half-inning team changes come from the server.
 */
export function SeedLabColumn() {
  const { controlMode, isPitching, pitchPhase, activeSeed, loadSeed } =
    useGameStore();
  const [customSeed, setCustomSeed] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const busy = isPitching || pitchPhase !== 'IDLE';
  const seedsDisabled = busy || controlMode !== 'PITCHING';

  function load(value: number) {
    if (seedsDisabled) return;
    setValidationError(null);
    void loadSeed(value);
  }

  function loadCustom() {
    const seed = parseSeedInput(customSeed);
    if (seed === null) {
      setValidationError('Enter a whole number from 0 to 4294967295.');
      return;
    }
    load(seed);
  }

  function loadRandom() {
    const seed = createSeed();
    setCustomSeed(String(seed));
    load(seed);
  }

  return (
    <View style={styles.container}>
      <View style={styles.introCard}>
        <Text style={styles.introTitle}>🌱 SEED LAB</Text>
        <Text style={styles.introText}>
          Every seed restarts a fresh game through the Flask API at Top 1st.
          Lineups, pitch outcomes, and half-inning team changes are all decided
          by the server.
        </Text>
      </View>

      {controlMode === 'BATTING' && (
        <View style={styles.noticeCard}>
          <Text style={styles.noticeTitle}>BATTING PRACTICE ACTIVE</Text>
          <Text style={styles.noticeText}>
            End the batting drill before loading a seeded game.
          </Text>
        </View>
      )}

      <View style={styles.activeCard}>
        <View style={styles.activeHeader}>
          <Text style={styles.activeLabel}>CURRENT SEED</Text>
          <Text style={styles.activeValue}>
            {activeSeed === null ? 'UNSEEDED' : activeSeed}
          </Text>
        </View>
        <Text style={styles.activeText}>
          {activeSeed === null
            ? 'The current game was started without a fixed seed.'
            : 'Reloading this seed restarts the same server-side sequence.'}
        </Text>
        {activeSeed !== null && (
          <TouchableOpacity
            style={[styles.secondaryBtn, seedsDisabled && styles.btnDisabled]}
            onPress={() => load(activeSeed)}
            disabled={seedsDisabled}
            activeOpacity={0.75}
          >
            <Text style={styles.secondaryBtnText}>RELOAD SEED</Text>
          </TouchableOpacity>
        )}
      </View>

      <Text style={styles.sectionLabel}>SEED PRESETS</Text>

      <View style={styles.presetGrid}>
        {SEED_PRESETS.map((seed) => {
          const isActive = activeSeed === seed;
          return (
            <TouchableOpacity
              key={seed}
              style={[
                styles.presetBtn,
                isActive && styles.presetBtnActive,
                seedsDisabled && styles.btnDisabled,
              ]}
              onPress={() => load(seed)}
              disabled={seedsDisabled}
              activeOpacity={0.75}
            >
              <Text
                style={[
                  styles.presetText,
                  isActive && styles.presetTextActive,
                ]}
              >
                {seed}
              </Text>
              {isActive && <Text style={styles.activePill}>ACTIVE</Text>}
            </TouchableOpacity>
          );
        })}
      </View>

      <Text style={styles.sectionLabel}>CUSTOM SEED</Text>

      <View style={styles.customCard}>
        <TextInput
          style={styles.seedInput}
          value={customSeed}
          onChangeText={(value) => {
            setCustomSeed(value);
            if (validationError) setValidationError(null);
          }}
          placeholder="e.g. 424201"
          placeholderTextColor="#475569"
          keyboardType="number-pad"
          inputMode="numeric"
          maxLength={10}
          editable={!seedsDisabled}
          onSubmitEditing={loadCustom}
          returnKeyType="go"
        />
        {validationError && (
          <Text style={styles.validationError}>{validationError}</Text>
        )}
        <View style={styles.actionRow}>
          <TouchableOpacity
            style={[styles.primaryBtn, seedsDisabled && styles.btnDisabled]}
            onPress={loadCustom}
            disabled={seedsDisabled}
            activeOpacity={0.75}
          >
            <Text style={styles.primaryBtnText}>LOAD SEED</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.secondaryBtn, seedsDisabled && styles.btnDisabled]}
            onPress={loadRandom}
            disabled={seedsDisabled}
            activeOpacity={0.75}
          >
            <Text style={styles.secondaryBtnText}>RANDOM SEED</Text>
          </TouchableOpacity>
        </View>
      </View>

      <Text style={styles.footnote}>
        A seed only fixes the server's random sequence. It does not force a
        specific result; play continues until the game ends or you load another
        seed.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 14,
    gap: 10,
  },
  introCard: {
    backgroundColor: '#0B132B',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#1E293B',
    padding: 12,
    gap: 4,
  },
  introTitle: {
    color: Colors.gameday.accentCyan,
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0.8,
  },
  introText: {
    color: '#94A3B8',
    fontSize: 11,
    lineHeight: 16,
  },
  noticeCard: {
    backgroundColor: 'rgba(249, 115, 22, 0.12)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.gameday.statusWarn,
    padding: 12,
    gap: 6,
  },
  noticeTitle: {
    color: Colors.gameday.statusWarn,
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0.8,
  },
  noticeText: {
    color: '#CBD5E1',
    fontSize: 11,
    lineHeight: 16,
  },
  activeCard: {
    backgroundColor: 'rgba(6, 182, 212, 0.10)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.gameday.accentCyan,
    padding: 12,
    gap: 4,
  },
  activeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  activeLabel: {
    color: Colors.gameday.accentCyan,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1,
  },
  activeValue: {
    color: '#F8FAFC',
    fontSize: 14,
    fontWeight: '800',
  },
  activeText: {
    color: '#94A3B8',
    fontSize: 11,
    lineHeight: 15,
  },
  sectionLabel: {
    color: '#64748B',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
    marginTop: 4,
  },
  presetGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  presetBtn: {
    backgroundColor: '#0F172A',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#1E293B',
    paddingHorizontal: 12,
    paddingVertical: 8,
    alignItems: 'center',
    gap: 2,
  },
  presetBtnActive: {
    borderColor: Colors.gameday.accentCyan,
    backgroundColor: 'rgba(6, 182, 212, 0.12)',
  },
  presetText: {
    color: '#E2E8F0',
    fontSize: 12,
    fontWeight: '800',
    fontVariant: ['tabular-nums'],
  },
  presetTextActive: {
    color: Colors.gameday.accentCyan,
  },
  activePill: {
    color: Colors.gameday.accentCyan,
    fontSize: 8,
    fontWeight: '900',
    letterSpacing: 0.8,
  },
  customCard: {
    backgroundColor: '#0F172A',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#1E293B',
    padding: 12,
    gap: 8,
  },
  seedInput: {
    backgroundColor: '#020617',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#334155',
    color: '#F8FAFC',
    fontSize: 14,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  validationError: {
    color: '#F87171',
    fontSize: 10,
    fontWeight: '700',
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
  },
  primaryBtn: {
    flex: 1,
    backgroundColor: 'rgba(6, 182, 212, 0.18)',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.gameday.accentCyan,
    paddingHorizontal: 10,
    paddingVertical: 7,
    alignItems: 'center',
  },
  primaryBtnText: {
    color: Colors.gameday.accentCyan,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  secondaryBtn: {
    flex: 1,
    backgroundColor: '#1E293B',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#334155',
    paddingHorizontal: 10,
    paddingVertical: 7,
    alignItems: 'center',
  },
  secondaryBtnText: {
    color: '#E2E8F0',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  btnDisabled: {
    opacity: 0.4,
  },
  footnote: {
    color: '#475569',
    fontSize: 10,
    lineHeight: 14,
    marginTop: 4,
  },
});
