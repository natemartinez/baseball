"""
MLB Statcast Strike Zone & Coordinate Mapper.
Provides 13-zone discrete targeting, 2D continuous coordinates,
and rulebook strike zone boundary testing.
"""

from typing import Dict, Tuple, Optional
try:
    from backend.engine.gameday_math import (
        ZONE_CENTERS,
        is_rulebook_strike,
        classify_gameday_zone,
        get_zone_nominal_target,
        ZONE_X_MIN, ZONE_X_MAX, ZONE_Z_BOT, ZONE_Z_TOP
    )
except ImportError:
    from gameday_math import (
        ZONE_CENTERS,
        is_rulebook_strike,
        classify_gameday_zone,
        get_zone_nominal_target,
        ZONE_X_MIN, ZONE_X_MAX, ZONE_Z_BOT, ZONE_Z_TOP
    )


class StrikeZone:
    def __init__(self, grid=None):
        self.grid = grid if grid is not None else {
            'INNER': {
                (0, 0): 'upper-in',    (0, 1): 'upper-middle', (0, 2): 'upper-away',
                (1, 0): 'middle-in',   (1, 1): 'heart',        (1, 2): 'middle-away',
                (2, 0): 'lower-in',    (2, 1): 'lower-middle', (2, 2): 'lower-away'
            },
            'OUTER': {
                (0, 0): 'chase-high',  (0, 1): 'chase-high',   (0, 2): 'chase-high',
                (1, 0): 'chase-in',    (1, 1): 'heart',        (1, 2): 'chase-away',
                (2, 0): 'chase-low',   (2, 1): 'chase-low',    (2, 2): 'chase-low'
            }
        }
        self.zone_centers = ZONE_CENTERS

    def __getitem__(self, item):
        return self.grid.get(item, self.grid['INNER'])

    def get_target_coords(self, zone_name: str) -> Tuple[float, float]:
        """Returns nominal (x, z) feet for a zone label."""
        return ZONE_CENTERS.get((zone_name or 'heart').lower(), (0.0, 2.50))

    def is_strike(self, x: float, z: float) -> bool:
        """Determines if (x, z) coordinate lands in the rulebook strike zone."""
        return is_rulebook_strike(x, z)

    def classify_zone(self, x: float, z: float) -> str:
        """Classifies coordinate into HEART, SHADOW, CHASE, or WASTE."""
        return classify_gameday_zone(x, z)

    def get_zone_nominal_target(self, zone_name: str) -> Tuple[float, float, str]:
        """Returns nominal (x, z) and zone category for a discrete target name."""
        return get_zone_nominal_target(zone_name)
