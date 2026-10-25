#!/usr/bin/env python3
"""
Pitch flow orchestrator tests.

Covers phase transitions, the BatterController seam, explicit reactions, and
the guarantee that GameEngine remains the only state mutator.
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from backend.api.app import create_app
from backend.database.db import get_player
from backend.engine.game_engine import GameEngine
from backend.engine.orchestration import (
    BatterReactionContext,
    PitchFlowError,
    PitchPhase,
)


class DeferredController:
    """A controller that pauses the flow until a reaction is submitted."""

    def __init__(self):
        self.context = None

    def choose_reaction(self, context: BatterReactionContext):
        self.context = context
        return None


def _game(seed=11, batter_controller=None):
    pitcher = get_player(1)
    batter = get_player(4)
    away = {
        'name': 'Away',
        'position_players': [batter],
        'pitchers': {'starters': [pitcher], 'bullpen': []},
    }
    home = {
        'name': 'Home',
        'position_players': [batter],
        'pitchers': {'starters': [pitcher], 'bullpen': []},
    }
    return GameEngine(
        home,
        away,
        'Home',
        'Away',
        seed=seed,
        batter_controller=batter_controller,
    )


def test_phase_transitions_and_guards():
    game = _game()
    orchestrator = game.orchestrator

    assert orchestrator.phase is PitchPhase.IDLE
    with pytest.raises(PitchFlowError, match='No pitch in flight'):
        orchestrator.resolve_pitch()

    game.throw_pitch(target_zone='heart')
    assert orchestrator.phase is PitchPhase.THROWN

    duplicate = game.throw_pitch(target_zone='heart')
    assert duplicate['status'] == 'error'
    assert 'already in flight' in duplicate['message']

    resolved = game.resolve_pitch()
    assert resolved['phase'] == 'RESOLVED'
    assert orchestrator.phase is PitchPhase.IDLE
    assert orchestrator.pending is None


def test_reset_clears_pending_from_every_phase():
    game = _game()
    orchestrator = game.orchestrator

    game.throw_pitch()
    assert orchestrator.has_pending
    orchestrator.reset()
    assert orchestrator.phase is PitchPhase.IDLE
    assert orchestrator.pending is None
    assert not orchestrator.has_pending

    deferred = DeferredController()
    game = _game(batter_controller=deferred)
    game.throw_pitch()
    outcome = game.resolve_pitch()
    assert outcome['phase'] == 'AWAITING_REACTION'
    assert game.orchestrator.phase is PitchPhase.AWAITING_REACTION
    game.orchestrator.reset()
    assert game.orchestrator.phase is PitchPhase.IDLE
    assert not game.has_pending_pitch


def test_explicit_take_matches_plate_crossing():
    game = _game(seed=21)
    thrown = game.throw_pitch(target_zone='heart')
    was_strike = thrown['pitch_details']['gameday_packet']['result']['isStrike']

    resolved = game.resolve_pitch(batter_decision='TAKE')
    assert resolved['status'] == 'success'
    assert resolved['pitch_details']['batter_decision'] == 'TAKE'
    expected = 'CALLED_STRIKE' if was_strike else 'BALL'
    assert resolved['pitch_details']['pitch_result'] == expected
    assert resolved['pitch_details']['gameday_packet']['result']['call'] == expected


def test_explicit_swing_never_takes():
    game = _game(seed=22)
    game.throw_pitch(target_zone='heart')
    resolved = game.resolve_pitch(batter_decision='SWING')

    assert resolved['pitch_details']['batter_decision'] == 'SWING'
    assert resolved['pitch_details']['pitch_result'] in {
        'SWINGING_STRIKE', 'FOUL', 'IN_PLAY_OUT',
        'SINGLE', 'DOUBLE', 'TRIPLE', 'HOME_RUN',
    }


def test_invalid_reaction_values_are_rejected_without_state_change():
    game = _game(seed=23)
    game.throw_pitch()
    before = (game.balls, game.strikes, game.outs, dict(game.score))

    inverted = game.resolve_pitch(batter_decision='BUNT')
    assert inverted['status'] == 'error'
    assert (game.balls, game.strikes, game.outs, dict(game.score)) == before
    assert game.has_pending_pitch

    bad_approach = game.resolve_pitch(batter_approach='RECKLESS')
    assert bad_approach['status'] == 'error'
    assert (game.balls, game.strikes, game.outs, dict(game.score)) == before
    assert game.has_pending_pitch


def test_manual_controller_pauses_then_submits_reaction():
    controller = DeferredController()
    game = _game(seed=24, batter_controller=controller)

    thrown = game.throw_pitch(target_zone='heart')
    before = (game.balls, game.strikes, game.outs, dict(game.score))

    paused = game.resolve_pitch()
    assert paused['status'] == 'success'
    assert paused['phase'] == 'AWAITING_REACTION'
    assert paused['reaction_context']['zone_name'] == thrown['pitch_details']['actual_zone']
    assert (game.balls, game.strikes, game.outs, dict(game.score)) == before

    # A second resolve cannot re-enter the reaction phase.
    rejected = game.resolve_pitch()
    assert rejected['status'] == 'error'

    resolved = game.submit_batter_reaction('SWING')
    assert resolved['status'] == 'success'
    assert resolved['phase'] == 'RESOLVED'
    assert resolved['pitch_details']['batter_decision'] == 'SWING'
    assert game.has_pending_pitch is False


def test_orchestrator_does_not_import_game_engine():
    source = (ROOT_DIR / 'backend' / 'engine' / 'orchestration' /
              'pitch_orchestrator.py').read_text()
    assert 'game_engine' not in source


def test_ai_mode_is_deterministic_for_a_seed():
    first = _game(seed=303)
    second = _game(seed=303)

    for _ in range(8):
        first.throw_pitch()
        second.throw_pitch()
        assert first.pitch_phase == second.pitch_phase
        first_resolved = first.resolve_pitch()
        second_resolved = second.resolve_pitch()
        assert first_resolved['pitch_details']['pitch_result'] == (
            second_resolved['pitch_details']['pitch_result']
        )
        assert first_resolved['pitch_details']['batter_decision'] == (
            second_resolved['pitch_details']['batter_decision']
        )


def test_api_throw_is_null_and_explicit_reaction_resolves():
    client = create_app().test_client()
    assert client.post('/api/start_game', json={'seed': 31}).status_code == 200

    thrown = client.post('/api/pitch/throw', json={})
    assert thrown.status_code == 200
    thrown_data = thrown.get_json()
    assert thrown_data['phase'] == 'THROWN'
    assert thrown_data['pitch_details']['batter_decision'] is None
    assert thrown_data['pitch_details']['pitch_result'] is None
    assert thrown_data['pitch_details']['gameday_packet']['result']['call'] is None

    invalid = client.post('/api/pitch/resolve', json={'batter_decision': 'BUNT'})
    assert invalid.status_code == 400
    still_pending = client.post('/api/pitch/throw', json={})
    assert still_pending.status_code == 409

    resolved = client.post('/api/pitch/resolve', json={'batter_decision': 'TAKE'})
    assert resolved.status_code == 200
    resolved_data = resolved.get_json()
    assert resolved_data['phase'] == 'RESOLVED'
    assert resolved_data['pitch_details']['batter_decision'] == 'TAKE'
    assert resolved_data['pitch_details']['pitch_result'] in (
        'BALL', 'CALLED_STRIKE'
    )
