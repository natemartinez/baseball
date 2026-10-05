"""
Pitching Engine: Main Coordinator.
Coordinates pitch strategy, pitch selection, target intent, bivariate Gaussian delivery,
and in-game pitcher rating adjustments for a baseball game instance.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from .pitch_objects import PitchArsenal, PITCH_CATEGORIES
from .strategy import PitchStrategy
from .pitchers import PitcherInstanceManager, InGamePitcherRatings
from .calculations import calculate_pitch_delivery

try:
    from backend.engine.gameday_math import (
        classify_gameday_zone,
        get_zone_nominal_target,
        determine_situation_category,
    )
except ImportError:
    from gameday_math import (
        classify_gameday_zone,
        get_zone_nominal_target,
        determine_situation_category,
    )


class PitchingEngine:
    """
    Authoritative pitching coordinator for an active game matchup.
    Communicates between GameEngine and pitching submodules (strategy, physics, pitcher ratings).
    """

    def __init__(self, pitcher: Any, batter: Any):
        # Enforce domain model boundary at engine entry point
        if isinstance(pitcher, dict):
            try:
                from backend.models.player import Player
                pitcher = Player.from_dict(pitcher)
            except ImportError:
                pass
        if isinstance(batter, dict):
            try:
                from backend.models.player import Player
                batter = Player.from_dict(batter)
            except ImportError:
                pass

        # Check if either object is invalid
        if not pitcher:
            raise ValueError("PitchingEngine requires a pitcher object.")
        if not batter:
            raise ValueError("PitchingEngine requires a batter object.")

        self.pitcher = pitcher
        self.batter = batter
        self.strategy = PitchStrategy(pitcher, batter)
        self.arsenal = PitchArsenal.extract_from_pitcher(pitcher)
        self.pitch_arsenal = self.strategy.pitch_arsenal


    def execute_pitch( # Returns "Delivery", line 214 -> game_engine.py
        self,
        balls: int,
        strikes: int,
        outs: int = 0,
        runners: Tuple[bool, bool, bool] = (False, False, False),
        pitch_count: int = 1,
        recent_pitches: Optional[List[str]] = None,
        pitch_intent: Optional[str] = None,
        pitch_type: Optional[str] = None,
        target_zone: Optional[str] = None,
        custom_target: Optional[Dict[str, float]] = None,
        situation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main Hand-Off Method:
        Executes the entire pitching pipeline for a pitch delivery:
          1. Computes in-game adjusted pitcher ratings (fatigue, effective command).
          2. Calculates pitch usage strategy and selects the recommended pitch.
          3. Evaluates target intent coordinates (nominal zone or custom override).
          4. Resolves bivariate Gaussian delivery error and pitch effectiveness.
        """
        r1, r2, r3 = runners
        sit_category = situation or determine_situation_category(balls, strikes, outs, r1, r2, r3)

        # 1. In-game adjusted ratings (without mutating persistent database objects)
        adjusted_ratings = PitcherInstanceManager.get_adjusted_ratings(
            pitcher=self.pitcher,
            pitch_count=pitch_count,
            balls=balls,
            strikes=strikes
        )

        # 2. Pitch Usage Strategy & Selection
        strat_result = self.strategy.choose_pitch(
            balls=balls,
            strikes=strikes,
            situation=sit_category,
            preferred_intent=pitch_intent,
            recent_pitches=recent_pitches
        )

        selected_pitch_name = pitch_type or strat_result['selected_pitch']
        velocity_mph = strat_result['velocity_mph']
        spin_rpm = strat_result['spin_rpm']

        # Adjust velocity and spin slightly based on in-game fatigue
        if adjusted_ratings.fatigue_pct > 25.0:
            velocity_mph = max(84.0, velocity_mph - ((adjusted_ratings.fatigue_pct - 25.0) * 0.05))
            spin_rpm = max(1900, int(spin_rpm - (adjusted_ratings.fatigue_pct * 4.0)))

        # 3. Target Intent & Coordinates
        is_manual_override = False
        if custom_target and 'x' in custom_target and 'z' in custom_target:
            target_x = float(custom_target['x'])
            target_z = float(custom_target['z'])
            intended_zone_cat = classify_gameday_zone(target_x, target_z)
            nominal_zone = target_zone or strat_result['recommended_zone']
            is_manual_override = True
        else:
            nominal_zone = target_zone or strat_result['recommended_zone']
            target_x, target_z, intended_zone_cat = get_zone_nominal_target(nominal_zone)

        # 4. Delivery Execution & Gaussian Error
        delivery_math = calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=adjusted_ratings.base_command,
            pitch_count=pitch_count,
            stamina=adjusted_ratings.base_stamina,
            intended_zone_cat=intended_zone_cat
        )

        pitch_category = PITCH_CATEGORIES.get(selected_pitch_name, 'Fastball')

        return {
            'selected_pitch': selected_pitch_name,
            'pitch_category': pitch_category,
            'velocity_mph': round(velocity_mph, 1),
            'spin_rpm': spin_rpm,
            'nominal_zone': nominal_zone,
            'target_x': target_x,
            'target_z': target_z,
            'intended_zone_cat': intended_zone_cat,
            'is_manual_override': is_manual_override,
            'realized_x': delivery_math['realized_x'],
            'realized_z': delivery_math['realized_z'],
            'realized_zone_cat': delivery_math['realized_zone_cat'],
            'is_strike': delivery_math['is_strike'],
            'sigma': delivery_math['sigma'],
            'delta_x_in': delivery_math['delta_x_in'],
            'delta_z_in': delivery_math['delta_z_in'],
            'radial_miss_in': delivery_math['radial_miss_in'],
            'is_heart_leak': delivery_math['is_heart_leak'],
            'hit_shadow_target': delivery_math['hit_shadow_target'],
            'pitch_effectiveness': delivery_math['effectiveness_score'],
            'strat_result': strat_result,
            'adjusted_ratings': adjusted_ratings.to_dict(),
        }
