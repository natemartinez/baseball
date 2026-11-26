import React from 'react';
import * as THREE from 'three';

import { getFencePoint } from './fieldGeometry';

/**
 * Specification for an outfield distance marker mounted on the home run wall.
 */
export interface WallDistanceMarkerSpec {
  text: string;
  sprayAngle: number;
  y: number;
  position: [number, number, number];
  rotation: [number, number, number];
}

export const MARKER_ELEVATION = 4.5; // ft above ground (eye level on 8 ft wall)
export const MARKER_WIDTH = 3.2; // ft wide badge
export const MARKER_HEIGHT = 1.6; // ft tall badge
export const MARKER_DEPTH = 0.04; // ft depth
export const MARKER_BORDER_COLOR = '#FFD700'; // stadium gold accent
export const MARKER_BG_COLOR = '#0D1721'; // dark navy backing plate
export const MARKER_TEXT_COLOR = '#FFFFFF'; // high-contrast white numerals

export const WALL_DISTANCE_MARKERS: WallDistanceMarkerSpec[] = [
  { text: '350', sprayAngle: -45.0, y: MARKER_ELEVATION },
  { text: '385', sprayAngle: -22.5, y: MARKER_ELEVATION },
  { text: '420', sprayAngle: 0.0, y: MARKER_ELEVATION },
  { text: '385', sprayAngle: 22.5, y: MARKER_ELEVATION },
  { text: '350', sprayAngle: 45.0, y: MARKER_ELEVATION },
].map((spec) => {
  const pt = getFencePoint(spec.sprayAngle, -0.05);
  const position: [number, number, number] = [pt[0], spec.y, pt[2]];
  const rotation: [number, number, number] = [
    0,
    -(spec.sprayAngle * Math.PI) / 180,
    0,
  ];
  return {
    ...spec,
    position,
    rotation,
  };
});

const markerTextureCache = new Map<string, THREE.Texture>();
const numeralGeometryCache = new Map<string, THREE.BufferGeometry>();

/**
 * Creates 2D segment quads for standard athletic block numerals (0-9).
 */
function getDigitSegments(
  digit: string,
  cx: number,
  cy: number,
  w: number,
  h: number,
  t: number,
) {
  const hw = w / 2;
  const hh = h / 2;
  const rects: Array<{ x: number; y: number; w: number; h: number }> = [];
  const map: Record<string, string[]> = {
    '0': ['a', 'b', 'c', 'd', 'e', 'f'],
    '1': ['b', 'c'],
    '2': ['a', 'b', 'g', 'e', 'd'],
    '3': ['a', 'b', 'g', 'c', 'd'],
    '4': ['f', 'g', 'b', 'c'],
    '5': ['a', 'f', 'g', 'c', 'd'],
    '6': ['a', 'f', 'e', 'g', 'c', 'd'],
    '7': ['a', 'b', 'c'],
    '8': ['a', 'b', 'c', 'd', 'e', 'f', 'g'],
    '9': ['a', 'b', 'c', 'd', 'f', 'g'],
  };
  const segs = map[digit] || [];
  for (const s of segs) {
    let rx = cx;
    let ry = cy;
    let rw = w;
    let rh = h;
    if (s === 'a') {
      ry = cy + hh - t / 2;
      rh = t;
    } else if (s === 'b') {
      rx = cx + hw - t / 2;
      ry = cy + hh / 2;
      rw = t;
      rh = hh;
    } else if (s === 'c') {
      rx = cx + hw - t / 2;
      ry = cy - hh / 2;
      rw = t;
      rh = hh;
    } else if (s === 'd') {
      ry = cy - hh + t / 2;
      rh = t;
    } else if (s === 'e') {
      rx = cx - hw + t / 2;
      ry = cy - hh / 2;
      rw = t;
      rh = hh;
    } else if (s === 'f') {
      rx = cx - hw + t / 2;
      ry = cy + hh / 2;
      rw = t;
      rh = hh;
    } else if (s === 'g') {
      ry = cy;
      rh = t;
    }
    rects.push({ x: rx, y: ry, w: rw, h: rh });
  }
  return rects;
}

/**
 * Generates a clean 3D procedural BufferGeometry for distance numerals (e.g. "350", "385", "420").
 * Works 100% natively on React Native (iOS, Android), web, and headless test environments with zero DOM canvas dependencies.
 */
