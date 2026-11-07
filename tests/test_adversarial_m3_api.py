"""
Adversarial Empirical Test Suite for Milestone 3: API Contract & Telemetry (`POST /api/pitch/throw`).

Stress-tests:
1. API Payload Boundary Testing:
   - Extreme / non-finite coordinates: NaN, Inf, -Inf, 99999.0, -99999.0, string numbers, None, missing pairs.
   - TimingTier invalid variations: EXCELLENT, FLAWLESS, integers, lists, dicts.
   - TimingTier case & whitespace normalization: "  perfect  ", "GoOd", "okay", "pOOr".
   - Unknown pitch rejection: "Ultra Curve", "", integers, lists.
   - Pitch family aliasing: "Slider", "Curveball", "Sweeper" for breaking arsenals.
   - Selection mode & intent boundaries.
   - Concurrency conflict (HTTP 409 when pitch in flight).
2. Response Telemetry Invariants (N >= 100 requests):
   - "execution" top-level envelope.
   - All 8 required telemetry keys present.
   - Invariants: base_radius > 0, executed_radius > 0, radial_miss >= 0, radial_miss <= executed_radius + 1e-4.
   - Strict multiplier consistency: executed_radius == round(base_radius * TIMING_MULTIPLIERS[timing_tier], 3).
   - Realized landing coordinate distance invariant.
"""

import math
import pytest
from tiers import TIMING_MULTIPLIERS, TimingTier, AbilityTier
from backend.api.app import create_app


@pytest.fixture(scope="module")
def app():
    """Module-scoped Flask application instance configured for testing."""
    application = create_app()
    application.config.update({"TESTING": True})
    return application


@pytest.fixture
def client(app):
    """Test client initialized with a fresh match between Team 1 (Mets) and Team 2 (Yankees)."""
    test_client = app.test_client()
    test_client.post("/api/start_game", json={"home_team_id": 1, "away_team_id": 2})
    return test_client


def _reset_game(client):
    """Helper to reset game state to ensure a clean start for at-bats."""
    client.post("/api/start_game", json={"home_team_id": 1, "away_team_id": 2})


# ═════════════════════════════════════════════════════════════════════════════
# 1. API Payload Boundary Testing (POST /api/pitch/throw)
# ═════════════════════════════════════════════════════════════════════════════

