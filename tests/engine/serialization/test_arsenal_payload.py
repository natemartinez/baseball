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


def test_default_arsenal_payload_sigma_scaled_to_radius():
    """Validates that DEFAULT_ARSENAL_PAYLOAD and DEFAULT_ARSENAL sigmas match max_radius_inches / 30.0."""
    from backend.engine.pitching_engine.pitcher_info.pitch_objects import DEFAULT_ARSENAL

    for source, label in [
        (DEFAULT_ARSENAL_PAYLOAD, "DEFAULT_ARSENAL_PAYLOAD"),
        (DEFAULT_ARSENAL, "DEFAULT_ARSENAL"),
    ]:
        for pitch in source:
            radius = pitch["max_radius_inches"]
            expected_sigma = round(radius / 30.0, 3)
            actual_sigma = round(pitch["sigma"], 3)
            assert actual_sigma == expected_sigma, (
                f"{label} {pitch.get('name') or pitch.get('id')} has unscaled sigma: "
                f"radius={radius}, sigma={actual_sigma}, expected={expected_sigma}"
            )



