/**
 * Baseball Simulation — Dark Mode Color Palette
 * Ported from the hex constants used throughout the Kotlin Compose UI.
 */

export const Colors = {
  // ─── Background layers ───────────────────────────────────────────────────
  /** Deep game background */
  bgDeep: '#0A0F15',
  /** Primary surface — cards, panels */
  bgSurface: '#131B24',
  /** Secondary surface — nested cards */
  bgCard: '#1A232E',
  /** Tertiary / input background */
  bgInput: '#0D131A',
  /** Slightly raised list item */
  bgListItem: '#1B2430',
  /** Pitch feed card */
  bgFeedItem: '#18212B',

  // ─── Borders ────────────────────────────────────────────────────────────
  borderPrimary: '#263238',
  borderSecondary: '#37474F',
  borderDivider: '#455A64',

  // ─── Text ────────────────────────────────────────────────────────────────
  textPrimary: '#ECEFF1',
  textSecondary: '#90A4AE',
  textMuted: '#78909C',
  textDisabled: '#546E7A',

  // ─── Accent — Yankees Navy ───────────────────────────────────────────────
  yankeesNavy: '#001C43',

  // ─── Accent — Mets ───────────────────────────────────────────────────────
  metsBlue: '#002D72',
  metsOrange: '#FF5910',

  // ─── Status — Green (Balls / Hit) ───────────────────────────────────────
  green: '#00E676',
  greenLight: '#69F0AE',
  greenDark: '#00C853',

  // ─── Status — Amber (Strikes) ────────────────────────────────────────────
  amber: '#FFB300',
  amberLight: '#FFD54F',
  amberHot: '#FFD600',
  yellow: '#FFEB3B',
  yellowLight: '#FFF9C4',

  // ─── Status — Red (Outs / Danger) ───────────────────────────────────────
  red: '#FF1744',
  redLight: '#FF5252',
  redMild: '#FF8A80',
  redSoft: '#FFCDD2',

  // ─── Status — Blue (Info) ────────────────────────────────────────────────
  blue: '#40C4FF',
  blueMid: '#0277BD',
  blueLight: '#64B5F6',
  blueSky: '#81D4FA',
  blueDeep: '#80D8FF',

  // ─── Home run / power ────────────────────────────────────────────────────
  homeRunRed: '#D50000',
  homeRunGlow: '#FF5252',

  // ─── Rating chips ────────────────────────────────────────────────────────
  ratingHighlight: 'rgba(255, 179, 0, 0.2)', // 0x33FFB300
  ratingHighlightBorder: '#FFD54F',

  // ─── Trait badge ─────────────────────────────────────────────────────────
  traitHrBg: 'rgba(213, 0, 0, 0.2)',   // 0x33D50000
  traitDefault: '#263238',

  // ─── Infield / diamond ──────────────────────────────────────────────────
  infieldClay: '#2A241C',
  infieldMound: '#3E362C',
  baseDefault: '#263238',
  baselineChalk: 'rgba(236, 239, 241, 0.6)',

  // ─── Strike zone ────────────────────────────────────────────────────────
  zoneStrike: '#4CAF50',
  zoneChase: '#1565C0',
  zoneHot: '#D50000',
  zoneCold: '#0277BD',
  zoneSelected: '#40C4FF',
  zoneHeatmapHigh: 'rgba(213, 0, 0, 0.6)',
  zoneHeatmapMid: 'rgba(255, 179, 0, 0.4)',
  zoneHeatmapLow: 'rgba(33, 150, 243, 0.2)',

  // ─── Gameday 2D Cross-Section & Calibration Diagnostics ──────────────────
  cyan: '#06B6D4',
  gameday: {
    accentCyan: '#06B6D4',
    statusPass: '#10B981',
    statusWarn: '#F59E0B',
    statusFail: '#EF4444',
    zoneHeart: '#EF4444',
    zoneShadow: '#3B82F6',
    zoneChase: '#6366F1',
    zoneWaste: '#64748B',
  },
} as const;
