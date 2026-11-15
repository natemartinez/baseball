try:
    from backend.engine.models.player import Player
except ImportError:
    from .player import Player

__all__ = ["Player"]
