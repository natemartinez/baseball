import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type { BattedBallTelemetry } from '../api';
import type { ActiveBattedBallData } from '../../components/gamefield/types';

describe('Fielding Telemetry Type Contract', () => {
  it('accepts enriched backend fielding telemetry', () => {
    const rawTrace: BattedBallTelemetry = {
      exit_velocity_mph: 98.4,
      launch_angle_deg: 16.5,
      spray_angle_deg: -18.2,
      hang_time_s: 3.42,
      apex_height_ft: 32.1,
      distance_ft: 268.4,
      landing_x_ft: -83.7,
      landing_y_ft: 255.0,
      sample_count: 20,
      samples: [
        [0.0, 0.0, 3.0, 0.0],
        [-83.7, 255.0, 0.0, 3.42],
      ],
      fielded: true,
      fielder_id: 'LF',
      fielder_name: 'Alex Verdugo',
      fielding_type: 'GROUND_SCOOP',
      fielder_start: [-115.0, 255.0],
      intercept_point: [-83.7, 255.0, 0.0],
      model_version: 'calibrated-projectile-v1',
    };

    assert.equal(rawTrace.fielded, true);
    assert.equal(rawTrace.fielder_id, 'LF');
    assert.equal(rawTrace.fielding_type, 'GROUND_SCOOP');
    assert.deepEqual(rawTrace.fielder_start, [-115.0, 255.0]);
    assert.deepEqual(rawTrace.intercept_point, [-83.7, 255.0, 0.0]);
  });

  it('maps raw telemetry to ActiveBattedBallData with camelCase properties', () => {
    const rawTrace: BattedBallTelemetry = {
      exit_velocity_mph: 102.0,
      launch_angle_deg: 24.0,
      spray_angle_deg: 0.0,
      hang_time_s: 3.85,
      apex_height_ft: 45.0,
      distance_ft: 325.0,
      landing_x_ft: 0.0,
      landing_y_ft: 325.0,
      sample_count: 20,
      samples: [[0, 0, 3, 0], [0, 325, 3.5, 3.85]],
      fielded: true,
      fielder_id: 'CF',
      fielder_name: 'Aaron Judge',
      fielding_type: 'ROUTINE_FLY_CATCH',
      fielder_start: [0.0, 330.0],
      intercept_point: [0.0, 325.0, 3.5],
      model_version: 'calibrated-projectile-v1',
    };

    const activeBall: ActiveBattedBallData = {
      id: 'batted-1',
      hangTime: rawTrace.hang_time_s,
      samples: rawTrace.samples,
      landingPos: [rawTrace.landing_x_ft, 0, -rawTrace.landing_y_ft],
      fielded: rawTrace.fielded,
      fielderId: rawTrace.fielder_id,
      fielderName: rawTrace.fielder_name,
      fieldingType: rawTrace.fielding_type,
      fielderStart: rawTrace.fielder_start,
      interceptPoint: rawTrace.intercept_point,
    };

    assert.equal(activeBall.fielded, true);
    assert.equal(activeBall.fielderId, 'CF');
    assert.equal(activeBall.fieldingType, 'ROUTINE_FLY_CATCH');
    assert.deepEqual(activeBall.fielderStart, [0.0, 330.0]);
    assert.deepEqual(activeBall.interceptPoint, [0.0, 325.0, 3.5]);
  });
});

