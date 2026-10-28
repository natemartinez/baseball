/** Seed presets and helpers for the dev-menu Seed Lab. */

export const SEED_PRESETS = [424201, 424202, 424203, 424204, 424205] as const;

export const MAX_SEED = 0xFFFFFFFF;

/** Fresh unsigned 32-bit seed for "random" seeded starts. */
export function createSeed(): number {
  return Math.floor(Math.random() * 0x100000000) >>> 0;
}

/** Parses a numeric input into a valid unsigned 32-bit seed, or null. */
export function parseSeedInput(value: string): number | null {
  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) return null;
  const seed = Number(trimmed);
  if (!Number.isSafeInteger(seed) || seed < 0 || seed > MAX_SEED) return null;
  return seed;
}
