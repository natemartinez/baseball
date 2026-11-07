"""League-average and pitcher-quality separation for 4-seam vs sinker."""

import random

from backend.engine.batting_engine.batters import InGameBatterRatings
from backend.engine.batting_engine.contact import ContactResolver
from backend.engine.pitch_shape import build_pitch_shape


def _ratings() -> InGameBatterRatings:
    return InGameBatterRatings(
        batter_id=1,
        batter_name='League Average',
        handedness='R',
        batter_side='R',
        power=60.0,
        contact=60.0,
        vision=60.0,
        speed=50.0,
        effective_contact=60.0,
        effective_discipline=60.0,
        hot_zones={},
    )


def _delivery(
    *,
    pitch_name: str,
    hb_in: float,
    ivb_in: float,
    realized_z: float = 2.5,
    velocity_mph: float = 94.0,
    effectiveness: float = 80.0,
    category: str = 'Fastball',
) -> dict:
    return {
        'selected_pitch': pitch_name,
        'pitch_category': category,
        'velocity_mph': velocity_mph,
        'spin_rpm': 2400,
        'horizontal_break_in': hb_in,
        'induced_vertical_break_in': ivb_in,
        'realized_x': 0.0,
        'realized_z': realized_z,
        'realized_zone_cat': 'SHADOW',
        'is_strike': True,
        'pitch_effectiveness': effectiveness,
        'release_point_ft': {'x': -1.85, 'y': 54.5, 'z': 5.9},
    }


def _whiff(delivery: dict) -> float:
    resolver = ContactResolver(_ratings(), rng=random.Random(1))
    shape = build_pitch_shape(delivery)
    return resolver._whiff_probability(
        zone_category='SHADOW',
        is_strike=True,
        pitch_category=str(delivery['pitch_category']),
        velocity=float(delivery['velocity_mph']),
        pitch_effectiveness=float(delivery['pitch_effectiveness']),
        balls=0,
        strikes=0,
        approach_mode='AUTO',
        shape=shape,
    )


def _samples(delivery: dict, n: int = 4000, seed: int = 20261103):
    resolver = ContactResolver(_ratings(), rng=random.Random(seed))
    shape = build_pitch_shape(delivery)
    launch = []
    ev = []
    for _ in range(n):
        result = resolver._resolve_batted_ball(
            actual_zone_name='heart',
            pitch_name=str(delivery['selected_pitch']),
            pitch_category=str(delivery['pitch_category']),
            velocity=float(delivery['velocity_mph']),
            realized_x=float(delivery['realized_x']),
            realized_z=float(delivery['realized_z']),
            pitch_effectiveness=float(delivery['pitch_effectiveness']),
            shape=shape,
        )
        launch.append(result['launch_angle_deg'])
        ev.append(result['exit_velocity_mph'])
    return launch, ev


def _rates(delivery: dict, n: int = 4000, seed: int = 20261103):
    launch, ev = _samples(delivery, n=n, seed=seed)
    ground = sum(1 for value in launch if value < 8.0) / len(launch)
    popup = sum(1 for value in launch if value > 38.0) / len(launch)
    return {
        'ground': ground,
        'popup': popup,
        'mean_launch': sum(launch) / len(launch),
        'mean_ev': sum(ev) / len(ev),
    }


def test_same_location_shape_separation():
    four = _delivery(pitch_name='Four-Seam Fastball', hb_in=-7.0, ivb_in=16.0)
    sink = _delivery(pitch_name='Sinker', hb_in=-14.0, ivb_in=6.0)

    four_shape = build_pitch_shape(four)
    sink_shape = build_pitch_shape(sink)

    assert sink_shape.vaa_deg <= four_shape.vaa_deg - 1.0
    assert sink_shape.vertical_offset_in <= four_shape.vertical_offset_in - 5.0
    assert _whiff(four) >= _whiff(sink) + 0.02

    four_rates = _rates(four)
    sink_rates = _rates(sink)
    assert four_rates['mean_launch'] >= sink_rates['mean_launch'] + 5.0
    assert four_rates['mean_ev'] >= sink_rates['mean_ev'] + 1.5
    assert sink_rates['ground'] >= four_rates['ground'] + 0.10
    assert sink_rates['popup'] < four_rates['popup']


