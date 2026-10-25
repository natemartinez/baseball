"""
Batter controllers for the pitch-flow orchestrator.

A controller turns a plate-crossing context into a SWING/TAKE reaction. The
default AI adapter preserves the exact RNG sequence used by the batting engine,
while a future user-controlled adapter can return ``None`` to pause the flow at
``AWAITING_REACTION``.
"""

import random
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple

try:
    from ..batting_engine.batter_strategy import BatterStrategy
    from ..batting_engine.batters import InGameBatterRatings
except ImportError:  # direct script execution from backend/engine
    from batting_engine.batter_strategy import BatterStrategy
    from batting_engine.batters import InGameBatterRatings

VALID_DECISIONS = ('SWING', 'TAKE')
VALID_APPROACHES = ('AUTO', 'AGGRESSIVE', 'PATIENT', 'CONTACT')


@dataclass(frozen=True)
class BatterReactionContext:
    """Everything a controller needs to choose a reaction for one pitch."""

    batter_id: Any
    batter_name: str
    balls: int
    strikes: int
    outs: int
    runners: Tuple[bool, bool, bool]
    situation: str
    delivery: Dict[str, Any]
    zone_name: str
    zone_category: str
    is_strike: bool
    ratings: InGameBatterRatings
    approach: str = 'AUTO'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'batter_id': self.batter_id,
            'batter_name': self.batter_name,
            'balls': self.balls,
            'strikes': self.strikes,
            'outs': self.outs,
            'runners': list(self.runners),
            'situation': self.situation,
            'delivery': dict(self.delivery),
            'zone_name': self.zone_name,
            'zone_category': self.zone_category,
            'is_strike': self.is_strike,
            'ratings': self.ratings.to_dict(),
            'approach': self.approach,
        }


@dataclass(frozen=True)
class BatterReaction:
    """A locked SWING/TAKE decision."""

    decision: str
    approach: str = 'AUTO'
    source: str = 'AI'
    swing_probability: Optional[float] = None

    @classmethod
    def explicit(cls, decision: str, approach: str = 'AUTO') -> 'BatterReaction':
        probability = 1.0 if decision == 'SWING' else 0.0
        return cls(
            decision=decision,
            approach=approach,
            source='USER',
            swing_probability=probability,
        )


class BatterController(Protocol):
    def choose_reaction(
        self, context: BatterReactionContext
    ) -> Optional[BatterReaction]:
        ...


class AIBatterController:
    """Default controller: adapts ``BatterStrategy`` to the controller protocol."""

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random

    def decide(
        self,
        *,
        delivery: Dict[str, Any],
        ratings: InGameBatterRatings,
        actual_zone_name: str,
        balls: int,
        strikes: int,
        approach: str = 'AUTO',
    ) -> BatterReaction:
        strategy = BatterStrategy(ratings, rng=self.rng)
        will_swing, probability = strategy.decide_swing(
            delivery,
            actual_zone_name=actual_zone_name,
            balls=balls,
            strikes=strikes,
            approach_mode=approach,
        )
        return BatterReaction(
            decision='SWING' if will_swing else 'TAKE',
            approach=approach,
            source='AI',
            swing_probability=probability,
        )

    def choose_reaction(
        self, context: BatterReactionContext
    ) -> Optional[BatterReaction]:
        return self.decide(
            delivery=context.delivery,
            ratings=context.ratings,
            actual_zone_name=context.zone_name,
            balls=context.balls,
            strikes=context.strikes,
            approach=context.approach,
        )
