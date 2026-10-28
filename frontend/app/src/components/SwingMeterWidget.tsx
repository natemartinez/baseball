import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { MutableRefObject } from 'react';

import { Colors } from '../theme/colors';

/**
 * Isolated charge meter. It polls the shared ref in its own animation frame so
 * per-frame batting input never re-renders the screen or the GameField.
 */
export function SwingMeterWidget({
  chargeRef,
  visible,
}: {
  chargeRef: MutableRefObject<number>;
  visible: boolean;
}) {
  const [charge, setCharge] = useState(0);

  useEffect(() => {
    if (!visible) {
      setCharge(0);
      return;
    }

    let frame = 0;
    const tick = () => {
      setCharge(chargeRef.current);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [visible, chargeRef]);

  if (!visible) return null;

  const percent = Math.round(charge * 100);
  const fillColor = charge >= 0.85 ? Colors.amber : Colors.gameday.accentCyan;

  return (
    <View pointerEvents="none" style={styles.wrap}>
      <View style={styles.row}>
        <Text style={styles.label}>SWING LOAD</Text>
        <Text style={styles.value}>{percent}%</Text>
      </View>
      <View style={styles.track}>
        <View
          style={[
            styles.fill,
            { width: `${Math.max(2, percent)}%`, backgroundColor: fillColor },
          ]}
        />
      </View>
      <Text style={styles.hint}>HOLD TO CHARGE · RELEASE TO SWING</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    left: 20,
    right: 20,
    bottom: 158,
    backgroundColor: 'rgba(3, 7, 18, 0.88)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#1E293B',
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 5,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    color: Colors.gameday.accentCyan,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1,
  },
  value: {
    color: '#E2E8F0',
    fontSize: 10,
    fontWeight: '800',
  },
  track: {
    height: 8,
    borderRadius: 4,
    backgroundColor: '#1E293B',
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 4,
  },
  hint: {
    color: '#64748B',
    fontSize: 8,
    fontWeight: '700',
    letterSpacing: 0.6,
    textAlign: 'center',
  },
});
