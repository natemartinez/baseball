"""
Pitcher Effectiveness Engine — Physical Pitch Quality & Stuff Tracking.

Effectiveness is distinct from Confidence:
- Confidence: Psychological state governing command accuracy (error dispersion circle).
- Effectiveness: Physical pitch quality (bite, movement sharpness, deception) governing
  batter whiff probability and exit velocity suppression.

Effectiveness is pitch-specific (not holistic) and starts at the pitch's baseline
stuff rating derived from velocity, movement break, and spin.

Ineffectiveness Drivers (physical degradation):
1. Hard contact allowed — batters are squaring the pitch up (seeing it well).
2. Stamina/fatigue — pitch flattens out, loses break and bite.
3. Severe low confidence drag — secondary coupling (mental → physical, minor).

Recovery Drivers:
1. Whiff/strikeout — pitch has good bite and is fooling batters.
2. Weak contact (popout/groundout) — pitch is inducing weak contact.
"""

from typing import Dict, List, Optional, Tuple

# ─── Constants ────────────────────────────────────────────────────────────────

NEUTRAL_EFFECTIVENESS = 50.0   # Used for normalization reference only
MIN_EFFECTIVENESS = 0.0
MAX_EFFECTIVENESS = 100.0

# Stamina fatigue drag constants
FATIGUE_EFFECTIVENESS_MAX_PENALTY = 15.0  # Max effectiveness drop from pure fatigue (at 0% stamina)

# Confidence coupling: severely low confidence causes minor physical drag
# (e.g., pitcher loses feel for break when mentally shaken)
CONFIDENCE_DRAG_THRESHOLD = 25.0  # Below 25% confidence, coupling activates
CONFIDENCE_DRAG_MAX = 5.0         # Max physical effectiveness drag from low confidence


def compute_baseline_effectiveness(
    velocity_mph: float,
    break_rating: float,
    spin_rpm: int,
    command: float = 75.0,
) -> float:
    """
    Computes a pitch's starting effectiveness from its physical stuff attributes.

    Formula weights:
    - Break rating (40%): Primary driver of pitch "bite" and deception.
    - Velocity (25%): Raw power contributes to effectiveness.
    - Spin rate (20%): High spin creates sharper movement.
    - Command (15%): Better command pitchers execute their stuff more consistently.

    Returns a value in [70.0, 95.0] — elite pitches start higher, secondary pitches lower.
    """
    # Normalize each component to a 0–100 scale
    velo_score = min(100.0, max(0.0, (float(velocity_mph) - 80.0) / (102.0 - 80.0) * 100.0))
    break_score = min(100.0, max(0.0, float(break_rating)))
    spin_score = min(100.0, max(0.0, (float(spin_rpm) - 1800.0) / (3500.0 - 1800.0) * 100.0))
    cmd_score = min(100.0, max(0.0, float(command)))

    raw = (
        0.40 * break_score
        + 0.25 * velo_score
        + 0.20 * spin_score
        + 0.15 * cmd_score
    )

    # Scale to [70.0, 95.0] range so pitches start in a realistic "good-to-elite" band
    baseline = 70.0 + (raw / 100.0) * 25.0
    return round(min(MAX_EFFECTIVENESS, max(70.0, baseline)), 2)


