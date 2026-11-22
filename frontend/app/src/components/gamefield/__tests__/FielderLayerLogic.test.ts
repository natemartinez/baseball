import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  statcastToScene,
  computeFielderPursuit,
  getCatchVisualProfile,
  computeAllFielderPositions,
} from '../fielderKinematics';
import type { ActiveBattedBallData } from '../types';

describe('FielderLayer Animation Logic & Transitions', () => {
  it('correctly tracks active fielder target across ball lifecycle', () => {
    const ball: ActiveBattedBallData = {
      id: 'hit-test',
      hangTime: 3.2,
      samples: [[0, 0, 3, 0], [40, 280, 0, 3.2]],
      fielded: true,
      fielderId: 'RF',
      fieldingType: 'RUNNING_CATCH',
      fielderStart: [115.0, 255.0],
      interceptPoint: [40.0, 280.0, 4.2],
    };

    // At t=0: RF is at start position
    const atStart = computeFielderPursuit({
      startStatcast: ball.fielderStart!,
      targetStatcast: ball.interceptPoint!,
      elapsedTime: 0.0,
      totalDuration: ball.hangTime,
    });
    assert.deepEqual(atStart.currentScenePos, statcastToScene(115.0, 255.0, 0.0));
    assert.equal(atStart.isArrived, false);

    // At t=3.2: RF has arrived at intercept point
    const atEnd = computeFielderPursuit({
      startStatcast: ball.fielderStart!,
      targetStatcast: ball.interceptPoint!,
      elapsedTime: 3.2,
      totalDuration: ball.hangTime,
    });
    assert.deepEqual(atEnd.currentScenePos, statcastToScene(40.0, 280.0, 0.0));
    assert.equal(atEnd.isArrived, true);
  });

  it('suppresses catch indicator when ball is unfielded', () => {
    const unfieldedBall: ActiveBattedBallData = {
      id: 'gap-double',
      hangTime: 4.5,
      samples: [[0, 0, 3, 0], [80, 310, 0, 4.5]],
      fielded: false,
      fielderId: null,
      fieldingType: 'UNFIELDED',
    };

    const profile = getCatchVisualProfile(unfieldedBall.fieldingType);
    assert.equal(profile.isCaught, false);
    assert.equal(profile.showRing, false);
  });

  it('handles seamless return transition to baseline positions when ball is null', () => {
    // When ball clears, fielders should be computed at baseline
    const positions = computeAllFielderPositions({
      activeFielderId: null,
      activeStartStatcast: null,
      activeTargetStatcast: null,
      elapsedTime: 0.0,
      totalDuration: 1.0,
    });

    assert.equal(positions.size, 8);
    const cf = positions.get('CF');
    assert.ok(cf);
    assert.deepEqual(cf.scenePos, [0.0, 0.0, -330.0]);
    assert.equal(cf.isPursuing, false);
  });
});

