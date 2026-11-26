import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';

import { fenceDistance, getFencePoint } from '../fieldGeometry';
import {
  MARKER_BORDER_COLOR,
  MARKER_ELEVATION,
  MARKER_TEXT_COLOR,
  WALL_DISTANCE_MARKERS,
  WallDistanceMarkers,
  createDistanceMarkerNumeralGeometry,
} from '../WallDistanceMarkers';

describe('WallDistanceMarkers Specification', () => {
  it('defines 5 standard distance signs along the fence perimeter', () => {
    assert.equal(WALL_DISTANCE_MARKERS.length, 5);
    assert.deepEqual(
      WALL_DISTANCE_MARKERS.map((m) => m.text),
      ['350', '385', '420', '385', '350'],
    );
    assert.deepEqual(
      WALL_DISTANCE_MARKERS.map((m) => m.sprayAngle),
      [-45, -22.5, 0, 22.5, 45],
    );
  });

  it('mounts markers at eye level on the inner face of the 8 ft wall', () => {
    assert.equal(MARKER_ELEVATION, 4.5);
    for (const marker of WALL_DISTANCE_MARKERS) {
      assert.equal(marker.y, 4.5);
      assert.equal(marker.position[1], 4.5);
    }
  });

  it('derives marker coordinates from getFencePoint with inward offset (-0.05 ft)', () => {
    for (const marker of WALL_DISTANCE_MARKERS) {
      const expectedPt = getFencePoint(marker.sprayAngle, -0.05);
      assert.ok(
        Math.abs(marker.position[0] - expectedPt[0]) < 1e-6,
        `X mismatch for ${marker.text}`,
      );
      assert.ok(
        Math.abs(marker.position[2] - expectedPt[2]) < 1e-6,
        `Z mismatch for ${marker.text}`,
      );

      const rExpected = fenceDistance(marker.sprayAngle) - 0.05;
      const rActual = Math.hypot(marker.position[0], marker.position[2]);
      assert.ok(
        Math.abs(rActual - rExpected) < 1e-5,
        `Radius mismatch for ${marker.text}: expected ${rExpected}, got ${rActual}`,
      );
    }

    // Explicit distance checks
    // Center field (0 deg) -> 420 - 0.05 = 419.95 ft
    const cf = WALL_DISTANCE_MARKERS[2];
    assert.equal(cf.text, '420');
    assert.equal(cf.position[0], 0);
    assert.equal(cf.position[2], -419.95);

    // Foul lines (+/- 45 deg) -> 350 - 0.05 = 349.95 ft
    const lf = WALL_DISTANCE_MARKERS[0];
    const rf = WALL_DISTANCE_MARKERS[4];
    assert.ok(Math.abs(Math.hypot(lf.position[0], lf.position[2]) - 349.95) < 1e-5);
    assert.ok(Math.abs(Math.hypot(rf.position[0], rf.position[2]) - 349.95) < 1e-5);

    // Gaps (+/- 22.5 deg) -> 385 - 0.05 = 384.95 ft
    const lcf = WALL_DISTANCE_MARKERS[1];
    const rcf = WALL_DISTANCE_MARKERS[3];
    assert.ok(Math.abs(Math.hypot(lcf.position[0], lcf.position[2]) - 384.95) < 1e-5);
    assert.ok(Math.abs(Math.hypot(rcf.position[0], rcf.position[2]) - 384.95) < 1e-5);
  });

  it('aligns marker rotation to face home plate along wall tangent', () => {
    for (const marker of WALL_DISTANCE_MARKERS) {
      const expectedRotY = -(marker.sprayAngle * Math.PI) / 180;
      assert.equal(marker.rotation[0], 0);
      assert.ok(
        Math.abs(marker.rotation[1] - expectedRotY) < 1e-6,
        `Rotation Y mismatch for angle ${marker.sprayAngle}`,
      );
      assert.equal(marker.rotation[2], 0);
    }
  });

  it('renders WallDistanceMarkers component with 5 marker groups', () => {
    const element = WallDistanceMarkers();
    assert.ok(element, 'WallDistanceMarkers must return a valid React element');
    assert.equal(element.type, 'group');

    const children = React.Children.toArray(element.props.children) as React.ReactElement[];
    assert.equal(children.length, 5, 'Must contain 5 marker elements');

    for (let i = 0; i < 5; i++) {
      const markerGroup = children[i];
      const spec = WALL_DISTANCE_MARKERS[i];
      assert.deepEqual(markerGroup.props.position, spec.position);
      assert.deepEqual(markerGroup.props.rotation, spec.rotation);

      const meshes = React.Children.toArray(markerGroup.props.children) as React.ReactElement[];
      assert.ok(meshes.length >= 1, 'Marker group must contain visual meshes');

      // Verify backing frame has gold accent color
      const frameMesh = meshes[0];
      const frameMat = frameMesh.props.children?.find(
        (c: React.ReactElement) => c?.type === 'meshStandardMaterial',
      );
      assert.ok(frameMat, 'Backing frame must have meshStandardMaterial');
      assert.equal(frameMat.props.color, MARKER_BORDER_COLOR);

      // Verify 3rd mesh has 3D vector numeral geometry with white text color
      const numeralMesh = meshes[2];
      assert.ok(numeralMesh, 'Marker group must contain 3D vector numeral mesh');
      assert.ok(numeralMesh.props.geometry, 'Numeral mesh must have procedural BufferGeometry');
      const numeralChildren = React.Children.toArray(numeralMesh.props.children);
      const numeralMat = numeralChildren.find(
        (c: any) => c?.type === 'meshStandardMaterial',
      ) as React.ReactElement;
      assert.ok(numeralMat, 'Numeral mesh must have meshStandardMaterial');
      assert.equal(numeralMat.props.color, MARKER_TEXT_COLOR);
    }
  });

  it('generates valid 3D procedural numeral geometries for 350, 385, and 420', () => {
    for (const text of ['350', '385', '420']) {
      const geom = createDistanceMarkerNumeralGeometry(text);
      assert.ok(geom.attributes.position, `Position attribute must exist for ${text}`);
      assert.ok(geom.attributes.position.count > 0, `Vertices must exist for ${text}`);
      assert.ok(geom.attributes.normal, `Normal attribute must exist for ${text}`);
      assert.ok(geom.index, `Index buffer must exist for ${text}`);
      assert.ok(geom.boundingBox, `Bounding box must be computed for ${text}`);

      // Fits within the 3.0 x 1.4 ft inner badge boundaries
      const bbox = geom.boundingBox!;
      const width = bbox.max.x - bbox.min.x;
      const height = bbox.max.y - bbox.min.y;
      assert.ok(width <= 3.0, `Width ${width} must fit inside 3.0 ft badge for ${text}`);
      assert.ok(height <= 1.4, `Height ${height} must fit inside 1.4 ft badge for ${text}`);
    }
    assert.equal(createDistanceMarkerNumeralGeometry('8').attributes.position.count, 7 * 4);
    assert.equal(createDistanceMarkerNumeralGeometry('2').attributes.position.count, 5 * 4);
  });
});