def _mix_delivery(pitch_name: str, hb_in: float, ivb_in: float, z_values: list) -> list:
    return [
        _delivery(
            pitch_name=pitch_name,
            hb_in=hb_in,
            ivb_in=ivb_in,
            realized_z=z,
        )
        for z in z_values
    ]


def _mix_rates(deliveries: list, n: int = 4000, seed: int = 20261103):
    resolver = ContactResolver(_ratings(), rng=random.Random(seed))
    launch = []
    ev = []
    whiffs = []
    for index in range(n):
        delivery = deliveries[index % len(deliveries)]
        shape = build_pitch_shape(delivery)
        whiffs.append(
            resolver._whiff_probability(
                zone_category='SHADOW',
                is_strike=True,
                pitch_category=str(delivery['pitch_category']),
                velocity=float(delivery['velocity_mph']),
                pitch_effectiveness=float(delivery['pitch_effectiveness']),
                balls=0,
                strikes=0,
                approach_mode='AUTO',
                shape=shape,
            )
        )
        result = resolver._resolve_batted_ball(
            actual_zone_name='heart',
            pitch_name=str(delivery['selected_pitch']),
            pitch_category=str(delivery['pitch_category']),
            velocity=float(delivery['velocity_mph']),
            realized_x=float(delivery['realized_x']),
            realized_z=float(delivery['realized_z']),
            pitch_effectiveness=float(delivery['pitch_effectiveness']),
            shape=shape,
        )
        launch.append(result['launch_angle_deg'])
        ev.append(result['exit_velocity_mph'])
    return {
        'whiff': sum(whiffs) / len(whiffs),
        'ground': sum(1 for value in launch if value < 8.0) / len(launch),
        'popup': sum(1 for value in launch if value > 38.0) / len(launch),
        'mean_launch': sum(launch) / len(launch),
        'mean_ev': sum(ev) / len(ev),
    }


def test_typical_location_mix_hits_baselines():
    four_mix = _mix_delivery(
        'Four-Seam Fastball',
        -7.0,
        16.0,
        [3.15] * 50 + [2.6] * 30 + [2.1] * 20,
    )
    sink_mix = _mix_delivery(
        'Sinker',
        -14.0,
        6.0,
        [1.85] * 60 + [2.4] * 30 + [2.9] * 10,
    )

    four = _mix_rates(four_mix)
    sink = _mix_rates(sink_mix)

    assert 0.22 <= four['whiff'] <= 0.28, four
    assert 0.12 <= sink['whiff'] <= 0.16, sink
    assert 0.32 <= four['ground'] <= 0.36, four
    assert 0.52 <= sink['ground'] <= 0.62, sink
    assert four['whiff'] >= sink['whiff'] + 0.04
    assert sink['ground'] >= four['ground'] + 0.20
    assert four['popup'] > sink['popup']


def test_elite_and_poor_pitchers_cross_the_baseline_bands():
    elite_four = _delivery(
        pitch_name='Four-Seam Fastball',
        hb_in=-5.0,
        ivb_in=19.0,
        realized_z=3.15,
        velocity_mph=98.0,
        effectiveness=92.0,
    )
    poor_four = _delivery(
        pitch_name='Four-Seam Fastball',
        hb_in=-8.0,
        ivb_in=13.0,
        realized_z=3.15,
        velocity_mph=90.0,
        effectiveness=65.0,
    )
    elite_sink = _delivery(
        pitch_name='Sinker',
        hb_in=-17.0,
        ivb_in=3.0,
        realized_z=1.85,
        velocity_mph=96.0,
        effectiveness=92.0,
    )
    poor_sink = _delivery(
        pitch_name='Sinker',
        hb_in=-12.0,
        ivb_in=9.0,
        realized_z=2.4,
        velocity_mph=88.0,
        effectiveness=65.0,
    )

    elite_four_whiff = _whiff(elite_four)
    poor_four_whiff = _whiff(poor_four)
    elite_sink_rates = _rates(elite_sink)
    poor_sink_rates = _rates(poor_sink)

    assert elite_four_whiff > 0.28
    assert poor_four_whiff < 0.22
    assert elite_sink_rates['ground'] > 0.62
    assert poor_sink_rates['ground'] < 0.52


def test_shape_is_deterministic():
    delivery = _delivery(pitch_name='Sinker', hb_in=-14.0, ivb_in=6.0)
    first = build_pitch_shape(delivery)
    second = build_pitch_shape(dict(delivery))
    assert first == second
