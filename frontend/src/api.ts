export type ConnectorState =
  | 'READY'
  | 'LIVE'
  | 'CREDENTIALS_REQUIRED'
  | 'PERMISSION_REQUIRED'
  | 'RATE_LIMITED'
  | 'NO_CREDITS'
  | 'DEGRADED'
  | 'DISABLED'
  | 'ERROR';

export interface ConnectorStatus {
  platform: string;
  state: ConnectorState;
  detail: string;
  source_mode?: 'LIVE' | 'REPLAY' | 'IMPORT' | null;
}

export interface TrendMetrics {
  score: number;
  status: string;
  current_bucket_volume: number;
  baseline_volume: number;
  growth_rate: number;
  burst_zscore: number;
  author_diversity: number;
  platform_count: number;
  engagement_signal: number;
  recency: number;
}

export interface NarrativeSummary {
  id: string;
  title: string;
  event_count: number;
  earliest_observed_at: string;
  latest_observed_at: string;
  earliest_event_id: string;
  earliest_platform: string;
  platform_mix: Record<string, number>;
  sentiment_mix: Record<string, number>;
  trend: TrendMetrics;
  representative_text: string;
  source_modes: Record<string, number>;
}

export interface Overview {
  total_events: number;
  platform_mix: Record<string, number>;
  source_modes: Record<string, number>;
  sentiment_mix: Record<string, number>;
  active_narratives: number;
  rising_narratives: number;
  alerts: number;
  top_narratives: NarrativeSummary[];
  latest_event_at?: string | null;
  coverage_note: string;
}

export interface TimelinePoint {
  time: string;
  count: number;
  sentiments: Record<string, number>;
  platforms: Record<string, number>;
}

export interface GraphNode {
  id: string;
  label: string;
  platform: string;
  pagerank: number;
  betweenness: number;
  degree_centrality: number;
  community: number;
  role: string;
  explanation: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  types: string[];
}

export interface NetworkResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  summary: {
    nodes: number;
    edges: number;
    communities?: number;
    high_reach_nodes?: number;
    bridge_nodes?: number;
  };
}

export interface AlertItem {
  alert_id: string;
  title: string;
  severity: string;
  narrative_id: string;
  triggered_at: string;
  trend_score: number;
  why_triggered: string[];
  evidence_event_ids: string[];
  earliest_observed_event_id?: string | null;
  top_amplifiers: Array<{ pseudo_id: string; display: string; role: string; score: number }>;
  platform_mix: Record<string, number>;
  sentiment_shift: Record<string, number | string>;
  coverage_warning?: string | null;
  confidence: number;
}

export interface SocialEvent {
  id: string;
  platform: string;
  source_event_id: string;
  event_type: string;
  author_pseudo_id?: string | null;
  author_display?: string | null;
  text: string;
  language?: string | null;
  created_at: string;
  url?: string | null;
  source_mode: 'LIVE' | 'REPLAY' | 'IMPORT';
  sentiment_label?: string | null;
  sentiment_score?: number | null;
  emotion_scores: Record<string, number>;
  stance_label?: string | null;
  stance_confidence?: number | null;
  sarcasm_probability?: number | null;
  topic_terms: string[];
  narrative_cluster_id?: string | null;
  trend_score?: number | null;
}

export interface NarrativeDetail extends NarrativeSummary {
  events: SocialEvent[];
  lineage: Array<{
    event_id: string;
    platform: string;
    source_mode: string;
    created_at: string;
    author?: string | null;
    author_pseudo_id?: string | null;
    text: string;
    sentiment?: string | null;
    stance?: string | null;
    source_url?: string | null;
  }>;
  network: NetworkResponse;
  origin_claim: string;
}

export interface DemographicSlice {
  counts: Record<string, number>;
  coverage: number;
  confidence: number;
  minimum_group_size: number;
  method: string;
}

export interface DemographicsResponse {
  unique_anonymized_users: number;
  language: DemographicSlice;
  broad_geography: DemographicSlice;
  professional_interests: DemographicSlice;
  age_brackets: DemographicSlice;
  privacy_note: string;
}

const DIRECT_API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const JAVA_API = import.meta.env.VITE_JAVA_GATEWAY_URL || 'http://127.0.0.1:8080';
const USE_GATEWAY = String(import.meta.env.VITE_USE_JAVA_GATEWAY || 'false').toLowerCase() === 'true';
export const API_BASE = USE_GATEWAY ? `${JAVA_API}/api/gateway` : DIRECT_API;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  });

  if (!response.ok) {
    const raw = await response.text();
    let message = raw || `Request failed: ${response.status}`;
    try {
      const parsed = JSON.parse(raw);
      const detail = parsed.detail;
      message = typeof detail === 'string' ? detail : detail?.message || JSON.stringify(detail);
    } catch {
      // Keep raw response.
    }
    throw new Error(message);
  }

  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return (await response.text()) as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  connectorStatus: () => request<{ connectors: ConnectorStatus[] }>('/api/connectors/status'),
  overview: () => request<Overview>('/api/overview'),
  timeline: () => request<{ bucket_minutes: number; points: TimelinePoint[] }>('/api/timeline'),
  narratives: () => request<{ narratives: NarrativeSummary[] }>('/api/narratives'),
  narrative: (id: string) => request<NarrativeDetail>(`/api/narratives/${encodeURIComponent(id)}`),
  network: (id?: string) => request<NetworkResponse>(`/api/network${id ? `?narrative_id=${encodeURIComponent(id)}` : ''}`),
  demographics: () => request<DemographicsResponse>('/api/demographics'),
  alerts: () => request<{ alerts: AlertItem[] }>('/api/alerts'),
  events: () => request<{ events: SocialEvent[] }>('/api/events?limit=500&newest_first=true'),
  seedDemo: () =>
    request<{ inserted: number; total_events: number; message: string }>('/api/demo/seed', {
      method: 'POST',
      body: JSON.stringify({ reset: true }),
    }),
  pollTelegram: () =>
    request<{ inserted: number; total_events: number }>('/api/connectors/telegram/poll', {
      method: 'POST',
      body: JSON.stringify({ max_updates: 50 }),
    }),
  searchX: (query: string) =>
    request<{ inserted: number; total_events: number }>('/api/connectors/x/search', {
      method: 'POST',
      body: JSON.stringify({ query, max_results: 20 }),
    }),
  searchYouTube: (query: string) =>
    request<{ inserted: number; total_events: number }>('/api/connectors/youtube/search', {
      method: 'POST',
      body: JSON.stringify({ query, max_videos: 3, max_comments_per_video: 20 }),
    }),
};
