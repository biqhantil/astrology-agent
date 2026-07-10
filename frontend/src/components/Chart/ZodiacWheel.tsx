/* ── SVG Zodiac Wheel — high-contrast astral map (deep black) ──
 *
 * Layout goals:
 * - Use near-full viewport (minimal padding)
 * - Wide outer bands for readable labels/glyphs
 * - Planet stacking by angular proximity (no overlap)
 * - Bright cream/amber on pure black
 */

import { useMemo, type FC } from 'react';
import type {
  ChartPayload,
  ChartBody,
  ChartAspect,
  AspectType,
  BodyKey,
  SignName,
} from '../../types/chart';
import {
  signIndex,
  arcPath,
  polarToCartesian,
  longitudeToAngle,
} from '../../utils/coordinates';
import { signGlyph, signLabel, bodyGlyph, bodyLabel, ANGLE_BODIES } from '../../utils/glyphs';
import { getAspectStyle } from '../../utils/aspectColors';

/** High-contrast palette on pure black */
const C = {
  amber: '#fbbf24',
  amberBright: '#fcd34d',
  amberDim: '#d97706',
  cream: '#f5f0e6',
  creamMuted: '#c8bfb0',
  black: '#000000',
  ink: '#050505',
  retro: '#f87171',
  highlight: '#e9d5ff',
} as const;

const SIGN_ABBR: Record<SignName, string> = {
  aries: 'ARI',
  taurus: 'TAU',
  gemini: 'GEM',
  cancer: 'CAN',
  leo: 'LEO',
  virgo: 'VIR',
  libra: 'LIB',
  scorpio: 'SCO',
  sagittarius: 'SAG',
  capricorn: 'CAP',
  aquarius: 'AQU',
  pisces: 'PIS',
};

// ── Public props ────────────────────────────────────────────────

export interface ZodiacWheelProps {
  chart: ChartPayload;
  size?: number;
  showHouses?: boolean;
  showAspects?: boolean;
  aspectFilter?: AspectType[];
  highlightedBody?: BodyKey | null;
  onBodyClick?: (body: ChartBody) => void;
  onAspectClick?: (aspect: ChartAspect) => void;
  onSignClick?: (sign: string) => void;
  planetOpacity?: number;
  planetScale?: number;
}

// ── Ring geometry ───────────────────────────────────────────────

interface SignRadii {
  outerRingOuter: number;
  outerRingInner: number;
  midRingOuter: number;
  midRingInner: number;
  tickRadius: number;
  planetOuter: number;
  planetInner: number;
  decorOuter: number;
  decorInner: number;
}

// ── Sign segment ────────────────────────────────────────────────

