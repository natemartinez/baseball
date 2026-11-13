def test_pitch_objects_imports_and_backward_compatibility():
    # Primary home: pitcher_info
    from backend.engine.pitching_engine.pitcher_info.pitch_objects import (
        Pitch as PitchPI,
        PitchArsenal as PitchArsenalPI,
        PITCH_CATEGORIES as CATS_PI,
        movement_for as mf_pi,
    )
    # Legacy re-export: pitch_execution
    from backend.engine.pitching_engine.pitch_execution.pitch_objects import (
        Pitch as PitchPX,
        PitchArsenal as PitchArsenalPX,
        PITCH_CATEGORIES as CATS_PX,
        movement_for as mf_px,
    )
    from backend.engine.pitching_engine.pitch_execution import Pitch as PitchPkg, PitchArsenal as ArsenalPkg

    assert PitchPI is PitchPX is PitchPkg
    assert PitchArsenalPI is PitchArsenalPX is ArsenalPkg
    assert CATS_PI is CATS_PX
    assert mf_pi == mf_px
