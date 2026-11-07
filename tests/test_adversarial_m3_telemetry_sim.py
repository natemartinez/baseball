"""
Adversarial Empirical Test Suite for Milestone 3: API Contract & Telemetry (`teamwork_challenger`).

Author: Challenger 2 (Empirical Verification)
Target: Backend API routes (/api/pitch/throw), GameEngine orchestration,
        simulation probability distribution adherence, interactive timing overrides,
        directional dispersion, and multi-game simulation telemetry stability.

Stress-test Dimensions:
1. Simulation Fallback Empirical Distribution:
   - Perform N=2,000 throws through engine.throw_pitch(selection_mode="ai") (omitting timing_tier).
   - Verify that rolled timing_tier frequencies match expected distributions for the active pitcher's ability tier within 3-sigma tolerance.
   - Verify that under composure leverage (RISP) or fatigue, the distribution shifts toward OKAY/POOR.
2. Interactive Timing Override & Radial Dispersion Adherence:
   - For each TimingTier (PERFECT, GOOD, OKAY, POOR), throw N=250 pitches via /api/pitch/throw.
   - Verify that execution['timing_tier'] strictly matches the requested tier.
   - For PERFECT: mean radial miss is < 45% of executed_radius_inches.
   - For OKAY/POOR with EARLY: verify miss direction has +Z tendency.
   - For OKAY/POOR with LATE: verify miss direction has -Z tendency.
   - Strict containment: 0% boundary leakage across all 1,000 pitches (radial_miss_inches <= executed_radius_inches + 1e-4).
3. Multi-Pitch Inning Simulation Stability:
   - Simulate 3 complete games (approx 400-500 pitches) through the engine ensuring every pitch returns valid execution telemetry with no crashes, NaN, or None values.
"""

import math
from collections import Counter, defaultdict
from typing import Dict, Any, List

import pytest
from tiers import (
    AbilityTier,
    TimingTier,
    TIMING_MULTIPLIERS,
    BASELINE_TIMING_PROBABILITIES,
)
from backend.api.app import create_app
from backend.api.routes import load_team_roster
from backend.engine.game_engine.engine import GameEngine


@pytest.fixture(scope="module")
def app():
    """Module-scoped Flask test application."""
    application = create_app()
    application.config.update({"TESTING": True})
    return application


@pytest.fixture
def client(app):
    """Test client with initialized match."""
    test_client = app.test_client()
    test_client.post("/api/start_game", json={"home_team_id": 1, "away_team_id": 2})
    return test_client


# ═════════════════════════════════════════════════════════════════════════════
# 1. Simulation Fallback Empirical Distribution (N = 2,000 throws)
# ═════════════════════════════════════════════════════════════════════════════