def calculate_effectiveness_delta(
    pitch_result: str,
    current_stamina_pct: float = 100.0,
    pitch_confidence: Optional[float] = None,
) -> float:
    """
    Calculates the delta to apply to a pitch's effectiveness based on the pitch outcome.

    Hard contact (batters squaring it up) degrades effectiveness.
    Whiffs and weak contact (outs) recover effectiveness.
    Stamina is applied as a multiplicative drag on any positive recovery
    (tired pitchers recover effectiveness more slowly).

    Args:
        pitch_result: The pitch outcome string (HOME_RUN, SINGLE, SWINGING_STRIKE, etc.)
        current_stamina_pct: Pitcher stamina from 0-100 (for fatigue-modified recovery scaling).
        pitch_confidence: Current pitch confidence 0-100 (for optional low-conf drag coupling).

    Returns:
        float: Delta to add to current effectiveness (can be negative).
    """
    result = str(pitch_result or '').upper()

    # ── Hard Contact: Batters are seeing the pitch well ─────────────────────
    # Primary degradation signal: batters square it up → pitch has less bite.
    if result == 'HOME_RUN':
        base_delta = -14.0   # Pitch was crushed — clearly hittable
    elif result == 'TRIPLE':
        base_delta = -10.0
    elif result == 'DOUBLE':
        base_delta = -7.0
    elif result == 'SINGLE':
        base_delta = -4.0
    elif result == 'HIT_BY_PITCH':
        # HBP is a command failure, not a pure effectiveness signal — mild dip
        base_delta = -2.0

    # ── Recovery: Pitch has good bite / fools batters ─────────────────────
    elif result == 'SWINGING_STRIKE':
        # Pure whiff — pitch has maximum bite
        base_delta = +5.0
    elif result == 'IN_PLAY_OUT':
        # Induced weak contact — pitch is effective
        base_delta = +3.5
    elif result == 'CALLED_STRIKE':
        # Painted corner or sharp movement — mild effectiveness signal
        base_delta = +1.5
    elif result == 'FOUL':
        # Batter made contact but couldn't square it — slight positive
        base_delta = +0.5
    elif result == 'BALL':
        # Missed location — no direct effectiveness signal (slight location noise)
        base_delta = -0.5
    else:
        base_delta = 0.0

    # ── Stamina Fatigue Drag on Recovery ──────────────────────────────────
    # Tired pitchers recover effectiveness more slowly (their stuff doesn't bounce back as fast)
    stamina = max(0.0, min(100.0, float(current_stamina_pct)))
    if base_delta > 0.0:
        # Recovery is scaled by stamina: full recovery at 100%, half at 50%, none near 0%
        stamina_multiplier = max(0.3, stamina / 100.0)
        base_delta = base_delta * stamina_multiplier

    # ── Low Confidence Secondary Drag ──────────────────────────────────────
    # When confidence is severely low, a minor physical drag couples in
    # (pitcher loses feel for the pitch's movement when mentally shaken)
    if pitch_confidence is not None:
        conf = max(0.0, min(100.0, float(pitch_confidence)))
        if conf < CONFIDENCE_DRAG_THRESHOLD:
            drag_scale = (CONFIDENCE_DRAG_THRESHOLD - conf) / CONFIDENCE_DRAG_THRESHOLD
            confidence_drag = -drag_scale * CONFIDENCE_DRAG_MAX
            base_delta = base_delta + confidence_drag

    return round(base_delta, 2)


def apply_stamina_fatigue_to_effectiveness(
    current_effectiveness: float,
    current_stamina_pct: float,
    baseline_effectiveness: float,
) -> float:
    """
    Applies a stamina-based fatigue floor: as stamina drops, a pitch's effectiveness
    is pulled toward a lower fatigue-degraded floor proportional to its baseline.

    This is applied passively each pitch (independent of outcome) and represents
    the pitch physically flattening out as the pitcher tires.

    At 100% stamina: no fatigue floor reduction.
    At 0% stamina: effectiveness floor = baseline - MAX_FATIGUE_PENALTY.
    """
    stamina = max(0.0, min(100.0, float(current_stamina_pct)))
    fatigue_factor = 1.0 - (stamina / 100.0)  # 0 at full stamina, 1 at empty
    fatigue_floor = baseline_effectiveness - (fatigue_factor * FATIGUE_EFFECTIVENESS_MAX_PENALTY)
    fatigue_floor = max(MIN_EFFECTIVENESS, fatigue_floor)

    # If current effectiveness is above the fatigue floor, push it down slightly
    if current_effectiveness > fatigue_floor:
        # Gentle pull toward the floor (not a hard snap)
        pull = (current_effectiveness - fatigue_floor) * 0.05 * fatigue_factor
        return round(max(fatigue_floor, current_effectiveness - pull), 2)
    return round(current_effectiveness, 2)


