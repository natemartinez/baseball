"""
MLB Statcast Authoritative Game Engine.

Implements the central simulation highway coordinating pitch execution,
batter reactions, count state, and telemetry serialization.
"""

import random
from typing import Any, Dict, List, Optional

from backend.models.player import Player
from .strike_zone import StrikeZone
from .gameday_math import determine_situation_category
from backend.engine.modes.mode_controller import ModeController
from .orchestration import (
    PitchFlowError,
    PitchFlowOrchestrator,
)
from .orchestration.packet_builder import (
    build_gameday_packet,
    build_pitch_details,
)
from .game_logic import (
    count_after_pitch,
    HalfInningState,
    switch_half_inning,
    BatterStatsTracker,
    GameSnapshot,
    StateDiff,
    apply_activity,
    swing_decision_telemetry_enabled,
)
from .serialization import (
    build_arsenal_payload,
    build_state_payload,
    DEFAULT_ARSENAL_PAYLOAD,
)


SWING_DECISION_TELEMETRY = swing_decision_telemetry_enabled()
_DEFAULT_ARSENAL_PAYLOAD = DEFAULT_ARSENAL_PAYLOAD


class GameEngine:
    @staticmethod
    def _ensure_player(player_or_dict: Any) -> Any:
        """Boundary guard: Ensures a participant is an authoritative Player object."""
        if player_or_dict is None:
            return None
        if isinstance(player_or_dict, dict) and Player is not None:
            return Player.from_dict(player_or_dict)
        return player_or_dict

    @staticmethod
    def _build_arsenal_payload(
        pitcher: Any, active_state: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Serializes the pitcher's hydrated arsenal for client display."""
        return build_arsenal_payload(pitcher, active_state=active_state)

    def __init__(
        self,
        home_roster: dict,
        away_roster: dict,
        home_name: Optional[str] = None,
        away_name: Optional[str] = None,
        seed: Optional[int] = None,
        batter_controller: Any = None,
    ):
        self.home_roster = home_roster
        self.away_roster = away_roster
        self.home_name = (
            home_name
            or (home_roster.get('team_name') if isinstance(home_roster, dict) else None)
            or 'Home'
        )
        self.away_name = (
            away_name
            or (away_roster.get('team_name') if isinstance(away_roster, dict) else None)
            or 'Away'
        )
        self.seed = seed
        self.rng = random.Random(seed)

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

        from ..pitching_engine import PitchingEngine

        self.away_pitcher_state = (
            PitchingEngine.create_pitcher_state(self.away_pitcher)
            if self.away_pitcher is not None
            else None
        )
        self.home_pitcher_state = (
            PitchingEngine.create_pitcher_state(self.home_pitcher)
            if self.home_pitcher is not None
            else None
        )

        self.pitch_count_home = 0
        self.pitch_count_away = 0
        self.session_pitch_count = 0
        self.recent_pitches_sequence: List[str] = []
        # Full pitch history for current plate appearance
        self.current_at_bat_pitches: List[Dict[str, Any]] = []

        self.strike_zone = StrikeZone()
        self.last_command_quality = 'TARGET_EXECUTED'
        # The orchestrator owns pitch phase and pending delivery snapshot
        self.orchestrator = PitchFlowOrchestrator(
            rng=self.rng, batter_controller=batter_controller
        )

        # Domain managers
        self._stats_tracker = BatterStatsTracker()
        self.mode_controller = ModeController(self)

    # ─── Read-only Field Lookups ──────────────────────────────────────────────

    def current_batter_obj(self) -> Any:
        lineup = self.away_lineup if self.top_bottom == 'TOP' else self.home_lineup
        idx = self.away_batter_idx if self.top_bottom == 'TOP' else self.home_batter_idx
        if lineup and idx < len(lineup):
            return lineup[idx]
        return None

    def current_pitcher_obj(self) -> Any:
        pitcher = self.home_pitcher if self.top_bottom == 'TOP' else self.away_pitcher
        if pitcher is not None:
            return pitcher

        defensive_roster = self.home_roster if self.top_bottom == 'TOP' else self.away_roster
        defensive_team_name = self.home_name if self.top_bottom == 'TOP' else self.away_name
        starters = defensive_roster.get('pitchers', {}).get('starters', []) if defensive_roster else []
        bullpen = defensive_roster.get('pitchers', {}).get('bullpen', []) if defensive_roster else []
        for candidate in (starters + bullpen):
            if candidate:
                resolved = self._ensure_player(candidate)
                if self.top_bottom == 'TOP':
                    self.home_pitcher = resolved
                else:
                    self.away_pitcher = resolved
                return resolved

        default_pitcher = Player(
            name=f"{defensive_team_name} Pitcher",
            position="P",
            ratings={'control': 75, 'velocity': 94, 'break': 80, 'stamina': 75},
        )
        if self.top_bottom == 'TOP':
            self.home_pitcher = default_pitcher
        else:
            self.away_pitcher = default_pitcher
        return default_pitcher

    def current_pitcher_state(self) -> Any:
        """Returns the ActivePitcherState for the pitcher currently on the mound."""
        self.current_pitcher_obj()
        from ..pitching_engine import PitchingEngine

        if self.top_bottom == 'TOP':
            if self.home_pitcher_state is None and self.home_pitcher is not None:
                self.home_pitcher_state = PitchingEngine.create_pitcher_state(self.home_pitcher)
            return self.home_pitcher_state
        else:
            if self.away_pitcher_state is None and self.away_pitcher is not None:
                self.away_pitcher_state = PitchingEngine.create_pitcher_state(self.away_pitcher)
            return self.away_pitcher_state

    def build_pitcher_arsenal_payload(self) -> List[Dict[str, Any]]:
        """Builds client pitch arsenal payload using cached metrics from active pitcher state."""
        cur_p = self.current_pitcher_obj()
        cur_state = self.current_pitcher_state()
        return build_arsenal_payload(cur_p, active_state=cur_state)

    def get_game_state_payload(self) -> Dict[str, Any]:
        """Constructs the authoritative client payload representing current game state."""
        return build_state_payload(self)

    # ─── Batter Stats Delegators ──────────────────────────────────────────────

    @property
    def _batter_game_stats(self) -> Dict[str, Dict[str, int]]:
        return self._stats_tracker.all_stats()

    @_batter_game_stats.setter
    def _batter_game_stats(self, val: Dict[str, Dict[str, int]]) -> None:
        self._stats_tracker._stats = val

    def _copy_batter_stats(self) -> Dict[str, Dict[str, int]]:
        return self._stats_tracker.copy()

    def _batter_game_line(self, batter: Any) -> Dict[str, int]:
        return self._stats_tracker.get_line(batter)

    def _batter_stats_key(self, batter: Any) -> str:
        return self._stats_tracker.stats_key(batter)

    # ─── Game Mode FSM & State ────────────────────────────────────────────────

    def set_mode(self, mode: Any) -> Dict[str, Any]:
        """Switches game execution mode (e.g. 'NORMAL', 'PRACTICE')."""
        return self.mode_controller.set_mode(mode)

    @property
    def active_mode(self) -> str:
        """Current execution mode name."""
        return self.mode_controller.active_mode.value

    # ─── State Mutation & Order Advancement ───────────────────────────────────

    def _advance_batter_order(self) -> None:
        if self.top_bottom == 'TOP':
            self.away_batter_idx = (self.away_batter_idx + 1) % max(1, len(self.away_lineup))
        else:
            self.home_batter_idx = (self.home_batter_idx + 1) % max(1, len(self.home_lineup))
        self.current_at_bat_pitches = []

    def _batting_score_diff(self) -> int:
        """Signed run differential for the team currently batting."""
        if self.top_bottom == 'TOP':
            return self.score[self.away_name] - self.score[self.home_name]
        return self.score[self.home_name] - self.score[self.away_name]

    def _switch_half_inning(self) -> None:
        """Switches half-inning, resets count/bases/outs and clears sequence buffers."""
        state = HalfInningState(
            outs=self.outs,
            balls=self.balls,
            strikes=self.strikes,
            bases=self.bases,
            top_bottom=self.top_bottom,
            inning=self.inning,
            game_over=self.game_over,
        )
        new_state = switch_half_inning(state, self.score, self.home_name, self.away_name)
        self.outs = new_state.outs
        self.balls = new_state.balls
        self.strikes = new_state.strikes
        self.bases = new_state.bases
        self.top_bottom = new_state.top_bottom
        self.inning = new_state.inning
        self.game_over = new_state.game_over
        self.recent_pitches_sequence = []
        self.current_at_bat_pitches = []

    def _commit(self, diff: StateDiff) -> None:
        """Single authoritative write point: applies a StateDiff to engine state."""
        self.balls = diff.balls
        self.strikes = diff.strikes
        self.outs = diff.outs
        self.bases = diff.bases
        for team, delta in (diff.score_delta or {}).items():
            self.score[team] = self.score.get(team, 0) + delta
        if diff.advance_batter:
            self._advance_batter_order()
        if diff.switch_half:
            self._switch_half_inning()
        if diff.game_over:
            self.game_over = True

    def _apply_batter_activity(self, activity: Any, batter: Any) -> None:
        """Pure delegator: routes activity through pure mutator and commits diff."""
        snapshot = GameSnapshot(
            balls=self.balls,
            strikes=self.strikes,
            outs=self.outs,
            bases=self.bases,
            score=self.score,
            top_bottom=self.top_bottom,
            inning=self.inning,
            game_over=self.game_over,
        )
        batting_team = self.away_name if self.top_bottom == 'TOP' else self.home_name
        batter_summary = {
            'id': getattr(batter, 'id', 1) if batter else 1,
            'name': getattr(batter, 'name', 'Batter') if batter else 'Batter',
            'jersey_number': getattr(batter, 'number', 99) if batter else 99,
            'position': getattr(batter, 'position', 'DH') if batter else 'DH',
            'team': batting_team,
        }
        diff = apply_activity(snapshot, activity, batter_summary, batting_team, self._stats_tracker)
        self._commit(diff)

    # ─── Orchestrator Properties ──────────────────────────────────────────────

    @property
    def has_pending_pitch(self) -> bool:
        """True while a thrown ball is in flight awaiting batter activity."""
        return self.orchestrator.has_pending

    @property
    def last_pitch_context(self) -> Any:
        """Authoritative black-box PitchContext for the most recent pitch."""
        return getattr(self.orchestrator, 'context', None)

    @property
    def pitch_phase(self) -> str:
        """Current pitch-flow phase (owned by the orchestrator)."""
        return self.orchestrator.phase.value

    # ─── Pitch Highway API ────────────────────────────────────────────────────

    def throw_pitch(
        self,
        pitch_intent: Optional[str] = None,
        pitch_type: Optional[str] = None,
        target_zone: Optional[str] = None,
        custom_target: Optional[Dict[str, float]] = None,
        practice: bool = False,
        selection_mode: Optional[str] = None,
        pitch_name: Optional[str] = None,
        timing_tier: Optional[str] = None,
        timing_label: Optional[str] = None,
        pitch_effectiveness: Optional[float] = None,
        delivery: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Stage 1 — Throw the ball.
        Runs pitching pipeline through delivery execution and returns flight telemetry.
        """
        if self.mode_controller.is_practice_active and delivery is None and not practice:
            return {
                'status': 'error',
                'message': 'Batting practice is active; use the practice endpoints.',
            }
        if self.game_over:
            return {'status': 'error', 'message': 'Game is over'}
        if self.has_pending_pitch:
            return {
                'status': 'error',
                'message': 'A pitch is already in flight; resolve it before throwing another.',
            }

        pitcher = self.current_pitcher_state() or self.current_pitcher_obj()
        batter = self.current_batter_obj()

        if timing_tier is None and getattr(getattr(self, 'home_roster', None), 'get', lambda k: None)('name') == 'Calibration':
            timing_tier = 'GOOD'
            timing_label = 'GOOD'

        if self.top_bottom == 'TOP':
            self.pitch_count_home += 1
            cur_pitch_count = self.pitch_count_home
        else:
            self.pitch_count_away += 1
            cur_pitch_count = self.pitch_count_away
        self.session_pitch_count += 1

        r1 = self.bases['first'] is not None
        r2 = self.bases['second'] is not None
        r3 = self.bases['third'] is not None
        sit_category = determine_situation_category(
            self.balls, self.strikes, self.outs, r1, r2, r3
        )

        from ..pitching_engine.pitch_selection import PitchSelectionError

        try:
            started = self.orchestrator.start_pitch(
                pitcher=pitcher,
                batter=batter,
                balls=self.balls,
                strikes=self.strikes,
                outs=self.outs,
                runners=(r1, r2, r3),
                situation=sit_category,
                pitch_count=cur_pitch_count,
                recent_pitches=self.recent_pitches_sequence,
                pitch_intent=pitch_intent,
                pitch_type=pitch_type,
                target_zone=target_zone,
                custom_target=custom_target,
                selection_mode=selection_mode,
                pitch_name=pitch_name,
                pitch_sequence=[dict(pitch) for pitch in self.current_at_bat_pitches],
                score_diff=self._batting_score_diff(),
                inning=self.inning,
                timing_tier=timing_tier,
                timing_label=timing_label,
                pitch_effectiveness=pitch_effectiveness,
                delivery=delivery,
            )
        except (PitchFlowError, PitchSelectionError) as error:
            return {'status': 'error', 'message': str(error)}

        delivery = started['delivery']
        actual_zone_name = started['actual_zone_name']
        self.recent_pitches_sequence.append(delivery['selected_pitch'])

        pending_result = {
            'call': None,
            'isStrike': delivery['is_strike'],
            'exitVelocityMph': None,
            'launchAngleDeg': None,
            'description': 'Pitch in flight - awaiting batter activity',
        }

        ctx = self.orchestrator.context
        gameday_packet = started.get('gameday_packet') or (
            build_gameday_packet(ctx, pending_result, rng=self.rng)
            if ctx
            else {}
        )
        pitch_details = started.get('pitch_details') or (
            build_pitch_details(
                ctx,
                description='Pitch in flight',
                gameday_packet=gameday_packet,
            )
            if ctx
            else {}
        )

        game_state = self.get_game_state_payload()
        return {
            'status': 'success',
            'phase': 'THROWN',
            'execution': {
                'ability_tier': delivery.get('ability_tier'),
                'timing_tier': delivery.get('timing_tier'),
                'timing_label': delivery.get('timing_label'),
                'base_radius_inches': delivery.get('base_radius_inches'),
                'executed_radius_inches': delivery.get('executed_radius_inches'),
                'radial_miss_inches': delivery.get('radial_miss_inches', delivery.get('radial_miss_in', 0.0)),
                'realized_x': delivery.get('realized_x'),
                'realized_z': delivery.get('realized_z'),
            },
            'pitch_details': pitch_details,
            'gameday_packet': gameday_packet,
            'game_state': game_state,
            'pitch': pitch_details,
            'game': game_state,
        }

    def resolve_pitch(
        self,
        batter_approach: str = 'AUTO',
        batter_decision: Optional[str] = None,
        contact: Optional[Dict[str, Any]] = None,
        practice: bool = False,
    ) -> Dict[str, Any]:
        """
        Stage 2 — Batter activity.
        Delegates reaction and contact to orchestrator, then commits state.
        """
        if self.mode_controller.is_practice_active and not practice:
            return {
                'status': 'error',
                'message': 'Batting practice is active; use the practice endpoints.',
            }
        if not self.has_pending_pitch:
            return {'status': 'error', 'message': 'No pitch in flight to resolve'}

        try:
            outcome = self.orchestrator.resolve_pitch(
                batter_decision=batter_decision,
                batter_approach=batter_approach,
                contact=contact,
            )
        except PitchFlowError as error:
            return {'status': 'error', 'message': str(error)}

        if outcome['phase'] == 'AWAITING_REACTION':
            game_state = self.get_game_state_payload()
            return {
                'status': 'success',
                'phase': 'AWAITING_REACTION',
                'reaction_context': outcome.get('reaction_context'),
                'game_state': game_state,
                'game': game_state,
            }

        return self._finalize_resolved_pitch(
            outcome['pending'], outcome['activity']
        )

    def submit_batter_reaction(
        self, decision: str, batter_approach: str = 'AUTO'
    ) -> Dict[str, Any]:
        """Future-facing facade for user-controlled batter reaction."""
        try:
            outcome = self.orchestrator.submit_reaction(
                decision, approach=batter_approach
            )
        except PitchFlowError as error:
            return {'status': 'error', 'message': str(error)}
        return self._finalize_resolved_pitch(
            outcome['pending'], outcome['activity']
        )

    def _finalize_resolved_pitch(self, pending: Any, activity: Any) -> Dict[str, Any]:
        """Applies resolved activity to state and constructs response payload."""
        balls_after, strikes_after = count_after_pitch(
            pending.balls, pending.strikes, activity.pitch_result
        )
        self.current_at_bat_pitches.append({
            'pitch_name': pending.delivery.get('selected_pitch', '4-Seam Fastball'),
            'pitch_category': pending.delivery.get('pitch_category', 'Fastball'),
            'zone_name': pending.actual_zone_name,
            'zone_category': pending.zone_category,
            'is_strike': pending.is_strike,
            'result': activity.pitch_result,
            'balls': balls_after,
            'strikes': strikes_after,
        })

        self._apply_batter_activity(activity, pending.batter)
        self.orchestrator.mark_applied()

        strike_check = activity.is_strike
        pitch_result_type = activity.pitch_result
        call = activity.call
        description = activity.description
        exit_velo = activity.exit_velocity_mph
        launch_angle = activity.launch_angle_deg

        result_payload = {
            'call': call,
            'isStrike': strike_check,
            'exitVelocityMph': exit_velo,
            'launchAngleDeg': launch_angle,
            'description': description,
        }

        ctx = self.orchestrator.context
        gameday_packet = getattr(ctx, 'gameday_packet', None) or (
            build_gameday_packet(ctx, result_payload, rng=self.rng) if ctx else {}
        )
        pitch_details = getattr(ctx, 'pitch_details', None) or (
            build_pitch_details(
                ctx,
                description=description,
                result_type=pitch_result_type,
                batter_decision='SWING' if activity.decision == 'SWING' else 'TAKE',
                exit_velo=exit_velo,
                launch_angle=launch_angle,
                spray_angle=activity.spray_angle_deg,
                batted_ball=activity.batted_ball,
                swing_decision=getattr(activity, 'swing_decision', None),
                gameday_packet=gameday_packet,
            )
            if ctx
            else {}
        )

        self.orchestrator.finish()
        game_state = self.get_game_state_payload()
        return {
            'status': 'success',
            'phase': 'RESOLVED',
            'pitch_details': pitch_details,
            'gameday_packet': gameday_packet,
            'game_state': game_state,
            'pitch': pitch_details,
            'game': game_state,
        }

    def pitch(
        self,
        pitch_intent: Optional[str] = None,
        pitch_type: Optional[str] = None,
        target_zone: Optional[str] = None,
        custom_target: Optional[Dict[str, float]] = None,
        batter_approach: str = 'AUTO',
        selection_mode: Optional[str] = None,
        pitch_name: Optional[str] = None,
        timing_tier: Optional[str] = None,
        timing_label: Optional[str] = None,
        pitch_effectiveness: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Synchronous throw + resolve convenience wrapper."""
        thrown = self.throw_pitch(
            pitch_intent=pitch_intent,
            pitch_type=pitch_type,
            target_zone=target_zone,
            custom_target=custom_target,
            selection_mode=selection_mode,
            pitch_name=pitch_name,
            timing_tier=timing_tier,
            timing_label=timing_label,
            pitch_effectiveness=pitch_effectiveness,
        )
        if thrown.get('status') != 'success':
            return thrown
        resolved = self.resolve_pitch(batter_approach=batter_approach)
        if 'execution' in thrown and 'execution' not in resolved:
            resolved['execution'] = thrown['execution']
        return resolved

    def pitching_engine(
        self,
        pitch_intent: Optional[str] = None,
        pitch_type: Optional[str] = None,
        target_zone: Optional[str] = None,
        custom_target: Optional[Dict[str, float]] = None,
        batter_approach: str = 'AUTO',
        selection_mode: Optional[str] = None,
        pitch_name: Optional[str] = None,
        timing_tier: Optional[str] = None,
        timing_label: Optional[str] = None,
        pitch_effectiveness: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Public alias for pitch()."""
        return self.pitch(
            pitch_intent=pitch_intent,
            pitch_type=pitch_type,
            target_zone=target_zone,
            custom_target=custom_target,
            batter_approach=batter_approach,
            selection_mode=selection_mode,
            pitch_name=pitch_name,
            timing_tier=timing_tier,
            timing_label=timing_label,
            pitch_effectiveness=pitch_effectiveness,
        )

    def sim_at_bat(self) -> Dict[str, Any]:
        """Simulates pitches until the current at-bat concludes."""
        if self.has_pending_pitch:
            return {
                'status': 'error',
                'message': 'A pitch is in flight; resolve it before simulating an at-bat.',
            }
        loops = 0
        last_result = None
        while loops < 15:
            loops += 1
            last_result = self.pitch()
            if self.balls == 0 and self.strikes == 0:
                break
        return last_result or self.pitch()

    def calculate_strategy_and_intent(
        self, state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        from ..pitching_engine.pitch_selection.recommendation import (
            calculate_strategy_and_intent,
        )

        batter = state.get('current_batter', {}) if state else {}
        pitcher = state.get('current_pitcher', {}) if state else {}
        return calculate_strategy_and_intent(
            outs=self.outs,
            balls=self.balls,
            strikes=self.strikes,
            bases=self.bases,
            batter=batter,
            pitcher=pitcher,
        )
