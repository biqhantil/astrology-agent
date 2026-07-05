/* ── SSE event type definitions ──────────────────────── */

import type { ChartPayload, ChartType, TransitSnapshot } from './chart';
import type { SynastryPayload } from './chart';
import type { LifePhase } from './chart';
import type { MessageRole } from './conversation';

/* ── SSE Event Names ─────────────────────────────────── */

export type SSEEventType =
  | 'chat.delta'
  | 'chat.tool_call'
  | 'chart.data'
  | 'transit.data'
  | 'synastry.data'
  | 'component.render'
  | 'session.status'
  | 'error';

/* ── Event Payloads ──────────────────────────────────── */

export interface ChatDeltaPayload {
  conversation_id: string;
  message_id: string;
  delta: string;
  finish_reason: string | null;
}

export interface ChatToolCallPayload {
  conversation_id: string;
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
}

export interface ChartDataPayload {
  chart_id: string;
  chart_type: ChartType;
  payload: ChartPayload;
  render_mode: 'replace' | 'overlay' | 'split';
}

export interface TransitDataPayload {
  chart_id: string;
  natal_chart_id: string;
  payload: TransitSnapshot;
  highlight_date?: string;
}

export interface SynastryDataPayload {
  synastry_id: string;
  chart_a: ChartPayload;
  chart_b: ChartPayload;
  inter_aspects: ChartPayload['aspects'];
  render_mode: 'bi_wheel' | 'composite' | 'aspect_table';
}

export interface ComponentRenderPayload {
  component: string;
  props: Record<string, unknown>;
  slot: 'sidebar' | 'main' | 'overlay';
}

export interface SessionStatusPayload {
  status: 'connected' | 'disconnected' | 'error';
  user_id?: string;
  active_chart_id?: string | null;
  queue_depth?: number;
}

export interface SSEErrorPayload {
  code: string;
  message: string;
}

/* ── Union type for all SSE events ───────────────────── */

export type SSEEventPayload =
  | { type: 'chat.delta'; data: ChatDeltaPayload }
  | { type: 'chat.tool_call'; data: ChatToolCallPayload }
  | { type: 'chart.data'; data: ChartDataPayload }
  | { type: 'transit.data'; data: TransitDataPayload }
  | { type: 'synastry.data'; data: SynastryDataPayload }
  | { type: 'component.render'; data: ComponentRenderPayload }
  | { type: 'session.status'; data: SessionStatusPayload }
  | { type: 'error'; data: SSEErrorPayload };

/* ── Client-to-server SSE message types ──────────────── */

export type ClientMessageType = 'client.message' | 'client.ping';

export interface ClientMessagePayload {
  type: ClientMessageType;
  conversation_id: string;
  content?: string;
}
