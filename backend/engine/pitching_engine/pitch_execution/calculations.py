"""
Pitching Execution Calculations & Statcast Math.
Calculates pitcher command sigma, bivariate Gaussian dispersion, radial miss distance,
and delivery execution metrics.
"""

import math
import random
from typing import Dict, Tuple, Any, Optional

from ...game_engine.gameday_math import (
    is_rulebook_strike,
    classify_gameday_zone,
    get_zone_nominal_target,
    calculate_execution_sigma,
    get_max_error_radius_inches,
    get_executed_radius_inches,
    sample_truncated_gaussian,
    sample_directional_dispersion,
    calculate_radial_miss_inches,
    determine_situation_category,
    ZONE_CENTERS,
    ZONE_X_MIN,
    ZONE_X_MAX,
    ZONE_Z_BOT,
    ZONE_Z_TOP,
)

try:
    from tiers import (
        AbilityTier,
        TimingTier,
        TIMING_MULTIPLIERS,
        BASELINE_TIMING_PROBABILITIES,
        TimingDict,
        AbilityDict,
        get_ability_tier,
    )
except ImportError:
    import sys
    from pathlib import Path
    root_path = str(Path(__file__).resolve().parents[4])
    if root_path not in sys.path:
        sys.path.insert(0, root_path)
    from tiers import (
        AbilityTier,
        TimingTier,
        TIMING_MULTIPLIERS,
        BASELINE_TIMING_PROBABILITIES,
        TimingDict,
        AbilityDict,
        get_ability_tier,
    )


def get_simulation_timing_distribution(
    ability_tier: Any,
    composure: float = 75.0,
    consistency: float = 75.0,
    pitch_count: int = 0,
    stamina: float = 75.0,
    fatigue_pct: Optional[float] = None,
    is_leverage: bool = False,
    effectiveness: Optional[float] = None,
) -> TimingDict:
    """
    Computes dynamically shifted TimingTier probability distribution:
    - Base probabilities derived from AbilityTier (Elite -> Poor).
    - Composure stress (is_leverage=True, low composure) shifts mass to OKAY and POOR.
    - Fatigue (high pitch count or fatigue_pct) shifts mass from PERFECT/GOOD to OKAY/POOR.
    - Consistency dampens the stress/fatigue degradation, suppressing collapse into POOR.
    - Pitch effectiveness (> 80 boosts PERFECT/GOOD; < 80 shifts mass to OKAY/POOR).
    Returns TimingDict summing to 1.00.
    """
    tier_key = ability_tier.value if hasattr(ability_tier, "value") else str(ability_tier)
    base_probs = BASELINE_TIMING_PROBABILITIES.get(tier_key.upper())
    if base_probs is None:
        base_probs = BASELINE_TIMING_PROBABILITIES.get("GOOD")

    p_P = float(base_probs["PERFECT"])
    p_G = float(base_probs["GOOD"])
    p_O = float(base_probs["OKAY"])
    p_X = float(base_probs["POOR"])

    # 1. Composure stress under leverage
    if is_leverage:
        comp_scale = max(0.0, (100.0 - float(composure)) / 100.0)
        stress_factor = comp_scale * 0.20
    else:
        stress_factor = 0.0

    # 2. Fatigue factor
    if fatigue_pct is not None:
        f_val = max(0.0, min(100.0, float(fatigue_pct)))
        fatigue_factor = (f_val / 100.0) * 0.20
    elif pitch_count <= 0:
        fatigue_factor = 0.0
    else:
        stam = max(1.0, float(stamina))
        thresh = stam * 0.75
        if pitch_count > thresh:
            overage = pitch_count - thresh
            fatigue_ratio = min(1.0, overage / max(1.0, stam * 0.6))
            fatigue_factor = fatigue_ratio * 0.20
        else:
            fatigue_factor = 0.0

    # 3. Consistency dampener: 0.15 (at cons=100) to 1.0 (at cons=0)
    cons = max(0.0, min(100.0, float(consistency)))
    cons_dampener = max(0.15, 1.0 - (cons / 100.0) * 0.85)

    # 4. Total probability shift
    delta = (stress_factor + fatigue_factor) * cons_dampener

    if delta > 0.0:
        delta_p = min(max(0.0, p_P - 0.01), delta * 0.55)
        delta_g = min(max(0.0, p_G - 0.05), delta * 0.45)
        delta_total = delta_p + delta_g

        # High consistency directs more towards OKAY and less to POOR
        poor_fraction = 0.15 + 0.55 * (1.0 - cons / 100.0)
        delta_poor = delta_total * poor_fraction
        delta_okay = delta_total * (1.0 - poor_fraction)

        p_P_new = max(0.0, p_P - delta_p)
        p_G_new = max(0.0, p_G - delta_g)
        p_O_new = p_O + delta_okay
        p_X_new = p_X + delta_poor
    else:
        p_P_new, p_G_new, p_O_new, p_X_new = p_P, p_G, p_O, p_X

    # Normalize to exactly 1.00
    total = p_P_new + p_G_new + p_O_new + p_X_new
    if total <= 0:
        total = 1.0
        p_P_new, p_G_new, p_O_new, p_X_new = p_P, p_G, p_O, p_X

    dist = TimingDict({
        "PERFECT": p_P_new / total,
        "GOOD": p_G_new / total,
        "OKAY": p_O_new / total,
        "POOR": p_X_new / total,
    })

    # 5. Pitch effectiveness modulation
    if effectiveness is not None:
        from ..pitch_effectiveness import adjust_simulation_timing_distribution
        dist_adjusted = adjust_simulation_timing_distribution(dist, effectiveness)
        return TimingDict(dist_adjusted)

    return dist