class TestSimulationFallbackEmpiricalDistribution:
    """
    Adversarial verification of simulation mode timing distributions rolled
    automatically by PitchingEngine and GameEngine when timing fields are omitted.
    """

    def test_simulation_fallback_2000_pitches_3sigma_tolerance(self):
        """
        Perform N=2,000 throws through engine.throw_pitch(selection_mode='ai').
        Verify rolled timing_tier frequencies match expected distributions for
        each active pitcher ability tier within 3-sigma tolerance.
        """
        r1 = load_team_roster(1)
        r2 = load_team_roster(2)
        engine = GameEngine(r1, r2, home_name=r1["team_name"], away_name=r2["team_name"], seed=999)

        by_tier = defaultdict(Counter)
        n_throws = 2000

        for _ in range(n_throws):
            # Keep pitcher fresh to isolate baseline ability tier distribution
            engine.pitch_count_home = 0
            engine.pitch_count_away = 0
            res = engine.throw_pitch(selection_mode="ai")

            assert res["status"] == "success", f"throw_pitch failed: {res}"
            assert "execution" in res, f"execution block missing: {res}"
            exec_data = res["execution"]

            ab_tier = exec_data["ability_tier"]
            tm_tier = exec_data["timing_tier"]
            assert ab_tier in [t.value for t in AbilityTier], f"Invalid ability tier: {ab_tier}"
            assert tm_tier in [t.value for t in TimingTier], f"Invalid timing tier: {tm_tier}"

            by_tier[ab_tier][tm_tier] += 1
            engine.orchestrator.reset()

        # At least one ability tier must have a substantial sample size
        assert len(by_tier) > 0, "No throws recorded"

        for ab_tier, counts in by_tier.items():
            tier_total = sum(counts.values())
            # Only evaluate tiers with statistically significant sample sizes (N >= 100)
            if tier_total < 100:
                continue

            expected_table = BASELINE_TIMING_PROBABILITIES[ab_tier]
            for timing_key in ["PERFECT", "GOOD", "OKAY", "POOR"]:
                obs_freq = counts[timing_key] / tier_total
                exp_freq = expected_table[timing_key]
                # 3-sigma binomial standard error
                sigma = math.sqrt(exp_freq * (1.0 - exp_freq) / tier_total)
                three_sigma = 3.0 * sigma
                abs_diff = abs(obs_freq - exp_freq)

                assert abs_diff <= three_sigma, (
                    f"Tier {ab_tier} {timing_key} frequency {obs_freq:.4f} deviates from expected "
                    f"{exp_freq:.4f} by {abs_diff:.4f}, exceeding 3-sigma tolerance {three_sigma:.4f} "
                    f"(sample N={tier_total})"
                )

    def test_simulation_distribution_shift_under_composure_leverage(self):
        """
        Verify that under composure leverage (RISP with runner on 2nd / 3rd),
        the timing distribution dynamically shifts toward OKAY/POOR.
        """
        r1 = load_team_roster(1)
        r2 = load_team_roster(2)

        # Configure pitcher with lower composure to accentuate stress response
        engine = GameEngine(r1, r2, home_name=r1["team_name"], away_name=r2["team_name"], seed=42)
        engine.home_pitcher.composure = 45.0
        engine.home_pitcher.consistency = 50.0

        n_samples = 1500

        # Baseline: Fresh, bases empty (no leverage)
        counts_base = Counter()
        for _ in range(n_samples):
            engine.pitch_count_home = 0
            res = engine.throw_pitch(selection_mode="ai")
            counts_base[res["execution"]["timing_tier"]] += 1
            engine.orchestrator.reset()

        # Leverage: Runner on second (RISP)
        engine.bases["second"] = {"name": "Lead Runner"}
        counts_lev = Counter()
        for _ in range(n_samples):
            engine.pitch_count_home = 0
            res = engine.throw_pitch(selection_mode="ai")
            counts_lev[res["execution"]["timing_tier"]] += 1
            engine.orchestrator.reset()

        p_base_bad = (counts_base["OKAY"] + counts_base["POOR"]) / n_samples
        p_lev_bad = (counts_lev["OKAY"] + counts_lev["POOR"]) / n_samples

        shift = p_lev_bad - p_base_bad
        assert shift > 0.02, (
            f"Expected positive shift toward OKAY/POOR under composure leverage, but got shift {shift:+.4f} "
            f"(base={p_base_bad:.4f}, lev={p_lev_bad:.4f})"
        )

    def test_simulation_distribution_shift_under_fatigue(self):
        """
        Verify that under severe pitch-count fatigue (pitch_count = 110),
        the timing distribution shifts mass toward OKAY/POOR and away from PERFECT/GOOD.
        """
        r1 = load_team_roster(1)
        r2 = load_team_roster(2)
        engine = GameEngine(r1, r2, home_name=r1["team_name"], away_name=r2["team_name"], seed=777)

        n_samples = 1500

        # Fresh pitcher
        counts_fresh = Counter()
        for _ in range(n_samples):
            engine.pitch_count_home = 0
            res = engine.throw_pitch(selection_mode="ai")
            counts_fresh[res["execution"]["timing_tier"]] += 1
            engine.orchestrator.reset()

        # Fatigued pitcher (pitch count well past stamina threshold)
        counts_fatigued = Counter()
        for _ in range(n_samples):
            engine.pitch_count_home = 110
            res = engine.throw_pitch(selection_mode="ai")
            counts_fatigued[res["execution"]["timing_tier"]] += 1
            engine.orchestrator.reset()

        p_fresh_bad = (counts_fresh["OKAY"] + counts_fresh["POOR"]) / n_samples
        p_fatigued_bad = (counts_fatigued["OKAY"] + counts_fatigued["POOR"]) / n_samples

        p_fresh_good = (counts_fresh["PERFECT"] + counts_fresh["GOOD"]) / n_samples
        p_fatigued_good = (counts_fatigued["PERFECT"] + counts_fatigued["GOOD"]) / n_samples

        fatigue_shift = p_fatigued_bad - p_fresh_bad
        assert fatigue_shift > 0.03, (
            f"Expected fatigue shift toward OKAY/POOR > 0.03, but got {fatigue_shift:+.4f} "
            f"(fresh={p_fresh_bad:.4f}, fatigued={p_fatigued_bad:.4f})"
        )
        assert p_fatigued_good < p_fresh_good, (
            f"Expected PERFECT+GOOD to decline under fatigue, but got fresh={p_fresh_good:.4f}, "
            f"fatigued={p_fatigued_good:.4f}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# 2. Interactive Timing Override & Radial Dispersion Adherence (N = 1,000)
# ═════════════════════════════════════════════════════════════════════════════

class TestInteractiveTimingOverrideAndRadialDispersion:
    """
    Adversarial verification of interactive release overrides via POST /api/pitch/throw:
    - Timing tier strictly overrides simulation rolls.
    - Radial dispersion adherence (PERFECT < 45% radius, early +Z, late -Z).
    - Hard containment (0% boundary leakage across all 1,000 pitches).
    """

    def _safe_throw_and_resolve(self, client, payload: dict) -> dict:
        """Throws pitch via API, asserts 200, resolves pitch, and resets game if finished."""
        res = client.post("/api/pitch/throw", json=payload)
        assert res.status_code == 200, f"throw failed ({res.status_code}): {res.data}"
        data = res.get_json()

        # Resolve pitch to clear pending state for next iteration
        res_resolve = client.post("/api/pitch/resolve", json={"batter_decision": "TAKE"})
        assert res_resolve.status_code == 200, f"resolve failed: {res_resolve.data}"
        resolve_data = res_resolve.get_json()

        # Restart match if game finished
        if resolve_data.get("game_state", {}).get("game_over"):
            client.post("/api/start_game", json={"home_team_id": 1, "away_team_id": 2})

        return data

    def test_interactive_timing_override_and_strict_match(self, client):
        """
        For each TimingTier (PERFECT, GOOD, OKAY, POOR), throw N=250 pitches via /api/pitch/throw.
        Verify that execution['timing_tier'] strictly matches requested tier on 100% of pitches.
        """
        tiers_to_test = [
            ("PERFECT", "PERFECT!"),
            ("GOOD", "GOOD"),
            ("OKAY", "EARLY • OKAY"),
            ("POOR", "LATE • POOR"),
        ]

        for tier_name, label in tiers_to_test:
            for _ in range(50):  # 50 throws per tier in this individual check
                payload = {
                    "selection_mode": "user",
                    "pitch_name": "4-Seam Fastball",
                    "pitch_intent": "STRIKE",
                    "target_zone": "heart",
                    "target_x": 0.0,
                    "target_z": 2.50,
                    "timing_tier": tier_name,
                    "timing_label": label,
                }
                data = self._safe_throw_and_resolve(client, payload)
                ex = data["execution"]
                assert ex["timing_tier"] == tier_name, f"Expected {tier_name}, got {ex['timing_tier']}"
                assert ex["timing_label"] == label, f"Expected {label}, got {ex['timing_label']}"

    def test_perfect_timing_tight_center_clustering_radial_miss(self, client):
        """
        Across N=250 PERFECT pitches via /api/pitch/throw:
        Verify mean radial miss is < 45% of executed_radius_inches.
        """
        n_throws = 250
        r_ratios = []

        for _ in range(n_throws):
            payload = {
                "selection_mode": "user",
                "pitch_name": "4-Seam Fastball",
                "pitch_intent": "STRIKE",
                "target_zone": "heart",
                "target_x": 0.0,
                "target_z": 2.50,
                "timing_tier": "PERFECT",
                "timing_label": "PERFECT!",
            }
            data = self._safe_throw_and_resolve(client, payload)
            ex = data["execution"]
            assert ex["timing_tier"] == "PERFECT"
            r_miss = ex["radial_miss_inches"]
            r_exec = ex["executed_radius_inches"]
            assert r_exec > 0.0
            r_ratios.append(r_miss / r_exec)

        mean_ratio = sum(r_ratios) / len(r_ratios)
        assert mean_ratio < 0.45, (
            f"PERFECT timing mean radial miss ratio {mean_ratio:.4f} is NOT < 0.45 "
            f"(folded normal theoretical ~0.279)"
        )
        assert 0.20 <= mean_ratio <= 0.35, f"PERFECT mean ratio {mean_ratio:.4f} deviated from folded normal range"

    def test_directional_dispersion_vertical_tendencies_early_and_late(self, client):
        """
        For OKAY and POOR:
        - EARLY releases must exhibit positive vertical (+Z) miss tendency.
        - LATE releases must exhibit negative vertical (-Z) miss tendency.
        """
        target_z = 2.50
        n_per_condition = 100

        # 1. OKAY with EARLY
        okay_early_plus_z = 0
        for _ in range(n_per_condition):
            data = self._safe_throw_and_resolve(client, {
                "selection_mode": "user",
                "pitch_name": "4-Seam Fastball",
                "pitch_intent": "STRIKE",
                "target_zone": "heart",
                "target_x": 0.0,
                "target_z": target_z,
                "timing_tier": "OKAY",
                "timing_label": "EARLY • OKAY",
            })
            if data["execution"]["realized_z"] > target_z:
                okay_early_plus_z += 1

        early_okay_pct = okay_early_plus_z / n_per_condition
        assert early_okay_pct >= 0.80, (
            f"EARLY • OKAY +Z tendency rate {early_okay_pct:.1%} below required 80%"
        )

        # 2. OKAY with LATE
        okay_late_minus_z = 0
        for _ in range(n_per_condition):
            data = self._safe_throw_and_resolve(client, {
                "selection_mode": "user",
                "pitch_name": "4-Seam Fastball",
                "pitch_intent": "STRIKE",
                "target_zone": "heart",
                "target_x": 0.0,
                "target_z": target_z,
                "timing_tier": "OKAY",
                "timing_label": "LATE • OKAY",
            })
            if data["execution"]["realized_z"] < target_z:
                okay_late_minus_z += 1

        late_okay_pct = okay_late_minus_z / n_per_condition
        assert late_okay_pct >= 0.80, (
            f"LATE • OKAY -Z tendency rate {late_okay_pct:.1%} below required 80%"
        )

        # 3. POOR with EARLY
        poor_early_plus_z = 0
        for _ in range(n_per_condition):
            data = self._safe_throw_and_resolve(client, {
                "selection_mode": "user",
                "pitch_name": "4-Seam Fastball",
                "pitch_intent": "STRIKE",
                "target_zone": "heart",
                "target_x": 0.0,
                "target_z": target_z,
                "timing_tier": "POOR",
                "timing_label": "EARLY • POOR",
            })
            if data["execution"]["realized_z"] > target_z:
                poor_early_plus_z += 1

        early_poor_pct = poor_early_plus_z / n_per_condition
        assert early_poor_pct >= 0.80, (
            f"EARLY • POOR +Z tendency rate {early_poor_pct:.1%} below required 80%"
        )

        # 4. POOR with LATE
        poor_late_minus_z = 0
        for _ in range(n_per_condition):
            data = self._safe_throw_and_resolve(client, {
                "selection_mode": "user",
                "pitch_name": "4-Seam Fastball",
                "pitch_intent": "STRIKE",
                "target_zone": "heart",
                "target_x": 0.0,
                "target_z": target_z,
                "timing_tier": "POOR",
                "timing_label": "LATE • POOR",
            })
            if data["execution"]["realized_z"] < target_z:
                poor_late_minus_z += 1

        late_poor_pct = poor_late_minus_z / n_per_condition
        assert late_poor_pct >= 0.80, (
            f"LATE • POOR -Z tendency rate {late_poor_pct:.1%} below required 80%"
        )

    def test_strict_containment_zero_boundary_leakage_1000_pitches(self, client):
        """
        Adversarial Boundary Invariant:
        Across N=1,000 total interactive throws (250 per timing tier: PERFECT, GOOD, OKAY, POOR):
        Zero boundary leakage allowed:
        radial_miss_inches <= executed_radius_inches + 1e-4 on 100.0% of pitches.
        """
        tiers = [
            ("PERFECT", "PERFECT!"),
            ("GOOD", "GOOD"),
            ("OKAY", "EARLY • OKAY"),
            ("POOR", "LATE • POOR"),
        ]

        total_checked = 0
        leakages = []

        for tier_name, label in tiers:
            for i in range(250):
                payload = {
                    "selection_mode": "user",
                    "pitch_name": "4-Seam Fastball",
                    "pitch_intent": "STRIKE",
                    "target_zone": "heart",
                    "target_x": 0.0,
                    "target_z": 2.50,
                    "timing_tier": tier_name,
                    "timing_label": label,
                }
                data = self._safe_throw_and_resolve(client, payload)
                ex = data["execution"]

                r_miss = ex["radial_miss_inches"]
                r_exec = ex["executed_radius_inches"]
                b_rad = ex["base_radius_inches"]

                assert r_miss >= 0.0, f"Negative radial miss: {r_miss}"
                assert r_exec > 0.0, f"Non-positive executed radius: {r_exec}"
                assert b_rad > 0.0, f"Non-positive base radius: {b_rad}"

                # Strict boundary containment tolerance: 1e-4 inches
                if r_miss > (r_exec + 1e-4):
                    leakages.append({
                        "tier": tier_name,
                        "pitch_index": i,
                        "radial_miss": r_miss,
                        "executed_radius": r_exec,
                        "leakage": r_miss - r_exec,
                    })
                total_checked += 1

        assert len(leakages) == 0, (
            f"Encountered {len(leakages)} boundary leakages out of {total_checked} throws: {leakages[:5]}"
        )
        assert total_checked == 1000, f"Expected 1,000 checked throws, got {total_checked}"


# ═════════════════════════════════════════════════════════════════════════════
# 3. Multi-Pitch Inning Simulation Stability (3 Complete Games)
# ═════════════════════════════════════════════════════════════════════════════

class TestMultiPitchInningSimulationStability:
    """
    Simulates 3 complete games through GameEngine (hundreds of consecutive pitches):
    Verifies that every pitch produces complete, valid Statcast execution telemetry
    with no unhandled exceptions, zero NaNs, and zero None values.
    """

    @pytest.mark.parametrize("seed", [101, 202, 303])
    def test_complete_game_simulation_telemetry_integrity(self, seed):
        """Simulate a complete 9+ inning game and verify execution telemetry on every pitch."""
        r1 = load_team_roster(1)
        r2 = load_team_roster(2)
        engine = GameEngine(r1, r2, home_name=r1["team_name"], away_name=r2["team_name"], seed=seed)

        pitch_count = 0
        max_pitches = 600

        required_execution_keys = [
            "ability_tier",
            "timing_tier",
            "timing_label",
            "base_radius_inches",
            "executed_radius_inches",
            "radial_miss_inches",
            "realized_x",
            "realized_z",
        ]

        while not engine.game_over and pitch_count < max_pitches:
            pitch_count += 1

            # 1. Stage 1: Throw
            thrown = engine.throw_pitch(selection_mode="ai")
            assert thrown["status"] == "success", f"throw_pitch failed at pitch {pitch_count}: {thrown}"
            assert thrown["phase"] == "THROWN"

            # Telemetry verification in throw response
            assert "execution" in thrown, f"execution block missing at pitch {pitch_count}"
            ex = thrown["execution"]

            for key in required_execution_keys:
                assert key in ex, f"Key '{key}' missing from execution dict at pitch {pitch_count}"
                val = ex[key]
                assert val is not None, f"Key '{key}' is None at pitch {pitch_count}"
                if isinstance(val, (int, float)):
                    assert math.isfinite(val), f"Key '{key}' is not finite ({val}) at pitch {pitch_count}"
                    assert not math.isnan(val), f"Key '{key}' is NaN at pitch {pitch_count}"

            assert ex["ability_tier"] in [t.value for t in AbilityTier]
            assert ex["timing_tier"] in [t.value for t in TimingTier]
            assert isinstance(ex["timing_label"], str) and len(ex["timing_label"]) > 0
            assert ex["base_radius_inches"] > 0
            assert ex["executed_radius_inches"] > 0
            assert ex["radial_miss_inches"] >= 0

            # Gameday packet execution telemetry verification
            assert "gameday_packet" in thrown
            gp_exec = thrown["gameday_packet"].get("execution", {})
            assert gp_exec.get("abilityTier") == ex["ability_tier"]
            assert gp_exec.get("timingTier") == ex["timing_tier"]
            assert gp_exec.get("timingLabel") == ex["timing_label"]
            assert gp_exec.get("baseRadiusInches") == ex["base_radius_inches"]
            assert gp_exec.get("executedRadiusInches") == ex["executed_radius_inches"]

            # 2. Stage 2: Resolve
            resolved = engine.resolve_pitch()
            assert resolved["status"] == "success", f"resolve_pitch failed at pitch {pitch_count}: {resolved}"
            assert resolved["phase"] == "RESOLVED"

        assert engine.game_over is True, f"Game did not conclude within {max_pitches} pitches"
        assert pitch_count >= 150, f"Unrealistically short game: {pitch_count} pitches"