const SignSegment: FC<{
  sign: SignName;
  radii: SignRadii;
  center: number;
  onClick?: (sign: SignName) => void;
}> = ({ sign, radii, center, onClick }) => {
  const { outerRingOuter, outerRingInner, midRingOuter, midRingInner } = radii;

  const idx = signIndex(sign);
  const startAngle = longitudeToAngle(idx * 30);
  const endAngle = longitudeToAngle((idx + 1) * 30);
  const midAngle = idx * 30 + 15;

  const outerPath = arcPath(startAngle, endAngle, outerRingOuter, outerRingInner, center);
  const midPath = arcPath(startAngle, endAngle, midRingOuter, midRingInner, center);

  const midAngleRad = longitudeToAngle(midAngle + 90);
  const nameR = (outerRingOuter + outerRingInner) / 2;
  const glyphR = (midRingOuter + midRingInner) / 2;

  const nameX = center + nameR * Math.cos(midAngleRad);
  const nameY = center + nameR * Math.sin(midAngleRad);
  const glyphX = center + glyphR * Math.cos(midAngleRad);
  const glyphY = center + glyphR * Math.sin(midAngleRad);

  const nameSize = Math.max(11, outerRingOuter * 0.042);
  const glyphSize = Math.max(18, midRingOuter * 0.075);

  return (
    <g
      className="sign-segment cursor-pointer"
      onClick={() => onClick?.(sign)}
      role="button"
      aria-label={`${signLabel(sign)} sign`}
    >
      <title>{signLabel(sign)}</title>

      {/* Outer name band */}
      <path d={outerPath} fill="rgba(251,191,36,0.04)" stroke={C.amber} strokeOpacity={0.55} strokeWidth={1} />
      <text
        x={nameX}
        y={nameY}
        textAnchor="middle"
        dominantBaseline="central"
        fill={C.amberBright}
        fillOpacity={0.95}
        fontSize={nameSize}
        fontWeight="600"
        fontFamily="Inter, system-ui, sans-serif"
        letterSpacing="0.12em"
        className="pointer-events-none select-none"
      >
        {SIGN_ABBR[sign]}
      </text>

      {/* Glyph band */}
      <path d={midPath} fill="rgba(251,191,36,0.03)" stroke={C.amber} strokeOpacity={0.45} strokeWidth={0.9} />
      <text
        x={glyphX}
        y={glyphY}
        textAnchor="middle"
        dominantBaseline="central"
        fill={C.amber}
        fillOpacity={0.9}
        fontSize={glyphSize}
        fontFamily="Segoe UI Symbol, DejaVu Sans, AstroGlyphs, serif"
        className="pointer-events-none select-none"
        style={{ fontVariantEmoji: 'text' } as React.CSSProperties}
      >
        {signGlyph(sign)}
      </text>

      {/* Segment dividers */}
      {[startAngle, endAngle].map((angle, i) => {
        const [xOut, yOut] = polarToCartesian(angle, midRingInner, center);
        const [xIn, yIn] = polarToCartesian(angle, outerRingOuter, center);
        return (
          <line
            key={i}
            x1={xOut}
            y1={yOut}
            x2={xIn}
            y2={yIn}
            stroke={C.amber}
            strokeOpacity={0.4}
            strokeWidth={0.8}
          />
        );
      })}
    </g>
  );
};

// ── Degree ticks (replace cramped degree labels) ────────────────

const DegreeTicks: FC<{ radius: number; center: number }> = ({ radius, center }) => (
  <g className="degree-ticks pointer-events-none">
    {Array.from({ length: 72 }, (_, i) => {
      const deg = i * 5;
      const angle = longitudeToAngle(deg);
      const major = deg % 30 === 0;
      const mid = deg % 10 === 0;
      const len = major ? 8 : mid ? 5 : 3;
      const [x1, y1] = polarToCartesian(angle, radius, center);
      const [x2, y2] = polarToCartesian(angle, radius - len, center);
      return (
        <line
          key={deg}
          x1={x1}
          y1={y1}
          x2={x2}
          y2={y2}
          stroke={C.amber}
          strokeOpacity={major ? 0.55 : mid ? 0.35 : 0.2}
          strokeWidth={major ? 1.2 : 0.7}
        />
      );
    })}
  </g>
);

// ── Planet stacking (angular proximity → radial offset) ─────────

interface PlacedBody {
  body: ChartBody;
  angle: number;
  radius: number;
  stackIndex: number;
  kind: 'planet' | 'angle';
}

