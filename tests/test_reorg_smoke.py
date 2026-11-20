#!/usr/bin/env python3
"""
Post-reorganization smoke tests.

Guards the canonical module paths introduced when the engine packages were
split into ``game_engine``, ``pitch_execution``, ``pitch_selection``, and
``pitcher_info``. Also verifies that the Flask routes used by the Expo client
still respond with the expected payloads.
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.api.app import create_app
from backend.engine.game_engine import GameEngine, PitchFlowError
from backend.engine.game_engine.ball_flight import compute_batted_ball_trace
from backend.engine.game_engine.gameday_math import classify_gameday_zone
from backend.engine.game_engine.strike_zone import StrikeZone
from backend.engine.pitching_engine import (
    PITCH_CATEGORIES,
    PitchArsenal,
    PitcherInstanceManager,
    PitchingEngine,
    PitchStrategy,
    calculate_pitch_delivery,
)
from backend.engine.pitching_engine.pitch_selection import (
    PitchSelection,
    PitchSelectionError,
    PitchSelectionMode,
    select_pitch,
)


def test_canonical_imports_resolve():
    assert GameEngine is not None
    assert PitchFlowError is not None
    assert PitchingEngine is not None
    assert PitchStrategy is not None
    assert PitcherInstanceManager is not None
    assert PitchArsenal is not None
    assert PITCH_CATEGORIES
    assert callable(calculate_pitch_delivery)
    assert callable(compute_batted_ball_trace)
    assert callable(classify_gameday_zone)
    assert StrikeZone is not None
    assert select_pitch is not None
    assert PitchSelection is not None
    assert PitchSelectionMode.AI.value == 'AI'
    assert issubclass(PitchSelectionError, ValueError)

    # Importing the seeder must not raise (do not execute it: it mutates SQLite).
    import backend.database.seed  # noqa: F401

    # Pitching subpackages are regular packages
    import backend.engine.pitching_engine.pitcher_info as pe_info
    import backend.engine.pitching_engine.pitch_selection as pe_sel
    import backend.engine.pitching_engine.pitch_execution as pe_exec
    assert pe_info.ActivePitcherState is not None
    assert pe_sel.PitchStrategy is not None
    assert pe_exec.calculate_pitch_delivery is not None

    # Batting subpackages are regular packages
    import backend.engine.batting_engine.batter_info as be_info
    import backend.engine.batting_engine.swing_decision as be_swing
    import backend.engine.batting_engine.contact as be_contact
    assert be_info.BatterInstanceManager is not None
    assert be_swing.BatterStrategy is not None
    assert be_contact.ContactResolver is not None

    # Game engine subpackages are regular packages
    import backend.engine.game_engine.physics as ge_phys
    import backend.engine.game_engine.geometry as ge_geom
    import backend.engine.game_engine.game_logic as ge_logic
    import backend.engine.game_engine.orchestration as ge_orch
    import backend.engine.game_engine.serialization as ge_ser
    assert ge_phys.compute_batted_ball_trace is not None
    assert ge_geom.StrikeZone is not None
    assert ge_logic.count_after_pitch is not None
    assert ge_orch.PitchFlowOrchestrator is not None
    assert ge_ser.build_state_payload is not None


def test_flask_endpoints_smoke():
    client = create_app().test_client()

    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.get_json()['status'] == 'ok'

    state = client.get('/api/state')
    assert state.status_code == 200
    state_data = state.get_json()
    assert state_data['game']
    assert state_data['lineups']
    assert state_data['rotations']

    teams = client.get('/api/teams')
    assert teams.status_code == 200
    team_list = teams.get_json()['teams']
    assert team_list

    roster = client.get(f"/api/rosters?team_id={team_list[0]['id']}")
    assert roster.status_code == 200
    assert roster.get_json()['team_id'] == team_list[0]['id']

    started = client.post(
        '/api/start_game',
        json={
            'home_team_id': team_list[0]['id'],
            'away_team_id': team_list[1]['id'] if len(team_list) > 1 else team_list[0]['id'],
            'seed': 424201,
        },
    )
    assert started.status_code == 200
    started_data = started.get_json()
    assert started_data['top_bottom'] == 'TOP'
    assert started_data['current_pitcher']

    thrown = client.post('/api/pitch/throw', json={})
    assert thrown.status_code == 200
    thrown_data = thrown.get_json()
    assert thrown_data['phase'] == 'THROWN'
    assert thrown_data['pitch_details']
    assert thrown_data['game_state']

    resolved = client.post('/api/pitch/resolve', json={'batter_decision': 'TAKE'})
    assert resolved.status_code == 200
    resolved_data = resolved.get_json()
    assert resolved_data['phase'] == 'RESOLVED'
    assert resolved_data['game_state']

    reset = client.post('/api/reset', json={'seed': 424201})
    assert reset.status_code == 200
    reset_data = reset.get_json()
    assert reset_data['game']
    assert reset_data['lineups']
    assert reset_data['rotations']


def test_conftest_fixtures_available():
    from tests.conftest import _game
    game = _game(seed=99)
    assert game is not None
    assert game.seed == 99


def test_test_folder_structure_is_modular():
    test_root = ROOT_DIR / 'tests'
    expected_dirs = ['api', 'database', 'engine', 'e2e_pitching_pipeline']
    for d in expected_dirs:
        assert (test_root / d).is_dir(), f"Expected directory tests/{d} to exist"

    engine_dirs = ['batting_engine', 'pitching_engine', 'game_engine', 'game_logic', 'game_modes', 'serialization']
    for ed in engine_dirs:
        assert (test_root / 'engine' / ed).is_dir(), f"Expected directory tests/engine/{ed} to exist"

    # Verify no stray test files at root
    root_test_files = list(test_root.glob('test_*.py'))
    assert len(root_test_files) == 1
    assert root_test_files[0].name == 'test_reorg_smoke.py'


