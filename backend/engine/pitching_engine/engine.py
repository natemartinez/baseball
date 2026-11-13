"""
Pitching Engine: Main Coordinator.
Coordinates pitch strategy, pitch selection, target intent, bivariate Gaussian delivery,
and in-game pitcher rating adjustments for a baseball game instance.
"""

import random
from typing import Dict, Any, Optional, List, Tuple

from .pitcher_info.pitch_objects import PitchArsenal, PITCH_CATEGORIES, movement_for
from .pitch_selection import PitchSelectionMode, PitchStrategy, select_pitch
from .pitcher_info.adjusted_ratings import (
    PitcherInstanceManager,
    PitchArsenalMetrics,
    evaluate_pitch_arsenal,
)
from .pitcher_info.active_pitcher import ActivePitcherState
from .pitch_execution.calculations import calculate_pitch_delivery

from ..game_engine.gameday_math import (
    determine_situation_category,
    is_rulebook_strike,
)


class PitchingEngine:
    """
    Authoritative pitching coordinator for an active game matchup.
    Communicates between GameEngine and pitching submodules (selection, physics, pitcher ratings).
    """

    @classmethod
    def create_pitcher_state(cls, pitcher: Any) -> ActivePitcherState:
        """Authoritative entry point to initialize and cache a pitcher's active state on mound entry."""
        return ActivePitcherState.from_player(pitcher)

    @staticmethod
    def _validate_player(player: Any, role: str) -> Any:
        """Enforces domain model boundary and validates participant presence."""
        if isinstance(player, ActivePitcherState):
            return player
        if isinstance(player, dict):
            try:
                from backend.models.player import Player
                player = Player.from_dict(player)
            except ImportError:
                pass

        if not player:
            raise ValueError(f"PitchingEngine requires a {role} object.")
        return player

    def __init__(
        self,
        pitcher: Any,
        batter: Any,
        rng: Optional[random.Random] = None,
        pitcher_state: Optional[ActivePitcherState] = None,
    ):
        pitcher_obj = self._validate_player(pitcher, "pitcher")
        self.batter = batter = self._validate_player(batter, "batter")
        self.rng = rng or random

        if isinstance(pitcher_obj, ActivePitcherState):
            self.pitcher_state = pitcher_obj
            self.pitcher = pitcher_obj.pitcher
        elif pitcher_state is not None:
            self.pitcher_state = pitcher_state
            self.pitcher = pitcher_obj
        else:
            self.pitcher_state = ActivePitcherState.from_player(pitcher_obj)
            self.pitcher = pitcher_obj

        self.arsenal = self.pitcher_state.arsenal
        self.pitch_arsenal = self.arsenal.to_raw_list()
        self.strategy = PitchStrategy(self.pitcher, self.batter, rng=self.rng, arsenal=self.arsenal)
        self.pitch_arsenal_metrics: Dict[str, PitchArsenalMetrics] = self.pitcher_state.baseline_metrics

    def init_pitch_arsenal(
        self,
        pitcher_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, PitchArsenalMetrics]:
        """
        Initializes and evaluates the pitcher's arsenal metrics by delegating to pitcher_info.
        Computes pitch-specific effective command, maximum error radius, and baseline effectiveness
        for all pitches in the pitcher's repertoire.
        """
        if pitcher_info is not None:
            raw_pitches = self.arsenal.pitches if hasattr(self, 'arsenal') and self.arsenal else None
            metrics = evaluate_pitch_arsenal(pitcher_info, arsenal_items=raw_pitches)
            self.pitch_arsenal_metrics = metrics
            return metrics
        if hasattr(self, 'pitch_arsenal_metrics') and self.pitch_arsenal_metrics:
            return self.pitch_arsenal_metrics
        pitcher = self.pitcher
        raw_pitches = self.arsenal.pitches if hasattr(self, 'arsenal') and self.arsenal else None
        metrics = evaluate_pitch_arsenal(pitcher, arsenal_items=raw_pitches)
        self.pitch_arsenal_metrics = metrics
        return metrics

    def execute_pitch(
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
        selection_mode: Optional[str] = None,
        pitch_name: Optional[str] = None,
        timing_tier: Optional[Any] = None,
        timing_label: Optional[str] = None,
        pitch_effectiveness: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Main Hand-Off Method:
        Executes the entire pitching pipeline for a pitch delivery:
          1. Computes in-game adjusted pitcher ratings (fatigue, effective command).
          2. Resolves the selection mode, the concrete pitch, and target intent.
          3. Evaluates target coordinates through the pitch-selection package.
          4. Resolves bivariate Gaussian delivery error and pitch effectiveness.

        ``pitch_intent`` is a tactical target goal (STRIKE/CHASE/WASTE), never a
        pitch name. ``pitch_name`` (or the legacy ``pitch_type`` alias) is the
        concrete pitch for user-selected pitches.
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

        # 2. Pitch Selection & Target Intent
        selection = select_pitch(
            self.strategy,
            self.arsenal,
            balls=balls,
            strikes=strikes,
            situation=sit_category,
            recent_pitches=recent_pitches,
            selection_mode=selection_mode,
            pitch_name=pitch_name or pitch_type,
            pitch_intent=pitch_intent,
            target_zone=target_zone,
            custom_target=custom_target,
            rng=self.rng,
        )

        strat_result = {
            'selected_pitch': selection.pitch_name,
            'velocity_mph': selection.velocity_mph,
            'spin_rpm': selection.spin_rpm,
            'repertoire_probabilities': dict(selection.repertoire_probabilities),
            'dynamic_modifier': selection.dynamic_modifier,
            'strategy_name': selection.strategy_name,
            'rationale': selection.rationale,
            'recommended_zone': selection.recommended_zone,
        }

        selected_pitch_name = selection.pitch_name
        selected_pitch_obj = selection.pitch
        velocity_mph = selection.velocity_mph
        spin_rpm = selection.spin_rpm

        if (
            selection.mode is PitchSelectionMode.AI
            and adjusted_ratings.fatigue_pct > 25.0
        ):
            # Adjust velocity and spin slightly based on in-game fatigue.
            velocity_mph = max(84.0, velocity_mph - ((adjusted_ratings.fatigue_pct - 25.0) * 0.05))
            spin_rpm = max(1900, int(spin_rpm - (adjusted_ratings.fatigue_pct * 4.0)))

        # 3. Resolved Target Coordinates
        target = selection.target_intent
        nominal_zone = target.nominal_zone
        target_x = target.target_x
        target_z = target.target_z
        intended_zone_cat = target.intended_zone_cat
        is_manual_override = target.is_manual_override

        # 4. Delivery Execution & Gaussian Error
        pitch_metrics = self.pitch_arsenal_metrics.get(selected_pitch_name)
        if pitch_metrics is None:
            for k, v in self.pitch_arsenal_metrics.items():
                if k.lower().replace('-', ' ') == selected_pitch_name.lower().replace('-', ' '):
                    pitch_metrics = v
                    break

        from .pitcher_info.pitch_effectiveness import (
            calculate_command_adjustment_from_effectiveness,
            apply_effectiveness_to_velocity,
            apply_effectiveness_to_break,
        )

        if pitch_metrics is not None:
            effective_pitch_command = pitch_metrics.effective_command
            if pitch_effectiveness is not None:
                cmd_adj = calculate_command_adjustment_from_effectiveness(pitch_effectiveness)
                effective_pitch_command = max(30.0, min(99.0, effective_pitch_command + cmd_adj))
        else:
            effective_pitch_command = adjusted_ratings.effective_command
            if pitch_effectiveness is not None:
                cmd_adj = calculate_command_adjustment_from_effectiveness(pitch_effectiveness)
                effective_pitch_command = max(30.0, min(99.0, effective_pitch_command + cmd_adj))

        if pitch_effectiveness is not None:
            from ..game_engine.gameday_math import calculate_execution_sigma, get_max_error_radius_inches
            precomputed_sigma = calculate_execution_sigma(effective_pitch_command)
            precomputed_max_radius = get_max_error_radius_inches(effective_pitch_command)
        else:
            precomputed_sigma = getattr(pitch_metrics, 'sigma', None) if pitch_metrics else None
            precomputed_max_radius = getattr(pitch_metrics, 'max_radius_inches', None) if pitch_metrics else None

        from .pitch_execution.tiers import AbilityTier, TimingTier, get_ability_tier
        from .pitch_execution.calculations import roll_simulation_timing

        ability_tier = get_ability_tier(effective_pitch_command)
        composure = float(getattr(self.pitcher, 'composure', 75.0) or 75.0)
        consistency = float(getattr(self.pitcher, 'consistency', 75.0) or 75.0)
        pitcher_hand = (
            'L'
            if str(getattr(self.pitcher, 'handedness', 'R') or 'R').upper().startswith('L')
            else 'R'
        )
        is_leverage = (r2 or r3) or (sit_category in ("RISP", "HIGH_LEVERAGE", "BASES_LOADED"))

        if timing_tier is not None:
            if isinstance(timing_tier, str):
                resolved_timing_tier = TimingTier(timing_tier.strip().upper())
            else:
                resolved_timing_tier = timing_tier
            resolved_timing_label = timing_label
            if resolved_timing_label is None:
                if resolved_timing_tier == TimingTier.PERFECT:
                    resolved_timing_label = "PERFECT!"
                elif resolved_timing_tier == TimingTier.GOOD:
                    resolved_timing_label = "GOOD"
                elif resolved_timing_tier == TimingTier.OKAY:
                    resolved_timing_label = "EARLY • OKAY"
                else:
                    resolved_timing_label = "EARLY • POOR"
        else:
            resolved_timing_tier, resolved_timing_label = roll_simulation_timing(
                ability_tier=ability_tier,
                composure=composure,
                consistency=consistency,
                fatigue_pct=adjusted_ratings.fatigue_pct,
                is_leverage=is_leverage,
                rng=self.rng,
                pitch_count=pitch_count,
                stamina=adjusted_ratings.base_stamina,
                effectiveness=pitch_effectiveness,
            )

        delivery_math = calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=effective_pitch_command,
            pitch_count=pitch_count,
            stamina=adjusted_ratings.base_stamina,
            intended_zone_cat=intended_zone_cat,
            rng=self.rng.random,
            precomputed_sigma=precomputed_sigma,
            precomputed_max_radius_in=precomputed_max_radius,
            timing_tier=resolved_timing_tier,
            timing_label=resolved_timing_label,
            ability_tier=ability_tier,
            pitcher_hand=pitcher_hand,
            pitch_type=selected_pitch_name,
            composure=composure,
            consistency=consistency,
            is_leverage=is_leverage,
        )

        pitch_category = PITCH_CATEGORIES.get(selected_pitch_name, 'Fastball')

        if selected_pitch_obj is not None:
            horizontal_break_in = selected_pitch_obj.horizontal_break_in
            induced_vertical_break_in = selected_pitch_obj.induced_vertical_break_in
        else:
            movement = movement_for(selected_pitch_name)
            horizontal_break_in = movement['hb']
            induced_vertical_break_in = movement['ivb']

        if pitch_effectiveness is not None:
            from .pitcher_info.pitch_effectiveness import (
                apply_effectiveness_to_velocity,
                apply_effectiveness_to_break,
            )
            velocity_mph = apply_effectiveness_to_velocity(velocity_mph, pitch_effectiveness)
            horizontal_break_in, induced_vertical_break_in = apply_effectiveness_to_break(
                horizontal_break_in, induced_vertical_break_in, pitch_effectiveness
            )

        radial_miss_val = float(delivery_math.get('radial_miss_inches', delivery_math.get('radial_miss_in', 0.0)))
        ability_tier_val = delivery_math.get('ability_tier')
        if hasattr(ability_tier_val, 'value'):
            ability_tier_val = ability_tier_val.value
        elif ability_tier_val is not None:
            ability_tier_val = str(ability_tier_val)

        timing_tier_val = delivery_math.get('timing_tier')
        if hasattr(timing_tier_val, 'value'):
            timing_tier_val = timing_tier_val.value
        elif timing_tier_val is not None:
            timing_tier_val = str(timing_tier_val)

        timing_label_val = delivery_math.get('timing_label')
        base_radius_inches_val = float(delivery_math.get('base_radius_inches', 0.0))
        executed_radius_inches_val = float(delivery_math.get('executed_radius_inches', 0.0))

        exec_dict = {
            'ability_tier': ability_tier_val,
            'timing_tier': timing_tier_val,
            'timing_label': timing_label_val,
            'base_radius_inches': base_radius_inches_val,
            'executed_radius_inches': executed_radius_inches_val,
            'radial_miss_inches': radial_miss_val,
            'realized_x': delivery_math['realized_x'],
            'realized_z': delivery_math['realized_z'],
        }

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
            'radial_miss_in': radial_miss_val,
            'radial_miss_inches': radial_miss_val,
            'base_radius_inches': base_radius_inches_val,
            'executed_radius_inches': executed_radius_inches_val,
            'ability_tier': ability_tier_val,
            'timing_tier': timing_tier_val,
            'timing_label': timing_label_val,
            'execution': exec_dict,
            'is_heart_leak': delivery_math['is_heart_leak'],
            'hit_shadow_target': delivery_math['hit_shadow_target'],
            'pitch_effectiveness': pitch_effectiveness if pitch_effectiveness is not None else delivery_math['effectiveness_score'],
            'effectiveness_score': delivery_math['effectiveness_score'],
            'strat_result': strat_result,
            'adjusted_ratings': adjusted_ratings.to_dict(),
            'release_point_ft': dict(getattr(self.pitcher, 'release_point_ft', {}) or {}),
        }
