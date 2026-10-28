import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import {
  Physics,
  RigidBody,
  BallCollider,
  CylinderCollider,
  useBeforePhysicsStep,
  type CollisionEnterPayload,
} from '@react-three/rapier';
import type { RigidBody as RapierRigidBody } from '@dimforge/rapier3d-compat';

import type { BattingLayerProps } from './types';
import type { SwingContactReport } from '../../types/api';
import { pitchPointAt, pitchVelocityAt, type PitchPath } from './pitchPath';
import {
  BALL_RADIUS_FT,
  BAT_CONTACT_ANGLE_RAD,
  BAT_LENGTH_FT,
  BAT_SECTIONS,
  CHARGE_MS,
  SWING_DURATION_S,
  aimPivot,
  batAxisPoint,
  clamp,
  closestPointOnSegment,
  computeContact,
  swingAngularVelocity,
  swingYawAt,
  type Vec3,
} from './battingMath';
import { useThree } from './useThree';

interface BatPose {
  pivot: Vec3;
  yaw: number;
  angularVelocity: number;
}

const DEFAULT_AIM: Vec3 = { x: 0, y: 2.5, z: 0 };
const INITIAL_PIVOT = aimPivot(DEFAULT_AIM);
const INITIAL_POSITION: [number, number, number] = [
  INITIAL_PIVOT.x,
  INITIAL_PIVOT.y,
  INITIAL_PIVOT.z,
];
const ARRIVAL_GRACE_MS = 70;
const UI_TOP_BAND = 0.14;
const UI_BOTTOM_BAND_PX = 170;

/**
 * Web-only Rapier batting layer.
 *
 * The bat is kinematic and only gains colliders during the swing; the ball is
 * a dynamic CCD body driven along the shared pitch path. The layer never
 * renders the batted-ball arc — `BattedBallVisualizer` owns that after the
 * backend/mock returns the trace.
 */
export function BattingLayer(props: BattingLayerProps) {
  return (
    <Physics timeStep={1 / 120} gravity={[0, 0, 0]}>
      <BattingScene {...props} />
    </Physics>
  );
}