function placeBodies(
  bodies: ChartBody[],
  planetOuter: number,
  planetInner: number,
  angleRadius: number,
): PlacedBody[] {
  const angles = bodies.filter((b) => ANGLE_BODIES.has(b.body_key as BodyKey));
  const planets = bodies.filter((b) => !ANGLE_BODIES.has(b.body_key as BodyKey));

  const placed: PlacedBody[] = angles.map((body) => ({
    body,
    angle: longitudeToAngle(body.longitude),
    radius: angleRadius,
    stackIndex: 0,
    kind: 'angle' as const,
  }));

  const sorted = [...planets].sort((a, b) => a.longitude - b.longitude);
  const clusterGapDeg = 12;
  let cluster: ChartBody[] = [];

  const flush = () => {
    if (cluster.length === 0) return;
    const n = cluster.length;
    const span = Math.max(18, planetOuter - planetInner);
    // Fixed step so stacked bodies never share a radius
    const step = n === 1 ? 0 : span / Math.max(n - 1, 1);
    cluster.forEach((body, i) => {
      const radius = n === 1 ? planetOuter - span * 0.15 : planetOuter - i * step;
      placed.push({
        body,
        angle: longitudeToAngle(body.longitude),
        radius: Math.max(planetInner, radius),
        stackIndex: i,
        kind: 'planet',
      });
    });
    cluster = [];
  };

  for (let i = 0; i < sorted.length; i++) {
    if (cluster.length === 0) {
      cluster.push(sorted[i]);
      continue;
    }
    let d = sorted[i].longitude - sorted[i - 1].longitude;
    if (d < 0) d += 360;
    if (d < clusterGapDeg) cluster.push(sorted[i]);
    else {
      flush();
      cluster.push(sorted[i]);
    }
  }
  flush();
  return placed;
}

// ── Planet marker ───────────────────────────────────────────────

const PlanetMarker: FC<{
  body: ChartBody;
  angle: number;
  radius: number;
  center: number;
  ringEdge: number;
  kind: 'planet' | 'angle';
  stackIndex: number;
  highlighted?: boolean;
  onClick?: (body: ChartBody) => void;
  opacity?: number;
  scale?: number;
}> = ({
  body,
  angle,
  radius,
  center,
  ringEdge,
  kind,
  stackIndex,
  highlighted = false,
  onClick,
  opacity = 1,
  scale = 1,
}) => {
  const [x, y] = polarToCartesian(angle, radius, center);
  const [ex, ey] = polarToCartesian(angle, ringEdge, center);
  const glyph = bodyGlyph(body.body_key);
  const isAngle = kind === 'angle';
  const glyphSize = isAngle
    ? Math.max(11, 12 * scale)
    : Math.max(17, 20 * scale);
  const labelSize = Math.max(9, 10 * scale);
  const degreeText = `${Math.floor(body.sign_degree)}°`;
  const showDegree = !isAngle && stackIndex === 0;

  return (
    <g
      className={`planet-marker ${highlighted ? 'planet-highlighted' : ''} cursor-pointer`}
      onClick={() => onClick?.(body)}
      opacity={opacity}
      role="button"
      aria-label={`${bodyLabel(body.body_key)} at ${body.sign} ${body.sign_degree.toFixed(1)}°`}
    >
      <title>{`${bodyLabel(body.body_key)} · ${signLabel(body.sign)} ${body.sign_degree.toFixed(1)}°${body.is_retrograde ? ' ℞' : ''}`}</title>

      {!isAngle && (
        <line
          x1={ex} y1={ey} x2={x} y2={y}
          stroke={C.amberDim}
          strokeWidth={1}
          strokeOpacity={0.4}
        />
      )}

      <circle
        cx={x} cy={y}
        r={isAngle ? glyphSize * 0.95 : glyphSize * 0.78}
        fill={C.ink}
        stroke={highlighted ? C.highlight : C.amber}
        strokeWidth={highlighted ? 1.8 : isAngle ? 1.0 : 1.2}
        strokeOpacity={highlighted ? 0.95 : 0.65}
      />

      <text
        x={x} y={y}
        textAnchor="middle"
        dominantBaseline="central"
        fill={C.cream}
        fontSize={glyphSize}
        fontFamily="Segoe UI Symbol, DejaVu Sans, AstroGlyphs, sans-serif"
        fontWeight={isAngle ? 600 : 400}
        className="pointer-events-none select-none"
        style={{ fontVariantEmoji: 'text' } as React.CSSProperties}
      >
        {glyph}
      </text>

      {showDegree && (
        <text
          x={x}
          y={y + glyphSize * 0.95}
          textAnchor="middle"
          dominantBaseline="hanging"
          fill={C.creamMuted}
          fontSize={labelSize}
          fontFamily="ui-monospace, monospace"
          fontWeight="500"
          className="pointer-events-none select-none"
        >
          {degreeText}
          {body.is_retrograde ? ' ℞' : ''}
        </text>
      )}
    </g>
  );
};

