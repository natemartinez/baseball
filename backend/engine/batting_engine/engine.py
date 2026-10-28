"""
Batting Engine: Main Coordinator.

Coordinates in-game batter ratings, the swing/take decision, and contact
resolution into a single BatterActivity. The engine is a pure calculator:
it consumes a realized pitch delivery plus pre-pitch context and returns an
outcome. GameEngine remains the only mutable game-state machine.
"""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from .batters import BatterInstanceManager
from .contact import ContactResolver
from .contact_outcome import resolve_contact_outcome

from ..game_engine.ball_flight import compute_batted_ball_trace

if TYPE_CHECKING:  # pragma: no cover - avoids a runtime import cycle
    from ..game_engine.orchestration.controllers import BatterReaction


@dataclass
class BatterActivity:
    """A completed batter-side result for one pitch."""
    decision: str
    swing_probability: float
    pitch_result: str
    call: str
    description: str
    is_in_play: bool
    is_strike: bool
    zone_name: str
    zone_category: str
    exit_velocity_mph: Optional[float]
    launch_angle_deg: Optional[float]
    spray_angle_deg: Optional[float]
    contact_quality: Optional[str]
    batter_ratings: Dict[str, Any]
    batted_ball: Optional[Dict[str, Any]] = None
    swing_decision: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'decision': self.decision,
            'swing_probability': self.swing_probability,
            'pitch_result': self.pitch_result,
            'call': self.call,
            'description': self.description,
            'is_in_play': self.is_in_play,
            'is_strike': self.is_strike,
            'zone_name': self.zone_name,
            'zone_category': self.zone_category,
            'exit_velocity_mph': self.exit_velocity_mph,
            'launch_angle_deg': self.launch_angle_deg,
            'spray_angle_deg': self.spray_angle_deg,
            'contact_quality': self.contact_quality,
            'batter_ratings': dict(self.batter_ratings),
            'batted_ball': dict(self.batted_ball) if self.batted_ball else None,
            'swing_decision': dict(self.swing_decision) if self.swing_decision else None,
        }


