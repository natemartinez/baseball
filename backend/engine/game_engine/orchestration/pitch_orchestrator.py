"""
Pitch Flow Orchestrator.

Owns the phase sequence for one pitch: delivery, plate crossing, batter
reaction, contact resolution, and hand-off back to ``GameEngine`` for the single
state commit. It never mutates count, bases, outs, or score and never imports
``GameEngine``.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:
    from ...batting_engine.engine import BatterActivity
from ...batting_engine.batters import BatterInstanceManager, InGameBatterRatings
from ..gameday_math import nearest_zone_name
from .pitch_context import PitchContext, CountSnapshot, PitchInput
from .packet_builder import build_gameday_packet, build_pitch_details

from .controllers import (
    AIBatterController,
    BatterController,
    BatterReaction,
    BatterReactionContext,
    VALID_APPROACHES,
    VALID_DECISIONS,
)


class PitchPhase(str, Enum):
    IDLE = 'IDLE'
    THROWN = 'THROWN'
    PLATE_CROSSED = 'PLATE_CROSSED'
    AWAITING_REACTION = 'AWAITING_REACTION'
    REACTION_LOCKED = 'REACTION_LOCKED'
    OUTCOME_RESOLVED = 'OUTCOME_RESOLVED'
    STATE_APPLIED = 'STATE_APPLIED'


class PitchFlowError(Exception):
    """Raised when a pitch-flow transition is invalid."""


@dataclass
class PendingPitch:
    """Pre-pitch snapshot plus the realized delivery for one pitch."""

    delivery: Dict[str, Any]
    pitcher: Any
    batter: Any
    situation: str
    actual_zone_name: str
    pitch_count: int
    command_rating: float
    balls: int
    strikes: int
    outs: int
    runners: Tuple[bool, bool, bool]
    pitcher_hand: str
    zone_category: str
    is_strike: bool
    ratings: InGameBatterRatings
    pitch_sequence: Tuple[Dict[str, Any], ...]
    pitcher_ratings: Dict[str, Any]
    score_diff: int
    inning: int


class PitchFlowOrchestrator:
    """Drives delivery -> reaction -> contact while ``GameEngine`` owns state."""

    def __init__(self, rng=None, batter_controller: Optional[BatterController] = None):
        self.rng = rng
        self.batter_controller = batter_controller or AIBatterController(rng=self.rng)
        self._phase = PitchPhase.IDLE
        self._pending: Optional[PendingPitch] = None
        self._reaction: Optional[BatterReaction] = None
        self._activity: Optional[BatterActivity] = None
        self._context: Optional[PitchContext] = None
        self._last_context: Optional[PitchContext] = None

    @property
    def phase(self) -> PitchPhase:
        return self._phase

    @property
    def pending(self) -> Optional[PendingPitch]:
        return self._pending

    @property
    def context(self) -> Optional[PitchContext]:
        return self._context or self._last_context

    @property
    def has_pending(self) -> bool:
        return self._pending is not None and self._phase is not PitchPhase.IDLE

    def _require(self, *allowed: PitchPhase) -> None:
        if self._phase not in allowed:
            if self._phase is PitchPhase.IDLE:
                raise PitchFlowError('No pitch in flight to resolve')
            allowed_names = ', '.join(phase.value for phase in allowed)
            raise PitchFlowError(
                f'Cannot process pitch while in phase {self._phase.value}; '
                f'expected {allowed_names}'
            )

    def start_pitch(
        self,
        *,
        pitcher: Any,
        batter: Any,
        balls: int,
        strikes: int,
        outs: int,
        runners: Tuple[bool, bool, bool],
        situation: str,
        pitch_count: int,
        recent_pitches: Optional[list] = None,
        pitch_intent: Optional[str] = None,
        pitch_type: Optional[str] = None,
        target_zone: Optional[str] = None,
        custom_target: Optional[Dict[str, float]] = None,
        selection_mode: Optional[str] = None,
        pitch_name: Optional[str] = None,
        pitch_sequence: Optional[list] = None,
        score_diff: int = 0,
        inning: int = 1,
        timing_tier: Optional[str] = None,
        timing_label: Optional[str] = None,
        pitch_effectiveness: Optional[float] = None,
        delivery: Optional[Dict[str, Any]] = None,
        context: Optional[PitchContext] = None,
    ) -> Dict[str, Any]:
        if self.has_pending:
            raise PitchFlowError(
                'A pitch is already in flight; resolve it before throwing another.'
            )
        if self._phase is not PitchPhase.IDLE:
            self.reset()

        pitcher_hand = (
            'L'
            if str(getattr(pitcher, 'handedness', 'R') or 'R').upper().startswith('L')
            else 'R'
        )

        if context is not None:
            self._context = context
        else:
            count_snap = CountSnapshot(
                balls=balls,
                strikes=strikes,
                outs=outs,
                runners=runners,
                inning=inning,
                score_diff=score_diff,
                situation=situation,
            )
            pitch_in = PitchInput(
                pitch_intent=pitch_intent,
                pitch_type=pitch_type,
                pitch_name=pitch_name,
                target_zone=target_zone,
                custom_target=custom_target,
                timing_tier=timing_tier,
                timing_label=timing_label,
                selection_mode=selection_mode,
                pitch_effectiveness=pitch_effectiveness,
            )
            pitch_id = f"pitch-{inning}-{pitch_count}"
            self._context = PitchContext.create(
                pitch_id=pitch_id,
                pitcher=pitcher,
                batter=batter,
                count=count_snap,
                pitch_input=pitch_in,
                pitch_count=pitch_count,
                recent_pitches=recent_pitches or [],
            )

        if delivery is not None:
            exec_delivery = delivery
        else:
            # Imported lazily: the pitching package loads gameday math from the
            # engine package, which would otherwise re-enter this module while its
            # initializer is still running.
            from ...pitching_engine import PitchingEngine

            pitching_engine = PitchingEngine(pitcher, batter, rng=self.rng)
            exec_delivery = pitching_engine.execute_pitch(
                balls=balls,
                strikes=strikes,
                outs=outs,
                runners=runners,
                pitch_count=pitch_count,
                recent_pitches=recent_pitches or [],
                pitch_intent=pitch_intent,
                pitch_type=pitch_type,
                target_zone=target_zone,
                custom_target=custom_target,
                situation=situation,
                selection_mode=selection_mode,
                pitch_name=pitch_name,
                timing_tier=timing_tier,
                timing_label=timing_label,
                pitch_effectiveness=pitch_effectiveness,
            )

        self._context.delivery = exec_delivery
        if hasattr(pitcher, 'record_pitch'):
            pitcher.record_pitch(exec_delivery.get('pitch_name', ''))
        is_strike = bool(exec_delivery.get('is_strike', False))
        actual_zone_name = nearest_zone_name(
            is_strike, exec_delivery.get('realized_x', 0.0), exec_delivery.get('realized_z', 2.5)
        )
        self._context.is_strike = is_strike
        self._context.actual_zone_name = actual_zone_name

        pending_result = {
            'call': None,
            'isStrike': is_strike,
            'exitVelocityMph': None,
            'launchAngleDeg': None,
            'description': 'Pitch in flight',
        }
        self._context.gameday_packet = build_gameday_packet(
            self._context, result=pending_result, rng=self.rng
        )
        self._context.pitch_details = build_pitch_details(
            self._context, description='Pitch in flight', gameday_packet=self._context.gameday_packet
        )

        ratings = self._context.batter.ratings

        self._pending = PendingPitch(
            delivery=exec_delivery,
            pitcher=pitcher,
            batter=batter,
            situation=situation,
            actual_zone_name=actual_zone_name,
            pitch_count=pitch_count,
            command_rating=exec_delivery.get('adjusted_ratings', {}).get('base_command', 70.0),
            balls=balls,
            strikes=strikes,
            outs=outs,
            runners=runners,
            pitcher_hand=pitcher_hand,
            zone_category=str(exec_delivery.get('realized_zone_cat', 'SHADOW')).upper(),
            is_strike=is_strike,
            ratings=ratings,
            pitch_sequence=tuple(dict(pitch) for pitch in (pitch_sequence or [])),
            pitcher_ratings=dict(exec_delivery.get('adjusted_ratings') or {}),
            score_diff=int(score_diff or 0),
            inning=int(inning or 1),
        )
        self._reaction = None
        self._activity = None
        self._phase = PitchPhase.THROWN

        return {
            'delivery': exec_delivery,
            'actual_zone_name': actual_zone_name,
            'pending': self._pending,
            'context': self._context,
            'gameday_packet': self._context.gameday_packet,
            'pitch_details': self._context.pitch_details,
        }

    def _reaction_context(
        self, pending: PendingPitch, approach: str
    ) -> BatterReactionContext:
        return BatterReactionContext(
            batter_id=getattr(pending.batter, 'id', None)
            if not isinstance(pending.batter, dict)
            else pending.batter.get('id'),
            batter_name=getattr(pending.batter, 'name', 'Batter')
            if not isinstance(pending.batter, dict)
            else str(pending.batter.get('name') or 'Batter'),
            balls=pending.balls,
            strikes=pending.strikes,
            outs=pending.outs,
            runners=pending.runners,
            situation=pending.situation,
            delivery=pending.delivery,
            zone_name=pending.actual_zone_name,
            zone_category=pending.zone_category,
            is_strike=pending.is_strike,
            ratings=pending.ratings,
            approach=approach,
            pitch_sequence=pending.pitch_sequence,
            pitcher_ratings=pending.pitcher_ratings,
            score_diff=pending.score_diff,
            inning=pending.inning,
        )

    @staticmethod
    def _validate(decision: str, approach: str) -> None:
        if decision not in VALID_DECISIONS:
            raise PitchFlowError("batter_decision must be 'SWING' or 'TAKE'")
        if approach not in VALID_APPROACHES:
            raise PitchFlowError(
                f"batter_approach must be one of {', '.join(VALID_APPROACHES)}"
            )

    def resolve_pitch(
        self,
        *,
        batter_decision: Optional[str] = None,
        batter_approach: str = 'AUTO',
        contact: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._require(PitchPhase.THROWN)
        pending = self._pending
        assert pending is not None

        approach = (batter_approach or 'AUTO').upper()
        if approach not in VALID_APPROACHES:
            raise PitchFlowError(
                f"batter_approach must be one of {', '.join(VALID_APPROACHES)}"
            )

        reaction: Optional[BatterReaction]
        context = None
        if contact is not None:
            # A physical contact report is always a player swing.
            decision = 'SWING'
            self._validate(decision, approach)
            reaction = BatterReaction.explicit(decision, approach)
        elif batter_decision is not None:
            decision = str(batter_decision).upper()
            self._validate(decision, approach)
            reaction = BatterReaction.explicit(decision, approach)
        else:
            reaction = None

        self._phase = PitchPhase.PLATE_CROSSED

        if reaction is None:
            context = self._reaction_context(pending, approach)
            reaction = self.batter_controller.choose_reaction(context)
        if reaction is None:
            self._phase = PitchPhase.AWAITING_REACTION
            return {
                'status': 'success',
                'phase': PitchPhase.AWAITING_REACTION.value,
                'pending': pending,
                'reaction_context': context.to_dict() if context else None,
            }

        try:
            self._validate(reaction.decision, reaction.approach)
        except PitchFlowError:
            # Reject the controller's reaction without losing the pitch.
            self._phase = PitchPhase.THROWN
            raise
        self._phase = PitchPhase.REACTION_LOCKED
        return self._resolve_contact(pending, reaction, contact=contact)

    def submit_reaction(
        self, decision: str, approach: str = 'AUTO'
    ) -> Dict[str, Any]:
        self._require(PitchPhase.AWAITING_REACTION)
        pending = self._pending
        assert pending is not None

        normalized_decision = str(decision).upper()
        normalized_approach = (approach or 'AUTO').upper()
        self._validate(normalized_decision, normalized_approach)

        self._phase = PitchPhase.REACTION_LOCKED
        reaction = BatterReaction.explicit(normalized_decision, normalized_approach)
        return self._resolve_contact(pending, reaction)

    def _resolve_contact(
        self,
        pending: PendingPitch,
        reaction: BatterReaction,
        contact: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            from ...batting_engine.engine import BattingEngine
            batting_engine = BattingEngine(
                pending.batter, pending.delivery, rng=self.rng
            )
            activity = batting_engine.resolve(
                balls=pending.balls,
                strikes=pending.strikes,
                outs=pending.outs,
                runners=pending.runners,
                situation=pending.situation,
                actual_zone_name=pending.actual_zone_name,
                batter_approach=reaction.approach,
                pitcher_hand=pending.pitcher_hand,
                reaction=reaction,
                contact=contact,
            )
        except Exception:
            self.reset()
            raise

        self._reaction = reaction
        self._activity = activity
        self._phase = PitchPhase.OUTCOME_RESOLVED

        if self._context is not None:
            self._context.reaction = reaction
            self._context.activity = activity
            resolved_result = {
                'call': activity.call,
                'isStrike': activity.is_strike,
                'exitVelocityMph': activity.exit_velocity_mph,
                'launchAngleDeg': activity.launch_angle_deg,
                'description': activity.description,
            }
            if self._context.gameday_packet is not None:
                self._context.gameday_packet['result'] = resolved_result
            else:
                self._context.gameday_packet = build_gameday_packet(
                    self._context, result=resolved_result, rng=self.rng
                )
            self._context.pitch_details = build_pitch_details(
                self._context,
                description=activity.description,
                result_type=activity.pitch_result,
                batter_decision='SWING' if reaction.decision == 'SWING' else 'TAKE',
                exit_velo=activity.exit_velocity_mph,
                launch_angle=activity.launch_angle_deg,
                spray_angle=activity.spray_angle_deg,
                batted_ball=activity.batted_ball,
                swing_decision=getattr(activity, 'swing_decision', None),
                gameday_packet=self._context.gameday_packet,
            )

        return {
            'status': 'success',
            'phase': PitchPhase.OUTCOME_RESOLVED.value,
            'pending': pending,
            'reaction': reaction,
            'activity': activity,
            'context': self._context,
            'gameday_packet': self._context.gameday_packet if self._context else None,
            'pitch_details': self._context.pitch_details if self._context else None,
        }

    def mark_applied(self) -> None:
        self._require(PitchPhase.OUTCOME_RESOLVED)
        self._phase = PitchPhase.STATE_APPLIED

    def finish(self) -> None:
        self._require(PitchPhase.STATE_APPLIED)
        self.reset()

    def reset(self) -> None:
        if self._context is not None:
            self._last_context = self._context
        self._phase = PitchPhase.IDLE
        self._pending = None
        self._reaction = None
        self._activity = None
        self._context = None
