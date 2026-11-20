"""Backward-compatibility re-export for gameday coordinates and dispersion math."""
import sys
from .geometry import gameday_math as _canonical

sys.modules[__name__] = _canonical

from .geometry.gameday_math import *  # noqa: F401, F403
