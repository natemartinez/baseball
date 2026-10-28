"""
Authoritative game engine package.

``GameEngine`` is the ultimate manager: it owns every mutation to count, bases,
outs, and score, while the nested pitch-flow orchestration drives delivery,
reaction, and contact resolution without touching game state.
"""

from .engine import GameEngine
from .orchestration import (
    AIBatterController,
    BatterController,
    BatterReaction,
    BatterReactionContext,
    PendingPitch,
    PitchFlowError,
    PitchFlowOrchestrator,
    PitchPhase,
    VALID_APPROACHES,
    VALID_DECISIONS,
)

__all__ = [
    'AIBatterController',
    'BatterController',
    'BatterReaction',
    'BatterReactionContext',
    'GameEngine',
    'PendingPitch',
    'PitchFlowError',
    'PitchFlowOrchestrator',
    'PitchPhase',
    'VALID_APPROACHES',
    'VALID_DECISIONS',
]
