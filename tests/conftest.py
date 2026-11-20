"""
Root Pytest Configuration and Shared Test Fixtures.
Ensures repository root is on sys.path and centralizes reusable simulation factories.
"""

import sys
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_player
from backend.engine.game_engine import GameEngine


def _game(seed: int = 42, batter_id: int = 4) -> GameEngine:
    """Standard game engine factory for test scenarios."""
    pitcher = get_player(1)
    batter = get_player(batter_id)
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
    return GameEngine(home, away, 'Home', 'Away', seed=seed)


@pytest.fixture
def standard_game() -> GameEngine:
    return _game(seed=42)
