"""Backward-compatibility re-export for batter strategy and swing decisions."""
import sys
from .swing_decision import strategy as _canonical

sys.modules[__name__] = _canonical

from .swing_decision.strategy import *  # noqa: F401, F403
from .swing_decision.strategy import BatterStrategy, SwingEvaluation, MODEL_CONFIG
