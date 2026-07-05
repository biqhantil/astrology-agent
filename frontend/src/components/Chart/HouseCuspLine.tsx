/* ── SVG House Cusp Line ─────────────────────────────── */

import type { FC } from 'react';
import type { ChartHouse } from '../../types/chart';
import { longitudeToAngle, polarToCartesian } from '../../utils/coordinates';

interface HouseCuspLineProps {
  house: ChartHouse;
  outerRadius: number;
  innerRadius: number;
  center: number;
}

/**
 * Renders a line from the inner to outer radius at the house cusp longitude,
 * plus a house number label at the inner edge.
 */
const HouseCuspLine: FC<HouseCuspLineProps> = ({
  house,
  outerRadius,
  innerRadius,
  center,
}) => {
  const angle = longitudeToAngle(house.cusps_longitude);
  const [xOut, yOut] = polarToCartesian(angle, outerRadius, center);
  const [xIn, yIn] = polarToCartesian(angle, innerRadius, center);
  const [xLabel, yLabel] = polarToCartesian(
    angle,
    innerRadius - 16,
    center,
  );

  return (
    <g className="house-cusp">
      {/* Cusp line */}
      <line
        x1={xIn}
        y1={yIn}
        x2={xOut}
        y2={yOut}
        stroke="#4b5563"
        strokeWidth={1}
        strokeOpacity={0.6}
      />
      {/* House number label */}
      <text
        x={xLabel}
        y={yLabel}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#6b7280"
        fontSize={10}
        fontWeight="600"
        className="pointer-events-none select-none"
      >
        {house.house_number}
      </text>
    </g>
  );
};

export default HouseCuspLine;
