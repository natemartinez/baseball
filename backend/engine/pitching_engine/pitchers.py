"""
In-Game Pitcher State & Dynamic Rating Adjustments.
Manages pitcher ratings for a specific baseball game instance, computing dynamic
fatigue, stamina degradation, and situational command adjustments without modifying
persistent database player records.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class InGamePitcherRatings:
    """Encapsulates in-game adjusted ratings for a pitcher during an active game."""
    pitcher_id: Any
    pitcher_name: str
    base_command: float
    base_stamina: float
    base_velocity: float
    base_break: float
    effective_command: float
    effective_stamina: float
    effective_velocity: float
    effective_break: float
    fatigue_pct: float
    pitch_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pitcher_id': self.pitcher_id,
            'pitcher_name': self.pitcher_name,
            'base_command': round(self.base_command, 1),
            'base_stamina': round(self.base_stamina, 1),
            'effective_command': round(self.effective_command, 1),
            'effective_stamina': round(self.effective_stamina, 1),
            'effective_velocity': round(self.effective_velocity, 1),
            'effective_break': round(self.effective_break, 1),
            'fatigue_pct': round(self.fatigue_pct, 1),
            'pitch_count': self.pitch_count,
        }


class PitcherInstanceManager:
    """Calculates in-game situational ratings without mutating database records."""

    @staticmethod
    def extract_base_rating(pitcher: Any, category: str, default: float = 75.0) -> float:
        """Safely retrieves a rating attribute from a domain Player."""
        if not pitcher:
            return float(default)

        if hasattr(pitcher, 'get_rating'):
            return float(pitcher.get_rating(category, default))

        if isinstance(pitcher, dict):
            ratings = pitcher.get('ratings', {})
            if isinstance(ratings, dict):
                return float(ratings.get(category) or ratings.get(category.lower()) or default)
            return float(pitcher.get(category.lower()) or pitcher.get(category) or default)

        return float(default)

    @classmethod
    def get_adjusted_ratings(
        cls,
        pitcher: Any,
        pitch_count: int,
        balls: int = 0,
        strikes: int = 0
    ) -> InGamePitcherRatings:
        """
        Calculates adjusted ratings for the current game instance based on pitch count
        and count leverage. Does NOT modify the underlying persistent player object.
        """
        if not pitcher:
            pitcher_id, pitcher_name = 1, "Pitcher"
            base_control, base_stamina, base_velocity, base_break = 70.0, 75.0, 94.0, 85.0
        else:
            # Ensure domain Player contract
            if isinstance(pitcher, dict):
                try:
                    from backend.models.player import Player
                    pitcher = Player.from_dict(pitcher)
                except ImportError:
                    pass

            pitcher_id = getattr(pitcher, 'id', None) or (pitcher.get('id', 1) if isinstance(pitcher, dict) else 1)
            pitcher_name = getattr(pitcher, 'name', None) or (pitcher.get('name', 'Pitcher') if isinstance(pitcher, dict) else 'Pitcher')

            base_control = cls.extract_base_rating(pitcher, 'Control', default=70.0)
            base_stamina = cls.extract_base_rating(pitcher, 'Stamina', default=75.0)
            base_velocity = cls.extract_base_rating(pitcher, 'Velocity', default=94.0)
            base_break = cls.extract_base_rating(pitcher, 'Break', default=85.0)

        # Fatigue curve: stamina degrades once pitch count exceeds 75% of base stamina
        stamina_threshold = base_stamina * 0.75
        if pitch_count > stamina_threshold:
            overage = pitch_count - stamina_threshold
            fatigue_pct = min(50.0, (overage / max(1.0, base_stamina * 0.6)) * 40.0)
        else:
            fatigue_pct = (pitch_count / max(1.0, stamina_threshold)) * 10.0

        effective_stamina = max(10.0, base_stamina - (fatigue_pct * 0.8))

        # Command degrades gently with high pitch counts / extreme fatigue
        command_decay = (fatigue_pct / 100.0) * 8.0
        effective_command = max(35.0, base_control - command_decay)

        # Velocity decreases slightly when heavily fatigued (> 25% fatigue)
        velo_penalty = 0.0
        if fatigue_pct > 25.0:
            velo_penalty = (fatigue_pct - 25.0) * 0.05
        effective_velocity = max(86.0, base_velocity - velo_penalty)

        # Break remains relatively resilient but loses bite under high fatigue
        break_penalty = (fatigue_pct / 100.0) * 5.0
        effective_break = max(50.0, base_break - break_penalty)

        return InGamePitcherRatings(
            pitcher_id=pitcher_id,
            pitcher_name=pitcher_name,
            base_command=base_control,
            base_stamina=base_stamina,
            base_velocity=base_velocity,
            base_break=base_break,
            effective_command=effective_command,
            effective_stamina=effective_stamina,
            effective_velocity=effective_velocity,
            effective_break=effective_break,
            fatigue_pct=fatigue_pct,
            pitch_count=pitch_count
        )

