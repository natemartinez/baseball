"""
Batter-Runner Sprint Kinematics and Base Play Clock Resolver.

Calculates home-to-first sprint times based on speed rating, batter handedness,
and swing follow-through. Compares arrival timestamps between ball and runner
to resolve outs vs. safe calls with close-play detection.
"""

from dataclasses import dataclass
from typing import Optional

from backend.engine.models.player import Player
from backend.engine.game_engine.physics.fielder_throw import ThrowResult


@dataclass(frozen=True)
class BasePlayResult:
    """Encapsulates the out/safe adjudication at a base bag."""
    is_out: bool
    is_close_play: bool
    margin_s: float  # ball_arrival_time_s - runner_arrival_time_s
    ball_arrival_time_s: float
    runner_arrival_time_s: float
    call: str  # 'OUT' or 'SAFE'
    description: str


def calculate_home_to_first_time(
    speed_rating: float = 65.0,
    is_left_handed: bool = False,
    exit_velocity_mph: float = 95.0,
    batter: Optional[Player] = None,
) -> float:
    """
    Computes home-to-first sprint duration in seconds.

    Elite speed (100) right-handed: ~4.00s.
    Elite speed (100) left-handed: ~3.92s (closer to 1B bag).
    Average speed (65): ~4.30s.
    Slow speed (20): ~4.68s.
    """
    if batter is not None:
        raw_spd = getattr(batter, "speed", None)
        if raw_spd is None and hasattr(batter, "ratings") and isinstance(batter.ratings, dict):
            raw_spd = batter.ratings.get("speed")
        if raw_spd is not None:
            speed_rating = float(raw_spd)

        bats_val = str(getattr(batter, "bats", "") or "").upper()
        if bats_val == "L":
            is_left_handed = True

    spd = max(0.0, min(100.0, float(speed_rating)))

    # Base sprint formula: 0 rating -> 4.85s, 100 rating -> 4.00s
    t_sprint = 4.85 - (spd / 100.0) * 0.85

    # Left-handed batter box advantage (-0.08s closer to first baseline)
    if is_left_handed:
        t_sprint -= 0.08

    # Swing follow-through vs. weak contact head start
    if exit_velocity_mph >= 100.0:
        t_sprint += 0.04  # violent swing recoiling before sprint start
    elif exit_velocity_mph <= 75.0:
        t_sprint -= 0.04  # soft dribbler / bunt momentum

    return round(t_sprint, 3)


def resolve_play_at_base(
    throw: ThrowResult,
    runner_arrival_time_s: float,
) -> BasePlayResult:
    """
    Authoritative clock comparison: t_ball_at_base vs. t_runner_at_base.

    margin_s = t_ball - t_runner
    margin <= 0 -> ball arrives first (OUT)
    margin > 0  -> runner arrives first (SAFE)
    """
    t_ball = throw.ball_arrival_time_s
    t_runner = round(runner_arrival_time_s, 3)
    margin = round(t_ball - t_runner, 3)

    is_out = margin <= 0.0
    is_close = abs(margin) <= 0.15

    base_name = throw.target_base.upper()
    target_label = "first" if base_name == "1B" else base_name

    if is_out:
        call = "OUT"
        if is_close:
            desc = f"Out at {target_label}! Close play (by {abs(margin):.2f}s)."
        else:
            desc = f"Out at {target_label} by {abs(margin):.2f}s."
    else:
        call = "SAFE"
        if is_close:
            desc = f"Safe at {target_label}! Batter beats the throw by {margin:.2f}s."
        else:
            desc = f"Safe at {target_label}! Batter beats the throw by {margin:.2f}s."

    return BasePlayResult(
        is_out=is_out,
        is_close_play=is_close,
        margin_s=margin,
        ball_arrival_time_s=t_ball,
        runner_arrival_time_s=t_runner,
        call=call,
        description=desc,
    )