def sample_simulation_timing_tier(
    ability_tier: Any,
    composure: float = 75.0,
    consistency: float = 75.0,
    pitch_count: int = 0,
    stamina: float = 75.0,
    fatigue_pct: Optional[float] = None,
    is_leverage: bool = False,
    effectiveness: Optional[float] = None,
    rng: Optional[Any] = None,
) -> TimingTier:
    """Samples a TimingTier based on dynamic simulation distribution."""
    dist = get_simulation_timing_distribution(
        ability_tier=ability_tier,
        composure=composure,
        consistency=consistency,
        pitch_count=pitch_count,
        stamina=stamina,
        fatigue_pct=fatigue_pct,
        is_leverage=is_leverage,
        effectiveness=effectiveness,
    )
    rand_func = rng.random if (hasattr(rng, "random") and callable(rng.random)) else (rng if callable(rng) else random.random)
    u = rand_func()

    p_p = dist["PERFECT"]
    p_g = dist["GOOD"]
    p_o = dist["OKAY"]

    if u < p_p:
        return TimingTier.PERFECT
    elif u < p_p + p_g:
        return TimingTier.GOOD
    elif u < p_p + p_g + p_o:
        return TimingTier.OKAY
    else:
        return TimingTier.POOR


def roll_simulation_timing(
    ability_tier: Any,
    composure: float = 75.0,
    consistency: float = 75.0,
    fatigue_pct: float = 0.0,
    is_leverage: bool = False,
    rng: Optional[Any] = None,
    pitch_count: int = 0,
    stamina: float = 75.0,
    effectiveness: Optional[float] = None,
) -> Tuple[TimingTier, str]:
    """Rolls TimingTier for simulation mode and determines human-readable timing_label.
    Returns (timing_tier, timing_label).
    """
    tier = sample_simulation_timing_tier(
        ability_tier=ability_tier,
        composure=composure,
        consistency=consistency,
        pitch_count=pitch_count,
        stamina=stamina,
        fatigue_pct=fatigue_pct,
        is_leverage=is_leverage,
        effectiveness=effectiveness,
        rng=rng,
    )
    rand_func = rng.random if (hasattr(rng, "random") and callable(rng.random)) else (rng if callable(rng) else random.random)
    u = rand_func()

    if tier == TimingTier.PERFECT:
        label = "PERFECT!"
    elif tier == TimingTier.GOOD:
        label = "GOOD"
    elif tier == TimingTier.OKAY:
        label = "EARLY • OKAY" if u < 0.5 else "LATE • OKAY"
    else:  # POOR
        label = "EARLY • POOR" if u < 0.5 else "LATE • POOR"

    return tier, label


