"""Backward-compatibility re-export for ball flight kinematics and trace generation."""
import sys
from .physics import ball_flight as _canonical

sys.modules[__name__] = _canonical

from .physics.ball_flight import *  # noqa: F401, F403
from .physics.ball_flight import (
    BALL_FLIGHT_TRACE_ENABLED,
    compute_batted_ball_geometry,
    compute_batted_ball_trace,
    ground_transit_time,
    solve_ground_motion,
)