// ── Aspect line ─────────────────────────────────────────────────

const AspectLine: FC<{
  aspect: ChartAspect;
  bodyA: ChartBody;
  bodyB: ChartBody;
  placements: Map<string, PlacedBody>;
  center: number;
  onClick?: (aspect: ChartAspect) => void;
}> = ({ aspect, bodyA, bodyB, placements, center, onClick }) => {
  const pa = placements.get(bodyA.body_key);
  const pb = placements.get(bodyB.body_key);
  if (!pa || !pb) return null;

  const [x1, y1] = polarToCartesian(pa.angle, pa.radius * 0.92, center);
  const [x2, y2] = polarToCartesian(pb.angle, pb.radius * 0.92, center);
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
      className="aspect-line cursor-pointer"
      onClick={() => onClick?.(aspect)}
      role="button"
      aria-label={`${aspect.body_a_key} ${aspect.aspect_type} ${aspect.body_b_key}`}
    >
      <title>{`${bodyLabel(aspect.body_a_key)} ${aspect.aspect_type} ${bodyLabel(aspect.body_b_key)} · orb ${aspect.orb}°`}</title>
    </line>
  );
};

// ── Subtle constellation decor ──────────────────────────────────

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

const ConstellationLines: FC<{
  innerRadius: number;
  outerRadius: number;
  center: number;
}> = ({ innerRadius, outerRadius, center }) => (
  <g className="constellation-lines pointer-events-none" opacity={0.22}>
    {Array.from({ length: 12 }, (_, idx) => {
      const rng = seededRandom(idx * 137 + 42);
      const count = 3 + Math.floor(rng() * 2);
      const points: [number, number][] = [];
      const startDeg = idx * 30;
      for (let i = 0; i < count; i++) {
        const deg = startDeg + 4 + rng() * 22;
        const angle = longitudeToAngle(deg);
        const r = innerRadius + rng() * (outerRadius - innerRadius);
        points.push([angle, r]);
      }
      return (
        <g key={idx}>
          {points.length > 1 && (
            <polyline
              points={points
                .map(([a, r]) => {
                  const [x, y] = polarToCartesian(a, r, center);
                  return `${x},${y}`;
                })
                .join(' ')}
              fill="none"
              stroke={C.amber}
              strokeWidth={0.4}
              strokeOpacity={0.5}
            />
          )}
          {points.map(([a, r], i) => {
            const [x, y] = polarToCartesian(a, r, center);
            return <circle key={i} cx={x} cy={y} r={1.2} fill={C.amberBright} fillOpacity={0.6} />;
          })}
        </g>
      );
    })}
  </g>
);

// ── Sacred geometry center ──────────────────────────────────────

const GeometricCenter: FC<{ radius: number; center: number }> = ({ radius, center }) => {
  const step = (2 * Math.PI) / 12;
  return (
    <g className="geometric-center pointer-events-none select-none">
      {[0.9, 0.65, 0.4].map((r, i) => (
        <circle
          key={i}
          cx={center}
          cy={center}
          r={radius * r}
          fill="none"
          stroke={C.amber}
          strokeOpacity={0.2 + i * 0.05}
          strokeWidth={0.8}
        />
      ))}
      {[0, 1].map((offset) => (
        <polygon
          key={offset}
          points={Array.from({ length: 6 }, (_, i) => {
            const angle = step * (i * 2 + offset) - Math.PI / 2;
            const r = radius * 0.75;
            return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
          }).join(' ')}
          fill="none"
          stroke={C.amber}
          strokeOpacity={0.28}
          strokeWidth={0.7}
        />
      ))}
      <circle cx={center} cy={center} r={radius * 0.08} fill={C.amber} fillOpacity={0.45} />
    </g>
  );
};

