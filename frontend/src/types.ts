export type SourceMode = 'LIVE' | 'REPLAY' | 'IMPORT' | string

export interface Summary {
  events: number
  unique_authors: number
  platforms: Record<string, number>
  source_modes: Record<string, number>
  narratives: number
  cross_platform_narratives: number
  rising_narratives: number
  active_alerts: number
  sentiment: Record<string, number>
  stance: Record<string, number>
  emotion: Record<string, number>
  required_platform_coverage_pct: number
  latest_event_at: string | null
  mode_label: string
}

export interface Narrative {
  id: string
  title: string
  event_count: number
  author_count: number
  origin_platform: string
  earliest_observed_event_id: string
  first_observed: string
  last_observed: string
  platforms: string[]
  platform_mix: Record<string, number>
  source_modes: Record<string, number>
  cross_platform: boolean
  cross_platform_hops: number
  mutation_count: number
  topic_terms: string[]
  sentiment_distribution: Record<string, number>
  stance_distribution: Record<string, number>
  cluster_confidence: number
  analysis_confidence_hint?: number | null
  sample_text: string
  event_ids: string[]
  lineage: LineageEdge[]
}

export interface LineageEdge {
  from_event_id: string
  to_event_id: string
  from_source_event_id: string
  to_source_event_id: string
  from_platform: string
  to_platform: string
  semantic_similarity: number
  cross_platform: boolean
  mutation: boolean
  elapsed_seconds: number
}

export interface Trend {
  narrative_id: string
  title: string
  status: string
  mentions: number
  current_window_mentions: number
  previous_window_mentions: number
  velocity_ratio: number
  acceleration: number
  burst_z_score: number
  trend_score: number
  platform_diversity: number
  platform_mix: Record<string, number>
  reason: string
  window_end: string
}

export interface Alert {
  alert_id: string
  title: string
  severity: string
  narrative_id: string
  triggered_at: string
  trend_score: number
  why_triggered: string[]
  evidence_event_ids: string[]
  earliest_observed_event_id?: string | null
  platform_mix: Record<string, number>
  confidence: number
  coverage_warning?: string | null
  top_amplifiers?: Array<Record<string, unknown>>
  sentiment_shift?: Record<string, unknown>
}

export interface NetworkNode {
  id: string
  label: string
  platform: string
  community: number | null
  pagerank: number
  degree_centrality: number
  betweenness_centrality: number
  bridge_score: number
  structural_influence_score: number
}

export interface NetworkEdge {
  source: string
  target: string
  weight: number
  types: string[]
}

export interface NetworkData {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  communities: Array<{ id: number; size: number; member_ids: string[]; platform_mix: Record<string, number> }>
  top_influence_nodes: NetworkNode[]
  top_bridge_nodes: NetworkNode[]
  metadata: { node_count: number; edge_count: number; meaning: string }
}

export interface DistributionItem {
  label: string
  count: number
  percentage: number
}

export interface Demographics {
  sample_size: number
  minimum_publishable_group: number
  publishable: boolean
  language: DistributionItem[]
  broad_geography: DistributionItem[]
  professional_interests: DistributionItem[]
  explicit_age_brackets: DistributionItem[]
  coverage: Record<string, number>
  confidence: number
  privacy_note: string
  age_note: string
}

export interface EvidenceNarrative {
  narrative_id: string
  credibility_state: string
  state_reason: string
  event_count: number
  platforms: string[]
  source_modes: string[]
  authoritative_source_count: number
  mean_analysis_confidence: number
  earliest_observed_event_id: string
  first_observed: string
  last_observed: string
  scope_note: string
}

export interface Evidence {
  event_count: number
  unique_pseudonymous_authors: number
  observed_platforms: string[]
  required_platforms: string[]
  required_platforms_present: string[]
  missing_required_platforms: string[]
  optional_platforms_present: string[]
  required_platform_coverage_pct: number
  source_modes: Record<string, number>
  earliest_source_time: string | null
  latest_source_time: string | null
  latest_ingest_time: string | null
  ingest_freshness_seconds: number | null
  mean_analysis_confidence: number
  narratives: EvidenceNarrative[]
  coverage_warning: string
  truthfulness_note: string
}

export interface EventItem {
  id: string
  source_event_id: string
  platform: string
  source_mode: SourceMode
  event_type: string
  author_display?: string | null
  text: string
  created_at: string
  language?: string | null
  url?: string | null
  sentiment_label?: string | null
  sentiment_score?: number | null
  emotion_scores?: Record<string, number>
  stance_label?: string | null
  stance_confidence?: number | null
  sarcasm_probability?: number | null
  topic_terms?: string[]
  narrative_cluster_id?: string | null
  trend_score?: number | null
}

export interface DashboardBundle {
  summary: Summary
  narratives: Narrative[]
  trends: Trend[]
  network: NetworkData
  demographics: Demographics
  evidence: Evidence
  alerts: Alert[]
  events: EventItem[]
  platformStatus: Record<string, unknown>
}
