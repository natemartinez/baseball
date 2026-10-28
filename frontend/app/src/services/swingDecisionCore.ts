/**
 * Plate-discipline swing/take model.
 *
 * Mirrors backend/engine/batting_engine/batter_strategy.py. Keep the shared
 * swingModelConfig.json files in sync; tests enforce that.
 */

export type SwingZoneClass =
  | 'heart'
  | 'shadow_strike'
  | 'shadow_ball'
  | 'chase'
  | 'waste';

export interface SwingPitchRecord {
  pitchCategory: string;
  result?: string;
  zoneName?: string;
  zoneCategory?: string;
  isStrike?: boolean;
}

export interface SwingRatings {
  vision: number;
  hotZones: Record<string, number>;
}

export interface SwingDelivery {
  pitchCategory: string;
  velocityMph: number;
  horizontalBreakIn: number;
  inducedVerticalBreakIn: number;
  zoneCategory: string;
  zoneName: string;
  isStrike: boolean;
  pitcherEffectiveBreak: number;
}

export interface SwingSituation {
  balls: number;
  strikes: number;
  outs: number;
  runners: [boolean, boolean, boolean];
  scoreDiff: number;
  inning: number;
  approach?: string;
  pitchSequence?: SwingPitchRecord[];
}

export interface SwingEvaluation {
  willSwing: boolean;
  probability: number;
  baseLogit: number;
  logit: number;
  factors: Record<string, number>;
  zoneClass: SwingZoneClass;
  countKey: string;
  modelVersion: string;
}

function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value));
}

function sigmoid(value: number): number {
  if (value >= 0) {
    return 1 / (1 + Math.exp(-value));
  }
  const z = Math.exp(value);
  return z / (1 + z);
}

function zoneClass(zoneCategory: string, isStrike: boolean): SwingZoneClass {
  const category = String(zoneCategory || 'SHADOW').toUpperCase();
  if (category === 'HEART') return 'heart';
  if (category === 'SHADOW') return isStrike ? 'shadow_strike' : 'shadow_ball';
  if (category === 'CHASE') return 'chase';
  return 'waste';
}

