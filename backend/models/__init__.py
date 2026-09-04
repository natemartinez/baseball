try:
    from backend.models.player import Player
except ImportError:
    from .player import Player

__all__ = ["Player"]