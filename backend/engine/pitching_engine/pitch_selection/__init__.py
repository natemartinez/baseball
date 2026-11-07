"""
Pitch selection, tactical target intent, and strategy recommendation models.

This package owns every backend pitch-selection responsibility: the AI/mix
strategy, explicit user pitch resolution, tactical target-intent resolution, and
the recommendation payload exposed to the UI. Delivery execution and pitcher
ratings stay in their existing packages.
"""

from .intent import (
    PitchSelectionError,
    TargetIntent,
    mix_ball_intent,
    normalize_pitch_intent,
    resolve_target_intent,
    sample_waste_target,
)
from .recommendation import calculate_strategy_and_intent
from .selection import PitchSelection, PitchSelectionMode, select_pitch
from .strategy import PitchStrategy

__all__ = [
    'PitchSelection',
    'PitchSelectionError',
    'PitchSelectionMode',
    'PitchStrategy',
    'TargetIntent',
    'calculate_strategy_and_intent',
    'mix_ball_intent',
    'normalize_pitch_intent',
    'resolve_target_intent',
    'sample_waste_target',
    'select_pitch',
]
