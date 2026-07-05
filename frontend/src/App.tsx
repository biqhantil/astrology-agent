/* ── Root App Component ──────────────────────────────── */

import { useCallback, type FC } from 'react';
import AppShell from './components/Layout/AppShell';
import Workspace from './components/Layout/Workspace';
import { AuthProvider, useAuthContext } from './context/AuthContext';
import { ChartProvider, useChartContext } from './context/ChartContext';
import { SSEProvider, useSSEContext } from './context/SSEContext';
import type { SSEEventPayload } from './types/events';

/**
 * Inner app that uses all the contexts.
 * SSE events are dispatched to the ChartContext.
 */
const AppInner: FC = () => {
  const { state, dispatch } = useChartContext();
  const { isConnected } = useSSEContext();
  const { user } = useAuthContext();

  // Global SSE event handler dispatches to chart context
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
          // Handle component.render for specific component types
          if (event.data.component === 'LifePhaseTimeline') {
            // TODO: wire life phase data when available
            console.log('LifePhaseTimeline render requested', event.data.props);
          }
          break;
        case 'session.status':
          console.log('SSE session status:', event.data.status);
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
      <AppShell>
        <Workspace />
      </AppShell>
    </SSEProvider>
  );
};

/**
 * Root App with all context providers.
 * AuthProvider auto-login creates an anonymous session.
 */
const App: FC = () => {
  return (
    <AuthProvider autoLogin={true}>
      <ChartProvider>
        <AppInner />
      </ChartProvider>
    </AuthProvider>
  );
};

export default App;
