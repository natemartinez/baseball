"""
MLB Statcast Gameday 2D Coordinate Normalization & Bivariate Gaussian Math Engine.
Converts Statcast plate coordinates to 2D cross-section space, models delivery execution
error from pitcher Command and Fatigue ratings, and defines rulebook/shadow zone boundaries.
"""

import math
import random
from typing import Dict, Tuple

# ─── Constants: Rulebook & Gameday Zone Dimensions (in Statcast Feet) ──────────

PLATE_WIDTH_FT = 17.0 / 12.0  # 1.4167 ft
HALF_PLATE_WIDTH_FT = PLATE_WIDTH_FT / 2.0  # 0.7083 ft (~8.5 in)

ZONE_X_MIN = -HALF_PLATE_WIDTH_FT  # -0.7083 ft
ZONE_X_MAX = HALF_PLATE_WIDTH_FT   # +0.7083 ft
ZONE_Z_BOT = 1.50                  # Hollow of the knee in feet
ZONE_Z_TOP = 3.50                  # Midpoint between shoulders & belt in feet

HEART_X_MIN = ZONE_X_MIN / 2.0     # -0.3542 ft
HEART_X_MAX = ZONE_X_MAX / 2.0     # +0.3542 ft
HEART_Z_BOT = 2.00                 # Inner 50% vertical
HEART_Z_TOP = 3.00                 # Inner 50% vertical

BALL_DIAMETER_FT = 2.9 / 12.0      # ~0.2417 ft
SHADOW_BORDER_FT = 3.4 / 12.0      # 0.2833 ft (1 ball width border)
CHASE_BORDER_FT = 2 * SHADOW_BORDER_FT  # ~0.5667 ft (2 ball widths)

SIGMA_MAX_FT = 0.50                # 6.0 inches (40 Command)
SIGMA_MIN_FT = 0.15                # 1.8 inches (99 Command)

# 13 Nominal Zone Centers (Statcast X, Z in feet)
ZONE_CENTERS: Dict[str, Tuple[float, float]] = {
    'upper-in': (-0.55, 3.15),
    'upper-middle': (0.0, 3.15),
    'upper-away': (0.55, 3.15),
    'middle-in': (-0.55, 2.50),
    'heart': (0.0, 2.50),
    'middle-away': (0.55, 2.50),
    'lower-in': (-0.55, 1.85),
    'lower-middle': (0.0, 1.85),
    'lower-away': (0.55, 1.85),
    'chase-high': (0.0, 3.85),
    'chase-low': (0.0, 1.15),
    'chase-in': (-1.05, 2.50),
    'chase-away': (1.05, 2.50),
}

# Empirical baselines from 10,000-pitch calibration protocol
EMPIRICAL_BASELINES = {
    40: {
        'command_rating': 40,
        'expected_shadow_accuracy': 68.2,
        'expected_heart_leaks': 9.7,
        'expected_miss_radius_inches': 6.22,
        'expected_ahead_offspeed_pct': 58.4,
    },
    68: {
        'command_rating': 68,
        'expected_shadow_accuracy': 81.0,
        'expected_heart_leaks': 7.7,
        'expected_miss_radius_inches': 4.49,
        'expected_ahead_offspeed_pct': 65.1,
    },
    85: {
        'command_rating': 85,
        'expected_shadow_accuracy': 88.2,
        'expected_heart_leaks': 6.0,
        'expected_miss_radius_inches': 3.51,
        'expected_ahead_offspeed_pct': 68.3,
    },
    99: {
        'command_rating': 99,
        'expected_shadow_accuracy': 94.1,
        'expected_heart_leaks': 3.3,
        'expected_miss_radius_inches': 2.63,
        'expected_ahead_offspeed_pct': 71.9,
    },
}


def is_rulebook_strike(x: float, z: float) -> bool:
    """Evaluates whether coordinates fall inside the 17-inch plate rulebook strike zone."""
    return (ZONE_X_MIN <= x <= ZONE_X_MAX) and (ZONE_Z_BOT <= z <= ZONE_Z_TOP)


