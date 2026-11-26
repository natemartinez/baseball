import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_SHOW_RESPONSIBILITY_RINGS,
  FIELDER_MESH_DIMENSIONS,
  FIELDER_MODEL_SCALE,
  shouldRenderResponsibilityRing,
} from '../FielderLayer';
import { CATCH_INDICATOR_DIMENSIONS } from '../CatchIndicator';
import {
  statcastToScene,
  computeFielderPursuit,
  getCatchVisualProfile,
  computeAllFielderPositions,
} from '../fielderKinematics';
import { DEFAULT_BATTED_BALL_RADIUS, type ActiveBattedBallData } from '../types';

describe('FielderLayer Animation Logic & Transitions', () => {
  it('correctly tracks active fielder target across ball lifecycle', () => {
    const ball: ActiveBattedBallData = {
      id: 'hit-test',
      hangTime: 3.2,
      samples: [[0, 0, 3, 0], [40, 280, 0, 3.2]],
      fielded: true,
      fielderId: 'RF',
      fieldingType: 'RUNNING_CATCH',
      fielderStart: [122.0, 268.0],
      interceptPoint: [40.0, 280.0, 4.2],
    };

    // At t=0: RF is at start position
    const atStart = computeFielderPursuit({
      startStatcast: ball.fielderStart!,
      targetStatcast: ball.interceptPoint!,
      elapsedTime: 0.0,
      totalDuration: ball.hangTime,
    });
    assert.deepEqual(atStart.currentScenePos, statcastToScene(122.0, 268.0, 0.0));
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
    assert.deepEqual(cf.scenePos, [0.0, 0.0, -335.0]);
    assert.equal(cf.isPursuing, false);
  });

  it('scales 3D fielder mesh dimensions proportionally without joint clipping', () => {
    assert.equal(FIELDER_MODEL_SCALE, 0.72);
    assert.equal(DEFAULT_SHOW_RESPONSIBILITY_RINGS, false);
    assert.equal(shouldRenderResponsibilityRing(), false);
    assert.equal(shouldRenderResponsibilityRing(false), false);
    assert.equal(shouldRenderResponsibilityRing(true), true);

    const { torso, head, visor, glove } = FIELDER_MESH_DIMENSIONS;
    assert.equal(torso.position[1], torso.height / 2);
    assert.ok(torso.radiusBottom < 0.7);
    const torsoTop = torso.height;
    const headBottom = head.position[1] - head.radius;
    assert.ok(headBottom >= torsoTop - 0.08 && headBottom <= torsoTop + 0.02);
    const scaledHeight = (head.position[1] + head.radius) * FIELDER_MODEL_SCALE;
    assert.ok(scaledHeight >= 3.8 && scaledHeight <= 4.3);
    assert.ok(torso.radiusBottom * 2 * FIELDER_MODEL_SCALE < 0.95);
    assert.ok(visor.position[2] < head.radius && visor.position[2] + visor.size[2] / 2 > head.radius);
    assert.ok(head.radius * FIELDER_MODEL_SCALE > DEFAULT_BATTED_BALL_RADIUS);
    assert.ok(glove.position[0] >= torso.radiusBottom - 0.05);
  });

  it('scales CatchIndicator rings and beacon to match compact fielders', () => {
    assert.equal(CATCH_INDICATOR_DIMENSIONS.ringInner, 2.0);
    assert.equal(CATCH_INDICATOR_DIMENSIONS.ringOuter, 2.6);
    assert.equal(CATCH_INDICATOR_DIMENSIONS.pulseInner, 2.6);
    assert.equal(CATCH_INDICATOR_DIMENSIONS.pulseOuter, 3.2);
    assert.equal(CATCH_INDICATOR_DIMENSIONS.beaconRadius, 0.4);
    assert.equal(CATCH_INDICATOR_DIMENSIONS.beaconY, 1.25);

    assert.ok(CATCH_INDICATOR_DIMENSIONS.ringInner > 0);
    assert.ok(CATCH_INDICATOR_DIMENSIONS.ringInner < CATCH_INDICATOR_DIMENSIONS.ringOuter);
    assert.ok(CATCH_INDICATOR_DIMENSIONS.ringOuter <= CATCH_INDICATOR_DIMENSIONS.pulseInner);
    assert.ok(CATCH_INDICATOR_DIMENSIONS.pulseInner < CATCH_INDICATOR_DIMENSIONS.pulseOuter);
    assert.ok(CATCH_INDICATOR_DIMENSIONS.beaconY - CATCH_INDICATOR_DIMENSIONS.beaconRadius > 0.5);
  });
});

