"""
Batting Practice Mode Module.

Encapsulates all practice drill functionality:
1. PracticeDeliveryBuilder: Synthesizes deterministic, zero-dispersion deliveries for drill pitches.
2. PracticeModeController: Manages the drill state machine (game state snapshotting, 0-0 resets,
   and drill pitch throw/resolve coordination).
"""

from typing import Any, Dict, Optional
from backend.engine.game_engine.gameday_math import (
    classify_gameday_zone,
    is_rulebook_strike,
)
from backend.engine.game_engine.orchestration import PitchFlowError
from backend.engine.pitching_engine.pitch_execution.pitch_objects import movement_for
from backend.engine.pitching_engine.pitcher_info.adjusted_ratings import PitcherInstanceManager


class PracticeDeliveryBuilder:
    """Builds deterministic, zero-dispersion delivery payloads for practice mode pitches."""

    @staticmethod
    def build(
        pitcher: Any,
        arsenal: Any,
        pitch_name: str,
        custom_target: Dict[str, float],
        target_zone: Optional[str] = None,
        situation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesizes a delivery payload forcing exact coordinates without error dispersion."""
        selected_pitch_name = pitch_name
        selected_pitch_obj = None

        if hasattr(arsenal, 'get_pitch'):
            selected_pitch_obj = arsenal.get_pitch(selected_pitch_name)

        if selected_pitch_obj:
            selected_pitch_name = selected_pitch_obj.name
            velocity_mph = float(selected_pitch_obj.velocity_mph)
            spin_rpm = int(selected_pitch_obj.spin_rpm)
            horizontal_break_in = float(selected_pitch_obj.horizontal_break_in)
            induced_vertical_break_in = float(selected_pitch_obj.induced_vertical_break_in)
            pitch_category = selected_pitch_obj.category
        else:
            movement = movement_for(selected_pitch_name)
            velocity_mph = 93.0
            spin_rpm = 2200
            horizontal_break_in = float(movement['hb'])
            induced_vertical_break_in = float(movement['ivb'])
            pitch_category = 'Fastball'

        target_x = float(custom_target['x'])
        target_z = float(custom_target['z'])
        nominal_zone = target_zone or 'heart'
        intended_zone_cat = classify_gameday_zone(target_x, target_z)

        # In-game adjusted ratings for a fresh pitcher throwing 0-0 drill pitch
        adjusted_ratings = PitcherInstanceManager.get_adjusted_ratings(
            pitcher=pitcher,
            pitch_count=1,
            balls=0,
            strikes=0,
        )

        is_strike = is_rulebook_strike(target_x, target_z)

        delivery_math = {
            'sigma': 0.0,
            'max_radius_inches': 0.0,
            'base_radius_inches': 0.0,
            'executed_radius_inches': 0.0,
            'realized_x': target_x,
            'realized_z': target_z,
            'realized_zone_cat': intended_zone_cat,
            'is_strike': is_strike,
            'delta_x_in': 0.0,
            'delta_z_in': 0.0,
            'radial_miss_in': 0.0,
            'radial_miss_inches': 0.0,
            'is_heart_leak': False,
            'hit_shadow_target': intended_zone_cat == 'SHADOW',
            'effectiveness_score': 100.0,
            'ability_tier': 'GOOD',
            'timing_tier': 'PERFECT',
            'timing_label': 'PERFECT!',
        }

        repertoire_probs = {}
        if hasattr(arsenal, 'pitches') and arsenal.pitches:
            for p in arsenal.pitches:
                p_name = getattr(p, 'name', str(p))
                repertoire_probs[p_name] = 1.0 if p_name == selected_pitch_name else 0.0
        else:
            repertoire_probs = {selected_pitch_name: 1.0}

        strat_result = {
            'selected_pitch': selected_pitch_name,
            'recommended_pitch': selected_pitch_name,
            'pitch_name': selected_pitch_name,
            'recommended_zone': nominal_zone,
            'pitch_intent': 'STRIKE',
            'velocity_mph': round(velocity_mph, 1),
            'spin_rpm': spin_rpm,
            'dynamic_modifier': 1.0,
            'strategy_name': 'PRACTICE_DRILL',
            'rationale': 'Batting practice: forced pitch and exact target.',
            'repertoire_probabilities': repertoire_probs,
        }

        exec_dict = {
            'ability_tier': 'GOOD',
            'timing_tier': 'PERFECT',
            'timing_label': 'PERFECT!',
            'base_radius_inches': 0.0,
            'executed_radius_inches': 0.0,
            'radial_miss_inches': 0.0,
            'realized_x': target_x,
            'realized_z': target_z,
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
            'is_manual_override': True,
            'realized_x': target_x,
            'realized_z': target_z,
            'realized_zone_cat': intended_zone_cat,
            'is_strike': is_strike,
            'sigma': 0.0,
            'max_radius_inches': 0.0,
            'delta_x_in': 0.0,
            'delta_z_in': 0.0,
            'radial_miss_in': 0.0,
            'radial_miss_inches': 0.0,
            'base_radius_inches': 0.0,
            'executed_radius_inches': 0.0,
            'ability_tier': 'GOOD',
            'timing_tier': 'PERFECT',
            'timing_label': 'PERFECT!',
            'execution': exec_dict,
            'is_heart_leak': False,
            'hit_shadow_target': intended_zone_cat == 'SHADOW',
            'pitch_effectiveness': 100.0,
            'effectiveness_score': 100.0,
            'strat_result': strat_result,
            'adjusted_ratings': adjusted_ratings.to_dict(),
            'release_point_ft': dict(getattr(pitcher, 'release_point_ft', {}) or {}),
        }


class PracticeModeController:
    """Coordinates Batting Practice drills: state snapshots, 0-0 count resets, and pitch execution."""

    def __init__(self, game_engine: Any):
        self.game = game_engine
        self.is_active: bool = False
        self.saved_state: Optional[Dict[str, Any]] = None
        self.baseline_state: Optional[Dict[str, Any]] = None
        self.pitch_count: int = 0

    def reset_drill_state(self) -> None:
        """Restores the frozen 0-0 drill state, keeping the practice pitch count."""
        baseline = self.baseline_state
        if baseline is None:
            return
        g = self.game
        g.inning = baseline['inning']
        g.top_bottom = baseline['top_bottom']
        g.outs = baseline['outs']
        g.balls = baseline['balls']
        g.strikes = baseline['strikes']
        g.score = dict(baseline['score'])
        g.bases = dict(baseline['bases'])
        g.game_over = baseline['game_over']
        g.away_batter_idx = baseline['away_batter_idx']
        g.home_batter_idx = baseline['home_batter_idx']
        g._batter_game_stats = {
            key: dict(value) for key, value in baseline['batter_stats'].items()
        }
        g.recent_pitches_sequence = []
        g.current_at_bat_pitches = []

    def start(self) -> Dict[str, Any]:
        """Snapshots the active game and switches into a repeatable 0-0 batting drill."""
        if self.is_active:
            return self.game.get_game_state_payload()
        if self.game.has_pending_pitch:
            raise PitchFlowError(
                'A pitch is already in flight; resolve it before starting practice.'
            )

        g = self.game
        self.saved_state = {
            'inning': g.inning,
            'top_bottom': g.top_bottom,
            'outs': g.outs,
            'balls': g.balls,
            'strikes': g.strikes,
            'score': dict(g.score),
            'bases': dict(g.bases),
            'game_over': g.game_over,
            'away_batter_idx': g.away_batter_idx,
            'home_batter_idx': g.home_batter_idx,
            'pitch_count_home': g.pitch_count_home,
            'pitch_count_away': g.pitch_count_away,
            'session_pitch_count': g.session_pitch_count,
            'recent_pitches_sequence': list(g.recent_pitches_sequence),
            'current_at_bat_pitches': [dict(pitch) for pitch in g.current_at_bat_pitches],
            'batter_stats': g._copy_batter_stats(),
            'last_command_quality': g.last_command_quality,
        }
        self.baseline_state = {
            'inning': g.inning,
            'top_bottom': g.top_bottom,
            'outs': 0,
            'balls': 0,
            'strikes': 0,
            'score': dict(g.score),
            'bases': {'first': None, 'second': None, 'third': None},
            'game_over': False,
            'away_batter_idx': g.away_batter_idx,
            'home_batter_idx': g.home_batter_idx,
            'batter_stats': g._copy_batter_stats(),
            'current_at_bat_pitches': [],
        }
        self.is_active = True
        self.pitch_count = 0
        g.pitch_count_home = 0
        g.pitch_count_away = 0
        g.session_pitch_count = 0
        g.orchestrator.reset()
        self.reset_drill_state()
        return g.get_game_state_payload()

    def end(self) -> Dict[str, Any]:
        """Restores the real game snapshot and exits practice mode."""
        if not self.is_active:
            return self.game.get_game_state_payload()

        g = self.game
        saved = self.saved_state or {}
        g.inning = saved.get('inning', g.inning)
        g.top_bottom = saved.get('top_bottom', g.top_bottom)
        g.outs = saved.get('outs', 0)
        g.balls = saved.get('balls', 0)
        g.strikes = saved.get('strikes', 0)
        g.score = dict(saved.get('score', g.score))
        g.bases = dict(saved.get('bases', g.bases))
        g.game_over = bool(saved.get('game_over', False))
        g.away_batter_idx = saved.get('away_batter_idx', 0)
        g.home_batter_idx = saved.get('home_batter_idx', 0)
        g.pitch_count_home = saved.get('pitch_count_home', 0)
        g.pitch_count_away = saved.get('pitch_count_away', 0)
        g.session_pitch_count = saved.get('session_pitch_count', 0)
        g.recent_pitches_sequence = list(saved.get('recent_pitches_sequence', []))
        g.current_at_bat_pitches = [
            dict(pitch) for pitch in saved.get('current_at_bat_pitches', [])
        ]
        g._batter_game_stats = {
            key: dict(value) for key, value in saved.get('batter_stats', {}).items()
        }
        g.last_command_quality = saved.get('last_command_quality', 'TARGET_EXECUTED')

        self.is_active = False
        self.saved_state = None
        self.baseline_state = None
        self.pitch_count = 0
        g.orchestrator.reset()
        return g.get_game_state_payload()

    def throw_pitch(
        self,
        pitch_type: Optional[str] = None,
        target_zone: Optional[str] = None,
        custom_target: Optional[Dict[str, float]] = None,
        pitch_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validates drill pitch parameters and dispatches throw_pitch(practice=True)."""
        selected_pitch_name = pitch_name or pitch_type
        if not self.is_active:
            return {'status': 'error', 'message': 'Batting practice is not active'}
        if not selected_pitch_name:
            return {'status': 'error', 'message': 'Practice pitch type is required'}
        if not custom_target or 'x' not in custom_target or 'z' not in custom_target:
            return {
                'status': 'error',
                'message': 'Practice pitches require an exact custom target',
            }
        self.pitch_count += 1
        pitcher = self.game.current_pitcher_obj()
        arsenal = self.game.get_pitcher_arsenal(pitcher) if hasattr(self.game, 'get_pitcher_arsenal') else []
        delivery = PracticeDeliveryBuilder.build(
            pitcher=pitcher,
            arsenal=arsenal,
            pitch_name=selected_pitch_name,
            custom_target=custom_target,
            target_zone=target_zone,
            situation='EMPTY_NEUTRAL',
        )
        return self.game.throw_pitch(
            pitch_name=selected_pitch_name,
            target_zone=target_zone,
            custom_target=custom_target,
            delivery=delivery,
        )

    def resolve_pitch(
        self,
        batter_approach: str = 'AUTO',
        batter_decision: Optional[str] = None,
        contact: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resolves the drill pitch and immediately resets count to 0-0."""
        if not self.is_active:
            return {'status': 'error', 'message': 'Batting practice is not active'}
        if batter_decision is None and contact is None:
            batter_decision = 'TAKE'

        outcome = self.game.resolve_pitch(
            batter_approach=batter_approach,
            batter_decision=batter_decision,
            contact=contact,
            practice=True,
        )
        if outcome.get('status') != 'success':
            return outcome

        self.reset_drill_state()
        game_state = self.game.get_game_state_payload()
        outcome['game_state'] = game_state
        outcome['game'] = game_state
        return outcome
