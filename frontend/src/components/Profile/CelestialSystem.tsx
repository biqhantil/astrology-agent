/* ── Animated solar system — fixed viewBox, full-viewport fill ── */

import { useMemo, type FC } from 'react';

// ── Constants ───────────────────────────────────────────

const VB_LEFT = -700;
const VB_TOP = -500;
const VB_W = 1400;
const VB_H = 1000;

const PLANETS: { name: string; glyph: string; orbit: number; speed: number; phase: number; size: number; color: string; tiltY: number }[] = [
  { name: 'mercury', glyph: '☿', orbit: 60,  speed: 12,   phase: 0,   size: 8,  color: '#d4c5a9', tiltY: 0.55 },
  { name: 'venus',   glyph: '♀', orbit: 90,  speed: 7,    phase: 1.2, size: 10, color: '#f0dfc0', tiltY: 0.45 },
  { name: 'earth',   glyph: '♁', orbit: 120, speed: 5,    phase: 2.8, size: 11, color: '#8ab8cc', tiltY: 0.4 },
  { name: 'mars',    glyph: '♂', orbit: 150, speed: 3.5,  phase: 4.1, size: 10, color: '#e07040', tiltY: 0.5 },
  { name: 'jupiter', glyph: '♃', orbit: 195, speed: 2,    phase: 0.7, size: 18, color: '#f0a050', tiltY: 0.45 },
  { name: 'saturn',  glyph: '♄', orbit: 240, speed: 1.2,  phase: 3.3, size: 16, color: '#cc9630', tiltY: 0.5 },
  { name: 'uranus',  glyph: '♅', orbit: 285, speed: 0.6,  phase: 5.0, size: 13, color: '#90d0e0', tiltY: 0.4 },
];

// ── Stars ───────────────────────────────────────────────

function Stars({ count = 600, opacityScale = 1 }: { count?: number; opacityScale?: number }) {
  const stars = useMemo(() => {
    const result = [];
    const margin = 0.05;
    for (let i = 0; i < count; i++) {
      // Distribute across the full viewBox with slight margin
      const x = VB_LEFT * (1 - margin) + Math.random() * VB_W * (1 + margin * 2);
      const y = VB_TOP * (1 - margin) + Math.random() * VB_H * (1 + margin * 2);
      // Size distribution: mostly small, some medium, rare large
      let r: number;
      const roll = Math.random();
      if (roll > 0.98) r = 3.5;
      else if (roll > 0.9) r = 2;
      else if (roll > 0.7) r = 1.2;
      else r = 0.6 + Math.random() * 0.3;
      result.push({
        x, y, r,
        baseOpacity: (0.35 + Math.random() * 0.65) * opacityScale,
        // Each star gets its own unique blink timing
        blinkLow: 0.05 + Math.random() * 0.15,
        delay: Math.random() * 10,
        dur: 2 + Math.random() * 6,
      });
    }
    return result;
  }, [count, opacityScale]);

  return (
    <g>
      {stars.map((s, i) => (
        <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="#e8dcc8" opacity={s.baseOpacity}>
          <animate attributeName="opacity"
            values={`${s.baseOpacity};${s.baseOpacity * s.blinkLow};${s.baseOpacity}`}
            dur={`${s.dur}s`} begin={`${s.delay}s`} repeatCount="indefinite" />
        </circle>
      ))}
    </g>
  );
}

// ── Sun ─────────────────────────────────────────────────

