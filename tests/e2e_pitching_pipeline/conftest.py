"""
Pytest configuration and shared fixtures for E2E Pitching Mechanics Pipeline tests.
"""

from pathlib import Path
import sys
import math
from typing import Tuple, Dict, Any, Optional
import pytest

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_player
from backend.api.app import create_app


@pytest.fixture(scope="session")
def app():
    """Returns Flask application instance."""
    app_instance = create_app()
    app_instance.config.update({"TESTING": True})
    return app_instance


@pytest.fixture
def client(app):
    """Returns Flask test client with an initialized game."""
    test_client = app.test_client()
    # Initialize a test game between Team 1 and Team 2
    test_client.post("/api/start_game", json={"home_team_id": 1, "away_team_id": 2})
    return test_client


@pytest.fixture
def test_matchup():
    """Returns Nolan McLean (Pitcher) and Aaron Judge (Batter)."""
    p1 = get_player(1)
    p2 = get_player(2)
    pitcher = p1 if p1 and p1.is_pitcher else p2
    batter = p2 if p1 and p1.is_pitcher else p1
    assert pitcher is not None, "Failed to load Nolan McLean (Pitcher) from DB"
    assert batter is not None, "Failed to load Aaron Judge (Batter) from DB"
    return pitcher, batter


# --- Dynamic Contract Importer Helpers ---

def get_tiers_module():
    """Safely imports and returns tiers module."""
    try:
        import tiers
        return tiers
    except Exception as e:
        pytest.fail(f"Failed to import tiers: {e}")


def get_adjusted_ratings_module():
    """Safely imports and returns adjusted_ratings module."""
    try:
        from backend.engine.pitching_engine.pitcher_info import adjusted_ratings
        return adjusted_ratings
    except Exception as e:
        pytest.fail(f"Failed to import adjusted_ratings: {e}")


def get_calculations_module():
    """Safely imports and returns calculations module."""
    try:
        from backend.engine.pitching_engine.pitch_execution import calculations
        return calculations
    except Exception as e:
        pytest.fail(f"Failed to import calculations: {e}")


# --- Interactive Delivery & Reticle Reference Models ---

def evaluate_charging_timing(
    hold_time_ms: float,
    target_sweet_spot_ms: float = 1000.0,
) -> Tuple[str, str]:
    """
    Reference model for F6 Press-and-Release charging mechanic.
    Maps hold duration relative to target window to (TimingTier, timing_label).
    
    Tolerances:
    - ratio in [0.95, 1.05]: PERFECT ("PERFECT!")
    - ratio in [0.85, 0.95): GOOD ("EARLY • GOOD")
    - ratio in (1.05, 1.15]: GOOD ("LATE • GOOD")
    - ratio in [0.65, 0.85): OKAY ("EARLY • OKAY")
    - ratio in (1.15, 1.35]: OKAY ("LATE • OKAY")
    - ratio < 0.65: POOR ("EARLY • POOR")
    - ratio > 1.35: POOR ("LATE • POOR")
    """
    if target_sweet_spot_ms <= 0:
        return "POOR", "EARLY • POOR"
    ratio = hold_time_ms / target_sweet_spot_ms
    if 0.95 <= ratio <= 1.05:
        return "PERFECT", "PERFECT!"
    elif 0.85 <= ratio < 0.95:
        return "GOOD", "EARLY • GOOD"
    elif 1.05 < ratio <= 1.15:
        return "GOOD", "LATE • GOOD"
    elif 0.65 <= ratio < 0.85:
        return "OKAY", "EARLY • OKAY"
    elif 1.15 < ratio <= 1.35:
        return "OKAY", "LATE • OKAY"
    elif ratio < 0.65:
        return "POOR", "EARLY • POOR"
    else:
        return "POOR", "LATE • POOR"


def calculate_reticle_geometry(
    base_radius_in: float,
    timing_tier: str,
) -> Dict[str, float]:
    """
    Reference model for F7 Reticle Geometry.
    Contracts on PERFECT (~0.52x), 1.00x on GOOD, expands on OKAY (~1.97x) and POOR (~3.75x).
    """
    multipliers = {
        "PERFECT": 0.52,
        "GOOD": 1.00,
        "OKAY": 1.97,
        "POOR": 3.75,
    }
    tier_upper = timing_tier.upper()
    multiplier = multipliers.get(tier_upper, 1.00)
    executed_radius_in = round(base_radius_in * multiplier, 3)
    bloom_ratio = round(executed_radius_in / max(1e-6, base_radius_in), 3)
    return {
        "base_radius_inches": base_radius_in,
        "executed_radius_inches": executed_radius_in,
        "multiplier": multiplier,
        "bloom_ratio": bloom_ratio,
    }


def calculate_miss_vector(
    target_x: float,
    target_z: float,
    realized_x: float,
    realized_z: float,
) -> Dict[str, float]:
    """
    Reference model for F7 Miss Vector Calculation.
    Coordinates in Statcast feet, converted to inches and polar angle.
    """
    delta_x_ft = realized_x - target_x
    delta_z_ft = realized_z - target_z
    delta_x_in = round(delta_x_ft * 12.0, 2)
    delta_z_in = round(delta_z_ft * 12.0, 2)
    radial_miss_in = round(math.sqrt(delta_x_in**2 + delta_z_in**2), 2)
    angle_deg = round(math.degrees(math.atan2(delta_z_ft, delta_x_ft)), 1)
    return {
        "delta_x_in": delta_x_in,
        "delta_z_in": delta_z_in,
        "radial_miss_inches": radial_miss_in,
        "angle_degrees": angle_deg,
    }