def update_pitch_effectiveness(
    current_effectiveness: float,
    pitch_result: str,
    current_stamina_pct: float = 100.0,
    pitch_confidence: Optional[float] = None,
    baseline_effectiveness: float = 80.0,
) -> float:
    """
    Full effectiveness update for a single pitch: applies outcome delta,
    stamina fatigue pull, and clamps to valid range.

    Returns: new effectiveness value clamped to [MIN_EFFECTIVENESS, MAX_EFFECTIVENESS].
    """
    # 1. Outcome-based delta
    delta = calculate_effectiveness_delta(
        pitch_result=pitch_result,
        current_stamina_pct=current_stamina_pct,
        pitch_confidence=pitch_confidence,
    )
    new_val = current_effectiveness + delta

    # 2. Passive stamina fatigue floor pull
    new_val = apply_stamina_fatigue_to_effectiveness(
        current_effectiveness=new_val,
        current_stamina_pct=current_stamina_pct,
        baseline_effectiveness=baseline_effectiveness,
    )

    # 3. Clamp
    return max(MIN_EFFECTIVENESS, min(MAX_EFFECTIVENESS, round(new_val, 2)))


def apply_effectiveness_to_whiff_rate(
    base_whiff_prob: float,
    pitch_effectiveness: float,
) -> float:
    """
    Adjusts a base whiff probability using current pitch effectiveness.

    At effectiveness == 80 (neutral baseline): no adjustment.
    At effectiveness > 80: whiff rate increases (sharper stuff).
    At effectiveness < 80: whiff rate decreases (flat stuff is easier to hit).

    Scale: ±0.0015 per effectiveness point from 80, capped at ±0.12.
    """
    neutral = 80.0
    effectiveness = max(MIN_EFFECTIVENESS, min(MAX_EFFECTIVENESS, float(pitch_effectiveness)))
    delta = (effectiveness - neutral) * 0.0015
    delta = max(-0.12, min(0.12, delta))
    return max(0.05, min(0.80, base_whiff_prob + delta))


def apply_effectiveness_to_exit_velocity(
    base_exit_velocity: float,
    pitch_effectiveness: float,
) -> float:
    """
    Adjusts mean exit velocity based on pitch effectiveness.

    High effectiveness (good bite) → suppresses exit velocity (batters make weak contact).
    Low effectiveness (flat pitch) → boosts exit velocity (batters square it up easily).

    At effectiveness == 80 (neutral): no adjustment.
    At effectiveness < 80: exit velocity increases by up to +4.5 mph at 0% effectiveness.
    At effectiveness > 80: exit velocity decreases by up to -3.0 mph at 100% effectiveness.

    Scale: 0.225 mph per point below 80, 0.15 mph per point above 80.
    """
    neutral = 80.0
    effectiveness = max(MIN_EFFECTIVENESS, min(MAX_EFFECTIVENESS, float(pitch_effectiveness)))
    if effectiveness < neutral:
        ev_adj = (neutral - effectiveness) * 0.225    # Flatter pitch → harder contact
    else:
        ev_adj = -(effectiveness - neutral) * 0.15    # Sharper stuff → weaker contact

    return round(float(base_exit_velocity) + ev_adj, 1)


def calculate_command_adjustment_from_effectiveness(effectiveness: float) -> float:
    """
    Calculates command modifier from a pitch's physical effectiveness.
    Baseline neutral is 80.0 (0.0 adjustment).

    - Higher effectiveness (sharp stuff / great feel) boosts command:
      e.g., at 90.0 effectiveness: +6.0 command; at 100.0: +12.0 command.
    - Lower effectiveness (flattening pitch / losing stuff) degrades command:
      e.g., at 75.0 effectiveness: -3.75 command; at 60.0: -15.0; at 40.0: -30.0.

    Scale:
      - Above 80: +0.60 command points per effectiveness point.
      - Below 80: -0.75 command points per effectiveness point, capped at -30.0.
    """
    eff = max(MIN_EFFECTIVENESS, min(MAX_EFFECTIVENESS, float(effectiveness)))
    if eff >= 80.0:
        return round((eff - 80.0) * 0.60, 2)
    else:
        penalty = (80.0 - eff) * 0.75
        return round(-min(30.0, penalty), 2)


def apply_effectiveness_to_velocity(base_velocity: float, pitch_effectiveness: float) -> float:
    """
    Scales pitch release velocity based on pitch effectiveness.
    - At 80.0 (neutral baseline): no velocity change.
    - At > 80.0: consistent higher velocity (up to +2.5 mph).
      e.g., at 90.0: +1.25 mph; at 100.0: +2.5 mph.
    - At < 80.0: losing velocity (down to -6.0 mph).
      e.g., at 75.0: -1.25 mph; at 60.0: -4.0 mph.
    """
    eff = max(MIN_EFFECTIVENESS, min(MAX_EFFECTIVENESS, float(pitch_effectiveness)))
    if eff >= 80.0:
        velo_adj = ((eff - 80.0) / 20.0) * 2.5
    else:
        velo_adj = -((80.0 - eff) / 20.0) * 5.0
    return round(float(base_velocity) + velo_adj, 1)