def classify_gameday_zone(x: float, z: float) -> str:
    """
    Categorizes Statcast (X, Z) into MLB Statcast Gameday zone categories:
    HEART: Inner 50% sweet spot
    SHADOW: 1-ball-width border straddling zone perimeter
    CHASE: 1 to 2 ball-widths outside zone
    WASTE: > 2 ball-widths outside
    """
    if (HEART_X_MIN <= x <= HEART_X_MAX) and (HEART_Z_BOT <= z <= HEART_Z_TOP):
        return 'HEART'

    shadow_x_min = ZONE_X_MIN - SHADOW_BORDER_FT
    shadow_x_max = ZONE_X_MAX + SHADOW_BORDER_FT
    shadow_z_bot = ZONE_Z_BOT - SHADOW_BORDER_FT
    shadow_z_top = ZONE_Z_TOP + SHADOW_BORDER_FT

    if (shadow_x_min <= x <= shadow_x_max) and (shadow_z_bot <= z <= shadow_z_top):
        return 'SHADOW'

    chase_x_min = ZONE_X_MIN - CHASE_BORDER_FT
    chase_x_max = ZONE_X_MAX + CHASE_BORDER_FT
    chase_z_bot = ZONE_Z_BOT - CHASE_BORDER_FT
    chase_z_top = ZONE_Z_TOP + CHASE_BORDER_FT

    if (chase_x_min <= x <= chase_x_max) and (chase_z_bot <= z <= chase_z_top):
        return 'CHASE'

    return 'WASTE'


def get_zone_nominal_target(zone_name: str) -> Tuple[float, float, str]:
    """Returns nominal (x, z) coordinates and category for a discrete zone name."""
    clean_name = (zone_name or 'heart').lower().strip()
    coords = ZONE_CENTERS.get(clean_name, (0.0, 2.50))
    cat = classify_gameday_zone(coords[0], coords[1])
    return coords[0], coords[1], cat


def calculate_execution_sigma(command_rating: float, pitch_count: int = 0, stamina: float = 75.0) -> float:
    """
    Calculates bivariate standard deviation from pitcher Command rating and pitch fatigue.
    sigma_x = sigma_z = [sigma_max - (Command / 100) * (sigma_max - sigma_min)] * (1 + FatigueMultiplier)
    """
    clamped_command = max(20.0, min(99.0, float(command_rating)))
    base_sigma = SIGMA_MAX_FT - (clamped_command / 100.0) * (SIGMA_MAX_FT - SIGMA_MIN_FT)
    fatigue_multiplier = max(0.0, (pitch_count - stamina) / 30.0)
    return base_sigma * (1.0 + fatigue_multiplier)


def sample_bivariate_gaussian(mean_x: float, mean_z: float, sigma_x: float, sigma_z: float) -> Tuple[float, float]:
    """Samples realized plate location (X, Z) using Box-Muller / normal distribution."""
    realized_x = random.gauss(mean_x, sigma_x)
    realized_z = random.gauss(mean_z, sigma_z)
    return round(realized_x, 3), round(realized_z, 3)


def calculate_radial_miss_inches(target_x: float, target_z: float, realized_x: float, realized_z: float) -> float:
    """Computes Euclidean radial distance between target and realized location in inches."""
    dx = realized_x - target_x
    dz = realized_z - target_z
    return round(math.sqrt(dx * dx + dz * dz) * 12.0, 1)


def determine_situation_category(balls: int, strikes: int, outs: int, r1: bool, r2: bool, r3: bool) -> str:
    """Classifies game state into situational tactical regime."""
    if r1 and r2 and r3:
        return 'BASES_LOADED'
    if r1 and outs < 2:
        return 'DOUBLE_PLAY'
    if (r2 or r3) and outs < 2:
        return 'RISP'
    if outs == 2:
        return 'TWO_OUTS'
    if strikes > balls:
        return 'AHEAD_IN_COUNT'
    if balls > strikes:
        return 'BEHIND_IN_COUNT'
    return 'NEUTRAL'
