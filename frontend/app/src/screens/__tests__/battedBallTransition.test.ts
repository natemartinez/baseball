import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { resolveGameCameraMode } from '../../components/camera/cameraShots';
import { isValidBattedBallTrace } from '../../services/battedBallValidation';
import type { GameCameraMode, ActiveBattedBallData } from '../../components/gamefield/types';
import type { BattedBallTelemetry } from '../../types/api';

/**
 * Pure state machine simulator replicating the exact React useEffect logic
 * from BaseballSimScreen for the batted-ball contact -> result hold -> next batter transition.
 */
class BattedBallLifecycleSimulator {
  pitchPhase: 'IDLE' | 'IN_FLIGHT' | 'RESOLVING' | 'REACTING' | 'BATTED_BALL' = 'IDLE';
  resultCameraHold: boolean = false;
  activeBattedBall: ActiveBattedBallData | null = null;
  debugCameraMode: GameCameraMode | null = null;
  manualCameraMode: GameCameraMode = 'PITCH';
  latestPitchBattedBall: BattedBallTelemetry | null = null;
  currentBatterName: string = 'Batter 1';

  // Timer tracking
  activeTimer: { callback: () => void; ms: number } | null = null;

  get cameraMode(): GameCameraMode {
    const hasPendingBattedBall = isValidBattedBallTrace(this.latestPitchBattedBall);
    const isGrounder =
      this.activeBattedBall?.isGrounder ??
      (this.latestPitchBattedBall
        ? Number.isFinite(this.latestPitchBattedBall.launch_angle_deg) &&
          (this.latestPitchBattedBall.launch_angle_deg <= 10.0 ||
            (Number.isFinite(this.latestPitchBattedBall.apex_height_ft) &&
              this.latestPitchBattedBall.apex_height_ft < 8.0))
        : false);

    return (
      this.debugCameraMode ??
      resolveGameCameraMode(
        this.pitchPhase,
        Boolean(
          this.activeBattedBall ||
            (this.pitchPhase === 'BATTED_BALL' && hasPendingBattedBall),
        ),
        this.resultCameraHold,
        this.manualCameraMode,
        true,
        isGrounder,
      )
    );
  }

  get isBattedBallCameraActive(): boolean {
    return this.cameraMode === 'TRACKING' || this.cameraMode === 'GROUNDER';
  }

  get isControlsDisabled(): boolean {
    return this.pitchPhase !== 'IDLE' || this.resultCameraHold;
  }

  get battingInputEnabled(): boolean {
    return this.cameraMode === 'PITCH' && !this.isBattedBallCameraActive;
  }

  get isBattingPracticeAutoPitchAllowed(): boolean {
    return this.pitchPhase === 'IDLE' && !this.resultCameraHold;
  }

  get battedBallTelemetry(): BattedBallTelemetry | null {
    if (this.pitchPhase === 'REACTING' || this.pitchPhase === 'BATTED_BALL') {
      return this.latestPitchBattedBall;
    }
    if (this.pitchPhase === 'IDLE' && (this.resultCameraHold || this.debugCameraMode !== null)) {
      return this.latestPitchBattedBall;
    }
    return null;
  }

  /**
   * Effect from BaseballSimScreen.tsx lines 462-469:
   * Handles the one-shot result hold after ball completes flight.
   */
  evaluateResultHoldEffect(hasBuggyActiveBattedBallGuard: boolean = false) {
    // If buggy: if (pitchPhase !== 'IDLE' || !resultCameraHold || activeBattedBall !== null) return;
    // If fixed: if (pitchPhase !== 'IDLE' || !resultCameraHold || debugCameraMode !== null) return;
    if (this.pitchPhase !== 'IDLE' || !this.resultCameraHold) {
      this.activeTimer = null;
      return;
    }

    if (hasBuggyActiveBattedBallGuard && this.activeBattedBall !== null) {
      // The bug: activeBattedBall is intentionally kept mounted through the hold,
      // so this condition causes an early return and NEVER schedules the timer!
      return;
    }

    if (!hasBuggyActiveBattedBallGuard && this.debugCameraMode !== null) {
      // Correct: Only debug hits prevent the game's auto-timer from running
      return;
    }

    this.activeTimer = {
      ms: 1600,
      callback: () => {
        this.resultCameraHold = false;
        this.activeBattedBall = null;
      },
    };
  }

  /** Fast-forwards the active timer */
  fireActiveTimer() {
    if (this.activeTimer) {
      const cb = this.activeTimer.callback;
      this.activeTimer = null;
      cb();
    }
  }
}

