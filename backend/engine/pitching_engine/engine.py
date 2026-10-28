"""
Pitching Engine: Main Coordinator.
Coordinates pitch strategy, pitch selection, target intent, bivariate Gaussian delivery,
and in-game pitcher rating adjustments for a baseball game instance.
"""

import random
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from .pitch_execution.pitch_objects import PitchArsenal, PITCH_CATEGORIES, movement_for
from .pitch_strategy.strategy import PitchStrategy
from .pitcher_info.pitchers import PitcherInstanceManager, InGamePitcherRatings
from .pitch_execution.calculations import calculate_pitch_delivery

from ..game_engine.gameday_math import (
    classify_gameday_zone,
    sample_zone_target,
    determine_situation_category,
    is_rulebook_strike,
)


class PitchingEngine:
    """
    Authoritative pitching coordinator for an active game matchup.
    Communicates between GameEngine and pitching submodules (strategy, physics, pitcher ratings).
    """

    def __init__(
        self,
        pitcher: Any,
        batter: Any,
        rng: Optional[random.Random] = None,
    ):
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
        self.rng = rng or random
        self.strategy = PitchStrategy(pitcher, batter, rng=self.rng)
        self.arsenal = PitchArsenal.extract_from_pitcher(pitcher)
        self.pitch_arsenal = self.strategy.pitch_arsenal


    def _mix_ball_intent(self, recommended_zone: str, balls: int, strikes: int) -> str:
        """
        Occasionally aim off the plate in early and leverage counts. Without
        this mix a high-command pitcher only targets the rulebook rectangle,
        making walks effectively impossible. The recommended strike target
        remains the default; a chase/waste target is selected on a realistic
        minority of pitches.
        """
        waste_chance = 0.0
        if strikes == 2 and balls >= 2:
            waste_chance = 0.50
        elif balls == 3 and strikes == 0:
            waste_chance = 0.40
        elif balls == 3 and strikes == 1:
            waste_chance = 0.45
        elif balls == 2:
            waste_chance = 0.52
        elif balls == 0 and strikes == 0:
            # Real first-pitch strike rate is far below the command model's
            # default, so mix in a deliberate ball a realistic share of the time.
            waste_chance = 0.38
        elif balls == 0 and strikes == 1:
            waste_chance = 0.45
        elif balls == 1 and strikes == 0:
            waste_chance = 0.45
        elif balls == 1 and strikes == 1:
            waste_chance = 0.38

        if waste_chance > 0.0 and self.rng.random() < waste_chance:
            return 'chase-low' if self.rng.random() < 0.35 else 'chase-away'
        return recommended_zone

    def execute_pitch( # Returns "Delivery", line 214 -> game_engine/engine.py
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
        practice: bool = False,
    ) -> Dict[str, Any]:
        """
        Main Hand-Off Method:
        Executes the entire pitching pipeline for a pitch delivery:
          1. Computes in-game adjusted pitcher ratings (fatigue, effective command).
          2. Calculates pitch usage strategy and selects the recommended pitch.
          3. Evaluates target intent coordinates (nominal zone or custom override).
          4. Resolves bivariate Gaussian delivery error and pitch effectiveness.

        ``practice`` is the Batting Practice drill path: the requested pitch and
        exact custom target are forced, command error is zero, and the pitcher
        is treated as fresh. The AI strategy does not choose the pitch.
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
        selected_pitch_obj = self.arsenal.get(selected_pitch_name)
        velocity_mph = strat_result['velocity_mph']
        spin_rpm = strat_result['spin_rpm']

        if practice:
            # A fresh pitcher throws the drill pitch at its base velocity/spin.
            if selected_pitch_obj is not None:
                velocity_mph = float(selected_pitch_obj.velocity_mph)
                spin_rpm = int(selected_pitch_obj.spin_rpm)
            adjusted_ratings = PitcherInstanceManager.get_adjusted_ratings(
                pitcher=self.pitcher,
                pitch_count=1,
                balls=0,
                strikes=0,
            )
        elif adjusted_ratings.fatigue_pct > 25.0:
            # Adjust velocity and spin slightly based on in-game fatigue
            velocity_mph = max(84.0, velocity_mph - ((adjusted_ratings.fatigue_pct - 25.0) * 0.05))
            spin_rpm = max(1900, int(spin_rpm - (adjusted_ratings.fatigue_pct * 4.0)))

        # 3. Target Intent & Coordinates
        is_manual_override = False
        if practice:
            if not custom_target or 'x' not in custom_target or 'z' not in custom_target:
                raise ValueError('Practice pitches require an exact custom target')
            target_x = float(custom_target['x'])
            target_z = float(custom_target['z'])
            intended_zone_cat = classify_gameday_zone(target_x, target_z)
            nominal_zone = target_zone or strat_result['recommended_zone']
            is_manual_override = True
        elif custom_target and 'x' in custom_target and 'z' in custom_target:
            target_x = float(custom_target['x'])
            target_z = float(custom_target['z'])
            intended_zone_cat = classify_gameday_zone(target_x, target_z)
            nominal_zone = target_zone or strat_result['recommended_zone']
            is_manual_override = True
        else:
            nominal_zone = target_zone or strat_result['recommended_zone']
            if not target_zone:
                nominal_zone = self._mix_ball_intent(nominal_zone, balls, strikes)
            target_x, target_z, intended_zone_cat = sample_zone_target(
                nominal_zone, rng=self.rng.random
            )

        # 4. Delivery Execution & Gaussian Error
        if practice:
            # No command error, no zone sampling, no velocity RNG.
            delivery_math = {
                'sigma': 0.0,
                'max_radius_inches': 0.0,
                'realized_x': target_x,
                'realized_z': target_z,
                'realized_zone_cat': intended_zone_cat,
                'is_strike': is_rulebook_strike(target_x, target_z),
                'delta_x_in': 0.0,
                'delta_z_in': 0.0,
                'radial_miss_in': 0.0,
                'is_heart_leak': False,
                'hit_shadow_target': intended_zone_cat == 'SHADOW',
                'effectiveness_score': 100.0,
            }
            strat_result = dict(strat_result)
            strat_result.update({
                'selected_pitch': selected_pitch_name,
                'velocity_mph': round(velocity_mph, 1),
                'spin_rpm': spin_rpm,
                'dynamic_modifier': 1.0,
                'recommended_zone': nominal_zone,
                'strategy_name': 'PRACTICE_DRILL',
                'rationale': 'Batting practice: forced pitch and exact target.',
            })
        else:
            delivery_math = calculate_pitch_delivery(
                target_x=target_x,
                target_z=target_z,
                command_rating=adjusted_ratings.base_command,
                pitch_count=pitch_count,
                stamina=adjusted_ratings.base_stamina,
                intended_zone_cat=intended_zone_cat,
                rng=self.rng.random,
            )

        pitch_category = PITCH_CATEGORIES.get(selected_pitch_name, 'Fastball')

        if selected_pitch_obj is not None:
            horizontal_break_in = selected_pitch_obj.horizontal_break_in
            induced_vertical_break_in = selected_pitch_obj.induced_vertical_break_in
        else:
            movement = movement_for(selected_pitch_name)
            horizontal_break_in = movement['hb']
            induced_vertical_break_in = movement['ivb']

        return {
            'selected_pitch': selected_pitch_name,
            'pitch_category': pitch_category,
            'velocity_mph': round(velocity_mph, 1),
            'release_speed_mph': round(velocity_mph, 1),
            'spin_rpm': spin_rpm,
            'horizontal_break_in': horizontal_break_in,
            'induced_vertical_break_in': induced_vertical_break_in,
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
            'max_radius_inches': delivery_math['max_radius_inches'],
            'delta_x_in': delivery_math['delta_x_in'],
            'delta_z_in': delivery_math['delta_z_in'],
            'radial_miss_in': delivery_math['radial_miss_in'],
            'is_heart_leak': delivery_math['is_heart_leak'],
            'hit_shadow_target': delivery_math['hit_shadow_target'],
            'pitch_effectiveness': delivery_math['effectiveness_score'],
            'strat_result': strat_result,
            'adjusted_ratings': adjusted_ratings.to_dict(),
        }
