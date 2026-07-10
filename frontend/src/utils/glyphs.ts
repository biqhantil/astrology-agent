/* ── Astrological planet and sign glyphs (SVG text / Unicode) ── */

import type { BodyKey, SignName } from '../types/chart';

/** Force text-style (monochrome) presentation — avoids multicolored emoji glyphs. */
const VS15 = '\uFE0E';

function mono(char: string): string {
  return char + VS15;
}

/**
 * Returns a Unicode glyph symbol for the given celestial body.
 * VS15 keeps symbols monochrome so SVG fill colors apply.
 */
export function bodyGlyph(body: BodyKey): string {
  const glyphMap: Partial<Record<BodyKey, string>> = {
    sun: mono('\u2609'),
    moon: mono('\u263D'),
    mercury: mono('\u263F'),
    venus: mono('\u2640'),
    mars: mono('\u2642'),
    jupiter: mono('\u2643'),
    saturn: mono('\u2644'),
    uranus: mono('\u2645'),
    neptune: mono('\u2646'),
    pluto: mono('\u2647'),
    north_node: mono('\u260A'),
    south_node: mono('\u260B'),
    chiron: mono('\u26B7'),
    asc: 'Asc',
    mc: 'MC',
    dsc: 'Dsc',
    ic: 'IC',
    lilith: mono('\u26B8'),
    part_of_fortune: mono('\u2297'),
  };
  return glyphMap[body] ?? body.slice(0, 2).toUpperCase();
}

/**
 * Returns a monochrome Unicode glyph for the given zodiac sign.
 */
export function signGlyph(sign: SignName): string {
  const glyphMap: Record<SignName, string> = {
    aries: mono('\u2648'),
    taurus: mono('\u2649'),
    gemini: mono('\u264A'),
    cancer: mono('\u264B'),
    leo: mono('\u264C'),
    virgo: mono('\u264D'),
    libra: mono('\u264E'),
    scorpio: mono('\u264F'),
    sagittarius: mono('\u2650'),
    capricorn: mono('\u2651'),
    aquarius: mono('\u2652'),
    pisces: mono('\u2653'),
  };
  return glyphMap[sign] ?? sign.slice(0, 3).toUpperCase();
}

/** Angle bodies rendered on the outer ring, not stacked with planets. */
export const ANGLE_BODIES = new Set<BodyKey>(['asc', 'mc', 'dsc', 'ic']);

/** Prefer these for the main planet band (cleaner wheel). */
export const CORE_PLANET_BODIES = new Set<BodyKey>([
  'sun', 'moon', 'mercury', 'venus', 'mars',
  'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
  'north_node', 'south_node', 'chiron', 'lilith', 'part_of_fortune',
]);

/**
 * Human-readable label for a body key.
 */
export function bodyLabel(body: BodyKey): string {
  const labels: Partial<Record<BodyKey, string>> = {
    sun: 'Sun',
    moon: 'Moon',
    mercury: 'Mercury',
    venus: 'Venus',
    mars: 'Mars',
    jupiter: 'Jupiter',
    saturn: 'Saturn',
    uranus: 'Uranus',
    neptune: 'Neptune',
    pluto: 'Pluto',
    north_node: 'North Node',
    south_node: 'South Node',
    chiron: 'Chiron',
    asc: 'Ascendant',
    mc: 'Midheaven',
    dsc: 'Descendant',
    ic: 'Imum Coeli',
    lilith: 'Lilith',
    part_of_fortune: 'Part of Fortune',
  };
  return labels[body] ?? body;
}

/**
 * Human-readable label for a sign name.
 */
export function signLabel(sign: SignName): string {
  return sign.charAt(0).toUpperCase() + sign.slice(1);
}

/**
 * Returns the element for a given sign.
 */
export function signElement(sign: SignName): 'fire' | 'earth' | 'air' | 'water' {
  const elementMap: Record<SignName, 'fire' | 'earth' | 'air' | 'water'> = {
    aries: 'fire',
    taurus: 'earth',
    gemini: 'air',
    cancer: 'water',
    leo: 'fire',
    virgo: 'earth',
    libra: 'air',
    scorpio: 'water',
    sagittarius: 'fire',
    capricorn: 'earth',
    aquarius: 'air',
    pisces: 'water',
  };
  return elementMap[sign];
}

/**
 * Tailwind / CSS color class for an element.
 */
export function elementColor(element: 'fire' | 'earth' | 'air' | 'water'): string {
  const colors: Record<string, string> = {
    fire: '#ef4444',
    earth: '#22c55e',
    air: '#eab308',
    water: '#3b82f6',
  };
  return colors[element];
}
