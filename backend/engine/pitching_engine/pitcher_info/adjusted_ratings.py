"""
In-Game Pitcher State & Dynamic Rating Adjustments.
Manages pitcher ratings for a specific baseball game instance, computing dynamic
fatigue, stamina degradation, and situational command adjustments without modifying
persistent database player records.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from ...game_engine.gameday_math import (
    get_max_error_radius_inches,
    calculate_execution_sigma,
)
from ..pitch_execution.pitch_objects import PITCH_CATEGORIES

try:
    from tiers import (
        AbilityTier,
        get_ability_tier,
        PITCH_TYPE_MODIFIERS,
        get_pitch_type_modifier,
    )
except ImportError:
    import sys
    from pathlib import Path
    root_path = str(Path(__file__).resolve().parents[4])
    if root_path not in sys.path:
        sys.path.insert(0, root_path)
    from tiers import (
        AbilityTier,
        get_ability_tier,
        PITCH_TYPE_MODIFIERS,
        get_pitch_type_modifier,
    )


@dataclass
class PitchArsenalMetrics:
    """Calculated delivery attributes for an individual pitch in an arsenal."""
    pitch_name: str
    category: str
    base_control: float
    effective_command: float
    max_radius_inches: float
    sigma: float
    baseline_effectiveness: float
    horizontal_break_in: float
    induced_vertical_break_in: float
    velocity_mph: float
    spin_rpm: int
    pitch_id: str = ""
    spin_axis_deg: float = 180.0
    tunnel_partners: List[str] = field(default_factory=list)
    ability_tier: Optional[AbilityTier] = None

    def __post_init__(self):
        if self.ability_tier is None:
            self.ability_tier = get_ability_tier(self.effective_command)

    def to_dict(self) -> Dict[str, Any]:
        tier_val = (
            self.ability_tier.value
            if hasattr(self.ability_tier, 'value')
            else (str(self.ability_tier) if self.ability_tier is not None else None)
        )
        return {
            'pitch_id': self.pitch_id,
            'pitch_name': self.pitch_name,
            'category': self.category,
            'base_control': round(self.base_control, 1),
            'command': round(self.base_control, 1),
            'effective_command': round(self.effective_command, 1),
            'ability_tier': tier_val,
            'max_radius_inches': round(self.max_radius_inches, 3),
            'sigma': round(self.sigma, 4),
            'baseline_effectiveness': round(self.baseline_effectiveness, 1),
            'horizontal_break_in': self.horizontal_break_in,
            'induced_vertical_break_in': self.induced_vertical_break_in,
            'velocity_mph': round(self.velocity_mph, 1),
            'spin_rpm': self.spin_rpm,
            'spin_rate_rpm': self.spin_rpm,
            'spin_axis_deg': self.spin_axis_deg,
            'tunnel_partners': list(self.tunnel_partners),
        }


@dataclass
class InGamePitcherRatings:
    """Encapsulates in-game adjusted ratings for a pitcher during an active game."""
    pitcher_id: Any = 1
    pitcher_name: str = "Pitcher"
    base_command: float = 75.0
    base_stamina: float = 75.0
    base_velocity: float = 94.0
    base_break: float = 85.0
    effective_command: float = 75.0
    effective_stamina: float = 75.0
    effective_velocity: float = 94.0
    effective_break: float = 85.0
    fatigue_pct: float = 0.0
    pitch_count: int = 0
    pitcher: Optional[Any] = None
    base_composure: float = 75.0
    effective_composure: float = 75.0
    consistency: float = 75.0
    composure: Optional[float] = None
    is_leverage: bool = False

    def __post_init__(self):
        if self.pitcher is not None:
            if hasattr(self.pitcher, 'id') and self.pitcher.id is not None:
                self.pitcher_id = self.pitcher.id
            if hasattr(self.pitcher, 'name') and self.pitcher.name is not None:
                self.pitcher_name = self.pitcher.name
            if hasattr(self.pitcher, 'stamina') and self.pitcher.stamina is not None:
                self.base_stamina = float(self.pitcher.stamina)
            if hasattr(self.pitcher, 'composure') and self.pitcher.composure is not None:
                self.base_composure = float(self.pitcher.composure)
            if hasattr(self.pitcher, 'consistency') and self.pitcher.consistency is not None:
                self.consistency = float(self.pitcher.consistency)
            if hasattr(self.pitcher, 'ratings') and isinstance(self.pitcher.ratings, dict):
                if 'Control' in self.pitcher.ratings:
                    self.base_command = float(self.pitcher.ratings['Control'])
                if 'Composure' in self.pitcher.ratings and self.base_composure == 75.0:
                    self.base_composure = float(self.pitcher.ratings['Composure'])
                if 'Consistency' in self.pitcher.ratings and self.consistency == 75.0:
                    self.consistency = float(self.pitcher.ratings['Consistency'])

        if self.composure is not None:
            if self.base_composure == 75.0 and self.effective_composure == 75.0:
                self.base_composure = float(self.composure)
            self.effective_composure = float(self.composure)
        elif self.effective_composure == 75.0 and self.base_composure != 75.0:
            self.effective_composure = self.base_composure

        if self.composure is None:
            self.composure = self.effective_composure

        if self.effective_command == 75.0 and self.base_command != 75.0:
            command_decay = (self.fatigue_pct / 100.0) * 8.0
            self.effective_command = max(35.0, self.base_command - command_decay)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pitcher_id': self.pitcher_id,
            'pitcher_name': self.pitcher_name,
            'base_command': round(self.base_command, 1),
            'base_stamina': round(self.base_stamina, 1),
            'base_composure': round(self.base_composure, 1),
            'composure': round(self.effective_composure, 1),
            'effective_composure': round(self.effective_composure, 1),
            'consistency': round(self.consistency, 1),
            'effective_command': round(self.effective_command, 1),
            'effective_stamina': round(self.effective_stamina, 1),
            'effective_velocity': round(self.effective_velocity, 1),
            'effective_break': round(self.effective_break, 1),
            'fatigue_pct': round(self.fatigue_pct, 1),
            'pitch_count': self.pitch_count,
            'is_leverage': self.is_leverage,
        }


class PitcherInstanceManager:
    """Calculates in-game situational ratings without mutating database records."""

    @staticmethod
    def extract_base_rating(pitcher: Any, category: str, default: float = 75.0) -> float:
        """Safely retrieves a rating attribute from a domain Player."""
        if not pitcher:
            return float(default)

        cat_lower = category.lower()

        if hasattr(pitcher, 'stamina') and cat_lower == 'stamina' and pitcher.stamina is not None:
            return float(pitcher.stamina)
        if hasattr(pitcher, 'composure') and cat_lower == 'composure' and pitcher.composure is not None:
            return float(pitcher.composure)
        if hasattr(pitcher, 'consistency') and cat_lower in ('consistency', 'release_consistency') and pitcher.consistency is not None:
            return float(pitcher.consistency)
        if hasattr(pitcher, 'release_consistency') and cat_lower in ('consistency', 'release_consistency') and pitcher.release_consistency is not None:
            return float(pitcher.release_consistency)

        if hasattr(pitcher, 'get_rating'):
            try:
                val = pitcher.get_rating(category, default)
                if val is not None:
                    return float(val)
            except Exception:
                pass

        if isinstance(pitcher, dict):
            ratings = pitcher.get('ratings', {})
            if isinstance(ratings, dict):
                val = ratings.get(category) or ratings.get(cat_lower) or ratings.get(category.capitalize())
                if val is not None:
                    return float(val)
            val = pitcher.get(cat_lower) or pitcher.get(category)
            if val is not None:
                return float(val)

        return float(default)

    @classmethod
    def get_adjusted_ratings(
        cls,
        pitcher: Any,
        pitch_count: int,
        balls: int = 0,
        strikes: int = 0,
        is_leverage: bool = False,
    ) -> InGamePitcherRatings:
        """
        Calculates adjusted ratings for the current game instance based on pitch count
        and count leverage. Does NOT modify the underlying persistent player object.
        """
        if not pitcher:
            pitcher_id, pitcher_name = 1, "Pitcher"
            base_control, base_stamina, base_velocity, base_break = 70.0, 75.0, 94.0, 85.0
            base_composure, consistency = 75.0, 75.0
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
            base_composure = cls.extract_base_rating(pitcher, 'Composure', default=75.0)
            consistency = cls.extract_base_rating(pitcher, 'Consistency', default=75.0)

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

        # Composure stress under leverage
        if is_leverage:
            comp_scale = max(0.0, (100.0 - base_composure) / 100.0)
            cons_dampener = max(0.2, 1.0 - (consistency / 100.0) * 0.5)
            comp_stress = 10.0 * comp_scale * cons_dampener
            effective_composure = max(30.0, min(99.0, base_composure - comp_stress))
        else:
            effective_composure = base_composure

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
            pitch_count=pitch_count,
            pitcher=pitcher,
            base_composure=base_composure,
            effective_composure=effective_composure,
            consistency=consistency,
            composure=effective_composure,
            is_leverage=is_leverage,
        )

    @staticmethod
    def compute_effective_command(
        base_command: float,
        pitch_type: str,
        pitch_count: int,
        stamina: float,
        composure: float,
        consistency: float,
        is_leverage: bool = False,
        fatigue_pct: Optional[float] = None,
        confidence: Optional[float] = None,
        effectiveness: Optional[float] = None,
    ) -> Tuple[float, AbilityTier]:
        return compute_effective_command(
            base_command=base_command,
            pitch_type=pitch_type,
            pitch_count=pitch_count,
            stamina=stamina,
            composure=composure,
            consistency=consistency,
            is_leverage=is_leverage,
            fatigue_pct=fatigue_pct,
            confidence=confidence,
            effectiveness=effectiveness,
        )

    @classmethod
    def evaluate_pitch_arsenal(
        cls,
        pitcher: Any,
        arsenal_items: Optional[List[Any]] = None,
        in_game_ratings: Optional[InGamePitcherRatings] = None,
        pitch_confidences: Optional[Dict[str, float]] = None,
        pitch_effectivenesses: Optional[Dict[str, float]] = None,
    ) -> Dict[str, PitchArsenalMetrics]:
        """
        Evaluates a pitcher's repertoire to calculate realistic delivery metrics for
        each pitch:
          - Base control acts as a baseline competency floor.
          - Individual pitch control, movement magnitude, spin, and category modulate
            the pitch's effective command and error radius.
          - Calculates exact max radius (inches), execution sigma, baseline effectiveness,
            and ability_tier.
        """
        pitcher_control = cls.extract_base_rating(pitcher, 'Control', default=75.0)

        raw_list = arsenal_items
        if raw_list is None:
            if hasattr(pitcher, 'pitch_arsenal'):
                raw_list = pitcher.pitch_arsenal
            elif isinstance(pitcher, dict):
                raw_list = pitcher.get('pitch_arsenal') or pitcher.get('arsenal') or []
            else:
                raw_list = []

        if in_game_ratings:
            p_pitch_count = in_game_ratings.pitch_count
            p_stamina = in_game_ratings.base_stamina
            p_composure = in_game_ratings.effective_composure
            p_consistency = in_game_ratings.consistency
            p_is_leverage = in_game_ratings.is_leverage
            p_fatigue_pct = in_game_ratings.fatigue_pct
        else:
            p_pitch_count = 0
            p_stamina = cls.extract_base_rating(pitcher, 'Stamina', default=75.0)
            p_composure = cls.extract_base_rating(pitcher, 'Composure', default=75.0)
            p_consistency = cls.extract_base_rating(pitcher, 'Consistency', default=75.0)
            p_is_leverage = False
            p_fatigue_pct = 0.0

        metrics_map: Dict[str, PitchArsenalMetrics] = {}

        for item in (raw_list or []):
            if hasattr(item, 'name'):
                p_name = item.name
                pitch_id = getattr(item, 'id', getattr(item, 'pitch_id', '')) or ''
                category = getattr(item, 'category', None) or PITCH_CATEGORIES.get(p_name, 'Fastball')
                velocity_mph = float(getattr(item, 'velocity_mph', 94.0))
                spin_rpm = int(getattr(item, 'spin_rpm', getattr(item, 'spin_rate_rpm', 2400)))
                spin_axis_deg = float(getattr(item, 'spin_axis_deg', 180.0))
                tunnel_partners = list(getattr(item, 'tunnel_partners', []))
                break_rating = float(getattr(item, 'break_rating', 80.0))
                pitch_control = float(getattr(item, 'command', getattr(item, 'control_rating', pitcher_control)))
                hb = float(getattr(item, 'horizontal_break_in', 0.0))
                ivb = float(getattr(item, 'induced_vertical_break_in', 0.0))
                precomputed_radius = getattr(item, 'max_radius_inches', None)
                precomputed_sigma = getattr(item, 'sigma', None)
            elif isinstance(item, dict):
                p_name = item.get('name') or item.get('pitch') or '4-Seam Fastball'
                pitch_id = str(item.get('id') or item.get('pitch_id') or '')
                category = item.get('category') or PITCH_CATEGORIES.get(p_name, 'Fastball')
                velocity_mph = float(item.get('velocity_mph') or item.get('avg_velo_mph') or 94.0)
                spin_rpm = int(item.get('spin_rate_rpm') or item.get('spin_rpm') or item.get('avg_spin_rpm') or 2400)
                spin_axis_deg = float(item.get('spin_axis_deg', 180.0))
                tunnel_partners = list(item.get('tunnel_partners') or [])
                break_rating = float(item.get('break_rating') or item.get('break') or 80.0)
                pitch_control = float(item.get('command') or item.get('control_rating') or item.get('control') or pitcher_control)
                hb = float(item.get('horizontal_break_in', 0.0))
                ivb = float(item.get('induced_vertical_break_in', 0.0))
                precomputed_radius = item.get('max_radius_inches')
                precomputed_sigma = item.get('sigma')
            else:
                continue

            pitch_type_key = pitch_id or p_name
            pitch_conf: Optional[float] = None
            if pitch_confidences:
                pitch_conf = pitch_confidences.get(pitch_id)
                if pitch_conf is None:
                    pitch_conf = pitch_confidences.get(p_name)
                if pitch_conf is None:
                    pitch_conf = pitch_confidences.get('overall')

            pitch_eff: Optional[float] = None
            if pitch_effectivenesses:
                pitch_eff = pitch_effectivenesses.get(pitch_id)
                if pitch_eff is None:
                    pitch_eff = pitch_effectivenesses.get(p_name)

            effective_cmd, ability_tier = compute_effective_command(
                base_command=pitch_control,
                pitch_type=pitch_type_key,
                pitch_count=p_pitch_count,
                stamina=p_stamina,
                composure=p_composure,
                consistency=p_consistency,
                is_leverage=p_is_leverage,
                fatigue_pct=p_fatigue_pct if (in_game_ratings and in_game_ratings.fatigue_pct > 0) else None,
                confidence=pitch_conf,
                effectiveness=pitch_eff,
            )

            max_radius = get_max_error_radius_inches(effective_cmd)
            sigma = calculate_execution_sigma(effective_cmd)
            if in_game_ratings and in_game_ratings.fatigue_pct > 0:
                sigma_scale = 1.0 + (in_game_ratings.fatigue_pct / 100.0) * 0.25
                sigma = round(sigma * sigma_scale, 4)
                max_radius = round(max_radius * sigma_scale, 3)

            baseline_eff = round(
                max(
                    10.0,
                    min(
                        99.0,
                        0.35 * effective_cmd
                        + 0.35 * break_rating
                        + 0.20 * min(99.0, (velocity_mph / 100.0) * 100.0)
                        + 0.10 * min(99.0, (spin_rpm / 3000.0) * 100.0),
                    ),
                ),
                1,
            )

            metrics = PitchArsenalMetrics(
                pitch_id=pitch_id,
                pitch_name=p_name,
                category=category,
                base_control=pitch_control,
                effective_command=effective_cmd,
                max_radius_inches=max_radius,
                sigma=sigma,
                baseline_effectiveness=baseline_eff,
                horizontal_break_in=hb,
                induced_vertical_break_in=ivb,
                velocity_mph=velocity_mph,
                spin_rpm=spin_rpm,
                spin_axis_deg=spin_axis_deg,
                tunnel_partners=tunnel_partners,
                ability_tier=ability_tier,
            )
            metrics_map[p_name] = metrics
            if pitch_id:
                metrics_map[pitch_id] = metrics

        return metrics_map


def compute_effective_command(
    base_command: float,
    pitch_type: str,
    pitch_count: int,
    stamina: float,
    composure: float,
    consistency: float,
    is_leverage: bool = False,
    fatigue_pct: Optional[float] = None,
    confidence: Optional[float] = None,
    effectiveness: Optional[float] = None,
) -> Tuple[float, AbilityTier]:
    """Computes effective command factoring pitch difficulty, fatigue, composure stress, confidence, and effectiveness.

    Formula:
    - Pitch type difficulty penalty: cmd = base_command - max(0.0, (pitch_type_mod - 1.0) * 20.0)
    - Fatigue decay: based on pitch count relative to stamina (up to 10 points deduction when fatigued)
    - Composure stress under leverage: when is_leverage is True, stress penalty is scaled by
      (100 - composure) / 100, dampened by consistency / 100.
    - Confidence scaling:
      - 50.0 is neutral baseline (0 adjustment).
      - < 50.0 penalizes command by up to -22.0 points at 0% confidence.
      - > 50.0 boosts command by up to +10.0 points at 100% confidence.
    - Effectiveness scaling:
      - 80.0 is neutral baseline (0 adjustment).
      - > 80.0 boosts command by up to +12.0 points at 100% effectiveness (+6.0 at 90%).
      - < 80.0 penalizes command by up to -30.0 points (e.g. -3.75 at 75%, -15.0 at 60%).
    - Clamped between 30.0 and 99.0.
    - Returns (effective_command, ability_tier).
    """
    # 1. Pitch type difficulty penalty (additive deduction, softening penalty for non-elite pitchers)
    pitch_type_mod = get_pitch_type_modifier(pitch_type)
    pitch_diff_penalty = max(0.0, (pitch_type_mod - 1.0) * 20.0)
    cmd = float(base_command) - pitch_diff_penalty

    # 2. Fatigue decay
    if fatigue_pct is not None:
        fatigue_val = max(0.0, min(100.0, float(fatigue_pct)))
        fatigue_decay = min(10.0, (fatigue_val / 50.0) * 10.0 if fatigue_val <= 50.0 else 10.0)
    elif pitch_count <= 0:
        fatigue_decay = 0.0
    else:
        stamina_val = max(1.0, float(stamina))
        stamina_threshold = stamina_val * 0.75
        if pitch_count > stamina_threshold:
            overage = pitch_count - stamina_threshold
            fatigue_ratio = min(1.0, overage / max(1.0, stamina_val * 0.6))
            fatigue_decay = 2.0 + fatigue_ratio * 8.0  # 2.0 to 10.0 points
        else:
            fatigue_decay = (pitch_count / max(1.0, stamina_threshold)) * 2.0  # 0.0 to 2.0 points

    # 3. Composure stress under leverage
    if is_leverage:
        comp_scale = max(0.0, (100.0 - float(composure)) / 100.0)
        cons_dampener = max(0.2, 1.0 - (float(consistency) / 100.0) * 0.5)
        composure_penalty = 10.0 * comp_scale * cons_dampener
    else:
        composure_penalty = 0.0

    # 4. Confidence effectiveness adjustment
    if confidence is not None:
        conf_val = max(0.0, min(100.0, float(confidence)))
        if conf_val < 50.0:
            confidence_adj = -((50.0 - conf_val) / 50.0) * 22.0
        else:
            confidence_adj = ((conf_val - 50.0) / 50.0) * 10.0
    else:
        confidence_adj = 0.0

    # 5. Pitch effectiveness adjustment
    if effectiveness is not None:
        from ..pitch_effectiveness import calculate_command_adjustment_from_effectiveness
        eff_adj = calculate_command_adjustment_from_effectiveness(effectiveness)
    else:
        eff_adj = 0.0

    # 6. Total and clamp
    raw_effective = cmd - fatigue_decay - composure_penalty + confidence_adj + eff_adj
    effective_command = max(30.0, min(99.0, raw_effective))
    effective_command = round(effective_command, 2)

    # 7. Evaluate AbilityTier
    ability_tier = get_ability_tier(effective_command)

    return effective_command, ability_tier


def evaluate_pitch_arsenal(
    pitcher: Any,
    arsenal_items: Optional[List[Any]] = None,
    in_game_ratings: Optional[InGamePitcherRatings] = None,
    pitch_confidences: Optional[Dict[str, float]] = None,
    pitch_effectivenesses: Optional[Dict[str, float]] = None,
) -> Dict[str, PitchArsenalMetrics]:
    """Top-level convenience function for evaluating pitcher repertoire metrics."""
    return PitcherInstanceManager.evaluate_pitch_arsenal(
        pitcher,
        arsenal_items=arsenal_items,
        in_game_ratings=in_game_ratings,
        pitch_confidences=pitch_confidences,
        pitch_effectivenesses=pitch_effectivenesses,
    )


