/* ── SVG Aspect Line between two body positions ──────── */

import type { FC } from 'react';
import type { ChartAspect, ChartBody } from '../../types/chart';
import { longitudeToAngle, polarToCartesian } from '../../utils/coordinates';
import { getAspectStyle } from '../../utils/aspectColors';

interface AspectLineProps {
  aspect: ChartAspect;
  bodyA: ChartBody;
  bodyB: ChartBody;
  radius: number;
  center: number;
  onClick?: (aspect: ChartAspect) => void;
}

/**
 * Renders an SVG line between two bodies representing an astrological aspect.
 *
 * Color-coded by aspect type:
 * - Trine: blue
 * - Square: red
 * - Sextile: green
 * - Conjunction: purple
 * - Opposition: orange
 * - Minor aspects: gray
 */
const AspectLine: FC<AspectLineProps> = ({
  aspect,
  bodyA,
  bodyB,
  radius,
  center,
  onClick,
}) => {
  const angleA = longitudeToAngle(bodyA.longitude);
  const angleB = longitudeToAngle(bodyB.longitude);

  const [x1, y1] = polarToCartesian(angleA, radius, center);
  const [x2, y2] = polarToCartesian(angleB, radius, center);

  const style = getAspectStyle(aspect.aspect_type);

  return (
    <line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke={style.color}
      strokeWidth={style.strokeWidth}
      strokeDasharray={style.strokeDasharray ?? 'none'}
      strokeOpacity={style.opacity}
      className="aspect-line cursor-pointer hover:stroke-opacity-100 transition-opacity"
      onClick={() => onClick?.(aspect)}
      role="button"
      aria-label={`${aspect.body_a_key} ${aspect.aspect_type} ${aspect.body_b_key} (orb: ${aspect.orb}°)`}
    >
      <title>{`${aspect.body_a_key} ${aspect.aspect_type} ${aspect.body_b_key}\nOrb: ${aspect.orb}°\nApplying: ${aspect.is_applying ? 'Yes' : 'No'}`}</title>
    </line>
  );
};

export default AspectLine;