function BattingScene({
  activePitch,
  pitchPhase,
  inputEnabled,
  chargeRef,
  onContact,
  onPitchArrival,
}: BattingLayerProps) {
  const camera = useThree((state) => state.camera);
  const gl = useThree((state) => state.gl);

  const batRef = useRef<RapierRigidBody>(null);
  const reticleRef = useRef<THREE.Mesh>(null);
  const aimRef = useRef<Vec3>({ ...DEFAULT_AIM });
  const poseRef = useRef<BatPose>({
    pivot: INITIAL_PIVOT,
    yaw: BAT_CONTACT_ANGLE_RAD,
    angularVelocity: 0,
  });
  const euler = useRef(new THREE.Euler()).current;
  const quaternion = useRef(new THREE.Quaternion()).current;

  const pressingRef = useRef(false);
  const pressStartRef = useRef(0);
  const swingStartRef = useRef(0);
  const swingChargeRef = useRef(0);
  const swingPivotRef = useRef<Vec3>(INITIAL_PIVOT);
  const swingingRef = useRef(false);
  const swingAttemptedRef = useRef(false);
  const contactedRef = useRef(false);
  const arrivedRef = useRef(false);

  const [swinging, setSwinging] = useState(false);
  const path = useMemo<PitchPath | null>(
    () =>
      activePitch
        ? {
            release: activePitch.release,
            plate: activePitch.plate,
            pfx: activePitch.pfx,
            flightTime: activePitch.flightTime,
          }
        : null,
    [activePitch],
  );

  // Reset the swing state for every pitch. The aim is intentionally kept so
  // the player can pre-position the bat before the next throw.
  useEffect(() => {
    pressingRef.current = false;
    swingingRef.current = false;
    swingAttemptedRef.current = false;
    contactedRef.current = false;
    arrivedRef.current = false;
    swingChargeRef.current = 0;
    chargeRef.current = 0;
    setSwinging(false);
    poseRef.current = {
      pivot: aimPivot(aimRef.current),
      yaw: BAT_CONTACT_ANGLE_RAD,
      angularVelocity: 0,
    };
  }, [activePitch?.id, chargeRef]);

  // Pointer input is attached to the window because the Canvas itself is
  // pointer-events:none. Ignore the scorebug band and the pitch-selector band.
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const raycaster = new THREE.Raycaster();
    const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
    const hit = new THREE.Vector3();
    const ndc = new THREE.Vector2();

    const isUiBand = (clientY: number): boolean => {
      const rect = gl.domElement.getBoundingClientRect();
      if (rect.height <= 0) return true;
      return (
        clientY < rect.top + rect.height * UI_TOP_BAND ||
        clientY > rect.top + rect.height - UI_BOTTOM_BAND_PX
      );
    };

    const updateAim = (event: PointerEvent): void => {
      if (!inputEnabled) return;
      const rect = gl.domElement.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;

      ndc.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(ndc, camera);
      if (raycaster.ray.intersectPlane(plane, hit)) {
        aimRef.current = {
          x: clamp(hit.x, -3.5, 3.5),
          y: clamp(hit.y, 1.0, 4.6),
          z: 0,
        };
      }
    };

    const onMove = (event: PointerEvent) => {
      if (isUiBand(event.clientY)) return;
      updateAim(event);
    };

    const onDown = (event: PointerEvent) => {
      if (!inputEnabled || pitchPhase !== 'IN_FLIGHT') return;
      if (isUiBand(event.clientY)) return;
      if (pressingRef.current || swingingRef.current) return;

      updateAim(event);
      pressingRef.current = true;
      pressStartRef.current = performance.now();
      swingAttemptedRef.current = true;
      chargeRef.current = 0;
    };

    const release = () => {
      if (!pressingRef.current) return;
      pressingRef.current = false;

      const now = performance.now();
      const charge = clamp((now - pressStartRef.current) / CHARGE_MS, 0, 1);
      swingStartRef.current = now;
      swingChargeRef.current = charge;
      swingPivotRef.current = aimPivot(aimRef.current);
      chargeRef.current = charge;
      swingingRef.current = true;
      setSwinging(true);
    };

    const onUp = () => release();
    const onCancel = () => release();

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerdown', onDown);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onCancel);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onCancel);
    };
  }, [inputEnabled, pitchPhase, camera, gl, chargeRef]);

  useBeforePhysicsStep(() => {
    const now = performance.now();
    let yaw = BAT_CONTACT_ANGLE_RAD;
    let pivot = aimPivot(aimRef.current);
    let angularVelocity = 0;

    if (swingingRef.current) {
      const progress = clamp(
        (now - swingStartRef.current) / (SWING_DURATION_S * 1000),
        0,
        1,
      );
      yaw = swingYawAt(progress, swingChargeRef.current);
      pivot = swingPivotRef.current;
      angularVelocity = swingAngularVelocity(swingChargeRef.current);

      if (progress >= 1) {
        swingingRef.current = false;
        chargeRef.current = 0;
        setSwinging(false);
      }
    } else if (pressingRef.current) {
      const charge = clamp((now - pressStartRef.current) / CHARGE_MS, 0, 1);
      chargeRef.current = charge;
      yaw = BAT_CONTACT_ANGLE_RAD - (80 * Math.PI) / 180;
      pivot = aimPivot(aimRef.current);
    }

    poseRef.current = { pivot, yaw, angularVelocity };

    const body = batRef.current;
    if (body) {
      body.setNextKinematicTranslation(pivot);
      euler.set(0, yaw, 0);
      quaternion.setFromEuler(euler);
      body.setNextKinematicRotation(quaternion);
    }

    if (reticleRef.current) {
      reticleRef.current.position.set(aimRef.current.x, aimRef.current.y, 0.02);
    }
  });

  const batVisible =
    inputEnabled && (pitchPhase === 'IDLE' || pitchPhase === 'IN_FLIGHT');

  return (
    <>
      <RigidBody
        ref={batRef}
        name="bat"
        type="kinematicPosition"
        canSleep={false}
        colliders={false}
        position={INITIAL_POSITION}
      >
        {swinging &&
          BAT_SECTIONS.map((section, index) => (
            <CylinderCollider
              key={`bat-collider-${index}`}
              args={[
                section.length / 2,
                (section.radiusStart + section.radiusEnd) / 2,
              ]}
              position={[section.offset + section.length / 2, 0, 0]}
              rotation={[0, 0, Math.PI / 2]}
            />
          ))}

        {batVisible &&
          BAT_SECTIONS.map((section, index) => (
            <mesh
              key={`bat-visual-${index}`}
              position={[section.offset + section.length / 2, 0, 0]}
              rotation={[0, 0, Math.PI / 2]}
              castShadow={false}
            >
              <cylinderGeometry
                args={[
                  section.radiusStart,
                  section.radiusEnd,
                  section.length,
                  12,
                ]}
              />
              <meshStandardMaterial
                color="#D9A066"
                roughness={0.62}
                emissive="#3B2413"
                emissiveIntensity={0.12}
              />
            </mesh>
          ))}
      </RigidBody>

      {inputEnabled && (
        <mesh ref={reticleRef} position={[DEFAULT_AIM.x, DEFAULT_AIM.y, 0.02]}>
          <ringGeometry args={[0.1, 0.14, 24]} />
          <meshBasicMaterial color="#67E8F9" transparent opacity={0.85} />
        </mesh>
      )}

      {path && activePitch && !contactedRef.current && (
        <PitchBall
          key={activePitch.id}
          path={path}
          batPoseRef={poseRef}
          chargeRef={chargeRef}
          getSwingAttempted={() => swingAttemptedRef.current}
          onContact={onContact}
          onArrive={onPitchArrival}
          onContactState={() => {
            contactedRef.current = true;
          }}
          onArriveState={() => {
            arrivedRef.current = true;
            chargeRef.current = 0;
          }}
        />
      )}
    </>
  );
}

