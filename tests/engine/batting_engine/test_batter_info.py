import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.engine.batting_engine.batter_info import (
    BatterInstanceManager,
    InGameBatterRatings,
    DEFAULT_BATTER_ZONES,
    DEFAULT_BATTER_RATINGS,
    LEAGUE_AVG_SLG,
    normalize_hot_zones,
    normalize_traits,
)

def test_batter_info_subpackage_exports():
    assert InGameBatterRatings is not None
    assert BatterInstanceManager is not None
    assert isinstance(DEFAULT_BATTER_ZONES, dict)
    assert isinstance(DEFAULT_BATTER_RATINGS, dict)
    assert LEAGUE_AVG_SLG == 0.400
    assert callable(normalize_hot_zones)
    assert callable(normalize_traits)


def test_batter_info_functional_hydration():
    player_dict = {
        'id': 42,
        'name': 'Test Slugger',
        'power': 85.0,
        'contact': 70.0,
        'vision': 60.0,
        'speed': 55.0,
        'bats': 'L',
    }
    adj = BatterInstanceManager.get_adjusted_ratings(player_dict, pitcher_hand='R')
    assert adj.batter_id == 42
    assert adj.batter_name == 'Test Slugger'
    assert adj.power == 85.0
    assert adj.contact == 70.0
    # Platoon bonus: opposite hand adds +2 contact
    assert adj.effective_contact == 72.0
    assert adj.handedness == 'L'
    assert adj.batter_side == 'L'
    assert 'heart' in adj.hot_zones

