"""Pure pitch-shape model shared by contact and telemetry.

The model converts a realized delivery's movement, velocity, release point, and
plate location into a vertical approach angle and a vertical bat-ball offset.
It is intentionally deterministic and free of game-state dependencies so the
same inputs always produce the same shape.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Optional

GRAVITY_FPS2 = 32.174
CLIENT_FLIGHT_DISTANCE_FT = 59.5
PLATE_FRONT_FT = 1.417
DEFAULT_RELEASE_Z_FT = 5.9
DEFAULT_RELEASE_DISTANCE_FT = 54.5

LEAGUE_AVG_IVB_IN = 10.0
LEAGUE_AVG_VAA_DEG = -4.5
# The raw projectile derivative is calibrated to the league 4-seam/sinker VAA
# bands: flatter than -4.5 for ride, steeper for drop.
VAA_SCALE = 1.30
VAA_OFFSET_DEG = 0.95

SHAPE_IVB_COEFF = 0.8
SHAPE_VAA_COEFF = 1.5
SHAPE_OFFSET_CLAMP_IN = 14.0
VERTICAL_OFFSET_CLAMP_IN = 18.0

RIDE_WHIFF_BASE = 0.065
DROP_WHIFF_BASE = 0.080
RIDE_WHIFF_HIGH = 0.030
DROP_WHIFF_LOW = 0.020
BREAK_WHIFF = 0.020
SPLIT_WHIFF = 0.025

EV_PER_INCH = 0.14

GROUND_LOGIT_BASE = -0.20
GROUND_LOGIT_PER_10IN = 0.60
GROUND_LAUNCH_MEAN = 1.0
GROUND_LAUNCH_SIGMA = 5.0
AIR_LAUNCH_MEAN = 27.0
AIR_LAUNCH_SIGMA = 13.0
AIR_DROP_MEAN_SHIFT = 5.0
AIR_DROP_SIGMA_SHIFT = 3.0
GROUND_EV_PENALTY = -2.0


@dataclass(frozen=True)
class PitchShape:
    pitch_name: str
    category: str
    velocity_mph: float
    hb_in: float
    ivb_in: float
    realized_z_ft: float
    release_z_ft: float
    distance_ft: float
    flight_time_s: float
    vaa_deg: float
    shape_offset_in: float
    vertical_offset_in: float
    ride_factor: float
    drop_factor: float
    run_factor: float
    high_factor: float
    low_factor: float
    is_four_seam: bool
    is_sinker_like: bool
    is_changeup_like: bool
    is_splitter_like: bool
    is_ride_pitch: bool
    is_drop_pitch: bool


def _finite(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def estimate_vaa_deg(
    *,
    release_z_ft: float,
    plate_z_ft: float,
    distance_ft: float,
    velocity_mph: float,
    ivb_in: float,
    flight_time_s: Optional[float] = None,
) -> float:
    """Estimates the vertical approach angle at the plate in degrees."""
    velocity_fps = max(1.0, velocity_mph * 1.4667)
    if flight_time_s is None:
        flight_time_s = max(0.05, CLIENT_FLIGHT_DISTANCE_FT / velocity_fps)
    t = max(0.05, flight_time_s)
    ivb_ft = ivb_in / 12.0
    initial_vy = (
        plate_z_ft - ivb_ft - release_z_ft + 0.5 * GRAVITY_FPS2 * t * t
    ) / t
    final_vy = initial_vy - GRAVITY_FPS2 * t + (2.0 * ivb_ft) / t
    horizontal_velocity = max(1.0, distance_ft / t)
    raw_vaa = math.degrees(math.atan2(final_vy, horizontal_velocity))
    return (
        LEAGUE_AVG_VAA_DEG
        + (raw_vaa - LEAGUE_AVG_VAA_DEG) * VAA_SCALE
        + VAA_OFFSET_DEG
    )


def build_pitch_shape(delivery: Dict[str, Any]) -> PitchShape:
    """Builds a deterministic pitch-shape profile from a delivery dict."""
    pitch_name = str(delivery.get('selected_pitch') or '4-Seam Fastball')
    category = str(delivery.get('pitch_category') or 'Fastball')
    velocity = max(1.0, _finite(delivery.get('velocity_mph'), 93.0))
    hb_in = _finite(delivery.get('horizontal_break_in'), 0.0)
    ivb_in = _finite(delivery.get('induced_vertical_break_in'), 0.0)
    realized_z = _finite(delivery.get('realized_z'), 2.5)

    release = delivery.get('release_point_ft') or {}
    if isinstance(release, dict):
        release_z = _finite(release.get('z'), DEFAULT_RELEASE_Z_FT)
        release_y = _finite(release.get('y'), DEFAULT_RELEASE_DISTANCE_FT)
        distance = max(1.0, release_y - PLATE_FRONT_FT)
    else:
        release_z = DEFAULT_RELEASE_Z_FT
        distance = DEFAULT_RELEASE_DISTANCE_FT

    flight_time = max(0.05, CLIENT_FLIGHT_DISTANCE_FT / (velocity * 1.4667))
    vaa_deg = estimate_vaa_deg(
        release_z_ft=release_z,
        plate_z_ft=realized_z,
        distance_ft=distance,
        velocity_mph=velocity,
        ivb_in=ivb_in,
        flight_time_s=flight_time,
    )

    lower_name = pitch_name.lower()
    lower_category = category.lower()
    is_four_seam = any(
        token in lower_name
        for token in ('four-seam', '4-seam', 'fourseam', '4seam')
    )
    is_changeup = any(
        token in lower_name
        for token in ('changeup', 'change-up', 'change up')
    )
    is_splitter = any(
        token in lower_name
        for token in ('splitter', 'split-finger', 'split finger', 'fork')
    )
    is_sinker = any(
        token in lower_name
        for token in ('sinker', 'two-seam', '2-seam', 'twoseam', '2seam')
    )
    if (
        not is_sinker
        and not is_changeup
        and not is_splitter
        and lower_category in ('fastball', 'sinker', 'two-seam')
        and ivb_in <= 8.0
        and hb_in <= -12.0
    ):
        is_sinker = True

    is_ride_pitch = is_four_seam or (
        lower_category == 'fastball' and ivb_in >= 13.0
    )
    is_drop_pitch = is_sinker or is_changeup

    ride_factor = _clamp((ivb_in - LEAGUE_AVG_IVB_IN) / 8.0, 0.0, 1.0)
    drop_factor = _clamp((LEAGUE_AVG_IVB_IN - ivb_in) / 8.0, 0.0, 1.0)
    run_factor = _clamp((abs(hb_in) - 8.0) / 8.0, 0.0, 1.0)
    high_factor = _clamp((realized_z - 2.6) / 0.8, 0.0, 1.0)
    low_factor = _clamp((2.6 - realized_z) / 0.8, 0.0, 1.0)

    shape_offset = _clamp(
        (ivb_in - LEAGUE_AVG_IVB_IN) * SHAPE_IVB_COEFF
        + (vaa_deg - LEAGUE_AVG_VAA_DEG) * SHAPE_VAA_COEFF,
        -SHAPE_OFFSET_CLAMP_IN,
        SHAPE_OFFSET_CLAMP_IN,
    )
    location_offset = (realized_z - 2.5) * 12.0
    vertical_offset = _clamp(
        location_offset + shape_offset,
        -VERTICAL_OFFSET_CLAMP_IN,
        VERTICAL_OFFSET_CLAMP_IN,
    )

    return PitchShape(
        pitch_name=pitch_name,
        category=category,
        velocity_mph=velocity,
        hb_in=hb_in,
        ivb_in=ivb_in,
        realized_z_ft=realized_z,
        release_z_ft=release_z,
        distance_ft=distance,
        flight_time_s=flight_time,
        vaa_deg=vaa_deg,
        shape_offset_in=shape_offset,
        vertical_offset_in=vertical_offset,
        ride_factor=ride_factor,
        drop_factor=drop_factor,
        run_factor=run_factor,
        high_factor=high_factor,
        low_factor=low_factor,
        is_four_seam=is_four_seam,
        is_sinker_like=is_sinker,
        is_changeup_like=is_changeup,
        is_splitter_like=is_splitter,
        is_ride_pitch=is_ride_pitch,
        is_drop_pitch=is_drop_pitch,
    )


def whiff_shape_adjustment(shape: PitchShape) -> float:
    """Shape-driven whiff adjustment for a fastball/offspeed profile."""
    adjustment = 0.0
    if shape.is_ride_pitch:
        adjustment += RIDE_WHIFF_BASE * shape.ride_factor
        adjustment += RIDE_WHIFF_HIGH * shape.ride_factor * shape.high_factor
    if shape.is_drop_pitch:
        adjustment -= DROP_WHIFF_BASE * shape.drop_factor
        adjustment -= DROP_WHIFF_LOW * shape.drop_factor * shape.low_factor
    if shape.is_splitter_like:
        adjustment += SPLIT_WHIFF
    if shape.category.lower() == 'breaking':
        adjustment += BREAK_WHIFF * shape.run_factor
    return adjustment


def ground_ball_probability(shape: PitchShape) -> float:
    """Shape-driven probability that contact becomes a ground ball."""
    logit = GROUND_LOGIT_BASE + GROUND_LOGIT_PER_10IN * (
        -shape.vertical_offset_in / 10.0
    )
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    exp_value = math.exp(logit)
    return exp_value / (1.0 + exp_value)


def ground_launch_parameters() -> tuple:
    return GROUND_LAUNCH_MEAN, GROUND_LAUNCH_SIGMA


def air_launch_parameters(shape: PitchShape) -> tuple:
    mean = AIR_LAUNCH_MEAN - AIR_DROP_MEAN_SHIFT * shape.drop_factor
    sigma = max(8.0, AIR_LAUNCH_SIGMA - AIR_DROP_SIGMA_SHIFT * shape.drop_factor)
    return mean, sigma


def exit_velocity_adjustment(shape: PitchShape) -> float:
    return shape.vertical_offset_in * EV_PER_INCH


def ground_ball_ev_adjustment(is_ground: bool) -> float:
    return GROUND_EV_PENALTY if is_ground else 0.0


def shape_telemetry(shape: PitchShape) -> Dict[str, float]:
    return {
        'verticalApproachAngleDeg': round(shape.vaa_deg, 2),
        'verticalOffsetInches': round(shape.vertical_offset_in, 2),
        'rideFactor': round(shape.ride_factor, 3),
        'dropFactor': round(shape.drop_factor, 3),
    }
