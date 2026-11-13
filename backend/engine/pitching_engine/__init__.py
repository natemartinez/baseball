"""
Pitching Engine Package.
Authoritative pitching coordination, pitch strategy, domain objects, and delivery execution.
"""

from .engine import PitchingEngine
from .pitch_execution import (
    PITCH_CATEGORIES,
    Pitch,
    PitchArsenal,
    calculate_pitch_delivery,
    PitchShape,
    build_pitch_shape,
    shape_telemetry,
)
from .pitch_selection import PitchStrategy
from .pitcher_info import (
    ActivePitcherState,
    InGamePitcherRatings,
    PitcherInstanceManager,
    PitchArsenalMetrics,
    evaluate_pitch_arsenal,
    calculate_pitch_confidence_delta,
    calculate_consecutive_miss_penalty,
    apply_holistic_confidence_update,
    calculate_effective_command_with_confidence,
    compute_baseline_effectiveness,
    calculate_effectiveness_delta,
    update_pitch_effectiveness,
    apply_effectiveness_to_whiff_rate,
    apply_effectiveness_to_exit_velocity,
)

__all__ = [
    'PitchingEngine',
    'ActivePitcherState',
    'PitchStrategy',
    'Pitch',
    'PitchArsenal',
    'PITCH_CATEGORIES',
    'PitcherInstanceManager',
    'InGamePitcherRatings',
    'PitchArsenalMetrics',
    'evaluate_pitch_arsenal',
    'calculate_pitch_delivery',
    'PitchShape',
    'build_pitch_shape',
    'shape_telemetry',
    'calculate_pitch_confidence_delta',
    'calculate_consecutive_miss_penalty',
    'apply_holistic_confidence_update',
    'calculate_effective_command_with_confidence',
    'compute_baseline_effectiveness',
    'calculate_effectiveness_delta',
    'update_pitch_effectiveness',
    'apply_effectiveness_to_whiff_rate',
    'apply_effectiveness_to_exit_velocity',
]
