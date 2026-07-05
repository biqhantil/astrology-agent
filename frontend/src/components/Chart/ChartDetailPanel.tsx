/* ── Chart Details Panel (planet list, aspect table) ─── */

import type { FC } from 'react';
import type { ChartPayload } from '../../types/chart';
import { bodyLabel, signLabel } from '../../utils/glyphs';

interface ChartDetailPanelProps {
  chart: ChartPayload;
}

/**
 * Shows a structured list of all chart bodies and their placements.
 * Used as a detail sidebar/below the ZodiacWheel.
 */
const ChartDetailPanel: FC<ChartDetailPanelProps> = ({ chart }) => {
  if (!chart.bodies.length) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No chart data available.
      </div>
    );
  }

  return (
    <div className="p-3 space-y-3">
      {/* Planet placement list */}
      <div>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Planetary Positions
        </h3>
        <div className="space-y-1">
          {chart.bodies.map((body) => (
            <div
              key={body.body_key}
              className="flex items-center justify-between text-sm py-0.5 px-2 rounded hover:bg-surface-light transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-200 w-20">
                  {bodyLabel(body.body_key)}
                </span>
                <span className="text-accent-light font-mono text-xs">
                  {body.is_retrograde ? '℞ ' : ''}
                  {signLabel(body.sign)} {body.sign_degree.toFixed(1)}°
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                {body.house && <span>H{body.house}</span>}
                {body.dignity && (
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      body.dignity === 'domicile'
                        ? 'bg-green-500/10 text-green-400'
                        : body.dignity === 'exaltation'
                          ? 'bg-blue-500/10 text-blue-400'
                          : body.dignity === 'detriment'
                            ? 'bg-red-500/10 text-red-400'
                            : body.dignity === 'fall'
                              ? 'bg-orange-500/10 text-orange-400'
                              : 'bg-gray-500/10 text-gray-400'
                    }`}
                  >
                    {body.dignity}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Aspect table (compact) */}
      {chart.aspects.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Aspects
          </h3>
          <div className="space-y-1">
            {chart.aspects
              .filter((a) => a.is_major)
              .map((aspect, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-sm py-0.5 px-2 rounded hover:bg-surface-light transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-gray-200">
                      {bodyLabel(aspect.body_a_key)}
                    </span>
                    <span className="text-gray-500 text-xs">{aspect.aspect_type}</span>
                    <span className="text-gray-200">
                      {bodyLabel(aspect.body_b_key)}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 font-mono">
                    orb {aspect.orb.toFixed(1)}°
                    {aspect.is_applying !== null && (
                      <span className="ml-1">
                        {aspect.is_applying ? '(app)' : '(sep)'}
                      </span>
                    )}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChartDetailPanel;
