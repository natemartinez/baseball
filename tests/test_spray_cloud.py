"""
Spray-cloud accuracy tests: command-to-radius mapping and truncation bounds.
"""

import math
import random
from unittest.mock import patch

import pytest

from backend.engine.gameday_math import (
    FATIGUE_ENABLED,
    ZONE_X_MAX,
    ZONE_X_MIN,
    ZONE_Z_BOT,
    ZONE_Z_TOP,
    calculate_execution_sigma,
    get_max_error_radius_inches,
    is_rulebook_strike,
    sample_truncated_gaussian,
)
from backend.engine.pitching_engine import calculations


def test_command_radius_tiers():
    assert get_max_error_radius_inches(99) == 1.0
    assert get_max_error_radius_inches(90) == 1.25
    assert get_max_error_radius_inches(82) == 1.5
    assert get_max_error_radius_inches(68) == 3.0
    assert get_max_error_radius_inches(55) == 4.5
    assert get_max_error_radius_inches(40) == 7.0
    # Interpolation and clamping
    assert round(get_max_error_radius_inches(85), 3) == 1.406
    assert get_max_error_radius_inches(20) == 7.0
    assert get_max_error_radius_inches(120) == 1.0


def test_sigma_matches_radius():
    for command in (40, 55, 68, 82, 90, 99):
        expected = get_max_error_radius_inches(command) / 2.5 / 12.0
        assert abs(calculate_execution_sigma(command) - expected) < 1e-9


def test_truncated_sampler_never_leaves_radius():
    random.seed(7)
    target_x, target_z = 0.2, 2.4
    for command in (40, 68, 82, 99):
        radius_ft = get_max_error_radius_inches(command) / 12.0
        sigma = calculate_execution_sigma(command)
        for _ in range(2000):
            x, z = sample_truncated_gaussian(target_x, target_z, sigma, radius_ft)
            assert math.hypot(x - target_x, z - target_z) <= radius_ft + 1e-3


def test_fatigue_disabled_for_spray_cloud_test():
    # The base cloud must not grow with pitch count while the flag is off.
    assert FATIGUE_ENABLED is False
    assert calculate_execution_sigma(82, 0) == calculate_execution_sigma(82, 120)


def test_sampler_preserves_precision_below_one_thousandth():
    values = iter([0.25, 0.0])
    x, z = sample_truncated_gaussian(
        0.0, 2.5, 0.1, 0.5, rng=lambda: next(values)
    )

    exp_term = math.exp(-(0.5 * 0.5) / (2.0 * 0.1 * 0.1))
    one_minus = 1.0 - 0.25 * (1.0 - exp_term)
    expected_r = 0.1 * math.sqrt(-2.0 * math.log(one_minus))

    assert x == pytest.approx(expected_r, abs=1e-12)
    assert z == pytest.approx(2.5, abs=1e-12)
    # A 3-decimal quantized sampler would return 0.076 here.
    assert x != round(x, 3)


@pytest.mark.parametrize(
    "x,z",
    [
        (ZONE_X_MAX, 2.5),
        (ZONE_X_MIN, 2.5),
        (0.0, ZONE_Z_TOP),
        (0.0, ZONE_Z_BOT),
    ],
)
def test_exact_rulebook_edges_are_strikes(x, z):
    assert is_rulebook_strike(x, z)
    with patch.object(
        calculations, "sample_truncated_gaussian", return_value=(x, z)
    ):
        delivery = calculations.calculate_pitch_delivery(0.0, 2.5, 82, 0)
    assert delivery["is_strike"] is True


@pytest.mark.parametrize(
    "x,z",
    [
        (ZONE_X_MAX + 1e-7, 2.5),
        (ZONE_X_MIN - 1e-7, 2.5),
        (0.0, ZONE_Z_TOP + 1e-7),
        (0.0, ZONE_Z_BOT - 1e-7),
    ],
)
def test_points_just_outside_the_edge_are_balls(x, z):
    assert not is_rulebook_strike(x, z)
    with patch.object(
        calculations, "sample_truncated_gaussian", return_value=(x, z)
    ):
        delivery = calculations.calculate_pitch_delivery(0.0, 2.5, 82, 0)
    assert delivery["is_strike"] is False