export function createDistanceMarkerNumeralGeometry(text: string): THREE.BufferGeometry {
  const w = 0.44;
  const h = 0.85;
  const t = 0.10;
  const gap = 0.14;
  const totalW = text.length * w + (text.length - 1) * gap;
  const startX = -totalW / 2 + w / 2;

  const rects: Array<{ x: number; y: number; w: number; h: number }> = [];
  for (let i = 0; i < text.length; i++) {
    const cx = startX + i * (w + gap);
    rects.push(...getDigitSegments(text[i], cx, 0, w, h, t));
  }

  const positions: number[] = [];
  const normals: number[] = [];
  const indices: number[] = [];
  let vIndex = 0;

  for (const r of rects) {
    const x0 = r.x - r.w / 2;
    const x1 = r.x + r.w / 2;
    const y0 = r.y - r.h / 2;
    const y1 = r.y + r.h / 2;
    positions.push(
      x0, y0, 0,
      x1, y0, 0,
      x1, y1, 0,
      x0, y1, 0,
    );
    for (let k = 0; k < 4; k++) normals.push(0, 0, 1);
    indices.push(vIndex, vIndex + 1, vIndex + 2, vIndex, vIndex + 2, vIndex + 3);
    vIndex += 4;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
  geometry.setIndex(indices);
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}

/**
 * Returns a cached procedural numeral geometry for the given marker text.
 */
export function getOrCreateDistanceMarkerNumeralGeometry(text: string): THREE.BufferGeometry {
  let geom = numeralGeometryCache.get(text);
  if (!geom) {
    geom = createDistanceMarkerNumeralGeometry(text);
    numeralGeometryCache.set(text, geom);
  }
  return geom;
}

/**
 * Generates a high-contrast canvas texture for a distance marker numeral.
 * Returns null in headless / test environments without DOM canvas support.
 */
export function createDistanceMarkerTexture(text: string): THREE.Texture | null {
  if (typeof document === 'undefined') {
    return null;
  }

  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  // Dark backing plate
  ctx.fillStyle = MARKER_BG_COLOR;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Gold border frame
  ctx.strokeStyle = MARKER_BORDER_COLOR;
  ctx.lineWidth = 8;
  ctx.strokeRect(4, 4, canvas.width - 8, canvas.height - 8);

  // Bold distance numerals
  ctx.fillStyle = MARKER_TEXT_COLOR;
  ctx.font = 'bold 64px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

/**
 * Returns a cached canvas texture for the given marker text, or null in headless environments.
 */
export function getOrCreateDistanceMarkerTexture(text: string): THREE.Texture | null {
  if (typeof document === 'undefined') {
    return null;
  }
  let texture = markerTextureCache.get(text);
  if (!texture) {
    const created = createDistanceMarkerTexture(text);
    if (created) {
      markerTextureCache.set(text, created);
      texture = created;
    }
  }
  return texture ?? null;
}

/**
 * WallDistanceMarkers Component
 *
 * Renders authentic stadium distance plates ("350", "385", "420", "385", "350")
 * mounted along the inner face of the outfield wall at Y = 4.5 ft.
 * Uses 100% native vector numeral geometry compatible with React Native (iOS, Android),
 * web, and headless test runners.
 */
export function WallDistanceMarkers(props?: React.ComponentProps<'group'>) {
  return (
    <group {...props}>
      {WALL_DISTANCE_MARKERS.map((marker, index) => {
        const numeralGeom = getOrCreateDistanceMarkerNumeralGeometry(marker.text);
        return (
          <group
            key={`${marker.text}-${index}`}
            position={marker.position}
            rotation={marker.rotation}
          >
            {/* Outer gold border frame plate */}
            <mesh position={[0, 0, 0]}>
              <boxGeometry args={[MARKER_WIDTH, MARKER_HEIGHT, MARKER_DEPTH]} />
              <meshStandardMaterial
                color={MARKER_BORDER_COLOR}
                roughness={0.4}
                metalness={0.3}
              />
            </mesh>

            {/* Inner dark navy inset plate */}
            <mesh position={[0, 0, MARKER_DEPTH / 2 + 0.005]}>
              <planeGeometry args={[MARKER_WIDTH - 0.2, MARKER_HEIGHT - 0.2]} />
              <meshStandardMaterial
                color={MARKER_BG_COLOR}
                roughness={0.6}
                metalness={0.1}
              />
            </mesh>

            {/* 3D crisp vector numerals (100% native on iOS, Android, Web & Node) */}
            <mesh position={[0, 0, MARKER_DEPTH / 2 + 0.010]} geometry={numeralGeom}>
              <meshStandardMaterial
                color={MARKER_TEXT_COLOR}
                roughness={0.3}
                metalness={0.1}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

export default WallDistanceMarkers;
