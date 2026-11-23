"""
Fielder Throw Kinematics and 3D Trajectory Solver.

Calculates glove-to-hand transfer time, recovery delays for diving/off-balance catches,
aerodynamic throw flight times to base targets (or unassisted bag touches), and
generates bounded 10-sample 4D space-time trajectories [x, y, z, t].
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple

from backend.engine.models.player import Player

# Standard 3D diamond base coordinates (Home, 1B, 2B, 3B) in feet.
# 90 ft baseline: 90 * sqrt(2)/2 = 63.6396 ft.
BASE_COORDINATES: Dict[str, Tuple[float, float, float]] = {
    "HOME": (0.0, 0.0, 0.0),
    "1B": (63.64, 63.64, 3.0),
    "2B": (0.0, 127.28, 3.0),
    "3B": (-63.64, 63.64, 3.0),
}


@dataclass(frozen=True)
class ThrowResult:
    """Encapsulates the complete kinematic resolution of a throw to a base."""
    thrower_id: str
    target_base: str
    start_pos: Tuple[float, float, float]
    target_pos: Tuple[float, float, float]
    transfer_time_s: float
    throw_flight_time_s: float
    throw_start_time_s: float
    ball_arrival_time_s: float
    throw_distance_ft: float
    throw_velocity_mph: float
    offline_distance_ft: float
    is_unassisted: bool
    samples: List[List[float]]  # 10 samples of [x, y, z, t]


def calculate_transfer_time(
    transfer_speed: float = 65.0,
    fielding_type: str = "GROUND_SCOOP",
    body_control: float = 65.0,
) -> float:
    """
    Computes glove-to-hand transfer duration in seconds.

    Base transfer scales from 0.85s (rating 0) to 0.45s (rating 100).
    Off-balance / diving catches incur a recovery pause scaled down by body control.
    """
    spd = max(0.0, min(100.0, float(transfer_speed)))
    bc = max(0.0, min(100.0, float(body_control)))

    base_transfer = 0.85 - (spd / 100.0) * 0.40

    recovery_penalty = 0.0
    if fielding_type in ("DIVING_CATCH", "SLIDING_CATCH"):
        # Diving/sliding stops require planting and rising
        recovery_penalty = 0.50 * max(0.20, 1.0 - (bc / 150.0))
    elif fielding_type == "BACKHAND_PICK":
        # Backhand picks require setting feet/slot
        recovery_penalty = 0.20 * max(0.20, 1.0 - (bc / 150.0))

    return round(base_transfer + recovery_penalty, 3)


def solve_fielder_throw(
    fielder_id: str,
    intercept_x: float,
    intercept_y: float,
    intercept_z: float,
    t_intercept: float,
    arm_strength: float = 65.0,
    arm_accuracy: float = 65.0,
    transfer_speed: float = 65.0,
    body_control: float = 65.0,
    fielding_type: str = "GROUND_SCOOP",
    target_base: str = "1B",
    sprint_speed: float = 27.0,
    fielder: Optional[Player] = None,
    intercept: Optional[Any] = None,
) -> ThrowResult:
    """
    Calculates physical throw trajectory from intercept location to target base.

    Seamlessly accepts either individual kinematic parameters or hydrations from
    `Player` and `InterceptResult`. Handles 1B unassisted bag steps when within 12 ft.
    """
    # 1. Ingest Player object if provided
    if fielder is not None:
        arm_strength = fielder.get_defensive_rating("arm_strength")
        arm_accuracy = fielder.get_defensive_rating("arm_accuracy")
        transfer_speed = fielder.get_defensive_rating("transfer_speed")
        body_control = fielder.get_defensive_rating("body_control")
        sprint_speed = fielder.get_sprint_speed_fps()

    # 2. Ingest InterceptResult if provided
    if intercept is not None:
        fielder_id = getattr(intercept, "fielder_id", fielder_id) or fielder_id
        intercept_x = getattr(intercept, "intercept_x", intercept_x)
        intercept_y = getattr(intercept, "intercept_y", intercept_y)
        intercept_z = getattr(intercept, "intercept_z", intercept_z)
        t_intercept = getattr(intercept, "t_intercept", t_intercept)
        fielding_type = getattr(intercept, "fielding_type", fielding_type)

    target_pos = BASE_COORDINATES.get(target_base.upper(), BASE_COORDINATES["1B"])
    target_x, target_y, target_z = target_pos

    dist_to_target = math.hypot(target_x - intercept_x, target_y - intercept_y)
    start_pos = (round(intercept_x, 2), round(intercept_y, 2), round(intercept_z, 2))

    # 3. Special Case: 1B Unassisted Step
    if fielder_id.upper() == "1B" and target_base.upper() == "1B" and dist_to_target <= 12.0:
        step_speed = max(18.0, sprint_speed)
        t_step = max(0.12, dist_to_target / step_speed)
        t_arrival = round(t_intercept + t_step, 3)

        # 10 linear ground samples of 1B stepping on the bag
        samples: List[List[float]] = []
        for i in range(10):
            u = i / 9.0
            sx = round(intercept_x + u * (target_x - intercept_x), 2)
            sy = round(intercept_y + u * (target_y - intercept_y), 2)
            st = round(t_intercept + u * t_step, 3)
            samples.append([sx, sy, 0.0, st])

        return ThrowResult(
            thrower_id=fielder_id,
            target_base=target_base,
            start_pos=start_pos,
            target_pos=target_pos,
            transfer_time_s=0.0,
            throw_flight_time_s=round(t_step, 3),
            throw_start_time_s=round(t_intercept, 3),
            ball_arrival_time_s=t_arrival,
            throw_distance_ft=round(dist_to_target, 1),
            throw_velocity_mph=0.0,
            offline_distance_ft=0.0,
            is_unassisted=True,
            samples=samples,
        )

    # 4. Standard Fielder Throw Kinematics
    t_transfer = calculate_transfer_time(transfer_speed, fielding_type, body_control)
    t_throw_start = round(t_intercept + t_transfer, 3)

    # Throw velocity: 70 mph at 0 rating to 102 mph at 100 rating
    v_throw_mph = 70.0 + (max(0.0, min(100.0, arm_strength)) / 100.0) * 32.0
    v_throw_fps = v_throw_mph * 1.46667

    # Aerodynamic flight time: mild drag reduction factor ~0.95
    t_flight = max(0.15, dist_to_target / (v_throw_fps * 0.95))
    t_arrival = round(t_throw_start + t_flight, 3)

    # Angular dispersion error: arm accuracy & body control
    acc = max(0.0, min(100.0, arm_accuracy))
    bc = max(0.0, min(100.0, body_control))
    sigma_deg = (100.0 - acc) * 0.03 * (1.3 - (bc / 250.0))
    offline_dist = round(dist_to_target * math.tan(math.radians(sigma_deg)), 2)

    # Generate 10 bounded 4D samples with parabolic arc height
    samples = []
    z_release = 5.0  # standard chest/shoulder release height in feet
    apex_boost = max(1.0, dist_to_target / 70.0)

    for i in range(10):
        u = i / 9.0
        sx = round(intercept_x + u * (target_x - intercept_x), 2)
        sy = round(intercept_y + u * (target_y - intercept_y), 2)
        # Parabolic arc in z
        base_z = (1.0 - u) * z_release + u * target_z
        arc_z = 4.0 * apex_boost * u * (1.0 - u)
        sz = round(max(0.0, base_z + arc_z), 2)
        st = round(t_throw_start + u * t_flight, 3)
        samples.append([sx, sy, sz, st])

    # Ensure last sample matches arrival coordinate
    samples[-1] = [round(target_x, 2), round(target_y, 2), round(target_z, 2), t_arrival]

    return ThrowResult(
        thrower_id=fielder_id,
        target_base=target_base,
        start_pos=start_pos,
        target_pos=target_pos,
        transfer_time_s=t_transfer,
        throw_flight_time_s=round(t_flight, 3),
        throw_start_time_s=t_throw_start,
        ball_arrival_time_s=t_arrival,
        throw_distance_ft=round(dist_to_target, 1),
        throw_velocity_mph=round(v_throw_mph, 1),
        offline_distance_ft=offline_dist,
        is_unassisted=False,
        samples=samples,
    )

