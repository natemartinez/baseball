import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.engine.game_engine.game_logic.config import swing_decision_telemetry_enabled


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv('SWING_DECISION_TELEMETRY', raising=False)
    assert swing_decision_telemetry_enabled() is False


def test_enabled_by_env(monkeypatch):
    monkeypatch.setenv('SWING_DECISION_TELEMETRY', '1')
    assert swing_decision_telemetry_enabled() is True