class TestApiPayloadBoundary:
    """Adversarial challenge of payload validation and edge cases."""

    @pytest.mark.parametrize("bad_x", [
        float("nan"),
        float("inf"),
        -float("inf"),
        99999.0,
        -99999.0,
        50.001,
        -50.001,
        None,
        "not_a_number",
        [],
        {},
    ])
    def test_extreme_non_finite_target_x_rejected(self, client, bad_x):
        """Extreme, non-finite, out-of-range, and non-numeric target_x return HTTP 400."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "target_x": bad_x,
            "target_z": 2.50,
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 400, f"Expected 400 for target_x={bad_x}, got {response.status_code}"
        data = response.get_json()
        assert data.get("status") == "error"

    @pytest.mark.parametrize("bad_z", [
        float("nan"),
        float("inf"),
        -float("inf"),
        99999.0,
        -99999.0,
        50.001,
        -50.001,
        None,
        "bad_z_val",
        [],
        {},
    ])
    def test_extreme_non_finite_target_z_rejected(self, client, bad_z):
        """Extreme, non-finite, out-of-range, and non-numeric target_z return HTTP 400."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "target_x": 0.0,
            "target_z": bad_z,
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 400, f"Expected 400 for target_z={bad_z}, got {response.status_code}"
        data = response.get_json()
        assert data.get("status") == "error"

    def test_partial_coordinates_pair_rejected(self, client):
        """Target coordinate pairs must be supplied together or omitted."""
        _reset_game(client)
        # target_x provided without target_z
        res1 = client.post("/api/pitch/throw", json={
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "target_x": 0.0,
        })
        assert res1.status_code == 400

        _reset_game(client)
        # target_z provided without target_x
        res2 = client.post("/api/pitch/throw", json={
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "target_z": 2.50,
        })
        assert res2.status_code == 400

    @pytest.mark.parametrize("tx_str,tz_str,expected_x,expected_z", [
        ("-10.5", "2.5", -10.5, 2.5),
        ("0.0", "3.0", 0.0, 3.0),
        ("1.25", "-1.5", 1.25, -1.5),
        ("  -5.0  ", "  2.0  ", -5.0, 2.0),
    ])
    def test_string_numeric_coordinates_proper_fallback(self, client, tx_str, tz_str, expected_x, expected_z):
        """String numeric coordinates gracefully parse and succeed with HTTP 200."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "target_x": tx_str,
            "target_z": tz_str,
            "timing_tier": "GOOD",
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 200, f"Expected 200 for '{tx_str}', '{tz_str}', got {response.status_code}"
        data = response.get_json()
        assert data.get("status") == "success"

    @pytest.mark.parametrize("tx,tz", [
        (50.0, 50.0),
        (-50.0, -50.0),
        (50.0, -50.0),
        (-50.0, 50.0),
    ])
    def test_exact_physical_boundary_coordinates(self, client, tx, tz):
        """Exact coordinate boundaries [-50.0, 50.0] are accepted without error."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "target_x": tx,
            "target_z": tz,
            "timing_tier": "GOOD",
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 200

    @pytest.mark.parametrize("invalid_tier", [
        "EXCELLENT",
        "FLAWLESS",
        "GREAT",
        "SUPER",
        "HORRIBLE",
        12345,
        0,
        True,
        False,
        ["PERFECT"],
        {"tier": "PERFECT"},
    ])
    def test_timing_tier_invalid_variations_rejected(self, client, invalid_tier):
        """Non-contract TimingTier variations return HTTP 400 Bad Request."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "timing_tier": invalid_tier,
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 400, f"Expected 400 for timing_tier={invalid_tier}, got {response.status_code}"
        data = response.get_json()
        assert data.get("status") == "error"

    @pytest.mark.parametrize("raw_input,expected_tier", [
        ("  perfect  ", "PERFECT"),
        ("PERFECT", "PERFECT"),
        ("perfect", "PERFECT"),
        ("  PERFECT  ", "PERFECT"),
        ("GoOd", "GOOD"),
        ("good", "GOOD"),
        (" GOOD ", "GOOD"),
        ("okay", "OKAY"),
        ("OKAY", "OKAY"),
        ("  Okay  ", "OKAY"),
        ("pOOr", "POOR"),
        ("poor", "POOR"),
        (" POOR ", "POOR"),
    ])
    def test_timing_tier_case_and_whitespace_normalization(self, client, raw_input, expected_tier):
        """TimingTier handles mixed-case and padded whitespace, normalizing to uppercase in telemetry."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "timing_tier": raw_input,
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert "execution" in data
        assert data["execution"]["timing_tier"] == expected_tier

    @pytest.mark.parametrize("empty_tier", ["", "   ", None])
    def test_timing_tier_empty_or_none_falls_back_to_simulation(self, client, empty_tier):
        """Empty string, whitespace-only, or None timing_tier triggers probabilistic simulation roll."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
        }
        if empty_tier is not None:
            payload["timing_tier"] = empty_tier
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["execution"]["timing_tier"] in ("PERFECT", "GOOD", "OKAY", "POOR")

    @pytest.mark.parametrize("bad_pitch", [
        "Ultra Curve",
        "Not A Pitch",
        "Knuckleball of Doom",
        "",
        "   ",
        123,
        99.9,
        ["4-Seam Fastball"],
        {"name": "4-Seam Fastball"},
    ])
    def test_unknown_pitch_rejection(self, client, bad_pitch):
        """Unknown or invalid pitch names return HTTP 400 Bad Request."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": bad_pitch,
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 400, f"Expected 400 for pitch_name={bad_pitch}, got {response.status_code}"
        data = response.get_json()
        assert data.get("status") == "error"

    @pytest.mark.parametrize("pitch_alias", [
        "Slider",
        "slider",
        " SLIDER ",
        "Curveball",
        "curveball",
        "  Curveball  ",
        "Sweeper",
        "sweeper",
        " SWEEPER ",
        "4-Seam Fastball",
        "Four-Seam Fastball",
        "Power Sinker",
        "Sinker",
    ])
    def test_pitch_family_aliasing_resolution(self, client, pitch_alias):
        """Pitchers with breaking pitches resolve aliases (Slider -> SWP, Curveball -> CB) with HTTP 200."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": pitch_alias,
            "timing_tier": "GOOD",
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 200, f"Failed to resolve alias '{pitch_alias}': {response.data}"
        data = response.get_json()
        assert data.get("status") == "success"
        assert "execution" in data

    @pytest.mark.parametrize("bad_label", [
        123,
        True,
        ["GOOD"],
        {"label": "GOOD"},
    ])
    def test_timing_label_invalid_types_rejected(self, client, bad_label):
        """Non-string timing_label returns HTTP 400 Bad Request."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "timing_tier": "GOOD",
            "timing_label": bad_label,
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 400

    def test_timing_label_unicode_and_whitespace_preservation(self, client):
        """Unicode characters and stripped whitespace in timing_label are cleanly preserved."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "timing_tier": "PERFECT",
            "timing_label": "  ⚡ PINPOINT PERFECT! ⚡  ",
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["execution"]["timing_label"] == "⚡ PINPOINT PERFECT! ⚡"

    def test_selection_mode_and_intent_boundaries(self, client):
        """Selection mode and intent validate strictly according to contract."""
        _reset_game(client)
        # selection_mode='manual' is invalid
        r1 = client.post("/api/pitch/throw", json={
            "selection_mode": "manual",
            "pitch_name": "4-Seam Fastball",
        })
        assert r1.status_code == 400

        _reset_game(client)
        # selection_mode='user' requires pitch_name
        r2 = client.post("/api/pitch/throw", json={
            "selection_mode": "user",
        })
        assert r2.status_code == 400

        _reset_game(client)
        # selection_mode='ai' does not accept pitch_name
        r3 = client.post("/api/pitch/throw", json={
            "selection_mode": "ai",
            "pitch_name": "4-Seam Fastball",
        })
        assert r3.status_code == 400

        _reset_game(client)
        # invalid pitch_intent
        r4 = client.post("/api/pitch/throw", json={
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "pitch_intent": "KILL",
        })
        assert r4.status_code == 400

    def test_pitch_in_flight_concurrency_conflict(self, client):
        """Throwing while a pitch is pending flight returns HTTP 409 Conflict."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "4-Seam Fastball",
            "timing_tier": "GOOD",
        }
        res1 = client.post("/api/pitch/throw", json=payload)
        assert res1.status_code == 200

        # Attempt immediate second throw without resolving
        res2 = client.post("/api/pitch/throw", json=payload)
        assert res2.status_code == 409
        data = res2.get_json()
        assert data.get("status") == "error"
        assert "in flight" in data.get("message", "").lower()

        # Resolve first pitch and verify throwing is unblocked
        res_res = client.post("/api/pitch/resolve", json={"batter_decision": "TAKE"})
        assert res_res.status_code == 200

        res3 = client.post("/api/pitch/throw", json=payload)
        assert res3.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# 2. Response Telemetry Invariants (N >= 100 requests)
