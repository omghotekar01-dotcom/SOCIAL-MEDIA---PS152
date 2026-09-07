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
  author_platform_id?: string | null;
  author_pseudo_id?: string | null;
  author_display?: string | null;
  text: string;
  language?: string | null;
  created_at: string;
  ingested_at?: string;
  url?: string | null;
  parent_event_id?: string | null;
  conversation_id?: string | null;
  mentions: string[];
  hashtags: string[];
  urls: string[];
  engagement: Record<string, number | string | null>;
  public_profile: Record<string, unknown>;
  source_mode: 'LIVE' | 'REPLAY' | 'IMPORT';
  connector_run_id?: string | null;
  raw_hash?: string;
  sentiment_label?: string | null;
  sentiment_score?: number | null;
  emotion_scores: Record<string, number>;
  stance_label?: string | null;
  stance_confidence?: number | null;
  sarcasm_probability?: number | null;
  topic_terms: string[];
  narrative_cluster_id?: string | null;
  trend_score?: number | null;
  quality_score?: number | null;
  inference_method?: string | null;
}

export interface WorkspaceSearchResponse {
  received: number;
  inserted: number;
  duplicates: number;
  total_events: number;
  query: string;
  search_session_id: string;
  reset: boolean;
  message: string;
  sources: Record<string, { state: string; received: number; detail?: string; connector?: string }>;
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
    engagement?: Record<string, unknown>;
    public_profile?: Record<string, unknown>;
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

export interface CollectorStatus {
  running: boolean;
  config?: {
    query: string;
    interval_seconds: number;
    enable_telegram: boolean;
    enable_x: boolean;
    enable_youtube: boolean;
  } | null;
  cycles: number;
  last_run_at?: string | null;
  last_result?: Record<string, unknown>;
  note: string;
}

type IngestResult = {
  received?: number;
  inserted: number;
  duplicates?: number;
  total_events: number;
  connector?: string;
  platform?: string;
  source_mode?: string;
};

type SearchOptions = {
  reset?: boolean;
  limitPerSource?: number;
  telegramChannel?: string;
  instagramProfile?: string;
};

const DIRECT_API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const JAVA_API = import.meta.env.VITE_JAVA_GATEWAY_URL || 'http://127.0.0.1:8080';
const USE_GATEWAY = String(import.meta.env.VITE_USE_JAVA_GATEWAY || 'false').toLowerCase() === 'true';
export const API_BASE = USE_GATEWAY ? `${JAVA_API}/api/gateway` : DIRECT_API;

const YOUTUBE_ID_RE = /^[A-Za-z0-9_-]{11}$/;
const YOUTUBE_URL_RE = /(?:youtube\.com\/(?:watch\?(?:[^#\s]*&)?v=|shorts\/|live\/|embed\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/i;

export function isExactYouTubeTarget(value: string): boolean {
  const clean = value.trim();
  return YOUTUBE_ID_RE.test(clean) || YOUTUBE_URL_RE.test(clean);
}

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
  if (!contentType.includes('application/json')) return (await response.text()) as T;
  return response.json() as Promise<T>;
}

async function officialYouTubeSearch(query: string, maxVideos: number, maxComments: number): Promise<IngestResult> {
  return request<IngestResult>('/api/connectors/youtube/search', {
    method: 'POST',
    body: JSON.stringify({
      query,
      max_videos: maxVideos,
      max_comments_per_video: maxComments,
    }),
  });
}

async function smartWorkspaceSearch(query: string, options?: SearchOptions): Promise<WorkspaceSearchResponse> {
  const clean = query.trim();
  const reset = options?.reset ?? true;
  const limit = options?.limitPerSource ?? 15;

  // Exact YouTube URLs/video IDs are conversation targets, not cross-platform
  // keywords. Route directly to the official Data API so Fresh Search collects
  // the root video + public comments + nested replies instead of creating a
  // zero-key `free:<video_id>` metadata-only record.
  if (isExactYouTubeTarget(clean)) {
    if (reset) {
      await request<{ status: string; total_events: number }>('/api/workspace/reset', {
        method: 'POST',
        body: '{}',
      });
    }

    const youtube = await officialYouTubeSearch(clean, 1, 100);
    const received = Number(youtube.received ?? youtube.inserted ?? 0);
    return {
      received,
      inserted: Number(youtube.inserted || 0),
      duplicates: Number(youtube.duplicates || 0),
      total_events: Number(youtube.total_events || 0),
      query: clean,
      search_session_id: `youtube-direct-${Date.now()}`,
      reset,
      message: 'Exact YouTube conversation loaded through YouTube Data API v3 with public comments/replies where available.',
      sources: {
        youtube: {
          state: 'OK',
          received,
          connector: 'youtube_data_api_v3',
        },
      },
    };
  }

  // For normal topic search, use the official YouTube connector whenever the
  // backend reports that the API key is ready. Other public sources remain
  // independent so a YouTube failure never destroys the rest of the workspace.
  let youtubeOfficialReady = false;
  try {
    const status = await request<{ connectors: ConnectorStatus[] }>('/api/connectors/status');
    const youtube = status.connectors.find((item) => item.platform === 'youtube');
    youtubeOfficialReady = !!youtube && (youtube.state === 'READY' || youtube.state === 'LIVE');
  } catch {
    // If status discovery itself fails, preserve the existing backend workspace
    // path rather than blocking all source collection.
  }

  const base = await request<WorkspaceSearchResponse>('/api/search/workspace', {
    method: 'POST',
    body: JSON.stringify({
      query: clean,
      reset,
      limit_per_source: limit,
      enable_youtube: !youtubeOfficialReady,
      enable_bluesky: true,
      enable_reddit: true,
      enable_mastodon: true,
      telegram_channel: options?.telegramChannel || null,
      instagram_profile: options?.instagramProfile || null,
    }),
  });

  if (!youtubeOfficialReady) return base;

  try {
    const youtube = await officialYouTubeSearch(clean, 3, 100);
    const received = Number(youtube.received ?? youtube.inserted ?? 0);
    return {
      ...base,
      received: base.received + received,
      inserted: base.inserted + Number(youtube.inserted || 0),
      duplicates: base.duplicates + Number(youtube.duplicates || 0),
      total_events: Number(youtube.total_events || base.total_events),
      message: `${base.message} Official YouTube video/comment/reply evidence appended.`,
      sources: {
        ...base.sources,
        youtube: {
          state: 'OK',
          received,
          connector: 'youtube_data_api_v3',
        },
      },
    };
  } catch (error) {
    return {
      ...base,
      sources: {
        ...base.sources,
        youtube: {
          state: 'ERROR',
          received: 0,
          connector: 'youtube_data_api_v3',
          detail: error instanceof Error ? error.message : 'Official YouTube collection failed.',
        },
      },
      message: `${base.message} Official YouTube collection reported an error; see source status.`,
    };
  }
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
  event: (id: string) => request<SocialEvent>(`/api/events/${encodeURIComponent(id)}`),
  resetWorkspace: () => request<{ status: string; total_events: number }>('/api/workspace/reset', {
    method: 'POST', body: '{}',
  }),
  searchWorkspace: smartWorkspaceSearch,
  seedDemo: () => request<{ inserted: number; total_events: number; message: string }>('/api/demo/seed', {
    method: 'POST', body: JSON.stringify({ reset: true }),
  }),
  pollTelegram: () => request<{ inserted: number; total_events: number }>('/api/connectors/telegram/poll', {
    method: 'POST', body: JSON.stringify({ max_updates: 100 }),
  }),
  searchX: (query: string) => request<{ inserted: number; total_events: number }>('/api/connectors/x/search', {
    method: 'POST', body: JSON.stringify({ query, max_results: 20 }),
  }),
  searchYouTube: (query: string) => officialYouTubeSearch(query, isExactYouTubeTarget(query) ? 1 : 3, 100),
  syncMeta: (source: 'instagram' | 'facebook') => request<{ inserted: number; total_events: number }>(
    '/api/connectors/meta/sync', { method: 'POST', body: JSON.stringify({ source, limit: 25 }) },
  ),
  collectorStatus: () => request<CollectorStatus>('/api/collector/status'),
  startCollector: (query: string, options?: { telegram?: boolean; x?: boolean; youtube?: boolean; interval?: number }) => request<CollectorStatus>(
    '/api/collector/start', {
      method: 'POST',
      body: JSON.stringify({
        query,
        interval_seconds: options?.interval || 60,
        enable_telegram: options?.telegram ?? true,
        enable_x: options?.x ?? false,
        enable_youtube: options?.youtube ?? false,
      }),
    },
  ),
  stopCollector: () => request<CollectorStatus>('/api/collector/stop', { method: 'POST', body: '{}' }),
  importEvents: (events: unknown[]) => request<{ inserted: number; total_events: number }>('/api/ingest/replay', {
    method: 'POST', body: JSON.stringify({ events }),
  }),
  narrativeJsonUrl: (id: string) => `${API_BASE}/api/export/narrative/${encodeURIComponent(id)}.json`,
  narrativeCsvUrl: (id: string) => `${API_BASE}/api/export/narrative/${encodeURIComponent(id)}.csv`,
};
