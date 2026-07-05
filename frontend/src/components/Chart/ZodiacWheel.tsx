/* ── SVG Zodiac Wheel ────────────────────────────────── */

import { useMemo, type FC } from 'react';
import type { ChartPayload, ChartBody, ChartAspect, AspectType, BodyKey } from '../../types/chart';
import SignSegment from './SignSegment';
import PlanetMarker from './PlanetMarker';
import AspectLine from './AspectLine';
import HouseCuspLine from './HouseCuspLine';

interface ZodiacWheelProps {
  chart: ChartPayload;
  /** Wheel diameter in px (default: 600) */
  size?: number;
  /** Whether to show houses (default: true) */
  showHouses?: boolean;
  /** Whether to show aspects (default: true) */
  showAspects?: boolean;
  /** Filter aspects by type */
  aspectFilter?: AspectType[];
  /** Highlighted body key */
  highlightedBody?: BodyKey | null;
  /** Click handler for body markers */
  onBodyClick?: (body: ChartBody) => void;
  /** Click handler for aspect lines */
  onAspectClick?: (aspect: ChartAspect) => void;
  /** Click handler for sign segments */
  onSignClick?: (sign: string) => void;
  /** Opacity for planet markers (default: 1) */
  planetOpacity?: number;
  /** Scale for planet markers (default: 1) */
  planetScale?: number;
}

/**
 * Main SVG ZodiacWheel component.
 *
 * Renders:
 * 1. Background ring with 12 zodiac sign segments (colored by element)
 * 2. House cusp lines (optional)
 * 3. Aspect lines between bodies (optional, filterable)
 * 4. Planet/body markers at computed polar positions
 *
 * The chart is celestial-oriented: 0° Aries at 12 o'clock, running clockwise.
 */
const ZodiacWheel: FC<ZodiacWheelProps> = ({
  chart,
  size = 600,
  showHouses = true,
  showAspects = true,
  aspectFilter,
  highlightedBody,
  onBodyClick,
  onAspectClick,
  onSignClick,
  planetOpacity = 1,
  planetScale = 1,
}) => {
  const center = size / 2;
  const padding = 40;
  const outerRadius = center - padding;
  const innerRadius = outerRadius * 0.7;
  const houseOuterRadius = outerRadius;
  const houseInnerRadius = innerRadius;
  const planetRadius = (outerRadius + innerRadius) / 2;

  // Filter aspects if a filter is provided
  const filteredAspects = useMemo(() => {
    if (!showAspects) return [];
    let aspects = chart.aspects;
    if (aspectFilter && aspectFilter.length > 0) {
      aspects = aspects.filter((a) => aspectFilter.includes(a.aspect_type));
    }
    // Only show major aspects by default for visual clarity
    return aspects.filter((a) => a.is_major);
  }, [chart.aspects, showAspects, aspectFilter]);

  // Create a map for quick body lookup
  const bodyMap = useMemo(() => {
    const map = new Map<string, ChartBody>();
    for (const body of chart.bodies) {
      map.set(body.body_key, body);
    }
    return map;
  }, [chart.bodies]);

  const allSigns: Array<ChartPayload['bodies'][0]['sign']> = [
    'aries', 'taurus', 'gemini', 'cancer',
    'leo', 'virgo', 'libra', 'scorpio',
    'sagittarius', 'capricorn', 'aquarius', 'pisces',
  ];

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="zodiac-wheel"
      role="img"
      aria-label={`${chart.chart_type} chart wheel`}
    >
      {/* Background circle */}
      <circle cx={center} cy={center} r={outerRadius + 2} fill="none" stroke="#374151" strokeWidth={1} />

      {/* 1. Sign segments */}
      {allSigns.map((sign) => (
        <SignSegment
          key={sign}
          sign={sign}
          outerRadius={outerRadius}
          innerRadius={innerRadius}
          center={center}
          onClick={onSignClick}
        />
      ))}

      {/* Inner zodiac ring border */}
      <circle cx={center} cy={center} r={innerRadius} fill="none" stroke="#374151" strokeWidth={0.5} opacity={0.5} />

      {/* 2. House cusps */}
      {showHouses &&
        chart.houses.map((house) => (
          <HouseCuspLine
            key={house.house_number}
            house={house}
            outerRadius={houseOuterRadius}
            innerRadius={houseInnerRadius}
            center={center}
          />
        ))}

      {/* 3. Aspect lines */}
      {filteredAspects.map((aspect, idx) => {
        const bodyA = bodyMap.get(aspect.body_a_key);
        const bodyB = bodyMap.get(aspect.body_b_key);
        if (!bodyA || !bodyB) return null;
        return (
          <AspectLine
            key={`aspect-${idx}`}
            aspect={aspect}
            bodyA={bodyA}
            bodyB={bodyB}
            radius={planetRadius}
            center={center}
            onClick={onAspectClick}
          />
        );
      })}

      {/* 4. Planet markers */}
      {chart.bodies.map((body) => (
        <PlanetMarker
          key={body.body_key}
          body={body}
          radius={planetRadius}
          center={center}
          highlighted={highlightedBody === body.body_key}
          onClick={onBodyClick}
          opacity={planetOpacity}
          scale={planetScale}
        />
      ))}

      {/* Center label */}
      <text
        x={center}
        y={center}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#6b7280"
        fontSize={12}
        className="pointer-events-none select-none"
      >
        {chart.chart_type.toUpperCase()}
      </text>
    </svg>
  );
};

export default ZodiacWheel;
