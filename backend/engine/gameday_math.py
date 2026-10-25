"""
MLB Statcast Gameday 2D Coordinate Normalization & Spray-Cloud Math Engine.
Converts Statcast plate coordinates to 2D cross-section space, models delivery execution
error from pitcher Command with a truncated Gaussian cloud, and defines rulebook/shadow
zone boundaries.
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

# Fatigue is intentionally disabled while the spray-cloud model is validated.
# Future: enable growth once the pitcher reaches ~75 pitches or low stamina.
FATIGUE_ENABLED = False

# Command -> hard maximum error radius (inches). Diameter = 2 * radius.
# Interpolate linearly between tiers and clamp outside the range.
MAX_ERROR_RADIUS_TIERS: list = [
    (99.0, 1.00),
    (90.0, 1.25),
    (82.0, 1.50),
    (68.0, 3.00),
    (55.0, 4.50),
    (40.0, 7.00),
]

# The cloud is a truncated Gaussian; sigma = radius / SIGMA_RADIUS_DIVISOR.
SIGMA_RADIUS_DIVISOR = 2.5

# 13 Nominal Zone Centers (Statcast X, Z in feet). These are display/label
# anchors only; pitch aims are sampled across the zone bounds below.
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

# Aim regions for each discrete zone: (x_min, x_max, z_min, z_max) in feet.
# The 9 inner regions partition the full rulebook rectangle into equal thirds
# so a sampled aim can be anywhere inside it, including the exact edges. Chase
# regions sit strictly outside the shadow band so they classify as CHASE.
_INNER_COL_WIDTH_FT = (ZONE_X_MAX - ZONE_X_MIN) / 3.0
_INNER_ROW_HEIGHT_FT = (ZONE_Z_TOP - ZONE_Z_BOT) / 3.0
_CHASE_INNER_INSET_FT = 1e-6

ZONE_TARGET_BOUNDS: Dict[str, Tuple[float, float, float, float]] = {
    'upper-in': (
        ZONE_X_MIN,
        ZONE_X_MIN + _INNER_COL_WIDTH_FT,
        ZONE_Z_TOP - _INNER_ROW_HEIGHT_FT,
        ZONE_Z_TOP,
    ),
    'upper-middle': (
        ZONE_X_MIN + _INNER_COL_WIDTH_FT,
        ZONE_X_MAX - _INNER_COL_WIDTH_FT,
        ZONE_Z_TOP - _INNER_ROW_HEIGHT_FT,
        ZONE_Z_TOP,
    ),
    'upper-away': (
        ZONE_X_MAX - _INNER_COL_WIDTH_FT,
        ZONE_X_MAX,
        ZONE_Z_TOP - _INNER_ROW_HEIGHT_FT,
        ZONE_Z_TOP,
    ),
    'middle-in': (
        ZONE_X_MIN,
        ZONE_X_MIN + _INNER_COL_WIDTH_FT,
        ZONE_Z_BOT + _INNER_ROW_HEIGHT_FT,
        ZONE_Z_TOP - _INNER_ROW_HEIGHT_FT,
    ),
    'heart': (
        ZONE_X_MIN + _INNER_COL_WIDTH_FT,
        ZONE_X_MAX - _INNER_COL_WIDTH_FT,
        ZONE_Z_BOT + _INNER_ROW_HEIGHT_FT,
        ZONE_Z_TOP - _INNER_ROW_HEIGHT_FT,
    ),
    'middle-away': (
        ZONE_X_MAX - _INNER_COL_WIDTH_FT,
        ZONE_X_MAX,
        ZONE_Z_BOT + _INNER_ROW_HEIGHT_FT,
        ZONE_Z_TOP - _INNER_ROW_HEIGHT_FT,
    ),
    'lower-in': (
        ZONE_X_MIN,
        ZONE_X_MIN + _INNER_COL_WIDTH_FT,
        ZONE_Z_BOT,
        ZONE_Z_BOT + _INNER_ROW_HEIGHT_FT,
    ),
    'lower-middle': (
        ZONE_X_MIN + _INNER_COL_WIDTH_FT,
        ZONE_X_MAX - _INNER_COL_WIDTH_FT,
        ZONE_Z_BOT,
        ZONE_Z_BOT + _INNER_ROW_HEIGHT_FT,
    ),
    'lower-away': (
        ZONE_X_MAX - _INNER_COL_WIDTH_FT,
        ZONE_X_MAX,
        ZONE_Z_BOT,
        ZONE_Z_BOT + _INNER_ROW_HEIGHT_FT,
    ),
    'chase-high': (
        ZONE_X_MIN,
        ZONE_X_MAX,
        ZONE_Z_TOP + SHADOW_BORDER_FT + _CHASE_INNER_INSET_FT,
        ZONE_Z_TOP + CHASE_BORDER_FT,
    ),
    'chase-low': (
        ZONE_X_MIN,
        ZONE_X_MAX,
        ZONE_Z_BOT - CHASE_BORDER_FT,
        ZONE_Z_BOT - SHADOW_BORDER_FT - _CHASE_INNER_INSET_FT,
    ),
    'chase-in': (
        ZONE_X_MIN - CHASE_BORDER_FT,
        ZONE_X_MIN - SHADOW_BORDER_FT - _CHASE_INNER_INSET_FT,
        ZONE_Z_BOT,
        ZONE_Z_TOP,
    ),
    'chase-away': (
        ZONE_X_MAX + SHADOW_BORDER_FT + _CHASE_INNER_INSET_FT,
        ZONE_X_MAX + CHASE_BORDER_FT,
        ZONE_Z_BOT,
        ZONE_Z_TOP,
    ),
}

# Empirical baselines from 10,000-pitch calibration protocol
EMPIRICAL_BASELINES = {
    40: {
        'command_rating': 40,
        'expected_shadow_accuracy': 80.8,
        'expected_heart_leaks': 14.9,
        'expected_miss_radius_inches': 3.29,
        'expected_ahead_offspeed_pct': 58.4,
    },
    55: {
        'command_rating': 55,
        'expected_shadow_accuracy': 84.1,
        'expected_heart_leaks': 13.0,
        'expected_miss_radius_inches': 2.12,
        'expected_ahead_offspeed_pct': 61.5,
    },
    68: {
        'command_rating': 68,
        'expected_shadow_accuracy': 86.1,
        'expected_heart_leaks': 11.4,
        'expected_miss_radius_inches': 1.42,
        'expected_ahead_offspeed_pct': 65.1,
    },
    82: {
        'command_rating': 82,
        'expected_shadow_accuracy': 92.5,
        'expected_heart_leaks': 6.15,
        'expected_miss_radius_inches': 0.71,
        'expected_ahead_offspeed_pct': 67.5,
    },
    85: {
        'command_rating': 85,
        'expected_shadow_accuracy': 93.1,
        'expected_heart_leaks': 5.66,
        'expected_miss_radius_inches': 0.66,
        'expected_ahead_offspeed_pct': 68.3,
    },
    90: {
        'command_rating': 90,
        'expected_shadow_accuracy': 94.6,
        'expected_heart_leaks': 4.44,
        'expected_miss_radius_inches': 0.59,
        'expected_ahead_offspeed_pct': 69.9,
    },
    99: {
        'command_rating': 99,
        'expected_shadow_accuracy': 96.8,
        'expected_heart_leaks': 2.63,
        'expected_miss_radius_inches': 0.47,
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


def nearest_zone_name(is_strike: bool, x: float, z: float) -> str:
    """
    Returns the closest 13-zone label constrained to the realized side of the
    plate. A strike can only be labeled with an inner zone and a ball can only
    be labeled with a chase zone, so a pitch just off the corner never inherits
    an inner-corner strike label.
    """
    candidates = [
        name
        for name in ZONE_CENTERS
        if name.startswith('chase-') != bool(is_strike)
    ]
    if not candidates:
        return 'heart'

    best = candidates[0]
    min_dist = float('inf')
    for name in candidates:
        zx, zz = ZONE_CENTERS[name]
        dist = (zx - x) ** 2 + (zz - z) ** 2
        if dist < min_dist:
            min_dist = dist
            best = name
    return best


def get_zone_nominal_target(zone_name: str) -> Tuple[float, float, str]:
    """Returns nominal (x, z) coordinates and category for a discrete zone name."""
    clean_name = (zone_name or 'heart').lower().strip()
    coords = ZONE_CENTERS.get(clean_name, (0.0, 2.50))
    cat = classify_gameday_zone(coords[0], coords[1])
    return coords[0], coords[1], cat


def get_zone_target_bounds(zone_name: str) -> Tuple[float, float, float, float]:
    """Returns the closed aim region (x_min, x_max, z_min, z_max) for a zone."""
    clean_name = (zone_name or 'heart').lower().strip()
    return ZONE_TARGET_BOUNDS.get(clean_name, ZONE_TARGET_BOUNDS['heart'])


def sample_zone_target(zone_name: str, rng=None) -> Tuple[float, float, str]:
    """
    Samples a uniform aim point inside a zone's closed rectangle and returns
    (x, z, category). The inner 9 zones cover the full rulebook rectangle, so
    an aim on any edge is a strike; chase aims are balls.
    """
    rand = rng or random.random
    x_min, x_max, z_min, z_max = get_zone_target_bounds(zone_name)
    x = x_min + (x_max - x_min) * rand()
    z = z_min + (z_max - z_min) * rand()
    return x, z, classify_gameday_zone(x, z)


def get_max_error_radius_inches(command_rating: float) -> float:
    """Interpolates the hard maximum miss radius (inches) for a command rating."""
    command = max(40.0, min(99.0, float(command_rating)))
    # Tiers are descending by command.
    for i in range(len(MAX_ERROR_RADIUS_TIERS) - 1):
        high_cmd, high_radius = MAX_ERROR_RADIUS_TIERS[i]
        low_cmd, low_radius = MAX_ERROR_RADIUS_TIERS[i + 1]
        if low_cmd <= command <= high_cmd:
            span = high_cmd - low_cmd
            if span <= 0:
                return high_radius
            t = (high_cmd - command) / span
            return round(high_radius + (low_radius - high_radius) * t, 3)
    return MAX_ERROR_RADIUS_TIERS[-1][1]


def calculate_execution_sigma(command_rating: float, pitch_count: int = 0, stamina: float = 75.0) -> float:
    """
    Sigma derived from the command's hard max radius. sigma = radius / 2.5.
    Fatigue growth is gated by FATIGUE_ENABLED and is off for now.
    """
    radius_ft = get_max_error_radius_inches(command_rating) / 12.0
    base_sigma = radius_ft / SIGMA_RADIUS_DIVISOR
    if not FATIGUE_ENABLED:
        return base_sigma
    fatigue_multiplier = max(0.0, (pitch_count - stamina) / 30.0)
    return base_sigma * (1.0 + fatigue_multiplier)


def sample_truncated_gaussian(
    target_x: float,
    target_z: float,
    sigma: float,
    max_radius_ft: float,
    rng=None,
) -> Tuple[float, float]:
    """
    Samples a 2D Gaussian location truncated to the hard max radius.
    Uses the closed-form truncated Rayleigh radial distribution, so no rejection
    loop is needed and the result can never leave the circle.

    Returns full-precision coordinates; callers should round only for display or
    telemetry so boundary pitches are classified from their true location.
    """
    rand = rng or random.random
    if max_radius_ft <= 0 or sigma <= 0:
        return target_x, target_z

    u = rand()
    exp_term = math.exp(-(max_radius_ft * max_radius_ft) / (2.0 * sigma * sigma))
    one_minus = 1.0 - u * (1.0 - exp_term)
    r = sigma * math.sqrt(-2.0 * math.log(max(1e-12, one_minus)))
    r = min(r, max_radius_ft)
    theta = 2.0 * math.pi * rand()

    realized_x = target_x + r * math.cos(theta)
    realized_z = target_z + r * math.sin(theta)
    # Keep full precision. Callers round only for display/telemetry so an
    # on-the-line pitch is classified from its actual coordinate.
    return realized_x, realized_z


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
