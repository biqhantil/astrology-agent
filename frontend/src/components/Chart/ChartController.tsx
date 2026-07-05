/* ── Chart Controller — state machine for chart views ── */

import type { FC } from 'react';
import { useChartContext } from '../../context/ChartContext';
import ZodiacWheel from './ZodiacWheel';
import ChartDetailPanel from './ChartDetailPanel';

/**
 * ChartController manages which chart view is shown based on the
 * ChartContext's render mode and available data.
 *
 * View states:
 * - No chart: "Calculate a chart to see your birth chart" placeholder
 * - Natal chart: Single ZodiacWheel
 * - Transit overlay: ZodiacWheel with transit data overlaid
 * - Synastry bi-wheel: Two overlapping ZodiacWheels
 * - Life phases: LifePhaseTimeline (placeholder)
 * - Loading: Spinner
 * - Error: Error message
 */
const ChartController: FC = () => {
  const { state } = useChartContext();
  const { activeChart, transitData, synastryData, loading, error } = state;

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <svg
          className="animate-spin h-8 w-8 mr-2"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <span className="text-sm">Loading chart...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-2">⚠️</div>
          <p className="text-red-400/80 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!activeChart) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center max-w-sm">
          <div className="text-4xl mb-3 opacity-30">♄</div>
          <p className="text-gray-500 text-sm">
            No chart loaded. Set up your birth profile or ask the astrologer
            to calculate your chart.
          </p>
        </div>
      </div>
    );
  }

  // Synastry bi-wheel view
  if (synastryData && state.renderMode === 'split') {
    // Note: Full SynastryBiWheel will be implemented in a later chunk
    return (
      <div className="p-4 space-y-4">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
          <span>Synastry</span>
          <span className="text-gray-600">·</span>
          <span className="text-accent-light">{synastryData.relationship_type ?? 'Comparison'}</span>
        </div>
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1 flex flex-col items-center">
            <span className="text-xs text-gray-500 mb-2">Chart A</span>
            <ZodiacWheel chart={synastryData.chart_a} size={300} planetScale={0.8} />
          </div>
          <div className="flex-1 flex flex-col items-center">
            <span className="text-xs text-gray-500 mb-2">Chart B</span>
            <ZodiacWheel chart={synastryData.chart_b} size={300} planetScale={0.8} />
          </div>
        </div>
        <ChartDetailPanel chart={activeChart} />
      </div>
    );
  }

  // Transit overlay (render transit data alongside the natal chart)
  if (transitData) {
    return (
      <div className="p-4 space-y-4">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
          <span>Transits</span>
          <span className="text-gray-600">·</span>
          <span className="text-gray-500">
            {transitData.date_from} to {transitData.date_to}
          </span>
          <span className="text-gray-600">·</span>
          <span className="text-accent-light">{transitData.events.length} events</span>
        </div>
        <div className="flex justify-center">
          <ZodiacWheel chart={activeChart} size={400} />
        </div>
        <ChartDetailPanel chart={activeChart} />
      </div>
    );
  }

  // Default: single chart view
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
        <span className="capitalize">{activeChart.chart_type} Chart</span>
        {activeChart.title && (
          <>
            <span className="text-gray-600">·</span>
            <span>{activeChart.title}</span>
          </>
        )}
      </div>

      <div className="flex flex-col items-center">
        <ZodiacWheel chart={activeChart} size={400} />
      </div>

      <ChartDetailPanel chart={activeChart} />
    </div>
  );
};

export default ChartController;
