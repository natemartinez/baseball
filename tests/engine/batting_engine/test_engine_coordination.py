import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.engine.batting_engine import (
    BattingEngine,
    BatterActivity,
    BatterInstanceManager,
    InGameBatterRatings,
    BatterStrategy,
    ContactResolver,
)
import backend.engine.batting_engine.batter_info as bi
import backend.engine.batting_engine.swing_decision as sd
import backend.engine.batting_engine.contact as ct

def test_engine_coordination_and_subpackage_alignment():
    assert bi.BatterInstanceManager is BatterInstanceManager
    assert bi.InGameBatterRatings is InGameBatterRatings
    assert sd.BatterStrategy is BatterStrategy
    assert ct.ContactResolver is ContactResolver
    assert BattingEngine is not None
    assert BatterActivity is not None

