"""
Pitch Context Domain Model.

Encapsulates the complete lifecycle and black-box state for a single pitch:
match situation, participant rating snapshots, pitcher delivery execution,
gameday flight telemetry, batter reaction, and game outcome resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ...pitching_engine.pitcher_info.adjusted_ratings import (
        InGamePitcherRatings,
    )
    from ...batting_engine.batters import (
        InGameBatterRatings,
    )


@dataclass
class CountSnapshot:
    balls: int = 0
    strikes: int = 0
    outs: int = 0
    runners: Tuple[bool, bool, bool] = (False, False, False)
    inning: int = 1
    score_diff: int = 0
    situation: str = "EMPTY_NEUTRAL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "balls": self.balls,
            "strikes": self.strikes,
            "outs": self.outs,
            "runners": list(self.runners),
            "inning": self.inning,
            "score_diff": self.score_diff,
            "situation": self.situation,
        }


@dataclass
class PitchInput:
    pitch_intent: Optional[str] = None
    pitch_type: Optional[str] = None
    pitch_name: Optional[str] = None
    target_zone: Optional[str] = None
    custom_target: Optional[Dict[str, float]] = None
    timing_tier: Optional[str] = None
    timing_label: Optional[str] = None
    selection_mode: Optional[str] = None
    pitch_effectiveness: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pitch_intent": self.pitch_intent,
            "pitch_type": self.pitch_type,
            "pitch_name": self.pitch_name,
            "target_zone": self.target_zone,
            "custom_target": self.custom_target,
            "timing_tier": self.timing_tier,
            "timing_label": self.timing_label,
            "selection_mode": self.selection_mode,
            "pitch_effectiveness": self.pitch_effectiveness,
        }


@dataclass
class PitcherParticipant:
    pitcher: Any
    pitch_count: int
    ratings: InGamePitcherRatings
    pitch_sequence: Tuple[str, ...] = ()
    pitcher_hand: str = "R"

    def to_dict(self) -> Dict[str, Any]:
        p_name = getattr(self.pitcher, "name", "Pitcher") if self.pitcher else "Pitcher"
        p_id = getattr(self.pitcher, "id", 1) if self.pitcher else 1
        return {
            "id": p_id,
            "name": p_name,
            "pitch_count": self.pitch_count,
            "pitcher_hand": self.pitcher_hand,
            "ratings": self.ratings.to_dict() if hasattr(self.ratings, "to_dict") else dict(self.ratings or {}),
            "pitch_sequence": list(self.pitch_sequence),
        }


@dataclass
class BatterParticipant:
    batter: Any
    ratings: InGameBatterRatings
    batter_line: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        b_name = getattr(self.batter, "name", "Batter") if self.batter else "Batter"
        b_id = getattr(self.batter, "id", 1) if self.batter else 1
        return {
            "id": b_id,
            "name": b_name,
            "ratings": self.ratings.to_dict() if hasattr(self.ratings, "to_dict") else dict(self.ratings or {}),
            "batter_line": dict(self.batter_line),
        }


@dataclass
class PitchContext:
    pitch_id: str
    count: CountSnapshot
    pitcher: PitcherParticipant
    batter: BatterParticipant
    inputs: PitchInput = field(default_factory=PitchInput)

    # Filled after pitcher execution
    delivery: Optional[Dict[str, Any]] = None
    actual_zone_name: Optional[str] = None
    is_strike: Optional[bool] = None

    # Standardized telemetry & detail payloads
    gameday_packet: Optional[Dict[str, Any]] = None
    pitch_details: Optional[Dict[str, Any]] = None

    # Filled after batter reaction & contact resolution
    reaction: Optional[Any] = None
    activity: Optional[Any] = None

    # Filled after state machine mutation
    game_delta: Optional[Dict[str, Any]] = None

    @classmethod
    def create(
        cls,
        pitch_id: str,
        pitcher: Any,
        batter: Any,
        count: CountSnapshot,
        pitch_input: Optional[PitchInput] = None,
        pitch_count: int = 1,
        recent_pitches: Optional[List[str]] = None,
        batter_line: Optional[Dict[str, int]] = None,
    ) -> "PitchContext":
        """
        Creates and snapshots a PitchContext for a single pitch.
        Calculates in-game situational ratings ONCE at creation.
        """
        pitcher_obj = getattr(pitcher, "pitcher", pitcher)
        pitcher_hand = (
            "L"
            if str(getattr(pitcher_obj, "handedness", "R") or "R").upper().startswith("L")
            else "R"
        )
        is_leverage = bool(
            count.runners[1] or count.runners[2] or (count.inning >= 7 and abs(count.score_diff) <= 2)
        )

        from ...pitching_engine.pitcher_info.adjusted_ratings import PitcherInstanceManager
        from ...batting_engine.batters import BatterInstanceManager

        pitcher_ratings = PitcherInstanceManager.get_adjusted_ratings(
            pitcher=pitcher_obj,
            pitch_count=pitch_count,
            balls=count.balls,
            strikes=count.strikes,
            is_leverage=is_leverage,
        )

        batter_ratings = BatterInstanceManager.get_adjusted_ratings(
            batter=batter,
            balls=count.balls,
            strikes=count.strikes,
            pitcher_hand=pitcher_hand,
        )

        pitcher_part = PitcherParticipant(
            pitcher=pitcher_obj,
            pitch_count=pitch_count,
            ratings=pitcher_ratings,
            pitch_sequence=tuple(recent_pitches or []),
            pitcher_hand=pitcher_hand,
        )

        batter_part = BatterParticipant(
            batter=batter,
            ratings=batter_ratings,
            batter_line=batter_line or {},
        )

        return cls(
            pitch_id=pitch_id,
            count=count,
            pitcher=pitcher_part,
            batter=batter_part,
            inputs=pitch_input or PitchInput(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Returns a complete, black-box JSON-serializable record of the pitch."""
        return {
            "pitch_id": self.pitch_id,
            "count": self.count.to_dict(),
            "pitcher": self.pitcher.to_dict(),
            "batter": self.batter.to_dict(),
            "inputs": self.inputs.to_dict(),
            "delivery": self.delivery,
            "actual_zone_name": self.actual_zone_name,
            "is_strike": self.is_strike,
            "reaction": getattr(self.reaction, "to_dict", lambda: self.reaction)() if self.reaction else None,
            "activity": getattr(self.activity, "to_dict", lambda: str(self.activity))() if self.activity else None,
            "game_delta": self.game_delta,
        }

