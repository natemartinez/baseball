"""Backward-compatibility re-export for StrikeZone."""
import sys
from .geometry import strike_zone as _canonical

sys.modules[__name__] = _canonical

from .geometry.strike_zone import *  # noqa: F401, F403
from .geometry.strike_zone import StrikeZone
