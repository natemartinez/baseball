"""
Batter Statistics Tracking.

Tracks in-game per-batter box score stats: at_bats, hits, rbis, home_runs.
"""

from typing import Any, Dict, Optional


class BatterStatsTracker:
    """Manages live per-batter game statistics."""

    def __init__(self, initial_stats: Optional[Dict[str, Dict[str, int]]] = None):
        self._stats: Dict[str, Dict[str, int]] = {}
        if initial_stats:
            for k, v in initial_stats.items():
                self._stats[k] = dict(v)

    @staticmethod
    def stats_key(batter: Any) -> str:
        """Produces unique identification key for a batter."""
        if isinstance(batter, dict):
            batter_id = batter.get('id')
            batter_name = batter.get('name', '')
        else:
            batter_id = getattr(batter, 'id', None) if batter is not None else None
            batter_name = getattr(batter, 'name', '') if batter is not None else ''
        return f'{batter_id if batter_id is not None else 0}:{batter_name}'

    def get_line(self, batter: Any) -> Dict[str, int]:
        """Returns or creates the mutable in-game batting line for a batter."""
        key = self.stats_key(batter)
        return self._stats.setdefault(
            key, {'at_bats': 0, 'hits': 0, 'rbis': 0, 'home_runs': 0}
        )

    def all_stats(self) -> Dict[str, Dict[str, int]]:
        """Returns internal stats dictionary."""
        return self._stats

    def copy(self) -> Dict[str, Dict[str, int]]:
        """Returns a deep copy of all tracked stats."""
        return {key: dict(value) for key, value in self._stats.items()}
