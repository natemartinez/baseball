"""
Active Pitcher State Module.

Encapsulates the persistent lifecycle of a pitcher on the mound:
1. Repertoire extraction (PitchArsenal) and baseline ratings evaluation (PitchArsenalMetrics)
   executed once upon mound entry (Cold Path).
2. Running in-game state tracking (pitch_count, pitch_confidences, pitch_effectivenesses).
3. Dynamic ratings adjustments (InGamePitcherRatings) reflecting count and fatigue deltas (Hot Path).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .pitch_objects import PitchArsenal
from .adjusted_ratings import (
    PitchArsenalMetrics,
    PitcherInstanceManager,
    InGamePitcherRatings,
    evaluate_pitch_arsenal,
)
from .pitch_confidence import NEUTRAL_CONFIDENCE


@dataclass
class ActivePitcherState:
    """
    Authoritative state for a pitcher currently active in a game matchup.
    Encapsulates static repertoire baselines and running in-game adjustments.
    """
    pitcher: Any
    arsenal: PitchArsenal
    baseline_metrics: Dict[str, PitchArsenalMetrics]
    pitch_count: int = 0
    pitch_confidences: Dict[str, float] = field(default_factory=dict)
    pitch_effectivenesses: Dict[str, float] = field(default_factory=dict)
    game_plan: Dict[Any, Any] = field(default_factory=dict)
    at_bat_history: Dict[Any, List[str]] = field(default_factory=dict)

    @classmethod
    def from_player(cls, pitcher: Any) -> 'ActivePitcherState':
        """
        Constructs and caches an active pitcher state from a Player domain object
        or a raw player dictionary.
        """
        if pitcher is None:
            raise ValueError("ActivePitcherState requires a pitcher object.")

        if isinstance(pitcher, dict):
            try:
                from backend.engine.models.player import Player
                pitcher = Player.from_dict(pitcher)
            except ImportError:
                pass

        arsenal = PitchArsenal.extract_from_pitcher(pitcher)
        raw_pitches = arsenal.pitches if arsenal else None
        baseline_metrics = evaluate_pitch_arsenal(pitcher, arsenal_items=raw_pitches)

        confidences = {p.name: NEUTRAL_CONFIDENCE for p in arsenal.pitches}
        effectivenesses = {
            name: metrics.baseline_effectiveness
            for name, metrics in baseline_metrics.items()
        }

        return cls(
            pitcher=pitcher,
            arsenal=arsenal,
            baseline_metrics=baseline_metrics,
            pitch_count=0,
            pitch_confidences=confidences,
            pitch_effectivenesses=effectivenesses,
        )

    def get_adjusted_ratings(
        self,
        balls: int = 0,
        strikes: int = 0,
        is_leverage: bool = False,
    ) -> InGamePitcherRatings:
        """
        Evaluates dynamic in-game ratings based on current pitch count and context.
        """
        return PitcherInstanceManager.get_adjusted_ratings(
            pitcher=self.pitcher,
            pitch_count=self.pitch_count,
            balls=balls,
            strikes=strikes,
            is_leverage=is_leverage,
        )

    def record_pitch(self, pitch_name: str) -> None:
        """
        Increments pitch count and advances running pitcher state.
        """
        self.pitch_count += 1

    @staticmethod
    def _batter_key(batter: Any) -> Any:
        if batter is None:
            return 'default'
        if isinstance(batter, dict):
            return batter.get('id') or batter.get('name') or 'unknown'
        return getattr(batter, 'id', None) or getattr(batter, 'name', None) or str(batter)

    def prebake_lineup_game_plan(self, lineup: List[Any]) -> None:
        """
        Pre-computes and caches matchup plans for all batters in the opposing lineup.
        """
        from ..pitch_selection.matchup import evaluate_platoon_and_arsenal

        for b in lineup:
            if b:
                key = self._batter_key(b)
                self.game_plan[key] = evaluate_platoon_and_arsenal(
                    self.pitcher, b, self.arsenal
                )

    def get_matchup_plan(self, batter: Any) -> Any:
        """
        Retrieves cached matchup plan or evaluates on demand.
        """
        key = self._batter_key(batter)
        if key not in self.game_plan:
            from ..pitch_selection.matchup import evaluate_platoon_and_arsenal

            self.game_plan[key] = evaluate_platoon_and_arsenal(
                self.pitcher, batter, self.arsenal
            )
        return self.game_plan[key]

    def record_at_bat_pitch(self, batter: Any, pitch_name: str) -> None:
        """
        Records a pitch thrown to a specific batter across their plate appearances.
        """
        key = self._batter_key(batter)
        if key not in self.at_bat_history:
            self.at_bat_history[key] = []
        self.at_bat_history[key].append(pitch_name)


