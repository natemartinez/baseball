"""
Game Engine Configuration.

Centralizes environment flags and configuration parameters.
"""

import os


def swing_decision_telemetry_enabled() -> bool:
    """Returns True if SWING_DECISION_TELEMETRY flag is active."""
    env_val = os.environ.get('SWING_DECISION_TELEMETRY')
    if env_val is not None:
        return env_val.strip().lower() in ('1', 'true', 'on', 'yes')

    try:
        import backend.engine.game_engine.engine as engine_module
        if hasattr(engine_module, 'SWING_DECISION_TELEMETRY') and engine_module.SWING_DECISION_TELEMETRY is not None:
            return bool(engine_module.SWING_DECISION_TELEMETRY)
    except (ImportError, AttributeError):
        pass

    return False
