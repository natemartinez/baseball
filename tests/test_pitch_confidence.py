"""
Tests for Pitcher Confidence & Arsenal Effectiveness Engine.

Verifies:
1. Consecutive strike-zone misses stack progressively starting at >= 2 misses.
2. Strikes / outs reset the consecutive miss streak.
3. Hits allowed, hit-by-pitch, and walks degrade confidence appropriately.
4. Holistic ripple: primary pitch takes 100% of delta, other repertoire pitches take 30%.
5. Correlation with pitch effectiveness: lower confidence reduces effective command,
   expands max error dispersion radius (inches), and increases execution sigma.
"""

import pytest
from backend.engine.pitching_engine.pitch_confidence import (
    calculate_consecutive_miss_penalty,
    calculate_pitch_confidence_delta,
    apply_holistic_confidence_update,
    calculate_effective_command_with_confidence,
    NEUTRAL_CONFIDENCE,
    RIPPLE_FACTOR,
)
from backend.engine.pitching_engine.pitcher_info.adjusted_ratings import (
    PitcherInstanceManager,
    compute_effective_command,
)
from backend.engine.game_engine.gameday_math import (
    get_max_error_radius_inches,
    calculate_execution_sigma,
)


class TestConsecutiveMissStacking:
    """Verifies that failing to locate the strike zone stacks progressively."""

    def test_zero_or_negative_streak(self):
        assert calculate_consecutive_miss_penalty(0) == 0.0
        assert calculate_consecutive_miss_penalty(-1) == 0.0

    def test_single_miss_minor_penalty(self):
        # 1 isolated ball has minor penalty
        assert calculate_consecutive_miss_penalty(1) == -2.5

    def test_consecutive_miss_stacking_escalation(self):
        # Miss 2: stacking begins (-6.0%)
        p2 = calculate_consecutive_miss_penalty(2)
        assert p2 == -6.0

        # Miss 3: escalates harder (-10.5%)
        p3 = calculate_consecutive_miss_penalty(3)
        assert p3 == -10.5
        assert abs(p3 - p2) > abs(p2 - calculate_consecutive_miss_penalty(1))

        # Miss 4: severe penalty (-16.0%)
        p4 = calculate_consecutive_miss_penalty(4)
        assert p4 == -16.0

        # Miss 5: continues stacking by -6.5%
        p5 = calculate_consecutive_miss_penalty(5)
        assert p5 == -22.5

    def test_consecutive_balls_via_pitch_confidence_delta(self):
        delta1, streak1 = calculate_pitch_confidence_delta('BALL', consecutive_misses=0)
        assert streak1 == 1
        assert delta1 == -2.5

        delta2, streak2 = calculate_pitch_confidence_delta('BALL', consecutive_misses=streak1)
        assert streak2 == 2
        assert delta2 == -6.0

        delta3, streak3 = calculate_pitch_confidence_delta('BALL', consecutive_misses=streak2)
        assert streak3 == 3
        assert delta3 == -10.5

    def test_strike_resets_consecutive_miss_streak(self):
        for strike_result in ['SWINGING_STRIKE', 'CALLED_STRIKE', 'FOUL', 'IN_PLAY_OUT']:
            delta, streak = calculate_pitch_confidence_delta(strike_result, consecutive_misses=3)
            assert streak == 0
            assert delta > 0.0


class TestIneffectiveHitAndWalkPenalties:
    """Verifies hit degradation and walk/HBP penalties."""

    def test_hits_allowed_penalties(self):
        hr_delta, streak = calculate_pitch_confidence_delta('HOME_RUN', consecutive_misses=2)
        assert hr_delta == -20.0
        assert streak == 0

        triple_delta, _ = calculate_pitch_confidence_delta('TRIPLE')
        assert triple_delta == -15.0

        double_delta, _ = calculate_pitch_confidence_delta('DOUBLE')
        assert double_delta == -11.0

        single_delta, _ = calculate_pitch_confidence_delta('SINGLE')
        assert single_delta == -7.0

    def test_hit_by_pitch_penalty(self):
        hbp_delta, streak = calculate_pitch_confidence_delta('HIT_BY_PITCH')
        assert hbp_delta == -9.0
        assert streak == 0

    def test_walk_penalty_adds_extra_degradation(self):
        # Ball 4 that results in a walk
        walk_delta, streak = calculate_pitch_confidence_delta('BALL', consecutive_misses=3, is_walk=True)
        assert streak == 4
        # -16.0 (streak 4) - 6.0 (walk) = -22.0
        assert walk_delta == -22.0


