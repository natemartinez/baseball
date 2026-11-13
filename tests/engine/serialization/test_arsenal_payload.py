import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.engine.game_engine.serialization.arsenal_payload import (
    build_arsenal_payload,
    DEFAULT_ARSENAL_PAYLOAD,
)


def test_none_pitcher_returns_default():
    result = build_arsenal_payload(None, None)
    assert result == [dict(item) for item in DEFAULT_ARSENAL_PAYLOAD]


def test_pitcher_with_no_arsenal_returns_default():
    p = MagicMock()
    p.pitch_arsenal = []
    result = build_arsenal_payload(p, None)
    assert result == [dict(item) for item in DEFAULT_ARSENAL_PAYLOAD]


def test_returns_list_of_dicts():
    result = build_arsenal_payload(None, None)
    assert isinstance(result, list)
    assert all(isinstance(item, dict) for item in result)

