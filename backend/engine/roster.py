


class Player:
    def __init__(self, name, number, field_rating, handedness=None, id=None):
        self.id = id
        self.name = name
        self.number = number
        self.field_rating = field_rating
        self.handedness = handedness
      

# Shared pitch archetype table (per-pitch: role, handedness bias, target)
# Breaking balls (Slider/Cutter/Curveball) carry an "in_target": a pitch breaking
# IN to the opposite-handed batter is high-risk/high-reward.
PITCH_PROFILES = {
    "Slider": {
        "role": "chase",                              # works outside the zone
        "handedness_bias": "same",                    # effective same-handed
        "target": {"RHP vs RHB": "down_away",
                   "RHP vs LHB": "down_away"},   # RELATIVE labels, not absolute coords
        "in_target": "down_in",                         # breaking IN vs opposite hand
        "effectiveness": {"control": 70, "movement": 85, "break": 90, "velocity": (85, 89)},
    },
    "Cutter": {
        "role": "catch_zone",                         # late break, attacks the zone
        "handedness_bias": "same",
        "target": {"RHP vs RHB": "up_in",
                   "RHP vs LHB": "down_away"},
        "in_target": "up_in",                         # breaking IN vs opposite hand
        "effectiveness": {"control": 75, "movement": 75, "break": 55, "velocity": (91, 95)},
    },
    "Curveball": {
        "role": "chase",
        "handedness_bias": "same",
        "target": {"RHP vs RHB": "down_away",
                   "RHP vs LHB": "down_away"},
        "in_target": "down_in",                       # hammering IN vs opposite hand
        "effectiveness": {"control": 65, "movement": 80, "break": 95, "velocity": (77, 82)},
    },
    "Fastball": {
        "role": "catch_zone",                         # attacks the zone
        "handedness_bias": "any",
        "target": {"*": "up_in"},
        "effectiveness": {"control": 75, "movement": 60, "break": 10, "velocity": (93, 97)},  # mph range (min, max)
    },
    "Changeup": {
        "role": "chase",
        "handedness_bias": "same",
        "target": {"*": "down_away"},
        "effectiveness": {"control": 75, "movement": 85, "break": 70, "velocity": (82, 87)},
    },
}

# A concrete pitch in a pitcher's arsenal: the archetype (from PITCH_PROFILES)
# plus THIS pitcher's unique per-pitch effectiveness (control, movement, break,
# velocity).

class Pitch:
    def __init__(self, name, profile, effectiveness=None):
        self.name = name
        self.profile = profile
        defaults = profile.get("effectiveness", {})
        self.effectiveness = {**defaults, **(effectiveness or {})}

    @property
    def role(self):
        return self.profile["role"]

    def __str__(self):
        parts = []
        for k, v in self.effectiveness.items():
            if isinstance(v, tuple):
                parts.append(f"{k}:{v[0]}-{v[1]}")
            else:
                parts.append(f"{k}:{v}")
        return f"{self.name} {' '.join(parts)}"


class Pitcher(Player): 
    def __init__(self, name, number, position, pitch_rating, control_rating,
                 field_rating, pitch_zones=None, arsenal=None, handedness="RHP"):
        super().__init__(name, number, field_rating, handedness)
        self.position = position
        self.pitch_rating = pitch_rating
        self.control_rating = control_rating
        self.pitch_zones = pitch_zones
        # Need to have some kind of generator for random arsenals
        self.arsenal = arsenal

    def __str__(self):
        return (f"#{self.number} {self.name} - {self.position} "
                f"\n Pitcher Ratings: Pitch: {self.pitch_rating} "
                f"Control: {self.control_rating} Fielding: {self.field_rating}"
                f"Pitch Zones: {self.pitch_zones}"
                f"\n Arsenal: {self.arsenal}")
    
class PositionPlayer(Player): 
    def __init__(self, name, number, position, hit_rating, field_rating, hitter_zones=None, handedness="RHB"):
        super().__init__(name, number, field_rating, handedness) # Takes from the parent class(inheritance from 'Player' class)
        self.position = position    # same parameters as the parent class besides 'self'
        self.hit_rating = hit_rating
        self.hitter_zones = hitter_zones

    def __str__(self):
        return f"#{self.number} {self.name} Pos: {self.position} / Ratings: Hitting: {self.hit_rating} Fielding: {self.field_rating} Zones: {self.hitter_zones}"   
    

# Eventually I want to move all rosters to a database

# MOCK ROSTERS
rosters = {
    "home_team" : {
        "position_players": [
            PositionPlayer("Juan Soto", 22, "RF", 97, 76, [

            ], 
            handedness="LHB"),
        ],
        "pitchers": {
            "starters": [
                Pitcher("Nolan Mclean", 28, "SP", 87, 77, 78,
                        arsenal=({"Fastball": {"effectiveness": {"velocity": (96, 98), "control": 78}}})),
            ],
            "relievers": [
                Pitcher("Devin Williams", 38, "CP", 84, 79, 78,
                        arsenal=({"Slider": {"effectiveness": {"break": 96, "movement": 90}}})),
            ]
        }
    },
    "away_team": {
        "position_players": [
           PositionPlayer("Aaron Judge", 99, "RF", 98, 92, [
               
           ]),
        ],
        "pitchers": {
            "starters": [
                Pitcher("Max Fried", 54, "SP", 87, 83, 78, handedness="LHP"),
            ],
            "relievers": [
                Pitcher("David Bednar", 53, "CP", 84, 80, 78)
            ]
        }        
    }
}