export function evaluateSwingWithConfig(
  config: any,
  delivery: SwingDelivery,
  ratings: SwingRatings,
  situation: SwingSituation,
  rng?: () => number,
): SwingEvaluation {
  const zone = zoneClass(delivery.zoneCategory, delivery.isStrike);
  const countKey = `${Math.max(0, Math.trunc(situation.balls))}-${Math.max(0, Math.trunc(situation.strikes))}`;
  const strike = delivery.isStrike;
  const factors: Record<string, number> = {};
  const baseLogit = Number(config.zone_logit[zone]);

  const countFactor =
    countKey === '3-0'
      ? Number(config.three_ball_no_strike[zone]) - baseLogit
      : situation.strikes === 2
        ? Number(config.two_strike.general)
        : Number(config.count_logit[countKey] ?? 0);
  factors.count = countFactor;

  let twoStrikeFactor = 0;
  if (situation.strikes === 2) {
    if (zone === 'heart' || zone === 'shadow_strike') {
      twoStrikeFactor = Number(config.two_strike.in_zone);
    } else if (zone === 'shadow_ball') {
      twoStrikeFactor = Number(config.two_strike.shadow_ball);
    } else if (zone === 'chase') {
      twoStrikeFactor = Number(config.two_strike.chase);
    } else {
      twoStrikeFactor = Number(config.two_strike.waste);
    }
  }
  factors.two_strike = twoStrikeFactor;

  const disciplineCfg = config.discipline;
  const disciplineZ = clamp(
    (Number(ratings.vision) - Number(disciplineCfg.center)) /
      Number(disciplineCfg.scale),
    -Number(disciplineCfg.clamp),
    Number(disciplineCfg.clamp),
  );
  factors.discipline =
    (strike ? Number(disciplineCfg.strike) : Number(disciplineCfg.ball)) *
    disciplineZ;

  const hotColdCfg = config.hot_cold;
  const slugging = Number(
    ratings.hotZones[delivery.zoneName] ?? hotColdCfg.center,
  );
  const hotColdZ = clamp(
    (slugging - Number(hotColdCfg.center)) / Number(hotColdCfg.scale),
    -Number(hotColdCfg.clamp),
    Number(hotColdCfg.clamp),
  );
  factors.hot_cold =
    (strike ? Number(hotColdCfg.strike) : Number(hotColdCfg.ball)) *
    hotColdZ;

  const category = String(delivery.pitchCategory || 'Fastball');
  const pitchTypeCfg =
    config.pitch_type[category] ?? config.pitch_type.Fastball;
  factors.pitch_type = strike
    ? Number(pitchTypeCfg.strike)
    : Number(pitchTypeCfg.ball);
  if (situation.strikes === 2 && !strike) {
    factors.pitch_type += Number(pitchTypeCfg.two_strike_ball);
  }

  const velocityCfg = config.velocity;
  const velocityZ = clamp(
    (Number(delivery.velocityMph) - Number(velocityCfg.center)) /
      Number(velocityCfg.scale),
    -Number(velocityCfg.clamp),
    Number(velocityCfg.clamp),
  );
  factors.velocity =
    (strike ? Number(velocityCfg.strike) : Number(velocityCfg.ball)) *
    velocityZ;

  const movementCfg = config.movement;
  const movement =
    Math.abs(Number(delivery.horizontalBreakIn)) +
    Math.abs(Number(delivery.inducedVerticalBreakIn));
  const movementZ = clamp(
    (movement - Number(movementCfg.center)) / Number(movementCfg.scale),
    -Number(movementCfg.clamp),
    Number(movementCfg.clamp),
  );
  factors.movement =
    (strike ? Number(movementCfg.strike) : Number(movementCfg.ball)) *
    movementZ;

  let pitcherStuffFactor = 0;
  if (!strike && (category === 'Breaking' || category === 'OffSpeed')) {
    const stuffCfg = config.pitcher_stuff;
    const stuffZ = clamp(
      (Number(delivery.pitcherEffectiveBreak) - Number(stuffCfg.center)) /
        Number(stuffCfg.scale),
      -Number(stuffCfg.clamp),
      Number(stuffCfg.clamp),
    );
    pitcherStuffFactor = Number(stuffCfg.ball) * stuffZ;
  }
  factors.pitcher_stuff = pitcherStuffFactor;

  const sequence = situation.pitchSequence ?? [];
  const sequenceCfg = config.sequence;
  let sequenceFactor = 0;
  if (sequence.length > 0) {
    const last = sequence[sequence.length - 1] ?? {};
    const lastCategory = String(last.pitchCategory ?? 'Fastball');
    if (lastCategory === category) {
      const entry = sequenceCfg.same_type;
      sequenceFactor += strike ? Number(entry.strike) : Number(entry.ball);
    }

    const priorBreaking = sequence.filter(
      (pitch) => String(pitch.pitchCategory) === 'Breaking',
    ).length;
    if (category === 'Breaking' || category === 'OffSpeed') {
      if (priorBreaking > 0) {
        const entry = sequenceCfg.prior_breaking;
        const capped = Math.min(priorBreaking, Number(entry.max_count));
        sequenceFactor +=
          capped * (strike ? Number(entry.strike) : Number(entry.ball));
      }
    }

    let consecutive = 0;
    for (let i = sequence.length - 1; i >= 0; i -= 1) {
      const pitchCategory = String(sequence[i]?.pitchCategory ?? 'Fastball');
      if (pitchCategory !== category) break;
      consecutive += 1;
    }
    if (consecutive >= 2) {
      const entry = sequenceCfg.consecutive_same_type;
      sequenceFactor += strike ? Number(entry.strike) : Number(entry.ball);
    }

    const lastResult = String(last.result ?? '').toUpperCase();
    const resultEntry = sequenceCfg.last_result[lastResult];
    if (resultEntry) {
      sequenceFactor += strike
        ? Number(resultEntry.strike)
        : Number(resultEntry.ball);
    }
  }
  factors.sequence = clamp(
    sequenceFactor,
    -Number(sequenceCfg.max_abs),
    Number(sequenceCfg.max_abs),
  );

  const situationCfg = config.situation;
  let situationFactor = 0;
  const runners = situation.runners ?? [false, false, false];
  if (runners[2] && situation.outs < 2) {
    const entry = situationCfg.runner_on_third_lt2;
    situationFactor += strike ? Number(entry.strike) : Number(entry.ball);
  }
  if (Math.trunc(situation.outs) === 2) {
    const entry = situationCfg.two_outs;
    situationFactor += strike ? Number(entry.strike) : Number(entry.ball);
  }
  const diff = Math.abs(Math.trunc(situation.scoreDiff || 0));
  if (diff <= 2 && Math.trunc(situation.inning) >= 7) {
    const entry = situationCfg.close_late;
    situationFactor += strike ? Number(entry.strike) : Number(entry.ball);
  }
  if (diff >= 5) {
    const entry = situationCfg.blowout;
    situationFactor += strike ? Number(entry.strike) : Number(entry.ball);
  }
  factors.situation = clamp(
    situationFactor,
    -Number(situationCfg.max_abs),
    Number(situationCfg.max_abs),
  );

  const approachCfg = config.approach;
  const mode = String(situation.approach || 'AUTO').toUpperCase();
  const entry = approachCfg[mode] ?? approachCfg.AUTO;
  let approachFactor =
    Number(entry.overall) + (strike ? Number(entry.strike) : Number(entry.ball));
  if (zone === 'waste') {
    approachFactor += Number(entry.waste);
  }
  factors.approach = clamp(
    approachFactor,
    -Number(approachCfg.max_abs),
    Number(approachCfg.max_abs),
  );

  const logit = baseLogit + Object.values(factors).reduce((a, b) => a + b, 0);
  const probability = clamp(
    sigmoid(logit),
    Number(config.bounds.min_probability),
    Number(config.bounds.max_probability),
  );

  return {
    willSwing: rng ? rng() < probability : false,
    probability,
    baseLogit,
    logit,
    factors,
    zoneClass: zone,
    countKey,
    modelVersion: String(config.model_version),
  };
}
