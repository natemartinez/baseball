import pytest
from backend.engine.models.player import Player
from backend.engine.game_engine.defense import (
    ActiveDefense,
    FielderState,
    STANDARD_FIELDER_COORDINATES,
)


def test_default_active_defense_has_all_8_positions():
    defense = ActiveDefense.default()
    assert len(defense.fielders) == 8
    expected_positions = ('P', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF')
    for pos in expected_positions:
        assert pos in defense.fielders
        fielder = defense.fielders[pos]
        assert isinstance(fielder, FielderState)
        assert isinstance(fielder.player, Player)
        assert fielder.position_id == pos
        # Default positioning (65.0) sits exactly at standard coordinates
        std_x, std_y = STANDARD_FIELDER_COORDINATES[pos]
        assert fielder.x == pytest.approx(std_x, abs=0.1)
        assert fielder.y == pytest.approx(std_y, abs=0.1)


def test_active_defense_from_lineup_maps_players():
    rf = Player(name="Aaron Judge", position="RF", ratings={"range": 85.0})
    ss = Player(name="Anthony Volpe", position="SS", ratings={"range": 82.0})
    pitcher = Player(name="Gerrit Cole", position="SP")
    lineup = [rf, ss]

    defense = ActiveDefense.from_lineup(lineup, pitcher)
    assert defense.get_fielder("RF").player.name == "Aaron Judge"
    assert defense.get_fielder("SS").player.name == "Anthony Volpe"
    assert defense.get_fielder("P").player.name == "Gerrit Cole"
    # Unfilled positions populate standard defaults
    cf = defense.get_fielder("CF")
    assert cf is not None
    assert cf.player.position == "CF"


def test_positioning_rating_applies_depth_shading():
    # CF with 95 positioning shades deeper than default for power protection
    deep_cf = Player(
        name="Deep CF",
        position="CF",
        ratings={"positioning": 95.0, "range": 80.0},
    )
    # CF with 35 positioning plays shallower
    shallow_cf = Player(
        name="Shallow CF",
        position="CF",
        ratings={"positioning": 35.0, "range": 80.0},
    )
    p = Player(name="Pitcher", position="P")

    defense_deep = ActiveDefense.from_lineup([deep_cf], p)
    defense_shallow = ActiveDefense.from_lineup([shallow_cf], p)

    cf_deep_state = defense_deep.get_fielder("CF")
    cf_shallow_state = defense_shallow.get_fielder("CF")

    assert cf_deep_state.y > STANDARD_FIELDER_COORDINATES["CF"][1]
    assert cf_shallow_state.y < STANDARD_FIELDER_COORDINATES["CF"][1]

