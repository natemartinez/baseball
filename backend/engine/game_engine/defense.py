"""
Active Defense Spatial Resolver.

Maintains 3D field coordinates, starting depths, and positioning adjustments
for the 8 active defensive fielders (P, 1B, 2B, 3B, SS, LF, CF, RF).
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Tuple

from backend.engine.models.player import (
    DEFAULT_DEFENSIVE_RATINGS,
    Player,
)

STANDARD_FIELDER_COORDINATES: Dict[str, Tuple[float, float]] = {
    "P": (0.0, 60.5),
    "1B": (63.6, 63.6),
    "2B": (45.0, 115.0),
    "3B": (-63.6, 63.6),
    "SS": (-45.0, 115.0),
    "LF": (-122.0, 268.0),
    "CF": (0.0, 335.0),
    "RF": (122.0, 268.0),
}

DEFENSIVE_POSITIONS: Tuple[str, ...] = (
    "P",
    "1B",
    "2B",
    "3B",
    "SS",
    "LF",
    "CF",
    "RF",
)


@dataclass
class FielderState:
    player: Player
    position_id: str
    x: float
    y: float
    depth_ft: float


@dataclass
class ActiveDefense:
    fielders: Dict[str, FielderState]

    def get_fielder(self, position_id: str) -> Optional[FielderState]:
        """Safely fetch a fielder state by standard position code."""
        return self.fielders.get(position_id.upper() if position_id else "")

    @classmethod
    def default(cls) -> "ActiveDefense":
        """Instantiates default 8-man defense positioned at standard coordinates."""
        fielders: Dict[str, FielderState] = {}
        for pos in DEFENSIVE_POSITIONS:
            std_x, std_y = STANDARD_FIELDER_COORDINATES[pos]
            p = Player(
                name=f"Default {pos}",
                position=pos,
                ratings=dict(DEFAULT_DEFENSIVE_RATINGS),
            )
            fielders[pos] = FielderState(
                player=p,
                position_id=pos,
                x=std_x,
                y=std_y,
                depth_ft=round(math.hypot(std_x, std_y), 1),
            )
        return cls(fielders=fielders)

    @classmethod
    def from_lineup(
        cls,
        defending_lineup: List[Player],
        pitcher: Optional[Player] = None,
    ) -> "ActiveDefense":
        """
        Builds ActiveDefense from the defending lineup and active pitcher,
        applying spatial depth offsets derived from each fielder's positioning rating.
        """
        lineup_by_pos: Dict[str, Player] = {}
        if defending_lineup:
            for p in defending_lineup:
                pos = str(getattr(p, "position", "") or "").upper()
                if pos in DEFENSIVE_POSITIONS and pos not in lineup_by_pos:
                    lineup_by_pos[pos] = p

        fielders: Dict[str, FielderState] = {}
        for pos in DEFENSIVE_POSITIONS:
            if pos == "P":
                player = pitcher or lineup_by_pos.get("P")
                if player is None:
                    player = Player(name="Default P", position="P", ratings=dict(DEFAULT_DEFENSIVE_RATINGS))
            else:
                player = lineup_by_pos.get(pos)
                if player is None:
                    player = Player(name=f"Default {pos}", position=pos, ratings=dict(DEFAULT_DEFENSIVE_RATINGS))

            std_x, std_y = STANDARD_FIELDER_COORDINATES[pos]
            pos_rating = player.get_defensive_rating("positioning")

            # Positioning depth shading
            if pos in ("LF", "CF", "RF"):
                # Outfielders shade deeper/shallower: +10 rating ~ +3.5 ft depth
                offset_y = (pos_rating - 65.0) * 0.35
                curr_x = std_x
                curr_y = std_y + offset_y
            elif pos in ("1B", "2B", "3B", "SS"):
                # Infielders adjust depth: +10 rating ~ +1.5 ft depth
                offset_y = (pos_rating - 65.0) * 0.15
                curr_x = std_x
                curr_y = std_y + offset_y
            else:
                curr_x = std_x
                curr_y = std_y

            depth = math.hypot(curr_x, curr_y)
            fielders[pos] = FielderState(
                player=player,
                position_id=pos,
                x=round(curr_x, 1),
                y=round(curr_y, 1),
                depth_ft=round(depth, 1),
            )

        return cls(fielders=fielders)

