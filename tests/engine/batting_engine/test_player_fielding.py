import pytest
from backend.engine.models.player import (
    Player,
    DEFAULT_DEFENSIVE_RATINGS,
    DEFENSIVE_RATING_KEYS,
    POSITION_WEIGHTS,
    POSITION_GATES,
)


def test_defensive_keys_defined():
    expected_keys = {
        "reaction",
        "route_efficiency",
        "range",
        "fielding",
        "transfer_speed",
        "arm_strength",
        "arm_accuracy",
        "body_control",
        "positioning",
        "baseball_iq",
    }
    assert set(DEFENSIVE_RATING_KEYS) == expected_keys
    for k in expected_keys:
        assert k in DEFAULT_DEFENSIVE_RATINGS
        assert DEFAULT_DEFENSIVE_RATINGS[k] == 65.0


def test_get_defensive_rating_fallback():
    p = Player(name="Bare Player")
    assert p.get_defensive_rating("range") == 65.0
    assert p.get_defensive_rating("reaction") == 65.0


def test_get_defensive_rating_explicit():
    p = Player(name="Speedster", ratings={"range": 95.0, "reaction": 82.0})
    assert p.get_defensive_rating("range") == 95.0
    assert p.get_defensive_rating("reaction") == 82.0
    assert p.get_defensive_rating("arm_strength") == 65.0


def test_kinematic_conversion_helpers():
    # Elite defender (all 99)
    elite = Player(name="Elite", ratings={k: 99.0 for k in DEFENSIVE_RATING_KEYS})
    assert elite.get_reaction_time_s() == pytest.approx(0.45 - (99.0 / 100.0) * 0.25, abs=1e-3)
    assert elite.get_sprint_speed_fps() == pytest.approx(22.0 + (99.0 / 100.0) * 8.5, abs=1e-3)
    assert elite.get_route_efficiency() == pytest.approx(0.85 + (99.0 / 100.0) * 0.15, abs=1e-3)
    assert elite.get_glove_radius_ft() == pytest.approx(3.2 + (99.0 / 100.0) * 2.3, abs=1e-3)
    assert elite.get_transfer_time_s() == pytest.approx(0.85 - (99.0 / 100.0) * 0.40, abs=1e-3)
    assert elite.get_throw_speed_mph() == pytest.approx(70.0 + (99.0 / 100.0) * 32.0, abs=1e-3)

    # Poor defender (all 0)
    poor = Player(name="Poor", ratings={k: 0.0 for k in DEFENSIVE_RATING_KEYS})
    assert poor.get_reaction_time_s() == pytest.approx(0.45, abs=1e-3)
    assert poor.get_sprint_speed_fps() == pytest.approx(22.0, abs=1e-3)
    assert poor.get_route_efficiency() == pytest.approx(0.85, abs=1e-3)
    assert poor.get_glove_radius_ft() == pytest.approx(3.2, abs=1e-3)
    assert poor.get_transfer_time_s() == pytest.approx(0.85, abs=1e-3)
    assert poor.get_throw_speed_mph() == pytest.approx(70.0, abs=1e-3)


def test_position_weights_sum_to_one():
    for pos, weights in POSITION_WEIGHTS.items():
        assert sum(weights.values()) == pytest.approx(1.0, abs=1e-4), f"{pos} weights do not sum to 1.0"


def test_height_inches_parsing():
    assert Player(name="P1", vitals={"height": "6'2\""}).get_height_inches() == 74
    assert Player(name="P2", vitals={"height": "6-4"}).get_height_inches() == 76
    assert Player(name="P3", vitals={"height": 72}).get_height_inches() == 72
    assert Player(name="P4", vitals={"height": "75"}).get_height_inches() == 75
    assert Player(name="P5", vitals={}).get_height_inches() is None


def test_ss_gates():
    # SS requires Range >= 60 (-15) and Arm >= 55 (-15)
    ss = Player(name="Shortstop", ratings={"range": 55.0, "arm_strength": 50.0})
    passed, penalty, reasons = ss.check_position_gates("SS")
    assert passed is False
    assert penalty == 30.0
    assert len(reasons) == 2


def test_1b_height_or_fielding_gate():
    # 1B requires Height >= 74 inches OR Fielding >= 65 (-10)
    p1 = Player(name="Tall 1B", vitals={"height": "6'3\""}, ratings={"fielding": 50.0})
    passed, penalty, _ = p1.check_position_gates("1B")
    assert passed is True
    assert penalty == 0.0

    p2 = Player(name="Short 1B", vitals={"height": "5'10\""}, ratings={"fielding": 75.0})
    passed, penalty, _ = p2.check_position_gates("1B")
    assert passed is True
    assert penalty == 0.0

    p3 = Player(name="Unfit 1B", vitals={"height": "5'10\""}, ratings={"fielding": 50.0})
    passed, penalty, reasons = p3.check_position_gates("1B")
    assert passed is False
    assert penalty == 10.0


def test_cf_gate_and_full_score():
    # CF requires Range >= 65 (-20)
    cf = Player(
        name="Speedy CF",
        position="CF",
        ratings={
            "range": 80.0,
            "reaction": 75.0,
            "route_efficiency": 85.0,
            "arm_strength": 70.0,
            "arm_accuracy": 70.0,
            "fielding": 75.0,
        },
    )
    score = cf.calculate_position_rating("CF", games_at_position=200)
    assert 78.2 <= score <= 78.5

    rookie_score = cf.calculate_position_rating("CF", games_at_position=0)
    assert rookie_score == pytest.approx(78.35 * 0.65, abs=0.15)


def test_player_serialization_round_trip():
    initial = Player(
        name="Mookie Betts",
        position="RF",
        ratings={
            "range": 88.0,
            "reaction": 92.0,
            "route_efficiency": 90.0,
            "arm_strength": 85.0,
            "fielding": 95.0,
            "transfer_speed": 88.0,
            "arm_accuracy": 82.0,
            "body_control": 90.0,
            "positioning": 85.0,
            "baseball_iq": 94.0,
        },
    )
    d = initial.to_dict()
    hydrated = Player.from_dict(d)
    for k in DEFENSIVE_RATING_KEYS:
        assert hydrated.get_defensive_rating(k) == initial.get_defensive_rating(k)


def test_roster_store_hydrates_position_players_with_defensive_ratings():
    from backend.database.roster_store import RosterStore

    store = RosterStore()
    store.warmup(force=True)
    teams = store.get_all_teams()
    assert len(teams) > 0
    first_team = teams[0]
    roster = store.get_roster(first_team["id"])
    assert roster is not None
    position_players = roster.get("position_players", [])
    if position_players:
        p = position_players[0]
        assert p.get_defensive_rating("range") > 0.0
        assert p.get_defensive_rating("reaction") > 0.0
        assert p.get_defensive_rating("fielding") > 0.0
        assert "route_efficiency" in p.ratings
        assert "arm_strength" in p.ratings



