import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.engine.game_engine.geometry import (
    StrikeZone,
    classify_gameday_zone,
    is_rulebook_strike,
    nearest_zone_name,
    get_zone_nominal_target,
    calculate_execution_sigma,
    get_max_error_radius_inches,
    sample_directional_dispersion,
    ZONE_CENTERS,
)

def test_geometry_subpackage_exports():
    assert StrikeZone is not None
    assert callable(classify_gameday_zone)
    assert callable(is_rulebook_strike)
    assert callable(nearest_zone_name)
    assert callable(get_zone_nominal_target)
    assert callable(calculate_execution_sigma)
    assert callable(get_max_error_radius_inches)
    assert callable(sample_directional_dispersion)
    assert isinstance(ZONE_CENTERS, dict)


def test_geometry_functional_calculations():
    # Dead center is strike
    assert is_rulebook_strike(0.0, 2.5) is True
    # Way outside is ball
    assert is_rulebook_strike(2.0, 2.5) is False
    # Macro zone classifications
    assert classify_gameday_zone(0.0, 2.5) == 'HEART'
    assert classify_gameday_zone(0.0, 3.9) == 'CHASE'
    assert classify_gameday_zone(0.0, 4.5) == 'WASTE'