function SunGlow() {
  return (
    <g>
      <circle cx={0} cy={0} r={55} fill="#d97706" opacity={0.08}>
        <animate attributeName="r" values="55;72;55" dur="4s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.08;0.04;0.08" dur="4s" repeatCount="indefinite" />
      </circle>
      <circle cx={0} cy={0} r={35} fill="#d97706" opacity={0.16}>
        <animate attributeName="r" values="35;48;35" dur="4s" begin="0.5s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.16;0.07;0.16" dur="4s" begin="0.5s" repeatCount="indefinite" />
      </circle>
      <circle cx={0} cy={0} r={22} fill="#f59e0b" opacity={0.3}>
        <animate attributeName="r" values="22;30;22" dur="4s" begin="1s" repeatCount="indefinite" />
      </circle>
      <circle cx={0} cy={0} r={12} fill="#fbbf24" opacity={0.65} />
      <circle cx={0} cy={0} r={6} fill="#fef3c7" />
      <line x1={-18} y1={0} x2={18} y2={0} stroke="#fbbf24" strokeWidth="0.8" opacity="0.18" />
      <line x1={0} y1={-18} x2={0} y2={18} stroke="#fbbf24" strokeWidth="0.8" opacity="0.18" />
      <circle cx={0} cy={0} r={18} fill="none" stroke="#fbbf24" strokeWidth="0.4" opacity="0.12" />
    </g>
  );
}

// ── Component ───────────────────────────────────────────

const CelestialSystem: FC = () => {
  return (
    <div className="relative w-full h-full overflow-hidden bg-black">
      <svg viewBox={`${VB_LEFT} ${VB_TOP} ${VB_W} ${VB_H}`}
        className="w-full h-full" preserveAspectRatio="xMidYMid slice"
        style={{ background: 'transparent' }}>
        {/* Full-viewport stars — 800 organic stars with individual blink */}
        <Stars count={800} />
        <Stars count={200} opacityScale={0.3} />

        {/* Orbital paths */}
        {PLANETS.map(p => (
          <ellipse key={p.name} cx={0} cy={0} rx={p.orbit} ry={p.orbit * p.tiltY}
            fill="none" stroke="rgba(212,197,169,0.04)" strokeWidth="0.6" />
        ))}

        {/* Sun — center-right of viewBox, roughly at 1/3 from left */}
        <g transform="translate(-60, 0)">
          <SunGlow />
        </g>

        {/* Planets — shifted to center-right */}
        <g transform="translate(-60, 0)">
          {PLANETS.map(p => (
            <g key={p.name}>
              <g>
                <animateMotion
                  dur={`${40 / p.speed}s`}
                  repeatCount="indefinite"
                  path={
                    `M0,0 m${p.orbit},0 ` +
                    `a${p.orbit},${p.orbit * p.tiltY} 0 1,0 -${p.orbit * 2},0 ` +
                    `a${p.orbit},${p.orbit * p.tiltY} 0 1,0 ${p.orbit * 2},0`
                  }
                  rotate="auto"
                  begin={`-${p.phase * 5}s`}
                />
                <circle cx={0} cy={0} r={p.size} fill={p.color} opacity={0.9}>
                  <animate attributeName="opacity" values="0.9;0.55;0.9"
                    dur={`${3 + (p.name.length % 3)}s`} repeatCount="indefinite" />
                </circle>
                {p.name === 'saturn' && (
                  <ellipse cx={0} cy={0} rx={p.size * 2.5} ry={p.size * 0.5}
                    fill="none" stroke="#cc9630" strokeWidth="1.2" opacity="0.3"
                    transform="rotate(-20)" />
                )}
                <text x={p.size + 12} y={5} fontSize="15" fill={p.color}
                  opacity="0.85" fontFamily="serif" fontWeight="600">
                  {p.glyph}
                </text>
              </g>
            </g>
          ))}
        </g>

        {/* Outer rings */}
        <circle cx={0} cy={0} r={360} fill="none" stroke="rgba(212,197,169,0.025)"
          strokeWidth="0.5" strokeDasharray="3 10">
          <animateTransform attributeName="transform" type="rotate"
            from="0" to="360" dur="150s" repeatCount="indefinite" />
        </circle>
        <circle cx={0} cy={0} r={380} fill="none" stroke="rgba(212,197,169,0.015)"
          strokeWidth="0.5" strokeDasharray="1 6">
          <animateTransform attributeName="transform" type="rotate"
            from="360" to="0" dur="200s" repeatCount="indefinite" />
        </circle>
      </svg>
    </div>
  );
};

export default CelestialSystem;