// ── Main wheel ──────────────────────────────────────────────────

export const ZodiacWheel: FC<ZodiacWheelProps> = ({
  chart,
  size = 640,
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
  // Minimal padding — reclaim dead space
  const padding = Math.max(6, size * 0.02);
  const outerRadius = center - padding;

  const radii: SignRadii = {
    // Outer name band ~12% of radius
    outerRingOuter: outerRadius,
    outerRingInner: outerRadius * 0.88,
    // Glyph band ~10%
    midRingOuter: outerRadius * 0.88,
    midRingInner: outerRadius * 0.78,
    tickRadius: outerRadius * 0.78,
    // Planets use mid field (wide band for stacking)
    planetOuter: outerRadius * 0.70,
    planetInner: outerRadius * 0.42,
    decorOuter: outerRadius * 0.40,
    decorInner: outerRadius * 0.14,
  };

  const filteredAspects = useMemo(() => {
    if (!showAspects) return [];
    let aspects = chart.aspects;
    if (aspectFilter?.length) {
      aspects = aspects.filter((a) => aspectFilter.includes(a.aspect_type));
    }
    return aspects.filter((a) => a.is_major && a.orb <= 6);
  }, [chart.aspects, showAspects, aspectFilter]);

  const bodyMap = useMemo(() => {
    const map = new Map<string, ChartBody>();
    for (const body of chart.bodies) map.set(body.body_key, body);
    return map;
  }, [chart.bodies]);

  const placements = useMemo(
    () => placeBodies(
      chart.bodies,
      radii.planetOuter,
      radii.planetInner,
      (radii.tickRadius + radii.midRingInner) / 2,
    ),
    [chart.bodies, radii.planetOuter, radii.planetInner, radii.tickRadius, radii.midRingInner],
  );

  const placementMap = useMemo(() => {
    const m = new Map<string, PlacedBody>();
    for (const p of placements) m.set(p.body.body_key, p);
    return m;
  }, [placements]);

  const allSigns: SignName[] = [
    'aries', 'taurus', 'gemini', 'cancer',
    'leo', 'virgo', 'libra', 'scorpio',
    'sagittarius', 'capricorn', 'aquarius', 'pisces',
  ];

  // Scale glyphs with wheel size
  const baseScale = (size / 600) * planetScale;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="zodiac-wheel"
      role="img"
      aria-label={`${chart.chart_type} chart wheel`}
      style={{ background: C.black, maxWidth: '100%', height: 'auto', display: 'block' }}
    >
      {/* Solid deep black disc */}
      <circle cx={center} cy={center} r={outerRadius + padding * 0.5} fill={C.black} />

      {allSigns.map((sign) => (
        <SignSegment
          key={sign}
          sign={sign}
          radii={radii}
          center={center}
          onClick={onSignClick}
        />
      ))}

      <DegreeTicks radius={radii.tickRadius} center={center} />

      <ConstellationLines
        innerRadius={radii.decorInner}
        outerRadius={radii.decorOuter}
        center={center}
      />

      <GeometricCenter radius={radii.decorInner} center={center} />

      {/* Aspects under planets */}
      <g className="aspects">
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
              placements={placementMap}
              center={center}
              onClick={onAspectClick}
            />
          );
        })}
      </g>

      {/* Planets */}
      <g className="planets">
        {placements.map((p) => (
          <PlanetMarker
            key={p.body.body_key}
            body={p.body}
            angle={p.angle}
            radius={p.radius}
            center={center}
            ringEdge={radii.tickRadius}
            kind={p.kind}
            stackIndex={p.stackIndex}
            highlighted={highlightedBody === p.body.body_key}
            onClick={onBodyClick}
            opacity={planetOpacity}
            scale={baseScale}
          />
        ))}
      </g>
    </svg>
  );
};

export default ZodiacWheel;
