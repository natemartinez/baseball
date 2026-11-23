import { FIELDERS, type Fielder } from '../../services/fielders';

export interface FielderPursuitParams {
  startStatcast: [number, number] | [number, number, number];
  targetStatcast: [number, number] | [number, number, number];
  elapsedTime: number;
  totalDuration: number;
  reactionDelay?: number;
}

export interface FielderPursuitState {
  currentScenePos: [number, number, number];
  gloveScenePos: [number, number, number];
  headingAngle: number;
  progress: number;
  hasBroken: boolean;
  isArrived: boolean;
}

export interface CatchVisualProfile {
  ringColor: string;
  badgeLabel: string | null;
  isCaught: boolean;
  showRing: boolean;
  gloveElevationOffset: number;
}

export interface AllFieldersParams {
  activeFielderId?: string | null;
  activeStartStatcast?: [number, number] | [number, number, number] | null;
  activeTargetStatcast?: [number, number] | [number, number, number] | null;
  elapsedTime: number;
  totalDuration: number;
  reactionDelay?: number;
}

export interface FielderRenderState {
  id: string;
  scenePos: [number, number, number];
  glovePos?: [number, number, number];
  headingAngle: number;
  isPursuing: boolean;
  isArrived: boolean;
}

/**
 * Converts Statcast field coordinates (+x right field, +y toward CF, +z height)
 * into Three.js scene coordinates (+x right, +y height, -z toward home plate / away from CF).
 */
export function statcastToScene(
  x: number,
  y: number,
  z: number = 0.0,
): [number, number, number] {
  return [x, z, -y];
}

/**
 * Computes pure kinematic pursuit positioning, progress, and heading for a fielder.
 */
export function computeFielderPursuit(params: FielderPursuitParams): FielderPursuitState {
  const {
    startStatcast,
    targetStatcast,
    elapsedTime,
    totalDuration,
    reactionDelay = 0.25,
  } = params;

  const startX = startStatcast[0];
  const startY = startStatcast[1];
  const targetX = targetStatcast[0];
  const targetY = targetStatcast[1];
  const targetZ = targetStatcast.length > 2 ? (targetStatcast[2] as number) : 0.0;

  // Guard reaction delay so it never exceeds half the total hang time
  const effDuration = Math.max(0.05, totalDuration);
  const effReaction = Math.min(reactionDelay, effDuration * 0.5);

  let progress = 0.0;
  let hasBroken = false;
  let isArrived = false;
  let currentX = startX;
  let currentY = startY;

  if (elapsedTime <= effReaction) {
    progress = 0.0;
    hasBroken = false;
    isArrived = false;
    currentX = startX;
    currentY = startY;
  } else if (elapsedTime >= effDuration) {
    progress = 1.0;
    hasBroken = true;
    isArrived = true;
    currentX = targetX;
    currentY = targetY;
  } else {
    hasBroken = true;
    isArrived = false;
    const sprintDuration = Math.max(0.05, effDuration - effReaction);
    const u = Math.min(1.0, Math.max(0.0, (elapsedTime - effReaction) / sprintDuration));
    // Athletic smoothstep easing: starts smoothly from rest, accelerates, and gathers at intercept
    const smoothProgress = u * u * (3.0 - 2.0 * u);
    progress = smoothProgress;
    currentX = startX + (targetX - startX) * progress;
    currentY = startY + (targetY - startY) * progress;
  }

  // Heading calculation: in Three.js, deltaX = targetX - startX, deltaZ = -(targetY - startY)
  const deltaX = targetX - startX;
  const deltaZ = -(targetY - startY);
  const distanceScene = Math.hypot(deltaX, deltaZ);
  const headingAngle = distanceScene >= 0.1 ? Math.atan2(deltaX, deltaZ) : 0.0;

  // Turf mesh position sits at ground level (Y = 0)
  const currentScenePos = statcastToScene(currentX, currentY, 0.0);
  // Glove intercept point retains z elevation
  const gloveScenePos = statcastToScene(currentX, currentY, targetZ * progress);

  return {
    currentScenePos,
    gloveScenePos,
    headingAngle,
    progress,
    hasBroken,
    isArrived,
  };
}

/**
 * Resolves styling and visual metadata for catch indicators and banner badges.
 */
