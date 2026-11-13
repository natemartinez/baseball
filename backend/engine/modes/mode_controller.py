"""
Game Mode Controller.

Manages top-level game execution modes (NORMAL vs. PRACTICE) and provides
an FSM transition interface driven by the client or routes.
"""

from enum import Enum
from typing import Any, Dict, Optional


class GameMode(str, Enum):
    NORMAL = 'NORMAL'
    PRACTICE = 'PRACTICE'


class ModeController:
    """Coordinates active game mode and delegates mode-specific drill execution."""

    def __init__(self, engine: Any):
        self.engine = engine
        self._active_mode: GameMode = GameMode.NORMAL
        self._practice_controller: Optional[Any] = None

    @property
    def active_mode(self) -> GameMode:
        return self._active_mode

    @property
    def practice_controller(self) -> Any:
        if self._practice_controller is None:
            from backend.engine.modes.practice_mode import PracticeModeController
            self._practice_controller = PracticeModeController(self.engine)
        return self._practice_controller

    @property
    def is_practice_active(self) -> bool:
        if self._active_mode != GameMode.PRACTICE:
            return False
        return bool(self.practice_controller.is_active)

    def set_mode(self, mode: str | GameMode) -> Dict[str, Any]:
        """Switches game execution mode and executes snapshot/restore lifecycles."""
        target_mode = GameMode(str(mode).upper())
        if target_mode == self._active_mode:
            return self.engine.get_game_state_payload()

        if target_mode == GameMode.PRACTICE:
            state = self.practice_controller.start()
            self._active_mode = GameMode.PRACTICE
            return state
        elif target_mode == GameMode.NORMAL:
            state = self.practice_controller.end()
            self._active_mode = GameMode.NORMAL
            return state

        return self.engine.get_game_state_payload()

    def start(self) -> Dict[str, Any]:
        """Convenience alias for set_mode(PRACTICE)."""
        return self.set_mode(GameMode.PRACTICE)

    def end(self) -> Dict[str, Any]:
        """Convenience alias for set_mode(NORMAL)."""
        return self.set_mode(GameMode.NORMAL)

    def throw_pitch(
        self,
        pitch_type: Optional[str] = None,
        target_zone: Optional[str] = None,
        custom_target: Optional[Dict[str, float]] = None,
        pitch_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Routes a drill pitch throw to the practice controller."""
        return self.practice_controller.throw_pitch(
            pitch_type=pitch_type,
            target_zone=target_zone,
            custom_target=custom_target,
            pitch_name=pitch_name,
        )

    def resolve_pitch(
        self,
        batter_approach: str = 'AUTO',
        batter_decision: Optional[str] = None,
        contact: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Routes a drill pitch resolution to the practice controller."""
        return self.practice_controller.resolve_pitch(
            batter_approach=batter_approach,
            batter_decision=batter_decision,
            contact=contact,
        )

