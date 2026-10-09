import { StyleSheet } from 'react-native';

/**
 * Typography scale for the Baseball Simulation app.
 * Mirrors the MaterialTheme typography used in the Kotlin Compose UI.
 */

export const FontFamily = {
  /** Primary — for body and data */
  mono: undefined, // platform default monospace
  /** Sans — for labels and headings */
  sans: undefined, // platform default sans-serif
} as const;

export const Typography = StyleSheet.create({
  // Display
  displayLarge: { fontSize: 32, fontWeight: '900', letterSpacing: -0.5 },
  displayMedium: { fontSize: 26, fontWeight: '800' },

  // Headings
  h1: { fontSize: 22, fontWeight: '800', letterSpacing: -0.2 },
  h2: { fontSize: 18, fontWeight: '700' },
  h3: { fontSize: 16, fontWeight: '700' },

  // Body
  bodyLarge: { fontSize: 15, fontWeight: '400', lineHeight: 22 },
  bodyMedium: { fontSize: 13, fontWeight: '400', lineHeight: 19 },
  bodySmall: { fontSize: 11.5, fontWeight: '400', lineHeight: 16 },

  // Labels (ALL CAPS telemetry style)
  labelLarge: { fontSize: 11, fontWeight: '700', letterSpacing: 1.0 },
  labelSmall: { fontSize: 9, fontWeight: '700', letterSpacing: 0.8 },

  // Scores and numbers
  scoreLarge: { fontSize: 36, fontWeight: '900' },
  scoreMedium: { fontSize: 24, fontWeight: '900' },
  scoreSmall: { fontSize: 18, fontWeight: '800' },

  // Jersey / sequence numbers
  jerseyNumber: { fontSize: 11, fontWeight: '900' },
  sequenceNumber: { fontSize: 11, fontWeight: '900' },

  // Stat chips
  statChipLabel: { fontSize: 9, fontWeight: '700' },
  statChipValue: { fontSize: 14, fontWeight: '900' },

  // Velocity / RPM telemetry
  telemetryPrimary: { fontSize: 12, fontWeight: '700' },
  telemetrySecondary: { fontSize: 10, fontWeight: '600' },
  telemetryMicro: { fontSize: 9.5, fontWeight: '700' },
});
