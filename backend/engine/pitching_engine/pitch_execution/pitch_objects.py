"""
Backward-compatibility re-export for pitch objects.
Authoritative source now resides in backend.engine.pitching_engine.pitcher_info.pitch_objects.
"""

from ..pitcher_info.pitch_objects import (
    PITCH_CATEGORIES,
    DEFAULT_ARSENAL,
    DEFAULT_PITCH_MOVEMENT,
    DEFAULT_MOVEMENT,
    movement_for,
    Pitch,
    PitchArsenal,
)

__all__ = [
    'PITCH_CATEGORIES',
    'DEFAULT_ARSENAL',
    'DEFAULT_PITCH_MOVEMENT',
    'DEFAULT_MOVEMENT',
    'movement_for',
    'Pitch',
    'PitchArsenal',
]
