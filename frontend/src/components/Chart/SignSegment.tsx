/* ── SVG Sign Segment (12 zodiac arcs) ───────────────── */

import type { FC } from 'react';
import type { SignName } from '../../types/chart';
import { signIndex, arcPath, longitudeToAngle } from '../../utils/coordinates';
import { signGlyph, signLabel, signElement, elementColor } from '../../utils/glyphs';

interface SignSegmentProps {
  sign: SignName;
  outerRadius: number;
  innerRadius: number;
  center: number;
  onClick?: (sign: SignName) => void;
}

/**
 * Renders a single zodiac sign arc segment in the ZodiacWheel.
 *
 * Each segment spans 30° and is colored by element.
 * Includes a glyph and name label at the midpoint of the arc.
 */
const SignSegment: FC<SignSegmentProps> = ({
  sign,
  outerRadius,
  innerRadius,
  center,
  onClick,
}) => {
  const startAngle = longitudeToAngle(signIndex(sign) * 30);
  const endAngle = longitudeToAngle((signIndex(sign) + 1) * 30);

  const path = arcPath(startAngle, endAngle, outerRadius, innerRadius, center);

  const element = signElement(sign);
  const fillColor = elementColor(element);
  const midRadius = (outerRadius + innerRadius) / 2;
  const midAngle = (startAngle + endAngle) / 2;

  // Compensate for angle wrapping
  const adjustedMidAngle =
    endAngle < startAngle
      ? (startAngle + endAngle + 2 * Math.PI) / 2
      : midAngle;

  const labelX = center + midRadius * 0.75 * Math.cos(adjustedMidAngle);
  const labelY = center + midRadius * 0.75 * Math.sin(adjustedMidAngle);
  const glyphX = center + midRadius * 0.55 * Math.cos(adjustedMidAngle);
  const glyphY = center + midRadius * 0.55 * Math.sin(adjustedMidAngle);
  const labelOffset = 12; // degrees offset for sign name

  return (
    <g
      className="sign-segment cursor-pointer"
      onClick={() => onClick?.(sign)}
      role="button"
      aria-label={`${signLabel(sign)} sign`}
    >
      {/* Filled arc */}
      <path
        d={path}
        fill={fillColor}
        fillOpacity={0.08}
        stroke={fillColor}
        strokeOpacity={0.3}
        strokeWidth={0.5}
        className="hover:fill-opacity-20 transition-all"
      />
      {/* Sign glyph */}
      <text
        x={glyphX}
        y={glyphY}
        textAnchor="middle"
        dominantBaseline="central"
        fill={fillColor}
        fillOpacity={0.7}
        fontSize={outerRadius * 0.055}
        fontFamily="AstroGlyphs, serif"
        className="pointer-events-none select-none"
      >
        {signGlyph(sign)}
      </text>
      {/* Sign label at outer edge */}
      <text
        x={labelX}
        y={labelY}
        textAnchor="middle"
        dominantBaseline="central"
        fill={fillColor}
        fillOpacity={0.5}
        fontSize={outerRadius * 0.035}
        className="pointer-events-none select-none"
        transform={`rotate(${labelOffset}, ${labelX}, ${labelY})`}
      >
        {signLabel(sign)}
      </text>
    </g>
  );
};

export default SignSegment;
