"""
MLB Statcast Authoritative Game Engine.
Implements the full 6-stage simulation pipeline, count state machine,
bivariate Gaussian delivery resolution, and emits standardized Gameday2DPitchPacket telemetry.
"""

import os
import sys
import math
import random
from typing import Dict, Any, Tuple, Optional, List

try:
    from backend.engine.gameday_math import (
        is_rulebook_strike,
        classify_gameday_zone,
        get_zone_nominal_target,
        calculate_execution_sigma,
        sample_bivariate_gaussian,
        calculate_radial_miss_inches,
        determine_situation_category,
        ZONE_CENTERS,
    )
    from backend.engine.strike_zone import StrikeZone
    from backend.engine.pitching_engine import PitchingEngine, PitchStrategy
    from backend.engine.batter_strategy import BatterStrategy, JUDGE_DEFAULT_ZONES
    from backend.models.player import Player
except ImportError:
    from gameday_math import (
        is_rulebook_strike,
        classify_gameday_zone,
        get_zone_nominal_target,
        calculate_execution_sigma,
        sample_bivariate_gaussian,
        calculate_radial_miss_inches,
        determine_situation_category,
        ZONE_CENTERS,
    )
    from strike_zone import StrikeZone
    from pitching_engine import PitchingEngine, PitchStrategy
    from batter_strategy import BatterStrategy, JUDGE_DEFAULT_ZONES
    try:
        from models.player import Player
    except ImportError:
        Player = None