class BattingEngine:
    """
    Authoritative batting coordinator for an active pitch.

    Communicates between GameEngine and batting submodules (ratings, swing
    decision, contact physics). It never mutates count, bases, outs, or score.
    """

    def __init__(
        self,
        batter: Any,
        delivery: Dict[str, Any],
        rng: Optional[random.Random] = None,
    ):
        if isinstance(batter, dict):
            try:
                from backend.models.player import Player
                batter = Player.from_dict(batter)
            except ImportError:
                pass

        self.batter = batter
        self.delivery = delivery or {}
        self.rng = rng or random

    def resolve(
        self,
        *,
        balls: int,
        strikes: int,
        outs: int,
        runners: Tuple[bool, bool, bool],
        situation: str,
        actual_zone_name: str,
        batter_approach: str = 'AUTO',
        pitcher_hand: str = 'R',
        reaction: Optional['BatterReaction'] = None,
        contact: Optional[Dict[str, Any]] = None,
    ) -> BatterActivity:
        """Resolves the batter's activity for the pitch in flight."""
        ratings = BatterInstanceManager.get_adjusted_ratings(
            self.batter,
            balls=balls,
            strikes=strikes,
            pitcher_hand=pitcher_hand,
        )
        zone_category = str(self.delivery.get('realized_zone_cat', 'SHADOW')).upper()
        is_strike = bool(self.delivery.get('is_strike', False))

        # Player-controlled contact: Rapier reports the impact, and the outcome
        # is derived from the actual landing point. This bypasses the AI
        # swing/contact RNG entirely.
        if contact is not None:
            return self._resolve_contact_report(
                contact,
                ratings=ratings,
                actual_zone_name=actual_zone_name,
                zone_category=zone_category,
                is_strike=is_strike,
            )

        if reaction is None:
            # Direct callers keep the historical single-call behavior. The
            # adaptor is imported lazily to avoid a package import cycle.
            from ..game_engine.orchestration.controllers import AIBatterController

            reaction = AIBatterController(rng=self.rng).decide(
                delivery=self.delivery,
                ratings=ratings,
                actual_zone_name=actual_zone_name,
                balls=balls,
                strikes=strikes,
                approach=batter_approach,
            )

        decision = reaction.decision
        approach = reaction.approach or batter_approach
        swing_probability = reaction.swing_probability
        if swing_probability is None:
            swing_probability = 1.0 if decision == 'SWING' else 0.0

        if decision == 'TAKE':
            if is_strike:
                call = 'CALLED_STRIKE'
                description = f'Called strike ({actual_zone_name})'
            else:
                call = 'BALL'
                description = f'Ball ({zone_category.lower()})'

            return BatterActivity(
                decision='TAKE',
                swing_probability=swing_probability,
                pitch_result=call,
                call=call,
                description=description,
                is_in_play=False,
                is_strike=is_strike,
                zone_name=actual_zone_name,
                zone_category=zone_category,
                exit_velocity_mph=None,
                launch_angle_deg=None,
                spray_angle_deg=None,
                contact_quality=None,
                batter_ratings=ratings.to_dict(),
                swing_decision=getattr(reaction, 'decision_factors', None),
            )

        resolver = ContactResolver(ratings, rng=self.rng)
        contact = resolver.resolve(
            self.delivery,
            actual_zone_name=actual_zone_name,
            balls=balls,
            strikes=strikes,
            approach_mode=approach,
        )

        batted_ball = contact.get('batted_ball')
        if batted_ball is None and contact.get('is_in_play'):
            batted_ball = compute_batted_ball_trace(
                contact.get('exit_velocity_mph'),
                contact.get('launch_angle_deg'),
                contact.get('spray_angle_deg'),
            )

        return BatterActivity(
            decision='SWING',
            swing_probability=swing_probability,
            pitch_result=contact['call'],
            call=contact['call'],
            description=contact['description'],
            is_in_play=contact['is_in_play'],
            is_strike=is_strike,
            zone_name=actual_zone_name,
            zone_category=zone_category,
            exit_velocity_mph=contact.get('exit_velocity_mph'),
            launch_angle_deg=contact.get('launch_angle_deg'),
            spray_angle_deg=contact.get('spray_angle_deg'),
            contact_quality=contact.get('contact_quality'),
            batter_ratings=ratings.to_dict(),
            batted_ball=batted_ball,
            swing_decision=getattr(reaction, 'decision_factors', None),
        )

    def _resolve_contact_report(
        self,
        contact: Dict[str, Any],
        *,
        ratings: Any,
        actual_zone_name: str,
        zone_category: str,
        is_strike: bool,
    ) -> BatterActivity:
        """Builds a player-contact activity from a Rapier contact report."""
        base = {
            'decision': 'SWING',
            'swing_probability': 1.0,
            'is_strike': is_strike,
            'zone_name': actual_zone_name,
            'zone_category': zone_category,
            'batter_ratings': ratings.to_dict(),
        }

        if not bool(contact.get('contacted')):
            return BatterActivity(
                **base,
                pitch_result='SWINGING_STRIKE',
                call='SWINGING_STRIKE',
                description='Swing and a miss.',
                is_in_play=False,
                exit_velocity_mph=None,
                launch_angle_deg=None,
                spray_angle_deg=None,
                contact_quality=None,
                batted_ball=None,
            )

        outcome = resolve_contact_outcome(
            contact.get('exit_velocity_mph'),
            contact.get('launch_angle_deg'),
            contact.get('spray_angle_deg'),
            batter_speed=float(getattr(ratings, 'speed', 75.0) or 75.0),
        )
        if outcome is None:
            return BatterActivity(
                **base,
                pitch_result='SWINGING_STRIKE',
                call='SWINGING_STRIKE',
                description='Swing and a miss.',
                is_in_play=False,
                exit_velocity_mph=None,
                launch_angle_deg=None,
                spray_angle_deg=None,
                contact_quality=None,
                batted_ball=None,
            )

        return BatterActivity(
            **base,
            pitch_result=outcome['call'],
            call=outcome['call'],
            description=outcome['description'],
            is_in_play=outcome['is_in_play'],
            exit_velocity_mph=outcome['exit_velocity_mph'],
            launch_angle_deg=outcome['launch_angle_deg'],
            spray_angle_deg=outcome['spray_angle_deg'],
            contact_quality=outcome['contact_quality'],
            batted_ball=outcome['batted_ball'],
        )