function PitchBall({
  path,
  batPoseRef,
  chargeRef,
  getSwingAttempted,
  onContact,
  onArrive,
  onContactState,
  onArriveState,
}: {
  path: PitchPath;
  batPoseRef: React.MutableRefObject<BatPose>;
  chargeRef: React.MutableRefObject<number>;
  getSwingAttempted: () => boolean;
  onContact: (contact: SwingContactReport) => void;
  onArrive: (swingAttempted: boolean) => void;
  onContactState: () => void;
  onArriveState: () => void;
}) {
  const ballRef = useRef<RapierRigidBody>(null);
  const startMsRef = useRef(performance.now());
  const velocityRef = useRef<Vec3>({ x: 0, y: 0, z: 0 });
  const contactedRef = useRef(false);
  const arrivedRef = useRef(false);

  const trailPoints = 24;
  const trailPositions = useMemo(() => {
    const array = new Float32Array(trailPoints * 3);
    for (let i = 0; i < trailPoints; i += 1) {
      array[i * 3] = path.release[0];
      array[i * 3 + 1] = path.release[1];
      array[i * 3 + 2] = path.release[2];
    }
    return array;
  }, [path.release]);
  const trailGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    const attribute = new THREE.BufferAttribute(trailPositions, 3);
    attribute.setUsage(THREE.DynamicDrawUsage);
    geometry.setAttribute('position', attribute);
    return geometry;
  }, [trailPositions]);
  const trailObject = useMemo(
    () =>
      new THREE.Line(
        trailGeometry,
        new THREE.LineBasicMaterial({
          color: '#ff0044',
          transparent: true,
          opacity: 0.8,
        }),
      ),
    [trailGeometry],
  );
  trailObject.frustumCulled = false;

  useEffect(
    () => () => {
      trailGeometry.dispose();
      (trailObject.material as THREE.Material).dispose();
    },
    [trailGeometry, trailObject],
  );

  useBeforePhysicsStep(() => {
    if (contactedRef.current || arrivedRef.current) return;
    const body = ballRef.current;
    if (!body) return;

    const now = performance.now();
    const elapsed = (now - startMsRef.current) / 1000;

    if (elapsed * 1000 >= path.flightTime * 1000 + ARRIVAL_GRACE_MS) {
      arrivedRef.current = true;
      onArriveState();
      onArrive(getSwingAttempted());
      return;
    }

    const point = pitchPointAt(elapsed, path);
    const velocity = pitchVelocityAt(elapsed, path);
    body.setTranslation(point, true);
    body.setLinvel(velocity, true);
    velocityRef.current = velocity;

    trailPositions.copyWithin(0, 3);
    trailPositions[(trailPoints - 1) * 3] = point.x;
    trailPositions[(trailPoints - 1) * 3 + 1] = point.y;
    trailPositions[(trailPoints - 1) * 3 + 2] = point.z;
    const attribute = trailGeometry.getAttribute('position') as THREE.BufferAttribute;
    attribute.needsUpdate = true;
  });

  const handleCollision = (payload: CollisionEnterPayload) => {
    if (contactedRef.current || arrivedRef.current) return;
    if (payload.other.rigidBodyObject?.name !== 'bat') return;

    const body = ballRef.current;
    if (!body) return;
    const manifold = payload.manifold;
    if (!manifold || manifold.numContacts() === 0) return;

    // The physics step resolves the ball past the bat, so the discrete ball
    // center is not the contact point. Rapier's manifold normal is the true
    // CCD impact normal; orient it against the relative velocity.
    const translation = body.translation();
    const pose = batPoseRef.current;
    const ballCenter = {
      x: translation.x,
      y: translation.y,
      z: translation.z,
    };
    const axisStart = pose.pivot;
    const axisEnd = batAxisPoint(pose.pivot, pose.yaw, BAT_LENGTH_FT);
    const closest = closestPointOnSegment(ballCenter, axisStart, axisEnd);
    const rX = closest.point.x - pose.pivot.x;
    const rZ = closest.point.z - pose.pivot.z;
    const batVelocity = {
      x: pose.angularVelocity * rZ,
      y: 0,
      z: -pose.angularVelocity * rX,
    };
    const rel = {
      x: velocityRef.current.x - batVelocity.x,
      y: velocityRef.current.y - batVelocity.y,
      z: velocityRef.current.z - batVelocity.z,
    };

    const rawNormal = manifold.normal();
    let normal = { x: rawNormal.x, y: rawNormal.y, z: rawNormal.z };
    const normalLength = Math.sqrt(
      normal.x * normal.x + normal.y * normal.y + normal.z * normal.z,
    );
    if (normalLength < 1e-6) return;
    normal = {
      x: normal.x / normalLength,
      y: normal.y / normalLength,
      z: normal.z / normalLength,
    };
    if (rel.x * normal.x + rel.y * normal.y + rel.z * normal.z > 0) {
      normal = { x: -normal.x, y: -normal.y, z: -normal.z };
    }

    const solved = computeContact({
      ballCenter,
      ballVelocity: velocityRef.current,
      pivot: pose.pivot,
      yaw: pose.yaw,
      angularVelocity: pose.angularVelocity,
      normalOverride: normal,
      skipDistanceCheck: true,
    });
    if (!solved) return;

    contactedRef.current = true;
    onContactState();
    onContact({
      contacted: true,
      exit_velocity_mph: solved.exitVelocityMph,
      launch_angle_deg: solved.launchAngleDeg,
      spray_angle_deg: solved.sprayAngleDeg,
      contact_offset_ft: solved.contactOffsetFt,
      bat_speed_mph: solved.batSpeedMph,
      charge: chargeRef.current,
      timing_offset_ms: Math.round(
        performance.now() - (startMsRef.current + path.flightTime * 1000),
      ),
    });
  };

  return (
    <>
      <RigidBody
        ref={ballRef}
        name="baseball"
        type="dynamic"
        ccd
        colliders={false}
        gravityScale={0}
        linearDamping={0}
        angularDamping={0}
        canSleep={false}
        position={[path.release[0], path.release[1], path.release[2]]}
        onCollisionEnter={handleCollision}
      >
        <BallCollider args={[BALL_RADIUS_FT]} />
        <mesh>
          <sphereGeometry args={[0.14, 16, 16]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
      </RigidBody>
      <primitive object={trailObject} />
    </>
  );
}