describe('Batted Ball Contact Result to Next Batter Transition', () => {
  const sampleTrace: BattedBallTelemetry = {
    exit_velocity_mph: 98.5,
    launch_angle_deg: 8.0,
    spray_angle_deg: 12.0,
    distance_ft: 180,
    apex_height_ft: 6.5,
    hang_time_s: 2.1,
    landing_x_ft: 40,
    landing_y_ft: 175,
    samples: [
      [0, 2.5, 0],
      [20, 4.0, -80],
      [40, 0, -175],
    ],
  };

  const sampleActiveBall: ActiveBattedBallData = {
    id: 'batted-1',
    hangTime: 2.1,
    samples: sampleTrace.samples,
    isGrounder: true,
    landingPos: [40, 0, -175],
    launchAngle: 8.0,
    apexHeight: 6.5,
    distance: 180,
  };

  it('demonstrates that the buggy guard freezes the game forever on contact result', () => {
    const sim = new BattedBallLifecycleSimulator();

    // 1. Ball in flight
    sim.pitchPhase = 'BATTED_BALL';
    sim.activeBattedBall = sampleActiveBall;
    sim.latestPitchBattedBall = sampleTrace;

    assert.equal(sim.cameraMode, 'GROUNDER');
    assert.equal(sim.isBattedBallCameraActive, true);
    assert.equal(sim.isControlsDisabled, true);

    // 2. Flight completes: handleBattedBallComplete sets hold & completeBattedBall sets IDLE
    sim.resultCameraHold = true;
    sim.pitchPhase = 'IDLE';
    sim.currentBatterName = 'Batter 2 (Next)'; // revealPitch updated gameState

    // 3. Evaluate buggy effect
    sim.evaluateResultHoldEffect(true);

    // With the bug, NO timer was scheduled because activeBattedBall !== null!
    assert.equal(sim.activeTimer, null);

    // Game is permanently stuck:
    assert.equal(sim.cameraMode, 'GROUNDER'); // Stuck on grounder camera forever!
    assert.equal(sim.isBattedBallCameraActive, true);
    assert.equal(sim.isControlsDisabled, true); // Pitch controls locked forever!
    assert.equal(sim.battingInputEnabled, false); // Batter controls disabled forever!
    assert.equal(sim.isBattingPracticeAutoPitchAllowed, false); // Practice auto-feed stalled forever!
  });

  it('successfully transitions from contact result to next batter with the fix', () => {
    const sim = new BattedBallLifecycleSimulator();

    // 1. Ball in flight
    sim.pitchPhase = 'BATTED_BALL';
    sim.activeBattedBall = sampleActiveBall;
    sim.latestPitchBattedBall = sampleTrace;

    assert.equal(sim.cameraMode, 'GROUNDER');
    assert.equal(sim.isBattedBallCameraActive, true);
    assert.equal(sim.isControlsDisabled, true);

    // 2. Flight completes: handleBattedBallComplete sets hold & completeBattedBall sets IDLE
    sim.resultCameraHold = true;
    sim.pitchPhase = 'IDLE';
    sim.currentBatterName = 'Batter 2 (Next)'; // revealPitch updated gameState

    // 3. Evaluate fixed effect
    sim.evaluateResultHoldEffect(false);

    // Timer is scheduled for RESULT_CAMERA_HOLD_MS (1600ms)
    assert.notEqual(sim.activeTimer, null);
    assert.equal(sim.activeTimer?.ms, 1600);

    // During the 1600ms hold, camera and metrics stay on the landing ball
    assert.equal(sim.cameraMode, 'GROUNDER');
    assert.equal(sim.isBattedBallCameraActive, true);
    assert.notEqual(sim.battedBallTelemetry, null);
    assert.equal(sim.isControlsDisabled, true);

    // 4. Timer fires after 1600ms
    sim.fireActiveTimer();

    // Verification of next batter transition:
    assert.equal(sim.resultCameraHold, false);
    assert.equal(sim.activeBattedBall, null);
    assert.equal(sim.cameraMode, 'PITCH'); // Camera snaps back to home plate / batter view!
    assert.equal(sim.isBattedBallCameraActive, false);
    assert.equal(sim.battedBallTelemetry, null); // Metrics card dismisses!
    assert.equal(sim.isControlsDisabled, false); // Controls unlocked!
    assert.equal(sim.battingInputEnabled, true); // Batting controls ready for next batter!
    assert.equal(sim.isBattingPracticeAutoPitchAllowed, true); // Practice auto-feed ready to pitch!
    assert.equal(sim.currentBatterName, 'Batter 2 (Next)'); // New batter ready!
  });

  it('preserves debug hit launcher autonomy when debugCameraMode is active', () => {
    const sim = new BattedBallLifecycleSimulator();

    // Debug hit launched from HitTestLauncher
    sim.pitchPhase = 'IDLE';
    sim.resultCameraHold = true;
    sim.activeBattedBall = sampleActiveBall;
    sim.debugCameraMode = 'GROUNDER'; // Debug mode overrides camera

    sim.evaluateResultHoldEffect(false);

    // Game timer must NOT be scheduled during debug hit test
    assert.equal(sim.activeTimer, null);
    assert.equal(sim.cameraMode, 'GROUNDER');
  });

  describe('isValidBattedBallTrace validation', () => {
    it('validates traces with 4-element samples [x, y, z, t] from aerodynamic flight', () => {
      const flightTrace4: BattedBallTelemetry = {
        exit_velocity_mph: 104.5,
        launch_angle_deg: 28.0,
        spray_angle_deg: -8.0,
        distance_ft: 405,
        apex_height_ft: 92.0,
        hang_time_s: 4.85,
        landing_x_ft: -56.3,
        landing_y_ft: 401.0,
        sample_count: 3,
        samples: [
          [0.0, 0.0, 3.0, 0.0],
          [-28.1, 200.5, 92.0, 2.42],
          [-56.3, 401.0, 0.0, 4.85],
        ],
        model_version: 'v2',
      };
      assert.equal(isValidBattedBallTrace(flightTrace4), true);
    });

    it('validates traces with 3-element samples [x, y, z] from fielded grounders', () => {
      const grounderTrace3: BattedBallTelemetry = {
        exit_velocity_mph: 92.0,
        launch_angle_deg: 4.0,
        spray_angle_deg: 15.0,
        distance_ft: 110,
        apex_height_ft: 4.0,
        hang_time_s: 1.1,
        landing_x_ft: 28.5,
        landing_y_ft: 106.2,
        sample_count: 2,
        samples: [
          [0.0, 0.0, 2.5],
          [28.5, 106.2, 0.0],
        ],
        model_version: 'v2',
      };
      assert.equal(isValidBattedBallTrace(grounderTrace3), true);
    });

    it('validates foul ball traces carrying 4-element aerodynamic samples', () => {
      const foulTrace: BattedBallTelemetry = {
        exit_velocity_mph: 94.0,
        launch_angle_deg: 24.0,
        spray_angle_deg: 58.0,
        distance_ft: 280,
        apex_height_ft: 65.0,
        hang_time_s: 3.8,
        landing_x_ft: 237.4,
        landing_y_ft: 148.4,
        sample_count: 3,
        samples: [
          [0.0, 0.0, 3.0, 0.0],
          [118.7, 74.2, 65.0, 1.9],
          [237.4, 148.4, 0.0, 3.8],
        ],
        model_version: 'v2',
      };
      assert.equal(isValidBattedBallTrace(foulTrace), true);
    });

    it('rejects malformed traces with invalid dimensions or non-finite numbers', () => {
      assert.equal(isValidBattedBallTrace(null), false);
      assert.equal(isValidBattedBallTrace({}), false);
      assert.equal(isValidBattedBallTrace({ hang_time_s: NaN, samples: [[0, 0, 0]] }), false);
      assert.equal(isValidBattedBallTrace({ hang_time_s: 2.0, samples: [[0, 0]] }), false);
      assert.equal(isValidBattedBallTrace({ hang_time_s: 2.0, samples: [[0, 0, 0, 0, 0]] }), false);
      assert.equal(isValidBattedBallTrace({ hang_time_s: 2.0, samples: [[0, 0, NaN]] }), false);
    });
  });

  describe('Full Pitch-to-Tracking camera lifecycle transitions', () => {
    it('seamlessly transitions airborne in-play balls from PITCH camera to TRACKING and holds result', () => {
      const sim = new BattedBallLifecycleSimulator();
      const airTrace4: BattedBallTelemetry = {
        exit_velocity_mph: 102.0,
        launch_angle_deg: 26.0,
        spray_angle_deg: -5.0,
        distance_ft: 380,
        apex_height_ft: 85.0,
        hang_time_s: 4.5,
        landing_x_ft: -33.1,
        landing_y_ft: 378.5,
        sample_count: 3,
        samples: [
          [0.0, 0.0, 3.0, 0.0],
          [-16.5, 189.0, 85.0, 2.25],
          [-33.1, 378.5, 0.0, 4.5],
        ],
        model_version: 'v2',
      };

      // 1. Contact impact moment in REACTING beat
      sim.pitchPhase = 'REACTING';
      sim.latestPitchBattedBall = airTrace4;
      assert.equal(sim.cameraMode, 'PITCH'); // Behind plate view to see bat strike ball

      // 2. 160ms contact follow-through ends, handed off to BATTED_BALL
      sim.pitchPhase = 'BATTED_BALL';
      // Even before activeBattedBall state finishes setting, cameraMode immediately knows it's TRACKING
      assert.equal(sim.cameraMode, 'TRACKING');

      // 3. activeBattedBall mounts in scene
      sim.activeBattedBall = {
        id: 'batted-fly-1',
        hangTime: airTrace4.hang_time_s,
        samples: airTrace4.samples,
        isGrounder: false,
        landingPos: [-33.1, 0, -378.5],
        launchAngle: 26.0,
        apexHeight: 85.0,
        distance: 380,
      };
      assert.equal(sim.cameraMode, 'TRACKING');
      assert.equal(sim.isBattedBallCameraActive, true);

      // 4. Ball lands: handleBattedBallComplete engages result hold and store sets IDLE
      sim.resultCameraHold = true;
      sim.pitchPhase = 'IDLE';
      sim.currentBatterName = 'Batter 2 (Next)';
      sim.evaluateResultHoldEffect(false);

      // Camera holds on landed ball in TRACKING
      assert.equal(sim.cameraMode, 'TRACKING');
      assert.notEqual(sim.activeTimer, null);

      // 5. Result hold completes after 1600ms
      sim.fireActiveTimer();
      assert.equal(sim.cameraMode, 'PITCH');
      assert.equal(sim.isBattedBallCameraActive, false);
      assert.equal(sim.battingInputEnabled, true);
      assert.equal(sim.currentBatterName, 'Batter 2 (Next)');
    });

    it('smoothly tracks foul balls into foul territory and returns to PITCH camera for same batter', () => {
      const sim = new BattedBallLifecycleSimulator();
      const foulTrace: BattedBallTelemetry = {
        exit_velocity_mph: 91.0,
        launch_angle_deg: 22.0,
        spray_angle_deg: 54.0,
        distance_ft: 260,
        apex_height_ft: 58.0,
        hang_time_s: 3.4,
        landing_x_ft: 210.3,
        landing_y_ft: 152.8,
        sample_count: 3,
        samples: [
          [0.0, 0.0, 3.0, 0.0],
          [105.1, 76.4, 58.0, 1.7],
          [210.3, 152.8, 0.0, 3.4],
        ],
        model_version: 'v2',
      };

      // 1. Batter fouls the ball off
      sim.pitchPhase = 'REACTING';
      sim.latestPitchBattedBall = foulTrace;
      assert.equal(sim.cameraMode, 'PITCH');

      // 2. Hand off to BATTED_BALL
      sim.pitchPhase = 'BATTED_BALL';
      assert.equal(sim.cameraMode, 'TRACKING');

      // 3. Mount active ball data
      sim.activeBattedBall = {
        id: 'batted-foul-1',
        hangTime: foulTrace.hang_time_s,
        samples: foulTrace.samples,
        isGrounder: false,
        landingPos: [210.3, 0, -152.8],
        launchAngle: 22.0,
        apexHeight: 58.0,
        distance: 260,
      };
      assert.equal(sim.cameraMode, 'TRACKING');

      // 4. Ball lands in foul territory: hold camera on landing spot
      sim.resultCameraHold = true;
      sim.pitchPhase = 'IDLE';
      sim.currentBatterName = 'Batter 1'; // Same batter because it is a foul!
      sim.evaluateResultHoldEffect(false);

      assert.equal(sim.cameraMode, 'TRACKING');
      assert.notEqual(sim.activeTimer, null);

      // 5. Hold expires: return to PITCH view for same batter
      sim.fireActiveTimer();
      assert.equal(sim.cameraMode, 'PITCH');
      assert.equal(sim.isBattedBallCameraActive, false);
      assert.equal(sim.currentBatterName, 'Batter 1'); // Still Batter 1 at the plate
      assert.equal(sim.battingInputEnabled, true);
    });
  });
});