def apply_effectiveness_to_break(
    horizontal_break_in: float,
    induced_vertical_break_in: float,
    pitch_effectiveness: float,
) -> Tuple[float, float]:
    """
    Scales physical pitch break ('bite') based on pitch effectiveness.
    - At 80.0: neutral multiplier 1.0.
    - At > 80.0: sharper bite / increased break (up to +15% at 100 effectiveness).
      e.g., at 90.0: 1.075x (+7.5% break).
    - At < 80.0: flatter pitch / reduced bite (down to -35% at 40 effectiveness).
      e.g., at 75.0: 0.95x (-5% break); at 60.0: 0.825x (-17.5% break).
    """
    eff = max(MIN_EFFECTIVENESS, min(MAX_EFFECTIVENESS, float(pitch_effectiveness)))
    if eff >= 80.0:
        multiplier = 1.0 + ((eff - 80.0) / 20.0) * 0.15
    else:
        multiplier = 1.0 - ((80.0 - eff) / 80.0) * 0.40
    multiplier = max(0.50, min(1.25, multiplier))
    hb = round(float(horizontal_break_in) * multiplier, 2)
    ivb = round(float(induced_vertical_break_in) * multiplier, 2)
    return hb, ivb


def adjust_simulation_timing_distribution(
    dist: Dict[str, float],
    effectiveness: float,
) -> Dict[str, float]:
    """
    Adjusts simulation TimingTier probability distribution according to pitch effectiveness:
    - Effectiveness > 80: shifts probability mass into PERFECT and GOOD (sharper command, easier execution).
    - Effectiveness < 80: shifts probability mass away from PERFECT and GOOD into OKAY and POOR.
    Returns normalized distribution summing to 1.00.
    """
    eff = max(MIN_EFFECTIVENESS, min(MAX_EFFECTIVENESS, float(effectiveness)))
    p_P = float(dist.get("PERFECT", 0.0))
    p_G = float(dist.get("GOOD", 0.0))
    p_O = float(dist.get("OKAY", 0.0))
    p_X = float(dist.get("POOR", 0.0))

    if eff > 80.0:
        # Scale 0.0 at 80 to 1.0 at 100
        scale = (eff - 80.0) / 20.0
        delta_p = min(p_O * 0.35, scale * 0.06)
        delta_g = min(p_O * 0.35, scale * 0.05)
        delta_okay = delta_p + delta_g * 0.6
        delta_poor = delta_g * 0.4

        p_P_new = p_P + delta_p
        p_G_new = p_G + delta_g
        p_O_new = max(0.01, p_O - delta_okay)
        p_X_new = max(0.01, p_X - delta_poor)
    elif eff < 80.0:
        # Scale 0.0 at 80 to 1.0 at 0
        scale = (80.0 - eff) / 80.0
        # Noticeable shift: up to 0.30 total shift at 0 eff, ~0.04 at 75 eff
        shift = min(0.35, (80.0 - eff) * 0.008)
        delta_p = min(max(0.0, p_P - 0.02), shift * 0.55)
        delta_g = min(max(0.0, p_G - 0.04), shift * 0.45)
        delta_total = delta_p + delta_g

        p_P_new = max(0.01, p_P - delta_p)
        p_G_new = max(0.02, p_G - delta_g)
        p_O_new = p_O + delta_total * 0.60
        p_X_new = p_X + delta_total * 0.40
    else:
        p_P_new, p_G_new, p_O_new, p_X_new = p_P, p_G, p_O, p_X

    total = p_P_new + p_G_new + p_O_new + p_X_new
    if total <= 0:
        total = 1.0
    return {
        "PERFECT": round(p_P_new / total, 4),
        "GOOD": round(p_G_new / total, 4),
        "OKAY": round(p_O_new / total, 4),
        "POOR": round(p_X_new / total, 4),
    }