export function getCatchVisualProfile(
  fieldingType: string | null | undefined,
): CatchVisualProfile {
  if (!fieldingType) {
    return {
      ringColor: '#6B7280',
      badgeLabel: null,
      isCaught: false,
      showRing: false,
      gloveElevationOffset: 0.0,
    };
  }

  switch (fieldingType.toUpperCase()) {
    case 'WALL_LEAP':
      return {
        ringColor: '#EF4444',
        badgeLabel: 'WALL LEAP',
        isCaught: true,
        showRing: true,
        gloveElevationOffset: 6.5,
      };
    case 'SLIDING_CATCH':
      return {
        ringColor: '#F59E0B',
        badgeLabel: 'SLIDING CATCH',
        isCaught: true,
        showRing: true,
        gloveElevationOffset: 1.2,
      };
    case 'GROUND_SCOOP':
      return {
        ringColor: '#3B82F6',
        badgeLabel: 'FIELDED',
        isCaught: true,
        showRing: true,
        gloveElevationOffset: 0.5,
      };
    case 'BACKHAND_PICK':
      return {
        ringColor: '#3B82F6',
        badgeLabel: 'BACKHAND PICK',
        isCaught: true,
        showRing: true,
        gloveElevationOffset: 0.5,
      };
    case 'ROUTINE_FLY_CATCH':
      return {
        ringColor: '#10B981',
        badgeLabel: 'ROUTINE CATCH',
        isCaught: true,
        showRing: true,
        gloveElevationOffset: 3.5,
      };
    case 'RUNNING_CATCH':
      return {
        ringColor: '#10B981',
        badgeLabel: 'RUNNING CATCH',
        isCaught: true,
        showRing: true,
        gloveElevationOffset: 3.5,
      };
    case 'UNFIELDED':
    case 'HOME_RUN':
    case 'FOUL':
    default:
      return {
        ringColor: '#6B7280',
        badgeLabel: null,
        isCaught: false,
        showRing: false,
        gloveElevationOffset: 0.0,
      };
  }
}

/**
 * Computes positions for all 8 defensive fielders:
 * - Active fielder executes pursuit path toward targetStatcast.
 * - Non-active fielders shade towards the ball path for backup and cutoff alignment.
 */
export function computeAllFielderPositions(
  params: AllFieldersParams,
): Map<string, FielderRenderState> {
  const {
    activeFielderId,
    activeStartStatcast,
    activeTargetStatcast,
    elapsedTime,
    totalDuration,
    reactionDelay = 0.25,
  } = params;

  const result = new Map<string, FielderRenderState>();

  for (const fielder of FIELDERS) {
    if (
      activeFielderId &&
      fielder.id === activeFielderId &&
      activeTargetStatcast
    ) {
      const start: [number, number] = activeStartStatcast
        ? [activeStartStatcast[0], activeStartStatcast[1]]
        : [fielder.x, fielder.y];

      const pursuit = computeFielderPursuit({
        startStatcast: start,
        targetStatcast: activeTargetStatcast,
        elapsedTime,
        totalDuration,
        reactionDelay,
      });

      result.set(fielder.id, {
        id: fielder.id,
        scenePos: pursuit.currentScenePos,
        glovePos: pursuit.gloveScenePos,
        headingAngle: pursuit.headingAngle,
        isPursuing: true,
        isArrived: pursuit.isArrived,
      });
    } else {
      // Off-ball fielder shading toward play
      if (activeTargetStatcast) {
        const targetX = activeTargetStatcast[0];
        const targetY = activeTargetStatcast[1];
        const dx = targetX - fielder.x;
        const dy = targetY - fielder.y;
        const dist = Math.hypot(dx, dy);

        if (dist >= 1.0) {
          const unitX = dx / dist;
          const unitY = dy / dist;

          const isOutfielder = fielder.id === 'LF' || fielder.id === 'CF' || fielder.id === 'RF';
          // Subtle, realistic anticipation steps (max 1.5 - 3.5 ft), not a 12-ft sprint!
          const maxShade = isOutfielder ? 3.5 : (fielder.id === 'P' ? 1.0 : 2.0);

          const effDuration = Math.max(0.05, totalDuration);
          const effReaction = Math.min(reactionDelay, effDuration * 0.4);
          // Rate-limit shading speed to natural walking/anticipating pace (<= 3.5 ft/s)
          const dtShade = Math.max(0.0, elapsedTime - effReaction);
          const currentShade = Math.min(maxShade, 3.5 * dtShade);

          const shadedX = fielder.x + currentShade * unitX;
          const shadedY = fielder.y + currentShade * unitY;

          const deltaSceneX = unitX;
          const deltaSceneZ = -unitY;
          const heading = Math.atan2(deltaSceneX, deltaSceneZ);

          result.set(fielder.id, {
            id: fielder.id,
            scenePos: statcastToScene(shadedX, shadedY, 0.0),
            headingAngle: heading,
            isPursuing: false,
            isArrived: false,
          });
          continue;
        }
      }

      // Default baseline position
      result.set(fielder.id, {
        id: fielder.id,
        scenePos: statcastToScene(fielder.x, fielder.y, 0.0),
        headingAngle: 0.0,
        isPursuing: false,
        isArrived: false,
      });
    }
  }

  return result;
}

