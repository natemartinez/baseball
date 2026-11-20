"""Backward-compatibility re-export for batter ratings and state."""
import sys
from .batter_info import batters as _canonical

sys.modules[__name__] = _canonical

from .batter_info.batters import *  # noqa: F401, F403
from .batter_info.batters import (
    BatterInstanceManager,
    InGameBatterRatings,
    DEFAULT_BATTER_ZONES,
    DEFAULT_BATTER_RATINGS,
    LEAGUE_AVG_SLG,
    normalize_hot_zones,
    normalize_traits,
    get_batter_hand,
    get_effective_batter_side,
)
