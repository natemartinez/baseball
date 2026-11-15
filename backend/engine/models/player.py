from typing import Any, Dict, List, Optional


class Player:
    """
    Authoritative Domain Model for a Baseball Player (Batter / Pitcher).
    Maintains clean, normalized state decoupled from database storage mechanics.
    """

    def __init__(
        self,
        name: str,
        number: str = "00",
        field_rating: int = 50,
        handedness: Optional[str] = None,
        position: str = "DH",
        id: Optional[int] = None,
        ratings: Optional[Dict[str, float]] = None,
        zones: Optional[Dict[str, float]] = None,
        traits: Optional[List[Dict[str, Any]]] = None,
        vitals: Optional[Dict[str, Any]] = None,
        stats: Optional[List[Dict[str, Any]]] = None,
        pitch_arsenal: Optional[List[Dict[str, Any]]] = None,
        role: Optional[str] = None,
        batting_order: Optional[int] = None,
        roster_status: str = "active",
        season: Optional[int] = None,
        stamina: Optional[float] = None,
        composure: Optional[float] = None,
        arm_slot: Optional[str] = None,
        arm_slot_angle_deg: Optional[float] = None,
        release_point_ft: Optional[Dict[str, float]] = None,
        release_consistency: Optional[float] = None,
        consistency: Optional[float] = None,
        motion_bio: Optional[Dict[str, Any]] = None,
        throws: Optional[str] = None,
        bats: Optional[str] = None,
        team: Optional[str] = None,
        jersey_number: Optional[Any] = None,
        season_stats: Optional[Dict[str, Any]] = None,
        live_game_stats: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.name = name
        self.number = str(number if number is not None else (jersey_number or "00"))
        self.field_rating = int(field_rating)
        self.team = team
        self.throws = str(throws or handedness or (vitals.get("throws") if vitals else "R") or "R")
        self.bats = str(bats or (vitals.get("bats") if vitals else "R") or "R")
        self.handedness = handedness or self.throws
        if jersey_number is not None and str(jersey_number).isdigit():
            self.jersey_number: int = int(jersey_number)
        elif str(self.number).isdigit():
            self.jersey_number = int(self.number)
        else:
            self.jersey_number = 0
        self.position = position
        self.role = role
        self.batting_order = batting_order
        self.roster_status = roster_status
        self.season = season

        # Normalized game engine attributes
        self.ratings: Dict[str, float] = ratings or {}
        self.zones: Dict[str, float] = zones or {}
        self.traits: List[Dict[str, Any]] = traits or []
        self.vitals: Dict[str, Any] = vitals or {}
        self.stats: List[Dict[str, Any]] = stats or []
        self.pitch_arsenal: List[Dict[str, Any]] = pitch_arsenal or []
        self.arsenal: List[Dict[str, Any]] = self.pitch_arsenal
        self.season_stats: Dict[str, Any] = dict(season_stats or {})
        self.live_game_stats: Dict[str, Any] = dict(live_game_stats or {})

        # Biomechanical & in-game attributes with sensible fallbacks
        self.stamina: float = float(
            stamina
            if stamina is not None
            else self.get_rating("Stamina", 75.0)
        )
        self.composure: float = float(
            composure
            if composure is not None
            else self.get_rating("Composure", 75.0)
        )
        motion_bio_dict = dict(motion_bio or {})
        self.arm_slot: str = str(
            arm_slot
            or motion_bio_dict.get("arm_slot")
            or "THREE_QUARTERS"
        )
        self.arm_slot_angle_deg: float = float(
            arm_slot_angle_deg
            if arm_slot_angle_deg is not None
            else motion_bio_dict.get("arm_slot_angle_deg", 50.0)
        )
        # +X is the first-base side (catcher's right). A right-handed pitcher
        # releases from the third-base/arm side (negative X); a left-handed
        # pitcher releases from the first-base/arm side (positive X).
        default_release = {
            "x": -1.85 if str(self.handedness or "R").upper().startswith("R") else 1.85,
            "y": 54.5,
            "z": 5.9,
        }
        self.release_point_ft: Dict[str, float] = dict(
            release_point_ft
            or motion_bio_dict.get("release_point_ft")
            or default_release
        )
        self.motion_bio: Dict[str, Any] = {
            "arm_slot": self.arm_slot,
            "arm_slot_angle_deg": self.arm_slot_angle_deg,
            "release_point_ft": self.release_point_ft,
        }
        self.consistency: float = float(
            consistency
            if consistency is not None
            else self.get_rating(
                "Consistency",
                self.get_rating(
                    "consistency",
                    release_consistency if release_consistency is not None else 80.0,
                ),
            )
        )
        self.release_consistency: float = self.consistency
        if self.is_pitcher and "consistency" not in self.ratings:
            self.ratings["consistency"] = self.consistency

        self._rebuild_pitch_cache()

    def _rebuild_pitch_cache(self) -> None:
        """Maintains O(1) indexed lookup tables for pitch arsenal retrieval."""
        self._pitch_by_id: Dict[str, Dict[str, Any]] = {}
        self._pitch_by_name: Dict[str, Dict[str, Any]] = {}
        for p in self.pitch_arsenal:
            if isinstance(p, dict):
                pid = p.get("id")
                if pid:
                    self._pitch_by_id[str(pid).upper()] = p
                    self._pitch_by_id[str(pid)] = p
                pname = p.get("name") or p.get("pitch")
                if pname:
                    self._pitch_by_name[str(pname).lower().strip()] = p

    @property
    def is_pitcher(self) -> bool:
        """Determines if the player is a pitcher based on position or arsenal."""
        return self.position in ('SP', 'RP', 'CP', 'P') or len(self.pitch_arsenal) > 0

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Player":
        """
        Universal factory method to hydrate a Player object from any dictionary payload.
        Handles both database row dictionaries (with unflattened ratings/zones lists)
        and pre-flattened application dictionaries.
        """
        if not raw:
            return cls(name="Unknown")

        vitals = raw.get("vitals") or {}
        if not isinstance(vitals, dict):
            vitals = {}

        # Extract handedness from vitals or direct fields. Pitchers are
        # handed by their throwing arm; position players are handed by their
        # batting side. This matters for left-handed pitchers who bat
        # right-handed (e.g. Sean Manaea).
        position_raw = str(raw.get("position") or "DH").upper()
        arsenal_raw = raw.get("pitch_arsenal") or raw.get("arsenal") or []
        is_pitcher_like = position_raw in ("P", "SP", "RP", "CP") or bool(arsenal_raw)
        handedness = (
            raw.get("handedness")
            or (vitals.get("throws") if is_pitcher_like else vitals.get("bats"))
            or vitals.get("throws")
            or vitals.get("handedness")
            or raw.get("bats")
        )

        # 1. Normalize ratings: list of dicts or direct map -> Dict[str, float]
        ratings_raw = raw.get("ratings") or {}
        ratings_map: Dict[str, float] = {}
        if isinstance(ratings_raw, list):
            for r in ratings_raw:
                if isinstance(r, dict) and "category" in r:
                    ratings_map[r["category"]] = float(r.get("rating", 50))
        elif isinstance(ratings_raw, dict):
            ratings_map = {k: float(v) for k, v in ratings_raw.items()}

        # 2. Normalize zones: list of dicts or direct map -> Dict[str, float]
        NUMERIC_ZONE_MAP = {
            1: "upper-in",    2: "upper-middle", 3: "upper-away",
            4: "middle-in",   5: "heart",        6: "middle-away",
            7: "lower-in",    8: "lower-middle", 9: "lower-away",
        }
        zones_raw = raw.get("zones") or raw.get("hot_zones") or {}
        zones_map: Dict[str, float] = {}
        if isinstance(zones_raw, list):
            for z in zones_raw:
                if isinstance(z, dict):
                    raw_name = z.get("name") or z.get("zone")
                    if isinstance(raw_name, int) and raw_name in NUMERIC_ZONE_MAP:
                        zone_key = NUMERIC_ZONE_MAP[raw_name]
                    elif str(raw_name).isdigit() and int(raw_name) in NUMERIC_ZONE_MAP:
                        zone_key = NUMERIC_ZONE_MAP[int(raw_name)]
                    else:
                        zone_key = str(raw_name or "heart")

                    slugging = z.get("slugging", z.get("slg"))
                    if slugging is None:
                        multiplier = z.get("slg_multiplier", z.get("multiplier"))
                        if multiplier is not None:
                            try:
                                slugging = 0.400 * float(multiplier)
                            except (TypeError, ValueError):
                                slugging = None
                    if slugging is None:
                        slugging = 0.300
                    zones_map[zone_key] = round(float(slugging), 3)
        elif isinstance(zones_raw, dict):
            zones_map = {k: float(v) for k, v in zones_raw.items()}

        # 3. Resolve fielding rating
        field_rating = int(raw.get("field_rating") or ratings_map.get("Fielding", 50))

        # 4. Extract arsenal
        raw_arsenal = raw.get("pitch_arsenal") or raw.get("arsenal") or []
        arsenal = []
        if isinstance(raw_arsenal, list):
            for p in raw_arsenal:
                if isinstance(p, dict):
                    p_copy = dict(p)
                    # Bidirectional command / control_rating aliasing
                    if "command" in p_copy and "control_rating" not in p_copy:
                        p_copy["control_rating"] = p_copy["command"]
                    elif "control_rating" in p_copy and "command" not in p_copy:
                        p_copy["command"] = p_copy["control_rating"]
                    elif "control" in p_copy:
                        if "control_rating" not in p_copy:
                            p_copy["control_rating"] = p_copy["control"]
                        if "command" not in p_copy:
                            p_copy["command"] = p_copy["control"]

                    # Bidirectional spin_rate_rpm / spin_rpm aliasing
                    if "spin_rate_rpm" in p_copy and "spin_rpm" not in p_copy:
                        p_copy["spin_rpm"] = p_copy["spin_rate_rpm"]
                    elif "spin_rpm" in p_copy and "spin_rate_rpm" not in p_copy:
                        p_copy["spin_rate_rpm"] = p_copy["spin_rpm"]

                    if "break_rating" not in p_copy and "break" in p_copy:
                        p_copy["break_rating"] = p_copy["break"]

                    # Ensure tunnel_partners is a list
                    if "tunnel_partners" not in p_copy:
                        p_copy["tunnel_partners"] = []

                    arsenal.append(p_copy)
                else:
                    arsenal.append(p)

        motion_bio = raw.get("motion_bio") or vitals.get("motion_bio") or {}
        if not isinstance(motion_bio, dict):
            motion_bio = {}

        stamina = ratings_map.get("Stamina") or ratings_map.get("stamina") or raw.get("stamina") or vitals.get("stamina")
        composure = ratings_map.get("Composure") or ratings_map.get("composure") or raw.get("composure") or vitals.get("composure")
        consistency = (
            ratings_map.get("consistency")
            or ratings_map.get("Consistency")
            or raw.get("consistency")
            or motion_bio.get("consistency")
            or raw.get("release_consistency")
            or vitals.get("consistency")
            or vitals.get("release_consistency")
        )
        if consistency is not None and "consistency" not in ratings_map:
            ratings_map["consistency"] = float(consistency)
        arm_slot = motion_bio.get("arm_slot") or raw.get("arm_slot") or vitals.get("arm_slot")
        arm_slot_angle_deg = motion_bio.get("arm_slot_angle_deg") or raw.get("arm_slot_angle_deg") or vitals.get("arm_slot_angle_deg")
        release_point_ft = motion_bio.get("release_point_ft") or raw.get("release_point_ft") or vitals.get("release_point_ft") or raw.get("release")

        return cls(
            id=raw.get("id"),
            name=raw.get("name", "Unknown"),
            number=str(raw.get("number") or raw.get("jersey_number") or "00"),
            position=raw.get("position") or raw.get("primary_position") or "DH",
            field_rating=field_rating,
            handedness=handedness,
            ratings=ratings_map,
            zones=zones_map,
            traits=raw.get("traits") if isinstance(raw.get("traits"), list) else [],
            vitals=vitals,
            stats=raw.get("stats") if isinstance(raw.get("stats"), list) else [],
            pitch_arsenal=arsenal,
            role=raw.get("role"),
            batting_order=raw.get("batting_order"),
            roster_status=raw.get("roster_status", "active"),
            season=raw.get("season"),
            stamina=float(stamina) if stamina is not None else None,
            composure=float(composure) if composure is not None else None,
            arm_slot=str(arm_slot) if arm_slot is not None else None,
            arm_slot_angle_deg=float(arm_slot_angle_deg) if arm_slot_angle_deg is not None else None,
            release_point_ft=release_point_ft if isinstance(release_point_ft, dict) else None,
            release_consistency=float(consistency) if consistency is not None else None,
            consistency=float(consistency) if consistency is not None else None,
            motion_bio=motion_bio if motion_bio else None,
            throws=raw.get("throws") or vitals.get("throws"),
            bats=raw.get("bats") or vitals.get("bats"),
            team=raw.get("team") or vitals.get("team"),
            jersey_number=raw.get("jersey_number"),
            season_stats=raw.get("season_stats"),
            live_game_stats=raw.get("live_game_stats"),
        )

    @classmethod
    def from_db(cls, raw: Dict[str, Any]) -> "Player":
        """Maintains backward compatibility with db.py calls."""
        return cls.from_dict(raw)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes hydrated Player object into a clean dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "number": self.number,
            "jersey_number": self.jersey_number,
            "position": self.position,
            "field_rating": self.field_rating,
            "handedness": self.handedness,
            "throws": self.throws,
            "bats": self.bats,
            "team": self.team or self.vitals.get("team"),
            "is_pitcher": self.is_pitcher,
            "role": self.role,
            "batting_order": self.batting_order,
            "roster_status": self.roster_status,
            "season": self.season,
            "stamina": self.stamina,
            "composure": self.composure,
            "consistency": self.consistency,
            "release_consistency": self.release_consistency,
            "motion_bio": dict(self.motion_bio),
            "arm_slot": self.arm_slot,
            "arm_slot_angle_deg": self.arm_slot_angle_deg,
            "release_point_ft": dict(self.release_point_ft),
            "ratings": dict(self.ratings),
            "zones": dict(self.zones),
            "traits": list(self.traits),
            "vitals": dict(self.vitals),
            "stats": list(self.stats),
            "pitch_arsenal": list(self.pitch_arsenal),
            "arsenal": list(self.pitch_arsenal),
            "season_stats": dict(self.season_stats),
            "live_game_stats": dict(self.live_game_stats),
        }

    def get_pitch_fast(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Instant O(1) lookup by pitch ID (e.g. '4SFB') or name."""
        if not identifier:
            return None
        clean = str(identifier).strip()
        p = self._pitch_by_id.get(clean) or self._pitch_by_id.get(clean.upper())
        if p is not None:
            return p
        return self._pitch_by_name.get(clean.lower())

    def get_rating(self, category: str, default: float = 50.0) -> float:
        """
        Safely fetch a player attribute rating with fallback.
        Supports exact key, case-insensitive match, and Statcast key aliases
        (e.g. 'Velocity' <-> 'velocity_rating', 'Break' <-> 'break_rating').
        """
        if category in self.ratings:
            return float(self.ratings[category])

        clean_cat = category.lower().strip().replace(" ", "_")
        candidates = {
            clean_cat,
            f"{clean_cat}_rating",
            clean_cat.replace("_rating", ""),
        }
        if "strength" in clean_cat:
            candidates.add("arm_strength")

        for k, v in self.ratings.items():
            clean_k = k.lower().strip().replace(" ", "_")
            if clean_k in candidates:
                return float(v)

        return float(default)

    def has_trait(self, trait_name: str) -> bool:
        """Check if a player possesses a specific badge or trait."""
        return any(t.get("name") == trait_name for t in self.traits if isinstance(t, dict))

    def get_pitch(self, pitch_name: str) -> Optional[Dict[str, Any]]:
        """Fetch pitch details from the player's pitch arsenal by pitch name."""
        clean = pitch_name.lower().strip()
        for p in self.pitch_arsenal:
            if isinstance(p, dict):
                p_name = (p.get("pitch") or p.get("name") or "").lower().strip()
                if p_name == clean:
                    return p
        return None

    def __repr__(self) -> str:
        role = "Pitcher" if self.is_pitcher else "Batter"
        return f"<Player #{self.number} {self.name} ({self.position} - {role})>"