def calculate_pitch_delivery(
    target_x: float,
    target_z: float,
    command_rating: float,
    pitch_count: int,
    stamina: float = 75.0,
    intended_zone_cat: str = 'HEART',
    rng=None,
    precomputed_sigma: Optional[float] = None,
    precomputed_max_radius_in: Optional[float] = None,
    timing_tier: Optional[Any] = None,
    timing_label: Optional[str] = None,
    ability_tier: Optional[Any] = None,
    pitcher_hand: str = "R",
    pitch_type: str = "4SFB",
    composure: float = 75.0,
    consistency: float = 75.0,
    is_leverage: bool = False,
) -> Dict[str, Any]:
    """
    Computes pitch delivery execution factoring ability tier, release timing, and directional dispersion.
    Returns realized coordinates, execution error, zone classification, and miss metrics.
    """
    # 1. AbilityTier resolution
    if ability_tier is None:
        ability_tier = get_ability_tier(command_rating)
    ability_tier_str = ability_tier.value if hasattr(ability_tier, "value") else str(ability_tier)

    # 2. Handle zero-radius convergence (e.g. test_f4_b4 and practice mode)
    if precomputed_max_radius_in == 0.0 or precomputed_sigma == 0.0:
        timing_tier_str = (timing_tier.value if hasattr(timing_tier, "value") else str(timing_tier)) if timing_tier else "PERFECT"
        label_str = timing_label or "PERFECT!"
        realized_zone_cat = classify_gameday_zone(target_x, target_z)
        strike_check = is_rulebook_strike(target_x, target_z)
        return {
            'sigma': 0.0,
            'max_radius_inches': 0.0,
            'realized_x': float(target_x),
            'realized_z': float(target_z),
            'realized_zone_cat': realized_zone_cat,
            'is_strike': strike_check,
            'delta_x_in': 0.0,
            'delta_z_in': 0.0,
            'delta_x_inches': 0.0,
            'delta_z_inches': 0.0,
            'radial_miss_in': 0.0,
            'radial_miss_inches': 0.0,
            'is_heart_leak': False,
            'hit_shadow_target': intended_zone_cat == 'SHADOW' and realized_zone_cat == 'SHADOW',
            'effectiveness_score': 100.0,
            'pitch_effectiveness': 100.0,
            'timing_tier': timing_tier_str,
            'timing_label': label_str,
            'ability_tier': ability_tier_str,
            'base_radius_inches': 0.0,
            'executed_radius_inches': 0.0,
            'sigma_x_ft': 0.0,
            'sigma_z_ft': 0.0,
        }

    # 3. Resolve TimingTier and TimingLabel
    # When timing_tier is omitted, default to TimingTier.GOOD baseline execution
    if timing_tier is None:
        timing_tier = TimingTier.GOOD
        timing_label = "GOOD"

    timing_tier_str = timing_tier.value if hasattr(timing_tier, "value") else str(timing_tier)
    if timing_label is None:
        if timing_tier_str.upper() == "PERFECT":
            timing_label = "PERFECT!"
        elif timing_tier_str.upper() == "GOOD":
            timing_label = "GOOD"
        elif timing_tier_str.upper() == "OKAY":
            timing_label = "OKAY"
        else:
            timing_label = "POOR"

    # 4. Base and Executed Radius
    base_radius_in = precomputed_max_radius_in if precomputed_max_radius_in is not None else get_max_error_radius_inches(command_rating)
    executed_radius_in = get_executed_radius_inches(base_radius_in, timing_tier)
    executed_radius_ft = executed_radius_in / 12.0
    sigma_ft = precomputed_sigma if precomputed_sigma is not None else calculate_execution_sigma(command_rating, pitch_count, stamina=stamina)

    # 5. Sample Landing Coordinates
    if timing_tier_str.upper() == "GOOD" and timing_label.upper() == "GOOD":
        realized_x, realized_z = sample_truncated_gaussian(
            target_x, target_z, sigma_ft, executed_radius_ft, rng=rng
        )
        delta_x_in = (realized_x - target_x) * 12.0
        delta_z_in = (realized_z - target_z) * 12.0
        radial_miss_in = math.hypot(delta_x_in, delta_z_in)
    else:
        delta_x_in, delta_z_in, radial_miss_in = sample_directional_dispersion(
            executed_radius_inches=executed_radius_in,
            timing_tier=timing_tier,
            pitcher_hand=pitcher_hand,
            timing_label=timing_label,
            rng=rng,
        )
        realized_x = target_x + (delta_x_in / 12.0)
        realized_z = target_z + (delta_z_in / 12.0)

    # 6. Ray-based boundary projection for chase pitches outside strike zone:
    # Clamps along the miss ray to the perimeter without escaping executed_radius
    if (
        intended_zone_cat == 'CHASE'
        and not is_rulebook_strike(target_x, target_z)
        and is_rulebook_strike(realized_x, realized_z)
    ):
        dx = realized_x - target_x
        dz = realized_z - target_z
        t_enter = 1.0
        eps = 1e-4

        if dx > 0 and target_x < ZONE_X_MIN <= realized_x:
            t_enter = min(t_enter, max(0.0, (ZONE_X_MIN - eps - target_x) / dx))
        elif dx < 0 and target_x > ZONE_X_MAX >= realized_x:
            t_enter = min(t_enter, max(0.0, (ZONE_X_MAX + eps - target_x) / dx))

        if dz > 0 and target_z < ZONE_Z_BOT <= realized_z:
            t_enter = min(t_enter, max(0.0, (ZONE_Z_BOT - eps - target_z) / dz))
        elif dz < 0 and target_z > ZONE_Z_TOP >= realized_z:
            t_enter = min(t_enter, max(0.0, (ZONE_Z_TOP + eps - target_z) / dz))

        realized_x = target_x + t_enter * dx
        realized_z = target_z + t_enter * dz
        delta_x_in = (realized_x - target_x) * 12.0
        delta_z_in = (realized_z - target_z) * 12.0
        radial_miss_in = math.hypot(delta_x_in, delta_z_in)

    realized_zone_cat = classify_gameday_zone(realized_x, realized_z)
    strike_check = is_rulebook_strike(realized_x, realized_z)

    is_heart_leak = (intended_zone_cat != 'HEART') and (realized_zone_cat == 'HEART')
    hit_shadow_target = (intended_zone_cat == 'SHADOW') and (realized_zone_cat == 'SHADOW')

    location_score = max(10.0, 100.0 - (radial_miss_in * 7.5))
    effectiveness_score = round(0.6 * location_score + 0.4 * command_rating, 1)

    return {
        'sigma': sigma_ft,
        'sigma_x_ft': sigma_ft,
        'sigma_z_ft': sigma_ft,
        'max_radius_inches': executed_radius_in,
        'base_radius_inches': base_radius_in,
        'executed_radius_inches': executed_radius_in,
        'radial_miss_inches': radial_miss_in,
        'radial_miss_in': round(radial_miss_in, 1),
        'realized_x': realized_x,
        'realized_z': realized_z,
        'delta_x_inches': delta_x_in,
        'delta_z_inches': delta_z_in,
        'delta_x_in': round(delta_x_in, 1),
        'delta_z_in': round(delta_z_in, 1),
        'realized_zone_cat': realized_zone_cat,
        'is_strike': strike_check,
        'is_heart_leak': is_heart_leak,
        'hit_shadow_target': hit_shadow_target,
        'effectiveness_score': effectiveness_score,
        'pitch_effectiveness': effectiveness_score,
        'ability_tier': ability_tier_str,
        'timing_tier': timing_tier_str,
        'timing_label': timing_label,
    }

