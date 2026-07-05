/* ── Polar coordinate math for the ZodiacWheel ───────── */

/**
 * Constants for the 12 zodiac signs in degrees on the 360° wheel.
 * 0° Aries = 0° (vernal equinox / 3 o'clock position).
 * The wheel runs counter-clockwise: Aries→Taurus→Gemini→...
 */
export const SIGN_START_DEGREES: Record<string, number> = {
  aries: 0,
  taurus: 30,
  gemini: 60,
  cancer: 90,
  leo: 120,
  virgo: 150,
  libra: 180,
  scorpio: 210,
  sagittarius: 240,
  capricorn: 270,
  aquarius: 300,
  pisces: 330,
};

/**
 * Map a sign name to its index (0 = Aries, 11 = Pisces).
 */
export function signIndex(sign: string): number {
  const signs = [
    'aries', 'taurus', 'gemini', 'cancer',
    'leo', 'virgo', 'libra', 'scorpio',
    'sagittarius', 'capricorn', 'aquarius', 'pisces',
  ];
  const idx = signs.indexOf(sign.toLowerCase());
  return idx >= 0 ? idx : 0;
}

/**
 * Convert ecliptic longitude (0–360) to polar angle in radians.
 *
 * In SVG astrological wheels, 0° is typically at the top (12 o'clock)
 * and the wheel runs clockwise.  Standard celestial orientation is
 * 0° at the vernal equinox (3 o'clock, east) running counter-clockwise.
 *
 * We rotate by -90° so that 0° Aries appears at top (12 o'clock)
 * and reverse direction to clockwise (which is the standard chart
 * orientation used in Western astrology).
 *
 * @param longitude - Ecliptic longitude in degrees (0–360)
 * @returns Angle in radians for SVG placement
 */
export function longitudeToAngle(longitude: number): number {
  // Start at top (12 o'clock) and go clockwise
  // The standard formula: angle = (90 - longitude) degrees, converted to radians
  const degrees = 90 - longitude;
  return ((degrees * Math.PI) / 180) % (2 * Math.PI);
}

/**
 * Convert polar coordinates to SVG cartesian (cx, cy).
 *
 * @param angle - Angle in radians
 * @param radius - Radius from center
 * @param center - Center offset (default 0)
 * @returns [x, y] SVG coordinates
 */
export function polarToCartesian(
  angle: number,
  radius: number,
  center: number = 0,
): [number, number] {
  const x = center + radius * Math.cos(angle);
  const y = center + radius * Math.sin(angle);
  return [x, y];
}

/**
 * Generate SVG arc path for a sign segment.
 *
 * @param startAngle - Start angle in radians
 * @param endAngle - End angle in radians
 * @param outerRadius - Outer radius of the ring
 * @param innerRadius - Inner radius of the ring (for donut)
 * @param center - Center offset
 * @returns SVG path "d" attribute
 */
export function arcPath(
  startAngle: number,
  endAngle: number,
  outerRadius: number,
  innerRadius: number,
  center: number,
): string {
  const [x1o, y1o] = polarToCartesian(startAngle, outerRadius, center);
  const [x2o, y2o] = polarToCartesian(endAngle, outerRadius, center);
  const [x1i, y1i] = polarToCartesian(endAngle, innerRadius, center);
  const [x2i, y2i] = polarToCartesian(startAngle, innerRadius, center);

  const largeArc = endAngle - startAngle > Math.PI ? '1' : '0';

  return [
    `M ${x1o} ${y1o}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${x2o} ${y2o}`,
    `L ${x1i} ${y1i}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x2i} ${y2i}`,
    'Z',
  ].join(' ');
}

/**
 * Get the sign name for a given ecliptic longitude.
 */
export function longitudeToSign(longitude: number): string {
  const signs = [
    'aries', 'taurus', 'gemini', 'cancer',
    'leo', 'virgo', 'libra', 'scorpio',
    'sagittarius', 'capricorn', 'aquarius', 'pisces',
  ];
  const normalized = ((longitude % 360) + 360) % 360;
  const index = Math.floor(normalized / 30);
  return signs[index] ?? 'aries';
}

/**
 * Get the degree within the sign for a given longitude.
 */
export function longitudeToSignDegree(longitude: number): number {
  const normalized = ((longitude % 360) + 360) % 360;
  return normalized % 30;
}

/**
 * Compute the midpoint between two longitudes.
 */
export function midpoint(lonA: number, lonB: number): number {
  const diff = ((lonB - lonA + 360) % 360 + 360) % 360;
  return ((lonA + diff / 2 + 360) % 360 + 360) % 360;
}
