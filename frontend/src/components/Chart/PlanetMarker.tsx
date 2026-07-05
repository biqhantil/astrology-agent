/* ── SVG Planet Marker on the Zodiac Wheel ───────────── */

import type { FC } from 'react';
import type { ChartBody } from '../../types/chart';
import { longitudeToAngle, polarToCartesian } from '../../utils/coordinates';
import { bodyGlyph, bodyLabel } from '../../utils/glyphs';

interface PlanetMarkerProps {
  body: ChartBody;
  radius: number;      // radius at which to place the marker
  center: number;
  highlighted?: boolean;
  onClick?: (body: ChartBody) => void;
  /** Opacity for outer/transit bodies (0-1) */
  opacity?: number;
  /** Font size multiplier (default: 1) */
  scale?: number;
}

/**
 * Renders a planet/body marker at the correct polar position on the wheel.
 *
 * Includes:
 * - Glyph symbol
 * - Degree label
 * - Retrograde badge (if retrograde)
 * - Click handler
 */
const PlanetMarker: FC<PlanetMarkerProps> = ({
  body,
  radius,
  center,
  highlighted = false,
  onClick,
  opacity = 1,
  scale = 1,
}) => {
  const angle = longitudeToAngle(body.longitude);
  const [x, y] = polarToCartesian(angle, radius, center);

  const glyph = bodyGlyph(body.body_key);
  const glyphSize = 16 * scale;
  const degreeText = `${Math.floor(body.sign_degree)}°${body.sign.slice(0, 3).toUpperCase()}`;
  const retrogradeText = body.is_retrograde ? '℞' : '';

  return (
    <g
      className={`planet-marker ${highlighted ? 'planet-highlighted' : ''} cursor-pointer`}
      onClick={() => onClick?.(body)}
      opacity={opacity}
      role="button"
      aria-label={`${bodyLabel(body.body_key)} at ${body.sign} ${body.sign_degree.toFixed(1)}°`}
    >
      {/* Highlight ring */}
      {highlighted && (
        <circle
          cx={x}
          cy={y}
          r={glyphSize * 0.8}
          fill="none"
          stroke="#c084fc"
          strokeWidth={1.5}
          strokeDasharray="3,2"
          opacity={0.6}
        />
      )}

      {/* Brief connecting line from body to ring */}
      <line
        x1={center + radius * 0.85 * Math.cos(angle)}
        y1={center + radius * 0.85 * Math.sin(angle)}
        x2={x}
        y2={y}
        stroke="#6b7280"
        strokeWidth={0.5}
        strokeOpacity={0.4}
      />

      {/* Glyph */}
      <text
        x={x}
        y={y}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#e5e7eb"
        fontSize={glyphSize}
        fontFamily="AstroGlyphs, sans-serif"
        fontWeight={body.is_retrograde ? 'bold' : 'normal'}
        className="pointer-events-none select-none"
      >
        {glyph}
      </text>

      {/* Degree label below glyph */}
      {body.house && (
        <text
          x={x}
          y={y + glyphSize * 0.7}
          textAnchor="middle"
          dominantBaseline="central"
          fill="#9ca3af"
          fontSize={9 * scale}
          className="pointer-events-none select-none"
        >
          {degreeText}
        </text>
      )}

      {/* Retrograde badge */}
      {body.is_retrograde && (
        <text
          x={x + glyphSize * 0.6}
          y={y - glyphSize * 0.5}
          textAnchor="middle"
          dominantBaseline="central"
          fill="#f87171"
          fontSize={11 * scale}
          fontWeight="bold"
          className="pointer-events-none select-none"
        >
          ℞
        </text>
      )}
    </g>
  );
};

export default PlanetMarker;
