import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.engine.game_engine.physics import (
    compute_batted_ball_geometry,
    compute_batted_ball_trace,
    solve_ground_motion,
    ground_transit_time,
    BALL_FLIGHT_TRACE_ENABLED,
)

def test_physics_subpackage_exports():
    assert callable(compute_batted_ball_geometry)
    assert callable(compute_batted_ball_trace)
    assert callable(solve_ground_motion)
    assert callable(ground_transit_time)
    assert isinstance(BALL_FLIGHT_TRACE_ENABLED, bool)


def test_physics_functional_trace_generation():
    trace = compute_batted_ball_trace(100.0, 25.0, 0.0)
    assert trace is not None
    assert 'samples' in trace
    assert len(trace['samples']) > 0
    assert 'hang_time_s' in trace
    assert trace['hang_time_s'] > 0.0