class GameEngine:
    @staticmethod
    def _ensure_player(player_or_dict: Any) -> Any:
        """Boundary guard: Ensures a participant is an authoritative Player object."""
        if player_or_dict is None:
            return None
        if isinstance(player_or_dict, dict) and Player is not None:
            return Player.from_dict(player_or_dict)
        return player_or_dict

    def __init__(self, home_roster: dict, away_roster: dict, home_name: str = 'New York Yankees', away_name: str = 'New York Mets'):
        self.home_roster = home_roster
        self.away_roster = away_roster
        self.home_name = home_name
        self.away_name = away_name

        self.inning = 1
        self.top_bottom = 'TOP'  # 'TOP' (away bats), 'BOT' (home bats)
        self.outs = 0
        self.balls = 0
        self.strikes = 0
        self.score = {self.away_name: 0, self.home_name: 0}
        self.bases = {'first': None, 'second': None, 'third': None}
        self.game_over = False

        raw_away_lineup = away_roster.get('position_players', [])[:]
        raw_home_lineup = home_roster.get('position_players', [])[:]
        self.away_lineup = [self._ensure_player(p) for p in raw_away_lineup if p]
        self.home_lineup = [self._ensure_player(p) for p in raw_home_lineup if p]
        self.away_batter_idx = 0
        self.home_batter_idx = 0

        raw_away_pitchers = away_roster.get('pitchers', {}).get('starters', [None])
        raw_home_pitchers = home_roster.get('pitchers', {}).get('starters', [None])
        self.away_pitcher = self._ensure_player(raw_away_pitchers[0] if raw_away_pitchers else None)
        self.home_pitcher = self._ensure_player(raw_home_pitchers[0] if raw_home_pitchers else None)


        self.pitch_count_home = 0
        self.pitch_count_away = 0
        self.session_pitch_count = 0
        self.recent_pitches_sequence: List[str] = []

        self.strike_zone = StrikeZone()
        self.last_command_quality = 'TARGET_EXECUTED'

    def current_batter_obj(self) -> Any:
        lineup = self.away_lineup if self.top_bottom == 'TOP' else self.home_lineup
        idx = self.away_batter_idx if self.top_bottom == 'TOP' else self.home_batter_idx
        if lineup and idx < len(lineup):
            return lineup[idx]
        return None

    def current_pitcher_obj(self) -> Any:
        return self.home_pitcher if self.top_bottom == 'TOP' else self.away_pitcher

    def _advance_batter_order(self):
        if self.top_bottom == 'TOP':
            self.away_batter_idx = (self.away_batter_idx + 1) % max(1, len(self.away_lineup))
        else:
            self.home_batter_idx = (self.home_batter_idx + 1) % max(1, len(self.home_lineup))

    def _advance_runners_on_hit(self, bases_taken: int, batter_summary: dict) -> int:
        """Advances existing runners and places batter. Returns runs scored."""
        runs = 0
        new_bases = {'first': None, 'second': None, 'third': None}

        # Clear existing runners forward
        order = ['third', 'second', 'first']
        base_map = {'first': 1, 'second': 2, 'third': 3}
        rev_map = {1: 'first', 2: 'second', 3: 'third'}

        for b_name in order:
            runner = self.bases[b_name]
            if runner:
                dest = base_map[b_name] + bases_taken
                if dest >= 4:
                    runs += 1
                else:
                    new_bases[rev_map[dest]] = runner

        if bases_taken >= 4:
            runs += 1
        elif bases_taken == 1:
            new_bases['first'] = batter_summary
        elif bases_taken == 2:
            new_bases['second'] = batter_summary
        elif bases_taken == 3:
            new_bases['third'] = batter_summary

        self.bases = new_bases
        return runs

    def _advance_runners_on_walk(self, batter_summary: dict) -> int:
        """Forces runners forward on a walk. Returns runs scored."""
        runs = 0
        b1 = self.bases['first']
        b2 = self.bases['second']
        b3 = self.bases['third']

        if b1 and b2 and b3:
            runs += 1
            self.bases['third'] = b2
            self.bases['second'] = b1
            self.bases['first'] = batter_summary
        elif b1 and b2:
            self.bases['third'] = b2
            self.bases['second'] = b1
            self.bases['first'] = batter_summary
        elif b1:
            self.bases['second'] = b1
            self.bases['first'] = batter_summary
        else:
            self.bases['first'] = batter_summary

        return runs

    def _switch_half_inning(self):
        self.outs = 0
        self.balls = 0
        self.strikes = 0
        self.bases = {'first': None, 'second': None, 'third': None}
        self.recent_pitches_sequence = []

        if self.top_bottom == 'TOP':
            self.top_bottom = 'BOT'
        else:
            self.top_bottom = 'TOP'
            self.inning += 1
            if self.inning > 9:
                # Basic game over logic, will eventually need to have extra innings
                if self.score[self.home_name] != self.score[self.away_name]:
                    self.game_over = True

    def pitch(
        self,
        pitch_intent: Optional[str] = None,
        pitch_type: Optional[str] = None,
        target_zone: Optional[str] = None,
        custom_target: Optional[Dict[str, float]] = None,
        batter_approach: str = 'AUTO'
    ) -> Dict[str, Any]:
        if self.game_over:
            return {'status': 'error', 'message': 'Game is over'}

        pitcher = self.current_pitcher_obj()
        batter = self.current_batter_obj()

        # Update pitch count
        if self.top_bottom == 'TOP':
            self.pitch_count_home += 1
            cur_pitch_count = self.pitch_count_home
        else:
            self.pitch_count_away += 1
            cur_pitch_count = self.pitch_count_away

        self.session_pitch_count += 1

        # Evaluate Situation
        r1 = self.bases['first'] is not None
        r2 = self.bases['second'] is not None
        r3 = self.bases['third'] is not None
        sit_category = determine_situation_category(self.balls, self.strikes, self.outs, r1, r2, r3)

        # 1. Pitching Engine: Strategy, Target Intent, Rating Adjustments & Delivery Execution
        pitching_engine = PitchingEngine(pitcher, batter)
        delivery = pitching_engine.execute_pitch( # Calls method from engine.py
            balls=self.balls,
            strikes=self.strikes,
            outs=self.outs,
            runners=(r1, r2, r3),
            pitch_count=cur_pitch_count,
            recent_pitches=self.recent_pitches_sequence,
            pitch_intent=pitch_intent,
            pitch_type=pitch_type,
            target_zone=target_zone,
            custom_target=custom_target,
            situation=sit_category,
        )

        selected_pitch_name = delivery['selected_pitch']
        velocity_mph = delivery['velocity_mph']
        spin_rpm = delivery['spin_rpm']
        self.recent_pitches_sequence.append(selected_pitch_name)

        target_x = delivery['target_x']
        target_z = delivery['target_z']
        intended_zone_cat = delivery['intended_zone_cat']
        is_manual_override = delivery['is_manual_override']

        sigma = delivery['sigma']
        realized_x = delivery['realized_x']
        realized_z = delivery['realized_z']
        realized_zone_cat = delivery['realized_zone_cat']
        strike_check = delivery['is_strike']
        delta_x_in = delivery['delta_x_in']
        delta_z_in = delivery['delta_z_in']
        radial_miss_in = delivery['radial_miss_in']
        is_heart_leak = delivery['is_heart_leak']
        hit_shadow_target = delivery['hit_shadow_target']
        strat_result = delivery['strat_result']
        command_rating = delivery['adjusted_ratings'].get('base_command', 70.0)

        # 4. Batter Swing & Reaction
        batter_engine = BatterStrategy(batter)
        actual_zone_name = target_zone or 'heart'
        # Closest zone label
        min_dist = 999.0
        for z_name, (zx, zz) in ZONE_CENTERS.items():
            dist = (zx - realized_x) ** 2 + (zz - realized_z) ** 2
            if dist < min_dist:
                min_dist = dist
                actual_zone_name = z_name

        will_swing, swing_prob = batter_engine.decide_swing(
            realized_zone_cat, actual_zone_name, strike_check, self.balls, self.strikes, approach_mode=batter_approach
        )

        pitch_result_type = 'BALL'
        call = 'BALL'
        description = 'Ball outside the zone'
        exit_velo = None
        launch_angle = None

        if not will_swing:
            if strike_check:
                pitch_result_type = 'CALLED_STRIKE'
                call = 'CALLED_STRIKE'
                description = f'Called strike ({actual_zone_name})'
            else:
                pitch_result_type = 'BALL'
                call = 'BALL'
                description = f'Ball ({realized_zone_cat.lower()})'
        else:
            contact = batter_engine.resolve_contact(
                selected_pitch_name, velocity_mph, actual_zone_name, realized_zone_cat, strike_check
            )
            call = contact['call']
            description = contact['description']
            exit_velo = contact.get('exit_velocity_mph')
            launch_angle = contact.get('launch_angle_deg')
            if call == 'SWINGING_STRIKE':
                pitch_result_type = 'SWINGING_STRIKE'
            elif call == 'FOUL':
                pitch_result_type = 'FOUL'
            else:
                pitch_result_type = call

        # 5. State Machine Update
        batter_summary = {
            'id': getattr(batter, 'id', 1) if batter else 1,
            'name': getattr(batter, 'name', 'Batter') if batter else 'Batter',
            'jersey_number': getattr(batter, 'number', 99) if batter else 99,
            'position': getattr(batter, 'position', 'DH') if batter else 'DH',
            'team': self.away_name if self.top_bottom == 'TOP' else self.home_name
        }

        batting_team = self.away_name if self.top_bottom == 'TOP' else self.home_name

        if pitch_result_type == 'BALL':
            self.balls += 1
            if self.balls == 4:
                runs = self._advance_runners_on_walk(batter_summary)
                self.score[batting_team] += runs
                self.balls = 0
                self.strikes = 0
                self._advance_batter_order()

        elif pitch_result_type in ('CALLED_STRIKE', 'SWINGING_STRIKE'):
            self.strikes += 1
            if self.strikes == 3:
                self.outs += 1
                self.balls = 0
                self.strikes = 0
                self._advance_batter_order()

        elif pitch_result_type == 'FOUL':
            if self.strikes < 2:
                self.strikes += 1

        elif pitch_result_type == 'IN_PLAY_OUT':
            self.outs += 1
            self.balls = 0
            self.strikes = 0
            self._advance_batter_order()

        elif pitch_result_type == 'SINGLE':
            runs = self._advance_runners_on_hit(1, batter_summary)
            self.score[batting_team] += runs
            self.balls = 0
            self.strikes = 0
            self._advance_batter_order()

        elif pitch_result_type == 'DOUBLE':
            runs = self._advance_runners_on_hit(2, batter_summary)
            self.score[batting_team] += runs
            self.balls = 0
            self.strikes = 0
            self._advance_batter_order()

        elif pitch_result_type == 'TRIPLE':
            runs = self._advance_runners_on_hit(3, batter_summary)
            self.score[batting_team] += runs
            self.balls = 0
            self.strikes = 0
            self._advance_batter_order()

        elif pitch_result_type == 'HOME_RUN':
            runs = self._advance_runners_on_hit(4, batter_summary)
            self.score[batting_team] += runs
            self.balls = 0
            self.strikes = 0
            self._advance_batter_order()

        # Inning completion check
        if self.outs >= 3:
            self._switch_half_inning()

        # 6. Construct Gameday2DPitchPacket
        pitcher_name = getattr(pitcher, 'name', 'Pitcher') if pitcher else 'Pitcher'
        batter_name = getattr(batter, 'name', 'Batter') if batter else 'Batter'
        batter_id = getattr(batter, 'id', 1) if batter else 1

        gameday_packet = {
            'meta': {
                'pitchNumber': self.session_pitch_count,
                'pitcherName': pitcher_name,
                'pitcherOvr': 85,
                'commandRating': int(command_rating),
                'staminaPct': max(10, 100 - cur_pitch_count),
                'pitchesThrown': cur_pitch_count,
                'inning': self.inning,
                'isTopInning': (self.top_bottom == 'TOP'),
                'count': {'balls': self.balls, 'strikes': self.strikes, 'outs': self.outs},
                'runnersOnBase': {
                    'first': self.bases['first'] is not None,
                    'second': self.bases['second'] is not None,
                    'third': self.bases['third'] is not None,
                },
                'batterName': batter_name,
                'batterId': batter_id,
                'situationCategory': sit_category,
            },
            'strategy': {
                'repertoireProbabilities': strat_result['repertoire_probabilities'],
                'selectedPitch': selected_pitch_name,
                'dynamicModifier': strat_result['dynamic_modifier'],
                'strategyName': strat_result['strategy_name'],
                'rationale': strat_result['rationale'],
            },
            'intent': {
                'targetX': target_x,
                'targetZ': target_z,
                'intendedZone': intended_zone_cat,
                'targetSpeedMph': velocity_mph,
                'isManualOverride': is_manual_override,
            },
            'execution': {
                'realizedX': realized_x,
                'realizedZ': realized_z,
                'realizedSpeedMph': velocity_mph,
                'radialMissInches': radial_miss_in,
                'deltaXInches': delta_x_in,
                'deltaZInches': delta_z_in,
                'sigmaXFeet': round(sigma, 3),
                'sigmaZFeet': round(sigma, 3),
                'isHeartZoneLeak': is_heart_leak,
                'hitShadowZoneTarget': hit_shadow_target,
                'realizedZoneCategory': realized_zone_cat,
            },
            'result': {
                'call': call,
                'isStrike': strike_check,
                'exitVelocityMph': exit_velo,
                'launchAngleDeg': launch_angle,
                'description': description,
            }
        }

        game_state = self.get_game_state_payload()

        pitch_details = {
            'pitch_name': selected_pitch_name,
            'velocity_mph': velocity_mph,
            'spin_rpm': spin_rpm,
            'intended_zone': target_zone or 'heart',
            'actual_zone': actual_zone_name,
            'batter_decision': 'SWING' if will_swing else 'TAKE',
            'pitch_result': pitch_result_type,
            'exit_velocity_mph': exit_velo,
            'launch_angle_deg': launch_angle,
            'description': description,
            'strategy_name': strat_result['strategy_name'],
            'command_quality': 'PINPOINT' if radial_miss_in <= 2.0 else 'TARGET_EXECUTED' if radial_miss_in <= 4.0 else 'SLIGHT_MISS',
            'pitch_effectiveness': delivery.get('pitch_effectiveness', 75.0),
            'adjusted_ratings': delivery.get('adjusted_ratings', {}),
            'gameday_packet': gameday_packet,
        }

        return {
            'status': 'success',
            'pitch_details': pitch_details,
            'game_state': game_state,
            'pitch': pitch_details,
            'game': game_state
        }

    def pitching_engine(
        self,
        pitch_intent: Optional[str] = None,
        pitch_type: Optional[str] = None,
        target_zone: Optional[str] = None,
        custom_target: Optional[Dict[str, float]] = None,
        batter_approach: str = 'AUTO'
    ) -> Dict[str, Any]:
        """
        Public alias for pitch() that delegates all pitching responsibilities
        to the Pitching Engine module.
        """
        return self.pitch(
            pitch_intent=pitch_intent,
            pitch_type=pitch_type,
            target_zone=target_zone,
            custom_target=custom_target,
            batter_approach=batter_approach
        )

    def sim_at_bat(self) -> Dict[str, Any]:
        """Simulates pitches until the current at-bat concludes."""
        loops = 0
        last_result = None
        while loops < 15:
            loops += 1
            last_result = self.pitch()
            if self.balls == 0 and self.strikes == 0:
                break
        return last_result or self.pitch()

    def calculate_strategy_and_intent(self, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        outs = self.outs
        balls = self.balls
        strikes = self.strikes
        bases = self.bases
        batter = (state.get('current_batter', {}) if state else {})
        pitcher = (state.get('current_pitcher', {}) if state else {})

        is_bases_loaded = bases.get('first') is not None and bases.get('second') is not None and bases.get('third') is not None
        is_double_play = bases.get('first') is not None and outs < 2
        is_scoring_pos = (bases.get('second') is not None or bases.get('third') is not None) and outs < 2

        is_ahead = strikes == 2
        is_behind = (balls == 3 and strikes < 2) or (balls == 2 and strikes == 0)
        is_full_count = balls == 3 and strikes == 2

        if is_bases_loaded:
            situation_tag = 'BASES_LOADED'
        elif is_double_play:
            situation_tag = 'DOUBLE_PLAY_SITUATION'
        elif is_scoring_pos:
            situation_tag = 'SCORING_POSITION'
        else:
            situation_tag = 'BASES_EMPTY'

        if is_ahead:
            count_context = f'AHEAD ({balls}-{strikes}) - PUT AWAY MODE'
        elif is_behind:
            count_context = f'BEHIND ({balls}-{strikes}) - STRIKE DEMAND'
        elif is_full_count:
            count_context = 'FULL COUNT (3-2) - HIGH LEVERAGE BATTLE'
        elif balls == 0 and strikes == 0:
            count_context = 'FIRST PITCH (0-0) - ESTABLISH COUNT'
        else:
            count_context = f'NEUTRAL ({balls}-{strikes}) - SETUP & ATTACK'

        if is_bases_loaded and is_ahead:
            strategy_name = 'BASES_LOADED_PUNCHOUT'
            rationale = 'Bases loaded with 2 strikes. Zero margin for error. Attack edges with high-whiff putaway arsenal to secure the strikeout.'
        elif is_bases_loaded and is_behind:
            strategy_name = 'BASES_LOADED_COMMAND_STRIKE'
            rationale = 'Bases loaded behind in count. Ball 4 forces home a run! Must challenge the zone with high-velocity 4-Seamer or Sinker.'
        elif is_bases_loaded:
            strategy_name = 'BASES_LOADED_LEVERAGE'
            rationale = 'Bases loaded pressure. Induce weak ground-ball or foul contact to prevent extra-base damage.'
        elif is_double_play:
            strategy_name = 'DOUBLE_PLAY_GROUNDER_HUNT'
            rationale = f'Runner on 1st with {outs} out. Target bottom of zone with Power Sinker (64% GB rate) to roll inning-ending double play.'
        elif is_ahead:
            strategy_name = 'TWO_STRIKE_PUT_AWAY'
            rationale = f'Ahead in count ({balls}-{strikes}). Expand zone into chase corridors with high-spin sweeper or breaking ball.'
        elif is_behind:
            strategy_name = 'CRITICAL_ZONE_CHALLENGE'
            rationale = f'Behind in count ({balls}-{strikes}). Paint strike zone shadow with high-velo fastball to prevent free pass.'
        elif is_scoring_pos:
            strategy_name = 'SCORING_POSITION_SUPPRESSION'
            rationale = f'Runner in scoring position with {outs} out. Suppress elevated contact to avoid sacrifice fly; attack batter cold zones.'
        else:
            strategy_name = 'NEUTRAL_PITCH_MIX'
            rationale = f'Bases empty, count {balls}-{strikes}. Balance fastball velocity and sweeper spin while avoiding batter hot zones.'

        arsenal = pitcher.get('arsenal', [])
        if not arsenal:
            arsenal = [
                {'name': '4-Seam Fastball', 'velocity_mph': 97.4, 'spin_rpm': 2480, 'break_rating': 90, 'control_rating': 84, 'statcast': {'whiff_pct': 28.5, 'chase_pct': 24.2, 'gb_pct': 38.0, 'stuff_plus': 118, 'zone_pct': 56.0, 'run_value': -4}},
                {'name': 'Spin Monster Sweeper', 'velocity_mph': 83.5, 'spin_rpm': 2980, 'break_rating': 99, 'control_rating': 80, 'statcast': {'whiff_pct': 44.5, 'chase_pct': 36.5, 'gb_pct': 42.0, 'stuff_plus': 135, 'zone_pct': 42.0, 'run_value': -12}},
                {'name': 'Power Sinker', 'velocity_mph': 95.8, 'spin_rpm': 2310, 'break_rating': 88, 'control_rating': 85, 'statcast': {'whiff_pct': 22.0, 'chase_pct': 28.0, 'gb_pct': 64.0, 'stuff_plus': 112, 'zone_pct': 58.0, 'run_value': -7}},
                {'name': 'Spike Curveball', 'velocity_mph': 81.2, 'spin_rpm': 2840, 'break_rating': 94, 'control_rating': 78, 'statcast': {'whiff_pct': 38.0, 'chase_pct': 33.0, 'gb_pct': 48.0, 'stuff_plus': 122, 'zone_pct': 46.0, 'run_value': -6}},
            ]

        pitch_weights_raw = []
        for item in arsenal:
            w = 100.0
            stat = item.get('statcast', {})
            name = item.get('name', '')
            if is_double_play:
                if 'Sinker' in name:
                    w *= 2.8
                elif 'Curveball' in name or 'Changeup' in name:
                    w *= 1.3
                elif 'Fastball' in name:
                    w *= 0.45
            if is_bases_loaded:
                if is_behind:
                    if 'Fastball' in name or 'Sinker' in name:
                        w *= 2.2
                    else:
                        w *= 0.4
                elif is_ahead:
                    if 'Sweeper' in name:
                        w *= 2.5
            if is_ahead:
                if 'Sweeper' in name:
                    w *= 3.0
                elif 'Curveball' in name:
                    w *= 2.0
                elif 'Fastball' in name:
                    w *= 0.55
            elif is_behind:
                if 'Fastball' in name:
                    w *= 2.6
                elif 'Sinker' in name:
                    w *= 1.9
                elif 'Sweeper' in name:
                    w *= 0.35

            if stat:
                if stat.get('stuff_plus', 0) > 125:
                    w *= 1.15
                if stat.get('whiff_pct', 0) > 40.0 and is_ahead:
                    w *= 1.25
                if stat.get('gb_pct', 0) > 60.0 and is_double_play:
                    w *= 1.35
            pitch_weights_raw.append({'item': item, 'w': w})

        total_pitch_weight = max(sum(x['w'] for x in pitch_weights_raw), 0.001)
        sorted_pitches = sorted(pitch_weights_raw, key=lambda x: x['w'], reverse=True)
        ranked_pitch_weights = []
        for idx, pw_dict in enumerate(sorted_pitches):
            item = pw_dict['item']
            w = pw_dict['w']
            prob = (w / total_pitch_weight) * 100.0
            if idx == 0 and is_double_play:
                reason = 'Primary weapon: Elite 64.0% GB rate to roll double play'
            elif idx == 0 and is_ahead:
                reason = 'Putaway weapon: 44.5% Whiff & elite spin rate'
            elif idx == 0 and is_behind:
                reason = 'Strike demand: High velocity & zone command'
            elif idx == len(sorted_pitches) - 1:
                reason = 'Deprioritized in current game leverage'
            else:
                reason = 'Secondary tactical option'

            ranked_pitch_weights.append({
                'pitch_name': item['name'],
                'weight': round(w, 1),
                'probability_pct': round(prob, 1),
                'rank': idx + 1,
                'is_most_likely': (idx == 0),
                'is_least_likely': (idx == len(sorted_pitches) - 1),
                'reasoning': reason,
                'statcast': item.get('statcast', {})
            })

        ALL_ZONES = [
            'upper-in', 'upper-middle', 'upper-away',
            'middle-in', 'heart', 'middle-away',
            'lower-in', 'lower-middle', 'lower-away',
            'chase-high', 'chase-low', 'chase-in', 'chase-away'
        ]
        RULEBOOK_STRIKES = {
            'upper-in', 'upper-middle', 'upper-away',
            'middle-in', 'heart', 'middle-away',
            'lower-in', 'lower-middle', 'lower-away'
        }
        hot_zones = batter.get('hot_zones', {})
        zone_weights_raw = []
        for zone in ALL_ZONES:
            zw = 10.0
            hot_slg = hot_zones.get(zone, 0.32)
            zone_is_strike = zone in RULEBOOK_STRIKES
            is_chase = not zone_is_strike

            if hot_slg >= 0.5:
                zone_type = 'HOT_ZONE'
            elif hot_slg <= 0.28 or zone in ('lower-away', 'middle-away'):
                zone_type = 'COLD_ZONE'
            elif is_chase:
                zone_type = 'CHASE_ZONE'
            else:
                zone_type = 'NEUTRAL_ZONE'

            if zone_type == 'HOT_ZONE':
                if is_behind and balls == 3 and strikes < 2:
                    zw *= 0.7
                else:
                    zw *= 0.22
            elif zone_type == 'COLD_ZONE':
                zw *= 2.4

            if is_ahead:
                if is_chase:
                    zw *= 3.4
                elif zone == 'heart':
                    zw *= 0.12
            elif is_behind:
                if is_chase:
                    zw *= 0.12
                else:
                    zw *= 2.0

            if is_double_play:
                if zone in ('lower-in', 'lower-middle', 'lower-away'):
                    zw *= 3.0
                elif zone == 'chase-low':
                    zw *= 2.6
                elif zone in ('upper-in', 'upper-middle', 'upper-away', 'chase-high'):
                    zw *= 0.3

            if is_bases_loaded and is_chase:
                zw *= 0.25

            zone_weights_raw.append({'zone': zone, 'zw': zw, 'zone_is_strike': zone_is_strike, 'zone_type': zone_type})

        total_zone_weight = max(sum(x['zw'] for x in zone_weights_raw), 0.001)
        sorted_zones = sorted(zone_weights_raw, key=lambda x: x['zw'], reverse=True)
        ranked_zone_weights = []
        for idx, zw_dict in enumerate(sorted_zones):
            zone = zw_dict['zone']
            zw = zw_dict['zw']
            prob = (zw / total_zone_weight) * 100.0
            ranked_zone_weights.append({
                'zone': zone,
                'weight': round(zw, 1),
                'probability_pct': round(prob, 1),
                'rank': idx + 1,
                'is_strike': zw_dict['zone_is_strike'],
                'zone_type': zw_dict['zone_type'],
                'is_most_likely': (idx == 0),
                'is_least_likely': (idx == len(sorted_zones) - 1)
            })

        top_pitch = ranked_pitch_weights[0]['pitch_name'] if ranked_pitch_weights else arsenal[0]['name']
        top_zone = ranked_zone_weights[0]['zone'] if ranked_zone_weights else 'lower-away'

        return {
            'strategy_name': strategy_name,
            'situation_tag': situation_tag,
            'count_context': count_context,
            'rationale': rationale,
            'recommended_pitch': top_pitch,
            'recommended_zone': top_zone,
            'pitch_weights': ranked_pitch_weights,
            'zone_weights': ranked_zone_weights,
            'command_quality': 'TARGET_EXECUTED'
        }

    def get_game_state_payload(self) -> Dict[str, Any]:
        cur_p = self.current_pitcher_obj()
        cur_b = self.current_batter_obj()

        p_name = getattr(cur_p, 'name', 'Pitcher') if cur_p else 'Pitcher'
        p_num = getattr(cur_p, 'number', 26) if cur_p else 26
        p_pos = getattr(cur_p, 'position', 'SP') if cur_p else 'SP'
        p_team = self.home_name if self.top_bottom == 'TOP' else self.away_name

        b_name = getattr(cur_b, 'name', 'Batter') if cur_b else 'Batter'
        b_num = getattr(cur_b, 'number', 99) if cur_b else 99
        b_pos = getattr(cur_b, 'position', 'RF') if cur_b else 'RF'
        b_team = self.away_name if self.top_bottom == 'TOP' else self.home_name

        pitch_count = self.pitch_count_home if self.top_bottom == 'TOP' else self.pitch_count_away

        payload = {
            'inning': self.inning,
            'top_bottom': self.top_bottom,
            'outs': self.outs,
            'balls': self.balls,
            'strikes': self.strikes,
            'score': {'home': self.score[self.home_name], 'away': self.score[self.away_name]},
            'bases': self.bases,
            'current_batter': {
                'id': getattr(cur_b, 'id', 201) if cur_b else 201,
                'name': b_name,
                'jersey_number': int(b_num) if str(b_num).isdigit() else 99,
                'position': b_pos,
                'team': b_team,
                'power': 99,
                'contact': 88,
                'vision': 85,
                'traits': ['Home Run Threat', 'First Pitch Ambush'],
                'hot_zones': JUDGE_DEFAULT_ZONES,
                'stats': {'at_bats': 3, 'hits': 1, 'rbis': 2, 'home_runs': 1}
            },
            'current_pitcher': {
                'id': getattr(cur_p, 'id', 101) if cur_p else 101,
                'name': p_name,
                'jersey_number': int(p_num) if str(p_num).isdigit() else 26,
                'position': p_pos,
                'team': p_team,
                'break_rating': 99,
                'velocity_rating': 98,
                'arm_strength': 97,
                'control': 68,
                'arsenal': [
                    {'name': '4-Seam Fastball', 'velocity_mph': 97.4, 'spin_rpm': 2480, 'break_rating': 90, 'control_rating': 84, 'statcast': {'whiff_pct': 28.5, 'chase_pct': 24.2, 'gb_pct': 38.0, 'stuff_plus': 118, 'zone_pct': 56.0, 'run_value': -4}},
                    {'name': 'Spin Monster Sweeper', 'velocity_mph': 83.5, 'spin_rpm': 2980, 'break_rating': 99, 'control_rating': 80, 'statcast': {'whiff_pct': 44.5, 'chase_pct': 36.5, 'gb_pct': 42.0, 'stuff_plus': 135, 'zone_pct': 42.0, 'run_value': -12}},
                    {'name': 'Power Sinker', 'velocity_mph': 95.8, 'spin_rpm': 2310, 'break_rating': 88, 'control_rating': 85, 'statcast': {'whiff_pct': 22.0, 'chase_pct': 28.0, 'gb_pct': 64.0, 'stuff_plus': 112, 'zone_pct': 58.0, 'run_value': -7}},
                    {'name': 'Spike Curveball', 'velocity_mph': 81.2, 'spin_rpm': 2840, 'break_rating': 94, 'control_rating': 78, 'statcast': {'whiff_pct': 38.0, 'chase_pct': 33.0, 'gb_pct': 48.0, 'stuff_plus': 122, 'zone_pct': 46.0, 'run_value': -6}},
                ],
                'stats': {'pitches_thrown': pitch_count, 'strikeouts': 6, 'walks': 1, 'hits_allowed': 3, 'runs_allowed': 1}
            },
            'game_over': self.game_over,
            'home_team': self.home_name,
            'away_team': self.away_name,
            'win_probability': 0.52
        }
        payload['strategy_intent'] = self.calculate_strategy_and_intent(payload)
        return payload

