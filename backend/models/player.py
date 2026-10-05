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
    ):
        self.id = id
        self.name = name
        self.number = str(number)
        self.field_rating = int(field_rating)
        self.handedness = handedness
        self.position = position

        # Normalized game engine attributes
        self.ratings: Dict[str, float] = ratings or {}
        self.zones: Dict[str, float] = zones or {}
        self.traits: List[Dict[str, Any]] = traits or []
        self.vitals: Dict[str, Any] = vitals or {}
        self.stats: List[Dict[str, Any]] = stats or []
        self.pitch_arsenal: List[Dict[str, Any]] = pitch_arsenal or []

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

        # Extract handedness from vitals or direct fields
        handedness = (
            raw.get("handedness")
            or vitals.get("bats")
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
        zones_raw = raw.get("zones") or {}
        zones_map: Dict[str, float] = {}
        if isinstance(zones_raw, list):
            for z in zones_raw:
                if isinstance(z, dict) and "zone" in z:
                    zones_map[z["zone"]] = float(z.get("slugging", 0.300))
        elif isinstance(zones_raw, dict):
            zones_map = {k: float(v) for k, v in zones_raw.items()}

        # 3. Resolve fielding rating
        field_rating = int(raw.get("field_rating") or ratings_map.get("Fielding", 50))

        # 4. Extract arsenal
        arsenal = raw.get("pitch_arsenal") or raw.get("arsenal") or []
        if not isinstance(arsenal, list):
            arsenal = []

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
            "position": self.position,
            "field_rating": self.field_rating,
            "handedness": self.handedness,
            "is_pitcher": self.is_pitcher,
            "ratings": dict(self.ratings),
            "zones": dict(self.zones),
            "traits": list(self.traits),
            "vitals": dict(self.vitals),
            "stats": list(self.stats),
            "pitch_arsenal": list(self.pitch_arsenal),
        }

    def get_rating(self, category: str, default: float = 50.0) -> float:
        """
        Safely fetch a player attribute rating (case-insensitive key lookup)
        with fallback.
        """
        if category in self.ratings:
            return float(self.ratings[category])
        for k, v in self.ratings.items():
            if k.lower() == category.lower():
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