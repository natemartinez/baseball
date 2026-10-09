import type {
  GameState,
  StrategyIntentDecision,
  PitchOptionWeight,
  ZoneOptionWeight,
  PitchArsenalItem,
} from '../types/api';
import {
  STRIKE_ZONES,
  ALL_ZONES,
  isStrike,
} from '../types/api';

function round1(val: number): number {
  return Math.round(val * 10) / 10;
}

/**
 * Pure strategy calculation engine.
 * Derives count leverage, tactical situation tags, AI strategy rationale,
 * ranked dynamic pitch selection weights (with most likely flag), and recommended zone.
 */
export function calculateStrategyAndIntent(state: GameState): StrategyIntentDecision {
  const { outs, balls, strikes, bases, current_batter: batter, current_pitcher: pitcher } = state;

  const isBasesLoaded = bases.first !== null && bases.second !== null && bases.third !== null;
  const isDoublePlay = bases.first !== null && outs < 2;
  const isScoringPos = (bases.second !== null || bases.third !== null) && outs < 2;

  const isAhead = strikes === 2;
  const isBehind = (balls === 3 && strikes < 2) || (balls === 2 && strikes === 0);
  const isFullCount = balls === 3 && strikes === 2;

  const situationTag = isBasesLoaded
    ? 'BASES_LOADED'
    : isDoublePlay
      ? 'DOUBLE_PLAY_SITUATION'
      : isScoringPos
        ? 'SCORING_POSITION'
        : 'BASES_EMPTY';

  const countContext = isAhead
    ? `AHEAD (${balls}-${strikes}) - PUT AWAY MODE`
    : isBehind
      ? `BEHIND (${balls}-${strikes}) - STRIKE DEMAND`
      : isFullCount
        ? 'FULL COUNT (3-2) - HIGH LEVERAGE BATTLE'
        : balls === 0 && strikes === 0
          ? 'FIRST PITCH (0-0) - ESTABLISH COUNT'
          : `NEUTRAL (${balls}-${strikes}) - SETUP & ATTACK`;

  let strategyName: string;
  let rationale: string;

  if (isBasesLoaded && isAhead) {
    strategyName = 'BASES_LOADED_PUNCHOUT';
    rationale =
      'Bases loaded with 2 strikes. Zero margin for error. Attack edges with high-whiff putaway arsenal to secure the strikeout.';
  } else if (isBasesLoaded && isBehind) {
    strategyName = 'BASES_LOADED_COMMAND_STRIKE';
    rationale =
      'Bases loaded behind in count. Ball 4 forces home a run! Must challenge the zone with high-velocity fastball or sinker.';
  } else if (isBasesLoaded) {
    strategyName = 'BASES_LOADED_LEVERAGE';
    rationale =
      'Bases loaded pressure. Induce weak ground-ball or foul contact to prevent extra-base damage.';
  } else if (isDoublePlay) {
    strategyName = 'DOUBLE_PLAY_GROUNDER_HUNT';
    rationale = `Runner on 1st with ${outs} out. Target bottom of zone with Power Sinker (64% GB rate) to roll inning-ending double play.`;
  } else if (isAhead) {
    strategyName = 'TWO_STRIKE_PUT_AWAY';
    rationale = `Ahead in count (${balls}-${strikes}). Expand zone into chase corridors with high-spin sweeper or breaking ball.`;
  } else if (isBehind) {
    strategyName = 'CRITICAL_ZONE_CHALLENGE';
    rationale = `Behind in count (${balls}-${strikes}). Paint strike zone shadow with high-velo fastball to prevent free pass.`;
  } else if (isScoringPos) {
    strategyName = 'SCORING_POSITION_SUPPRESSION';
    rationale = `Runner in scoring position with ${outs} out. Suppress elevated contact to avoid sacrifice fly; attack batter cold zones.`;
  } else {
    strategyName = 'NEUTRAL_PITCH_MIX';
    rationale = `Bases empty, count ${balls}-${strikes}. Balance fastball velocity and sweeper spin while avoiding batter hot zones.`;
  }

  // 1. Ranked Pitch weights
  const defaultArsenal: PitchArsenalItem[] = [
    {
      name: '4-Seam Fastball',
      velocity_mph: 97.4,
      spin_rpm: 2480,
      break_rating: 90,
      control_rating: 84,
      statcast: { whiff_pct: 28.5, chase_pct: 24.2, gb_pct: 38.0, stuff_plus: 118, zone_pct: 56.0, run_value: -4 },
    },
    {
      name: 'Spin Monster Sweeper',
      velocity_mph: 83.5,
      spin_rpm: 2980,
      break_rating: 99,
      control_rating: 80,
      statcast: { whiff_pct: 44.5, chase_pct: 36.5, gb_pct: 42.0, stuff_plus: 135, zone_pct: 42.0, run_value: -12 },
    },
    {
      name: 'Power Sinker',
      velocity_mph: 95.8,
      spin_rpm: 2310,
      break_rating: 88,
      control_rating: 85,
      statcast: { whiff_pct: 22.0, chase_pct: 28.0, gb_pct: 64.0, stuff_plus: 112, zone_pct: 58.0, run_value: -7 },
    },
  ];

  const arsenal = pitcher?.arsenal?.length ? pitcher.arsenal : defaultArsenal;

  const pitchWeightsRaw: Array<{ item: PitchArsenalItem; w: number }> = arsenal.map((item) => {
    let w = 100.0;
    const stat = item.statcast;
    if (isDoublePlay) {
      if (item.name.includes('Sinker')) w *= 2.8;
      else if (item.name.includes('Curveball') || item.name.includes('Changeup')) w *= 1.3;
      else if (item.name.includes('Fastball')) w *= 0.45;
    }
    if (isBasesLoaded) {
      if (isBehind) {
        if (item.name.includes('Fastball') || item.name.includes('Sinker')) w *= 2.2;
        else w *= 0.4;
      } else if (isAhead) {
        if (item.name.includes('Sweeper')) w *= 2.5;
      }
    }
    if (isAhead) {
      if (item.name.includes('Sweeper')) w *= 3.0;
      else if (item.name.includes('Curveball')) w *= 2.0;
      else if (item.name.includes('Fastball')) w *= 0.55;
    } else if (isBehind) {
      if (item.name.includes('Fastball')) w *= 2.6;
      else if (item.name.includes('Sinker')) w *= 1.9;
      else if (item.name.includes('Sweeper')) w *= 0.35;
    }
    if (stat) {
      if (stat.stuff_plus > 125) w *= 1.15;
      if (stat.whiff_pct > 40.0 && isAhead) w *= 1.25;
      if (stat.gb_pct > 60.0 && isDoublePlay) w *= 1.35;
    }
    return { item, w };
  });

  const totalPitchWeight = Math.max(pitchWeightsRaw.reduce((s, x) => s + x.w, 0), 0.001);
  const sortedPitches = [...pitchWeightsRaw].sort((a, b) => b.w - a.w);

  const rankedPitchWeights: PitchOptionWeight[] = sortedPitches.map(({ item, w }, idx) => {
    const prob = (w / totalPitchWeight) * 100.0;
    const reason =
      idx === 0 && isDoublePlay
        ? 'Primary weapon: Elite 64.0% GB rate to roll double play'
        : idx === 0 && isAhead
          ? 'Putaway weapon: 44.5% Whiff & elite spin rate'
          : idx === 0 && isBehind
            ? 'Strike demand: High velocity & zone command'
            : idx === sortedPitches.length - 1
              ? 'Deprioritized in current game leverage'
              : 'Secondary tactical option';

    return {
      pitch_name: item.name,
      weight: round1(w),
      probability_pct: round1(prob),
      rank: idx + 1,
      is_most_likely: idx === 0,
      is_least_likely: idx === sortedPitches.length - 1,
      reasoning: reason,
      statcast: item.statcast,
    };
  });

  // 2. Zone weights
  const hotZones = batter?.hot_zones ?? {};
  const zoneWeightsRaw = ALL_ZONES.map((zone) => {
    let zw = 10.0;
    const hotSlg = hotZones[zone] ?? 0.32;
    const zoneIsStrike = isStrike(zone);
    const isChase = !zoneIsStrike;

    const zoneType =
      hotSlg >= 0.5
        ? 'HOT_ZONE'
        : hotSlg <= 0.28 || zone === STRIKE_ZONES.LOWER_AWAY || zone === STRIKE_ZONES.MIDDLE_AWAY
          ? 'COLD_ZONE'
          : isChase
            ? 'CHASE_ZONE'
            : 'NEUTRAL_ZONE';

    if (zoneType === 'HOT_ZONE') {
      if (isBehind && balls === 3 && strikes < 2) zw *= 0.7;
      else zw *= 0.22;
    } else if (zoneType === 'COLD_ZONE') {
      zw *= 2.4;
    }

    if (isAhead) {
      if (isChase) zw *= 3.4;
      else if (zone === STRIKE_ZONES.HEART) zw *= 0.12;
    } else if (isBehind) {
      if (isChase) zw *= 0.12;
      else zw *= 2.0;
    }

    if (isDoublePlay) {
      if ([STRIKE_ZONES.LOWER_IN, STRIKE_ZONES.LOWER_MIDDLE, STRIKE_ZONES.LOWER_AWAY].includes(zone as any)) zw *= 3.0;
      else if (zone === STRIKE_ZONES.CHASE_LOW) zw *= 2.6;
      else if ([STRIKE_ZONES.UPPER_IN, STRIKE_ZONES.UPPER_MIDDLE, STRIKE_ZONES.UPPER_AWAY, STRIKE_ZONES.CHASE_HIGH].includes(zone as any)) zw *= 0.3;
    }

    if (isBasesLoaded && isChase) zw *= 0.25;

    return { zone, zw, zoneIsStrike, zoneType };
  });

  const totalZoneWeight = Math.max(zoneWeightsRaw.reduce((s, x) => s + x.zw, 0), 0.001);
  const sortedZones = [...zoneWeightsRaw].sort((a, b) => b.zw - a.zw);
  const rankedZoneWeights: ZoneOptionWeight[] = sortedZones.map(({ zone, zw, zoneIsStrike, zoneType }, idx) => {
    const prob = (zw / totalZoneWeight) * 100.0;
    return {
      zone,
      weight: round1(zw),
      probability_pct: round1(prob),
      rank: idx + 1,
      is_strike: zoneIsStrike,
      zone_type: zoneType as ZoneOptionWeight['zone_type'],
      is_most_likely: idx === 0,
      is_least_likely: idx === sortedZones.length - 1,
    };
  });

  const topPitch = rankedPitchWeights[0]?.pitch_name ?? arsenal[0].name;
  const topZone = rankedZoneWeights[0]?.zone ?? STRIKE_ZONES.LOWER_AWAY;

  return {
    strategy_name: strategyName,
    situation_tag: situationTag as StrategyIntentDecision['situation_tag'],
    count_context: countContext,
    rationale,
    recommended_pitch: topPitch,
    recommended_zone: topZone,
    pitch_weights: rankedPitchWeights,
    zone_weights: rankedZoneWeights,
  };
}