# ═════════════════════════════════════════════════════════════════════════════

class TestResponseTelemetryInvariants:
    """Rigorous empirical validation of mathematical and physical invariants across 125 requests."""

    REQUIRED_TELEMETRY_KEYS = {
        "ability_tier",
        "timing_tier",
        "timing_label",
        "base_radius_inches",
        "executed_radius_inches",
        "radial_miss_inches",
        "realized_x",
        "realized_z",
    }

    VALID_ABILITY_TIERS = {"ELITE", "GREAT", "GOOD", "OKAY", "MEDIOCRE", "POOR"}
    VALID_TIMING_TIERS = {"PERFECT", "GOOD", "OKAY", "POOR"}

    def test_telemetry_invariants_across_125_pitches(self, client):
        """
        Executes N = 125 pitch requests across all release timing regimes:
        - 25 PERFECT requests
        - 25 GOOD requests
        - 25 OKAY requests
        - 25 POOR requests
        - 25 Simulated rolls (timing_tier omitted)

        Asserts on every response:
        1. 'execution' key present in response JSON.
        2. All 8 required telemetry keys present.
        3. Invariants:
           - base_radius_inches > 0
           - executed_radius_inches > 0
           - radial_miss_inches >= 0
           - radial_miss_inches <= executed_radius_inches + 1e-4 (zero boundary leakage)
        4. Consistency:
           - executed_radius_inches == round(base_radius_inches * TIMING_MULTIPLIERS[timing_tier], 3)
           - math.hypot(delta_x, delta_z) <= executed_radius_inches + 1e-4
        """
        _reset_game(client)

        regimes = [
            ("PERFECT", "PERFECT!"),
            ("GOOD", "GOOD"),
            ("OKAY", "EARLY • OKAY"),
            ("POOR", "LATE • POOR"),
            (None, None),  # Simulation timing roll
        ]

        total_tested = 0

        for tier, label in regimes:
            for iteration in range(25):
                target_x = round((iteration % 5 - 2) * 0.3, 2)  # vary x: -0.6 to +0.6
                target_z = round(2.0 + (iteration % 4) * 0.3, 2)  # vary z: 2.0 to 2.9

                payload = {
                    "selection_mode": "user",
                    "pitch_name": "4-Seam Fastball" if iteration % 2 == 0 else "Slider",
                    "target_x": target_x,
                    "target_z": target_z,
                }
                if tier is not None:
                    payload["timing_tier"] = tier
                if label is not None:
                    payload["timing_label"] = label

                response = client.post("/api/pitch/throw", json=payload)
                assert response.status_code == 200, (
                    f"Iteration {iteration} for tier={tier} failed with {response.status_code}: {response.data}"
                )
                data = response.get_json()

                # Invariant 1: Top-level execution envelope
                assert "execution" in data, f"Missing 'execution' in response: {data}"
                exec_data = data["execution"]

                # Invariant 2: All 8 keys present
                missing_keys = self.REQUIRED_TELEMETRY_KEYS - set(exec_data.keys())
                assert not missing_keys, f"Missing telemetry keys: {missing_keys}"

                # Key extractions
                ability_tier = exec_data["ability_tier"]
                timing_tier = exec_data["timing_tier"]
                timing_label = exec_data["timing_label"]
                base_radius = exec_data["base_radius_inches"]
                exec_radius = exec_data["executed_radius_inches"]
                radial_miss = exec_data["radial_miss_inches"]
                realized_x = exec_data["realized_x"]
                realized_z = exec_data["realized_z"]

                # Invariant 3: Enum domains
                assert ability_tier in self.VALID_ABILITY_TIERS, f"Invalid ability_tier: {ability_tier}"
                assert timing_tier in self.VALID_TIMING_TIERS, f"Invalid timing_tier: {timing_tier}"
                assert isinstance(timing_label, str) and len(timing_label.strip()) > 0

                # Invariant 4: Positivity and zero boundary leakage
                assert base_radius > 0.0, f"base_radius_inches {base_radius} <= 0"
                assert exec_radius > 0.0, f"executed_radius_inches {exec_radius} <= 0"
                assert radial_miss >= 0.0, f"radial_miss_inches {radial_miss} < 0"
                assert radial_miss <= exec_radius + 1e-4, (
                    f"Radial miss boundary leakage! radial_miss ({radial_miss:.5f}) > "
                    f"executed_radius ({exec_radius:.5f}) by {radial_miss - exec_radius:.6f}"
                )

                # Invariant 5: Exact multiplier consistency
                expected_multiplier = TIMING_MULTIPLIERS[TimingTier(timing_tier)]
                expected_exec_radius = round(base_radius * expected_multiplier, 3)
                assert exec_radius == expected_exec_radius, (
                    f"Executed radius mismatch: {exec_radius} != round({base_radius} * {expected_multiplier}, 3)"
                )

                # Invariant 6: Realized coordinates geometric consistency
                dx_in = (realized_x - target_x) * 12.0
                dz_in = (realized_z - target_z) * 12.0
                euclidean_dist = math.hypot(dx_in, dz_in)
                assert euclidean_dist <= exec_radius + 1e-4, (
                    f"Realized coordinate ({realized_x}, {realized_z}) exceeds circle! "
                    f"Distance {euclidean_dist:.4f} > executed_radius {exec_radius:.4f}"
                )

                # Invariant 7: Radial miss matches realized distance within rounding tolerance
                assert math.isclose(radial_miss, euclidean_dist, abs_tol=1e-3), (
                    f"radial_miss_inches {radial_miss} differs from euclidean distance {euclidean_dist}"
                )

                # Cleanly resolve pitch
                res_resolve = client.post("/api/pitch/resolve", json={"batter_decision": "TAKE"})
                assert res_resolve.status_code == 200

                total_tested += 1

                # Periodically re-seed/reset to avoid game-over triggers during 125 throws
                if total_tested % 15 == 0:
                    _reset_game(client)

        assert total_tested == 125, f"Expected 125 tests, ran {total_tested}"


