import React from 'react';
import { StyleSheet } from 'react-native';
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg';

import { Colors } from '../../theme/colors';

/**
 * Screen-space scrims that keep the HUD legible over the 3D field.
 * Rendered outside the Canvas so it works on web and native.
 */
export const FieldScrims = React.memo(function FieldScrims() {
  return (
    <Svg
      pointerEvents="none"
      style={styles.root}
      width="100%"
      height="100%"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
    >
      <Defs>
        <LinearGradient id="gameFieldTopScrim" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor={Colors.bgDeep} stopOpacity="0.94" />
          <Stop offset="0.5" stopColor={Colors.bgDeep} stopOpacity="0.55" />
          <Stop offset="1" stopColor={Colors.bgDeep} stopOpacity="0" />
        </LinearGradient>
        <LinearGradient id="gameFieldBottomScrim" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor={Colors.bgDeep} stopOpacity="0" />
          <Stop offset="0.45" stopColor={Colors.bgDeep} stopOpacity="0.62" />
          <Stop offset="1" stopColor={Colors.bgDeep} stopOpacity="0.92" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y="0" width="100" height="14" fill="url(#gameFieldTopScrim)" />
      <Rect x="0" y="74" width="100" height="26" fill="url(#gameFieldBottomScrim)" />
    </Svg>
  );
});

const styles = StyleSheet.create({
  root: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    pointerEvents: 'none',
  },
});
