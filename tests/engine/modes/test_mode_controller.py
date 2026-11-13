import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.api.app import create_app
from backend.engine.modes.mode_controller import ModeController, GameMode
from backend.engine.game_engine.engine import GameEngine


def test_initial_mode_is_normal():
    engine = GameEngine({}, {})
    assert engine.mode_controller.active_mode == GameMode.NORMAL
    assert not engine.mode_controller.is_practice_active


def test_set_mode_switches_to_practice_and_back():
    engine = GameEngine({}, {})
    engine.set_mode('PRACTICE')
    assert engine.active_mode == 'PRACTICE'
    assert engine.mode_controller.is_practice_active

    engine.set_mode('NORMAL')
    assert engine.active_mode == 'NORMAL'
    assert not engine.mode_controller.is_practice_active


def test_api_mode_fsm_endpoint():
    client = create_app().test_client()
    assert client.post('/api/start_game', json={'seed': 2026}).status_code == 200

    # Switch to PRACTICE
    resp = client.post('/api/mode', json={'mode': 'PRACTICE'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['game']['balls'] == 0
    assert data['game']['strikes'] == 0

    # Switch back to NORMAL
    resp = client.post('/api/mode', json={'mode': 'NORMAL'})
    assert resp.status_code == 200
