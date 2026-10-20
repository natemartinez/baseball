"""
Spray-cloud accuracy tests: command-to-radius mapping and truncation bounds.
"""

import math
import random

from backend.engine.gameday_math import (
    calculate_execution_sigma,
    get_max_error_radius_inches,
    sample_truncated_gaussian,
    FATIGUE_ENABLED,
)


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