class TestHolisticArsenalRipple:
    """Verifies holistic confidence cascading across the entire repertoire."""

    def test_holistic_update_primary_and_ripple(self):
        initial = {
            'Four-Seam Fastball': 50.0,
            'Slider': 50.0,
            'Changeup': 50.0,
            'Curveball': 50.0,
        }
        repertoire = list(initial.keys())

        # Thrown pitch is Slider, gets hit for a Home Run (-20.0%)
        updated = apply_holistic_confidence_update(
            current_confidences=initial,
            all_pitch_names=repertoire,
            thrown_pitch_name='Slider',
            primary_delta=-20.0,
            ripple_factor=RIPPLE_FACTOR,
        )

        # Primary pitch received full 100% of penalty
        assert updated['Slider'] == 30.0  # 50 - 20

        # Ripple pitches received 30% of penalty (-6.0%)
        assert updated['Four-Seam Fastball'] == 44.0  # 50 - 6
        assert updated['Changeup'] == 44.0
        assert updated['Curveball'] == 44.0

        # Overall average is computed
        expected_avg = round((30.0 + 44.0 + 44.0 + 44.0) / 4.0, 2)
        assert updated['overall'] == expected_avg

    def test_clamping_at_boundaries(self):
        initial = {
            'Four-Seam Fastball': 10.0,
            'Slider': 95.0,
        }
        repertoire = list(initial.keys())

        # Push below 0
        updated_low = apply_holistic_confidence_update(
            current_confidences=initial,
            all_pitch_names=repertoire,
            thrown_pitch_name='Four-Seam Fastball',
            primary_delta=-20.0,
        )
        assert updated_low['Four-Seam Fastball'] == 0.0

        # Push above 100
        updated_high = apply_holistic_confidence_update(
            current_confidences=initial,
            all_pitch_names=repertoire,
            thrown_pitch_name='Slider',
            primary_delta=+10.0,
        )
        assert updated_high['Slider'] == 100.0


class TestConfidenceToEffectivenessCorrelation:
    """Verifies that pitch confidence correlates directly with effective command and dispersion."""

    def test_command_modification_curve(self):
        base_cmd = 80.0

        # Neutral confidence (50%) -> no adjustment
        neutral_cmd = calculate_effective_command_with_confidence(base_cmd, confidence=50.0)
        assert neutral_cmd == 80.0

        # Low confidence (25%) -> command degrades
        low_cmd = calculate_effective_command_with_confidence(base_cmd, confidence=25.0)
        assert low_cmd < neutral_cmd
        # Halfway from neutral to 0 gives 50% of 22 penalty = -11
        assert low_cmd == 69.0

        # Zero confidence (0%) -> maximum penalty (-22)
        zero_cmd = calculate_effective_command_with_confidence(base_cmd, confidence=0.0)
        assert zero_cmd == 58.0

        # High confidence (100%) -> maximum boost (+10)
        high_cmd = calculate_effective_command_with_confidence(base_cmd, confidence=100.0)
        assert high_cmd == 90.0

    def test_dispersion_circle_expansion_on_ineffective_pitch(self):
        """A pitcher with low confidence has wider error radius and higher sigma."""
        base_cmd = 85.0
        pitch_type = 'Slider'

        cmd_neutral, _ = compute_effective_command(
            base_command=base_cmd,
            pitch_type=pitch_type,
            pitch_count=10,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
            confidence=50.0,
        )
        radius_neutral = get_max_error_radius_inches(cmd_neutral)
        sigma_neutral = calculate_execution_sigma(cmd_neutral)

        # Ineffective pitch at 10% confidence
        cmd_ineffective, _ = compute_effective_command(
            base_command=base_cmd,
            pitch_type=pitch_type,
            pitch_count=10,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
            confidence=10.0,
        )
        radius_ineffective = get_max_error_radius_inches(cmd_ineffective)
        sigma_ineffective = calculate_execution_sigma(cmd_ineffective)

        # Verified: command drops, radius expands, sigma increases
        assert cmd_ineffective < cmd_neutral
        assert radius_ineffective > radius_neutral
        assert sigma_ineffective > sigma_neutral

    def test_evaluate_pitch_arsenal_confidence_integration(self):
        """evaluate_pitch_arsenal reflects individual pitch confidence in metrics."""
        class MockPitcher:
            id = 1
            pitch_count = 15
            stamina = 85.0
            control = 80.0
            consistency = 80.0
            composure = 80.0

        arsenal = [
            {'name': 'Four-Seam Fastball', 'pitch_id': 'FF', 'command': 82.0, 'velocity_mph': 95.0},
            {'name': 'Sweeper', 'pitch_id': 'ST', 'command': 78.0, 'velocity_mph': 82.0},
        ]

        # Neutral confidence metrics
        metrics_neutral = PitcherInstanceManager.evaluate_pitch_arsenal(
            pitcher=MockPitcher(),
            arsenal_items=arsenal,
            pitch_confidences={'FF': 50.0, 'ST': 50.0},
        )

        # Sweeper became uneffective (confidence dropped to 15.0)
        metrics_uneffective = PitcherInstanceManager.evaluate_pitch_arsenal(
            pitcher=MockPitcher(),
            arsenal_items=arsenal,
            pitch_confidences={'FF': 45.0, 'ST': 15.0},
        )

        # Fastball only dropped slightly (ripple), Sweeper dropped heavily
        ff_cmd_diff = metrics_neutral['FF'].effective_command - metrics_uneffective['FF'].effective_command
        st_cmd_diff = metrics_neutral['ST'].effective_command - metrics_uneffective['ST'].effective_command

        assert st_cmd_diff > ff_cmd_diff
        assert metrics_uneffective['ST'].max_radius_inches > metrics_neutral['ST'].max_radius_inches
        assert metrics_uneffective['ST'].sigma > metrics_neutral['ST'].sigma
        assert metrics_uneffective['ST'].baseline_effectiveness < metrics_neutral['ST'].baseline_effectiveness
