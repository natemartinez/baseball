"""
Pitching Execution Calculations & Statcast Math.
Calculates pitcher command sigma, bivariate Gaussian dispersion, radial miss distance,
and delivery execution metrics.
"""

import math
import random
from typing import Dict, Tuple, Any

try:
    from backend.engine.gameday_math import (
        is_rulebook_strike,
        classify_gameday_zone,
        get_zone_nominal_target,
        calculate_execution_sigma,
        sample_bivariate_gaussian,
        calculate_radial_miss_inches,
        determine_situation_category,
        ZONE_CENTERS,
    )
except ImportError:
    from gameday_math import (
        is_rulebook_strike,
        classify_gameday_zone,
        get_zone_nominal_target,
        calculate_execution_sigma,
        sample_bivariate_gaussian,
        calculate_radial_miss_inches,
        determine_situation_category,
        ZONE_CENTERS,
    )


def calculate_pitch_delivery(
    target_x: float,
    target_z: float,
    command_rating: float,
    pitch_count: int,
    stamina: float = 75.0,
    intended_zone_cat: str = 'HEART'
) -> Dict[str, Any]:
    """
    Computes the bivariate Gaussian dispersion for a pitch delivery.
    Returns realized coordinates, execution error, zone classification, and miss metrics.
    """
    sigma = calculate_execution_sigma(command_rating, pitch_count, stamina=stamina)
    realized_x, realized_z = sample_bivariate_gaussian(target_x, target_z, sigma, sigma)
    realized_zone_cat = classify_gameday_zone(realized_x, realized_z)
    strike_check = is_rulebook_strike(realized_x, realized_z)

    delta_x_in = round((realized_x - target_x) * 12.0, 1)
    delta_z_in = round((realized_z - target_z) * 12.0, 1)
    radial_miss_in = calculate_radial_miss_inches(target_x, target_z, realized_x, realized_z)
    is_heart_leak = (intended_zone_cat != 'HEART') and (realized_zone_cat == 'HEART')
    hit_shadow_target = (intended_zone_cat == 'SHADOW') and (realized_zone_cat == 'SHADOW')

    # Pitch effectiveness score (0-100 scale based on command, location accuracy, and stuff)
    # Lower radial miss yields higher score
    location_score = max(10.0, 100.0 - (radial_miss_in * 7.5))
    effectiveness_score = round(0.6 * location_score + 0.4 * command_rating, 1)

    return {
        'sigma': sigma,
        'realized_x': round(realized_x, 4),
        'realized_z': round(realized_z, 4),
        'realized_zone_cat': realized_zone_cat,
        'is_strike': strike_check,
        'delta_x_in': delta_x_in,
        'delta_z_in': delta_z_in,
        'radial_miss_in': radial_miss_in,
        'is_heart_leak': is_heart_leak,
        'hit_shadow_target': hit_shadow_target,
        'effectiveness_score': effectiveness_score,
    }
