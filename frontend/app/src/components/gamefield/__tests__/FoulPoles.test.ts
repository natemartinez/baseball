import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';

import {
  FOUL_POLE_HEIGHT,
  FOUL_POLE_LEFT_POS,
  FOUL_POLE_RADIUS,
  FOUL_POLE_RIGHT_POS,
} from '../fieldGeometry';
import {
  FOUL_POLE_COLOR,
  FOUL_POLE_WING_HEIGHT,
  FOUL_POLE_WING_THICKNESS,
  FOUL_POLE_WING_WIDTH,
  FoulPoles,
} from '../FoulPoles';

describe('FoulPoles Component Specification', () => {
  it('anchors left and right foul pole coordinates at 350 ft fence intersections', () => {
    assert.ok(Math.abs(Math.hypot(FOUL_POLE_LEFT_POS[0], FOUL_POLE_LEFT_POS[2]) - 350.0) < 0.2);
    assert.ok(Math.abs(Math.hypot(FOUL_POLE_RIGHT_POS[0], FOUL_POLE_RIGHT_POS[2]) - 350.0) < 0.2);
  });

  it('specifies 32 ft elevation with gold material color', () => {
    assert.equal(FOUL_POLE_HEIGHT, 32.0);
    assert.equal(FOUL_POLE_COLOR, '#FFD700');
    assert.equal(FOUL_POLE_RADIUS, 0.4);
    assert.equal(FOUL_POLE_WING_WIDTH, 2.5);
    assert.equal(FOUL_POLE_WING_HEIGHT, 24.0);
    assert.equal(FOUL_POLE_WING_THICKNESS, 0.05);
  });

  it('renders FoulPoles component tree with left and right pole groups', () => {
    const element = FoulPoles();
    assert.ok(element, 'FoulPoles must return a valid React element');
    assert.equal(element.type, 'group');

    const children = React.Children.toArray(element.props.children) as React.ReactElement[];
    assert.equal(children.length, 2, 'Expected left and right foul pole groups');

    const leftGroup = children[0];
    const rightGroup = children[1];

    assert.deepEqual(leftGroup.props.position, FOUL_POLE_LEFT_POS);
    assert.deepEqual(rightGroup.props.position, FOUL_POLE_RIGHT_POS);
  });

  it('configures regulation cylinder geometry and fair-territory screen wings', () => {
    const element = FoulPoles();
    const [leftGroup, rightGroup] = React.Children.toArray(element.props.children) as React.ReactElement[];

    for (const group of [leftGroup, rightGroup]) {
      const meshes = React.Children.toArray(group.props.children) as React.ReactElement[];
      assert.equal(meshes.length, 2, 'Each pole group must contain main pole mesh and screen wing mesh');

      const [poleMesh, wingMesh] = meshes;

      // Verify Main Pole
      assert.deepEqual(poleMesh.props.position, [0, FOUL_POLE_HEIGHT / 2, 0]);
      const poleGeom = poleMesh.props.children[0];
      const poleMat = poleMesh.props.children[1];
      assert.equal(poleGeom.type, 'cylinderGeometry');
      assert.deepEqual(poleGeom.props.args, [FOUL_POLE_RADIUS, FOUL_POLE_RADIUS, FOUL_POLE_HEIGHT, 16]);
      assert.equal(poleMat.type, 'meshStandardMaterial');
      assert.equal(poleMat.props.color, FOUL_POLE_COLOR);
      assert.equal(poleMat.props.roughness, 0.4);
      assert.equal(poleMat.props.metalness, 0.2);

      // Verify Screen Wing
      assert.equal(wingMesh.props.position[1], 20.0, 'Screen wing must be elevated between 8 ft and 32 ft');
      const wingGeom = wingMesh.props.children[0];
      const wingMat = wingMesh.props.children[1];
      assert.equal(wingGeom.type, 'boxGeometry');
      assert.deepEqual(wingGeom.props.args, [
        FOUL_POLE_WING_THICKNESS,
        FOUL_POLE_WING_HEIGHT,
        FOUL_POLE_WING_WIDTH,
      ]);
      assert.equal(wingMat.type, 'meshStandardMaterial');
      assert.equal(wingMat.props.color, FOUL_POLE_COLOR);
    }

    // Verify fair territory projection orientation:
    // Left pole wing should project inward (+X towards center field)
    const leftMeshes = React.Children.toArray(leftGroup.props.children) as React.ReactElement[];
    const leftWing = leftMeshes[1];
    assert.ok(leftWing.props.position[0] > 0, 'Left screen wing must project inward towards fair territory (+X)');

    // Right pole wing should project inward (-X towards center field)
    const rightMeshes = React.Children.toArray(rightGroup.props.children) as React.ReactElement[];
    const rightWing = rightMeshes[1];
    assert.ok(rightWing.props.position[0] < 0, 'Right screen wing must project inward towards fair territory (-X)');
  });
});
