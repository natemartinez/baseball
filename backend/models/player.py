from typing import Any, Optional


class Player:

    def __init__(
        self,
        name: str,
        number: str,
        field_rating: int = 50,
        handedness: Optional[str] = None,
        position: str = "DH",
        id: Optional[int] = None,
        ratings: Optional[dict[str, int]] = None,
        zones: Optional[dict[str, float]] = None,
        traits: Optional[list[dict[str, str]]] = None,
        vitals: Optional[dict[str, Any]] = None,
        stats: Optional[list[dict[str, Any]]] = None,
    ):
        self.id = id
        self.name = name
        self.number = str(number)
        self.field_rating = field_rating
        self.handedness = handedness
        self.position = position

        # Game engine attributes
        self.ratings = ratings or {}
        self.zones = zones or {}
        self.traits = traits or []
        self.vitals = vitals or {}
        self.stats = stats or []

    @classmethod
    def from_db(cls, raw: dict[str, Any]) -> "Player":
        """Factory method to hydrate a Player object from a database row dictionary."""
        vitals = raw.get("vitals", {})

        # Extract handedness if stored inside vitals, e.g., {"bats": "R", "throws": "R"}
        handedness = vitals.get("bats") or vitals.get("handedness")

        # Flatten ratings: [{'category': 'Power', 'rating': 99}] -> {'Power': 99}
        ratings_list = raw.get("ratings", [])
        ratings_map = (
            {r["category"]: r["rating"] for r in ratings_list}
            if isinstance(ratings_list, list)
            else ratings_list
        )

        # Flatten zones: [{'zone': 'heart', 'slugging': 0.82}] -> {'heart': 0.82}
        zones_list = raw.get("zones", [])
        zones_map = (
            {z["zone"]: z["slugging"] for z in zones_list}
            if isinstance(zones_list, list)
            else zones_list
        )

        # Pull fielding rating from ratings map if available, fallback to 50
        field_rating = ratings_map.get("Fielding", 50)

        return cls(
            id=raw.get("id"),
            name=raw.get("name", "Unknown"),
            number=raw.get("number", "00"),
            position=raw.get("position", "DH"),
            field_rating=field_rating,
            handedness=handedness,
            ratings=ratings_map,
            zones=zones_map,
            traits=raw.get("traits", []),
            vitals=vitals,
            stats=raw.get("stats", []),
        )

    def get_rating(self, category: str, default: int = 50) -> int:
        """Safely fetch a player attribute rating with a fallback."""
        return self.ratings.get(category, default)

    def has_trait(self, trait_name: str) -> bool:
        """Check if a player possesses a specific badge or trait."""
        return any(t.get("name") == trait_name for t in self.traits)

    def __repr__(self) -> str:
        return f"<Player #{self.number} {self.name} ({self.position})>"