import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { HIT_PRESETS, buildActiveBattedBallFromPreset } from '../../debug/hitPresets';
import { computeAllFielderPositions, statcastToScene } from '../fielderKinematics';

describe('FieldScene & Hit Presets End-to-End Choreography Wiring', () => {
  it('wires all hit presets into dynamic fielder pursuit models without errors', () => {
    for (const preset of HIT_PRESETS) {
      const activeBall = buildActiveBattedBallFromPreset(preset, 100);

      // Verify at t = 0
      const startPositions = computeAllFielderPositions({
        activeFielderId: activeBall.fielderId,
        activeStartStatcast: activeBall.fielderStart,
        activeTargetStatcast: activeBall.interceptPoint,
        elapsedTime: 0.0,
        totalDuration: activeBall.hangTime,
      });

      assert.equal(startPositions.size, 8);

      if (activeBall.fielderId && activeBall.fielderStart) {
        const activeFielder = startPositions.get(activeBall.fielderId);
        assert.ok(activeFielder);
        assert.deepEqual(
          activeFielder.scenePos,
          statcastToScene(activeBall.fielderStart[0], activeBall.fielderStart[1], 0.0),
        );
      }

      // Verify at t = hangTime
      const endPositions = computeAllFielderPositions({
        activeFielderId: activeBall.fielderId,
        activeStartStatcast: activeBall.fielderStart,
        activeTargetStatcast: activeBall.interceptPoint,
        elapsedTime: activeBall.hangTime,
        totalDuration: activeBall.hangTime,
      });

      assert.equal(endPositions.size, 8);

      if (activeBall.fielderId && activeBall.interceptPoint) {
        const activeFielder = endPositions.get(activeBall.fielderId);
        assert.ok(activeFielder);
        assert.equal(activeFielder.isArrived, true);
        assert.deepEqual(
          activeFielder.scenePos,
          statcastToScene(activeBall.interceptPoint[0], activeBall.interceptPoint[1], 0.0),
        );
      }
    }
  });
});