# ═════════════════════════════════════════════════════════════════════════════
# 3. Interactive Delivery Flow & CamelCase Gameday Contract
# ═════════════════════════════════════════════════════════════════════════════

class TestInteractiveDeliveryFlow:
    """Verifies end-to-end interactive delivery integration with gameday packet."""

    def test_gameday_packet_execution_parity(self, client):
        """Verifies that gameday_packet contains matched camelCase execution telemetry."""
        _reset_game(client)
        payload = {
            "selection_mode": "user",
            "pitch_name": "Slider",
            "target_zone": "heart",
            "target_x": 0.10,
            "target_z": 2.45,
            "timing_tier": "PERFECT",
            "timing_label": "SWEET SPOT PERFECT!",
        }
        response = client.post("/api/pitch/throw", json=payload)
        assert response.status_code == 200
        data = response.get_json()

        assert "gameday_packet" in data
        gp_exec = data["gameday_packet"]["execution"]
        resp_exec = data["execution"]

        assert gp_exec["abilityTier"] == resp_exec["ability_tier"]
        assert gp_exec["timingTier"] == resp_exec["timing_tier"]
        assert gp_exec["timingLabel"] == resp_exec["timing_label"]
        assert gp_exec["baseRadiusInches"] == resp_exec["base_radius_inches"]
        assert gp_exec["executedRadiusInches"] == resp_exec["executed_radius_inches"]
        assert gp_exec["radialMissInches"] == resp_exec["radial_miss_inches"]
        assert gp_exec["realizedX"] == resp_exec["realized_x"]
        assert gp_exec["realizedZ"] == resp_exec["realized_z"]
