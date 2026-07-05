/* ── Astrological planet and sign glyphs (SVG text / Unicode fallback) ── */

import type { BodyKey, SignName } from '../types/chart';

/**
 * Returns a Unicode glyph symbol for the given celestial body.
 * These are standard astrological Unicode characters.
 */
export function bodyGlyph(body: BodyKey): string {
  const glyphMap: Partial<Record<BodyKey, string>> = {
    sun: '\u2609',       // ☉
    moon: '\u263D',      // ☽
    mercury: '\u263F',   // ☿
    venus: '\u2640',     // ♀
    mars: '\u2642',      // ♂
    jupiter: '\u2643',   // ♃
    saturn: '\u2644',    // ♄
    uranus: '\u2645',    // ♅
    neptune: '\u2646',   // ♆
    pluto: '\u2647',     // ♇
    north_node: '\u260A',  // ☊
    south_node: '\u260B',  // ☋
    chiron: '\u26B7',    // ⚷
    asc: 'ASC',
    mc: 'MC',
    dsc: 'DSC',
    ic: 'IC',
    lilith: '\u26B8',    // ⚸
    part_of_fortune: '\u2297', // ⊗
  };
  return glyphMap[body] ?? body.slice(0, 2).toUpperCase();
}

/**
 * Returns a Unicode glyph for the given zodiac sign.
 */
export function signGlyph(sign: SignName): string {
  const glyphMap: Record<SignName, string> = {
    aries: '\u2648',        // ♈
    taurus: '\u2649',       // ♉
    gemini: '\u264A',       // ♊
    cancer: '\u264B',       // ♋
    leo: '\u264C',          // ♌
    virgo: '\u264D',        // ♍
    libra: '\u264E',        // ♎
    scorpio: '\u264F',      // ♏
    sagittarius: '\u2650',  // ♐
    capricorn: '\u2651',    // ♑
    aquarius: '\u2652',     // ♒
    pisces: '\u2653',       // ♓
  };
  return glyphMap[sign] ?? sign.slice(0, 3).toUpperCase();
}

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
