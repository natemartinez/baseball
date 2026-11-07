"""
Batting Engine Package.

Authoritative batting coordination, batter ratings, swing decisions, and
batted-ball contact resolution.
"""

from .batters import (
    BatterInstanceManager,
    InGameBatterRatings,
    DEFAULT_BATTER_ZONES,
    DEFAULT_BATTER_RATINGS,
    LEAGUE_AVG_SLG,
    normalize_hot_zones,
    normalize_traits,
)
from .engine import BattingEngine, BatterActivity
from .batter_strategy import BatterStrategy, SwingEvaluation
from .contact import ContactResolver

__all__ = [
    'BattingEngine',
    'BatterActivity',
    'BatterStrategy',
    'SwingEvaluation',
    'BatterInstanceManager',
    'InGameBatterRatings',
    'ContactResolver',
    'DEFAULT_BATTER_ZONES',
    'DEFAULT_BATTER_RATINGS',
    'LEAGUE_AVG_SLG',
    'normalize_hot_zones',
    'normalize_traits',
]
