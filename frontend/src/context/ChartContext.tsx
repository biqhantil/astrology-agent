/* ── Chart React Context ─────────────────────────────── */

import { createContext, useContext, useReducer, type ReactNode } from 'react';
import type {
  ChartPayload,
  TransitSnapshot,
  SynastryPayload,
  LifePhase,
  RenderMode,
} from '../types/chart';

/* ── State ───────────────────────────────────────────── */

interface ChartState {
  /** The currently active natal/event chart */
  activeChart: ChartPayload | null;
  /** Transit data overlaid on the active chart */
  transitData: TransitSnapshot | null;
  /** Synastry data for comparison view */
  synastryData: SynastryPayload | null;
  /** Life phase timeline data */
  lifePhases: LifePhase[];
  /** Current render mode for the ChartWorkspace */
  renderMode: RenderMode;
  /** Highlighted body key (e.g., for tooltip or emphasis) */
  highlightedBody: string | null;
  /** Whether a chart is loading */
  loading: boolean;
  /** Error message if chart loading failed */
  error: string | null;
}

const initialState: ChartState = {
  activeChart: null,
  transitData: null,
  synastryData: null,
  lifePhases: [],
  renderMode: 'replace',
  highlightedBody: null,
  loading: false,
  error: null,
};

/* ── Actions ─────────────────────────────────────────── */

type ChartAction =
  | { type: 'SET_CHART'; payload: ChartPayload; renderMode?: RenderMode }
  | { type: 'SET_TRANSIT'; payload: TransitSnapshot }
  | { type: 'SET_SYNASTRY'; payload: SynastryPayload }
  | { type: 'SET_LIFE_PHASES'; payload: LifePhase[] }
  | { type: 'SET_RENDER_MODE'; payload: RenderMode }
  | { type: 'HIGHLIGHT_BODY'; payload: string | null }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'CLEAR_CHART' };

function chartReducer(state: ChartState, action: ChartAction): ChartState {
  switch (action.type) {
    case 'SET_CHART':
      return {
        ...state,
        activeChart: action.payload,
        renderMode: action.renderMode ?? state.renderMode,
        loading: false,
        error: null,
      };
    case 'SET_TRANSIT':
      return {
        ...state,
        transitData: action.payload,
        loading: false,
        error: null,
      };
    case 'SET_SYNASTRY':
      return {
        ...state,
        synastryData: action.payload,
        loading: false,
        error: null,
      };
    case 'SET_LIFE_PHASES':
      return {
        ...state,
        lifePhases: action.payload,
        loading: false,
        error: null,
      };
    case 'SET_RENDER_MODE':
      return { ...state, renderMode: action.payload };
    case 'HIGHLIGHT_BODY':
      return { ...state, highlightedBody: action.payload };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'CLEAR_CHART':
      return { ...initialState };
    default:
      return state;
  }
}

/* ── Context ─────────────────────────────────────────── */

interface ChartContextValue {
  state: ChartState;
  dispatch: React.Dispatch<ChartAction>;
}

const ChartContext = createContext<ChartContextValue | null>(null);

/* ── Provider ────────────────────────────────────────── */

interface ChartProviderProps {
  children: ReactNode;
}

export function ChartProvider({ children }: ChartProviderProps) {
  const [state, dispatch] = useReducer(chartReducer, initialState);

  return (
    <ChartContext.Provider value={{ state, dispatch }}>
      {children}
    </ChartContext.Provider>
  );
}

/* ── Hook ────────────────────────────────────────────── */

export function useChartContext(): ChartContextValue {
  const ctx = useContext(ChartContext);
  if (!ctx) {
    throw new Error('useChartContext must be used within a ChartProvider');
  }
  return ctx;
}
