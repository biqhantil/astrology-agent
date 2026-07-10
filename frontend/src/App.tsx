/* ── Root App Component ──────────────────────────────── */

import { useCallback, type FC } from 'react';
import AppShell from './components/Layout/AppShell';
import Workspace from './components/Layout/Workspace';
import { AuthProvider } from './context/AuthContext';
import { ChartProvider, useChartContext } from './context/ChartContext';
import { SSEProvider, useSSEContext } from './context/SSEContext';
import { I18nProvider } from './i18n/I18nContext';
import type { SSEEventPayload } from './types/events';

/**
 * Middle component that bridges ChartContext dispatch into SSEProvider's onEvent.
 * Renders SSEProvider so AppInner can consume useSSEContext().
 */
const AppWithSSE: FC = () => {
  const { dispatch } = useChartContext();

  const handleSSEEvent = useCallback(
    (event: SSEEventPayload) => {
      switch (event.type) {
        case 'chart.data':
          dispatch({
            type: 'SET_CHART',
            payload: event.data.payload,
            renderMode: event.data.render_mode,
          });
          break;
        case 'transit.data':
          dispatch({
            type: 'SET_TRANSIT',
            payload: event.data.payload,
          });
          break;
        case 'synastry.data':
          dispatch({
            type: 'SET_SYNASTRY',
            payload: {
              id: event.data.synastry_id,
              chart_a: event.data.chart_a,
              chart_b: event.data.chart_b,
              inter_aspects: event.data.inter_aspects,
              house_overlays: [],
              render_mode: event.data.render_mode,
            },
          });
          break;
        case 'component.render':
          if (event.data.component === 'LifePhaseTimeline') {
            console.log('LifePhaseTimeline render requested', event.data.props);
          }
          break;
        case 'error':
          dispatch({ type: 'SET_ERROR', payload: event.data.message });
          break;
        default:
          break;
      }
    },
    [dispatch],
  );

  return (
    <SSEProvider onEvent={handleSSEEvent}>
      <AppInner />
    </SSEProvider>
  );
};

/**
 * Inner app that uses all contexts.
 */
const AppInner: FC = () => {
  // Keep SSE context subscribed so the stream stays active under the shell.
  useSSEContext();

  return (
    <AppShell>
      <Workspace />
    </AppShell>
  );
};

/**
 * Root App with all context providers.
 */
const App: FC = () => {
  return (
    <I18nProvider>
      <AuthProvider autoLogin={true}>
        <ChartProvider>
          <AppWithSSE />
        </ChartProvider>
      </AuthProvider>
    </I18nProvider>
  );
};

export default App;
