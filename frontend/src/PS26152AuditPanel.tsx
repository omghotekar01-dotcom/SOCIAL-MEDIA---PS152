import { useEffect, useMemo, useState } from 'react';
import {
  Activity, BarChart3, CheckCircle2, ChevronRight, Clock3, Database, GitBranch, Network,
  Radio, RefreshCw, ShieldCheck, Sparkles, Users2, X, Zap,
} from 'lucide-react';
import {
  api,
  type CollectorStatus,
  type ConnectorStatus,
  type DemographicsResponse,
  type GraphNode,
  type NarrativeSummary,
  type NetworkResponse,
  type Overview,
  type SocialEvent,
  type TimelinePoint,
} from './api';

type RichOverview = Overview & {
  root_content_events?: number;
  reaction_events?: number;
  root_sentiment_mix?: Record<string, number>;
  reaction_sentiment_mix?: Record<string, number>;
  reaction_stance_mix?: Record<string, number>;
  emotion_mix?: Record<string, number>;
  reaction_overview?: {
    captured_reactions?: number;
    overall_negative_share?: number;
    overall_positive_share?: number;
    overall_against_share?: number;
    overall_supportive_share?: number;
    risk_score?: number;
    risk_label?: string;
    coverage?: number;
  };
};

type RichTimeline = TimelinePoint & {
  reaction_count?: number;
  root_count?: number;
  supportive_share?: number;
  against_share?: number;
  sarcasm_mean?: number;
  emotions?: Record<string, number>;
};

type RichTrend = NarrativeSummary['trend'] & {
  velocity?: number;
  momentum?: string;
  predicted_next_bucket_volume?: number;
  forecast_confidence?: number;
  forecast_scope?: string;
};

type CommunityDetail = {
  community: number;
  events: number;
  authors: number;
  first_observed_at: string;
  last_observed_at: string;
  sentiment_mix: Record<string, number>;
  stance_mix: Record<string, number>;
  platform_mix: Record<string, number>;
};

type CrossCommunityFlow = {
  source_community: number;
  target_community: number;
  weight: number;
  edge_count: number;
  types: Record<string, number>;
};

type SpreadPoint = {
  time: string;
  communities: Record<string, number>;
  sentiment_balance: Record<string, number>;
};

type RichNetwork = NetworkResponse & {
  edge_type_counts?: Record<string, number>;
  direct_observed_edges?: number;
  co_discussion_edges?: number;
  key_opinion_leader_candidates?: GraphNode[];
  communities_detail?: CommunityDetail[];
  cross_community_flows?: CrossCommunityFlow[];
  spread_timeline?: SpreadPoint[];
  spread_method_note?: string;
};

type Loaded = {
  overview: RichOverview;
  timeline: RichTimeline[];
  narratives: NarrativeSummary[];
  network: RichNetwork;
  demographics: DemographicsResponse;
  connectors: ConnectorStatus[];
  events: SocialEvent[];
  collector: CollectorStatus;
};

const PLATFORM_TIERS = [
  { platform: 'x', label: 'X', tier: 'ESSENTIAL' },
  { platform: 'telegram', label: 'Telegram', tier: 'ESSENTIAL' },
  { platform: 'instagram', label: 'Instagram', tier: 'DESIRABLE' },
  { platform: 'facebook', label: 'Facebook', tier: 'DESIRABLE' },
  { platform: 'reddit', label: 'Reddit', tier: 'APPRECIABLE' },
  { platform: 'youtube', label: 'YouTube', tier: 'APPRECIABLE' },
] as const;

const EMOTIONS = ['anxiety', 'anger', 'excitement', 'sadness', 'joy', 'disgust', 'surprise', 'trust'];

function pct(value: number | undefined) {
  return `${Math.round((value || 0) * 100)}%`;
}

function isReaction(event: SocialEvent) {
  const type = (event.event_type || '').toLowerCase();
  return Boolean(event.parent_event_id) || /comment|reply|response|replied_to/.test(type);
}

function fmt(value: string | undefined | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

function topTerms(events: SocialEvent[]) {
  if (!events.length) return [];
  const ordered = [...events].sort((a, b) => +new Date(a.created_at) - +new Date(b.created_at));
  const split = Math.max(1, Math.floor(ordered.length * 0.7));
  const previous = ordered.slice(0, split);
  const recent = ordered.slice(split);

  const count = (rows: SocialEvent[]) => {
    const map = new Map<string, number>();
    for (const event of rows) {
      const terms = new Set([...(event.topic_terms || []), ...(event.hashtags || [])].map((value) => String(value).toLowerCase()).filter((value) => value.length >= 3));
      for (const term of terms) map.set(term, (map.get(term) || 0) + 1);
    }
    return map;
  };

  const before = count(previous);
  const now = count(recent);
  const all = new Set([...before.keys(), ...now.keys()]);
  return [...all].map((term) => {
    const a = before.get(term) || 0;
    const b = now.get(term) || 0;
    return { term, previous: a, recent: b, delta: b - a };
  }).sort((a, b) => (b.delta - a.delta) || (b.recent - a.recent)).slice(0, 10);
}

function RequirementCard({ id, title, state, detail, icon: Icon }: { id: string; title: string; state: 'STRONG' | 'PARTIAL' | 'EMPTY'; detail: string; icon: typeof Activity }) {
  return (
    <div className={`psreq-card psreq-${state.toLowerCase()}`}>
      <div className="psreq-id">{id}</div>
      <Icon size={18} />
      <div><strong>{title}</strong><span>{detail}</span></div>
      <b>{state}</b>
    </div>
  );
}

export default function PS26152AuditPanel() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overview, timeline, narratives, network, demographics, connectors, events, collector] = await Promise.all([
        api.overview(), api.timeline(), api.narratives(), api.network(), api.demographics(), api.connectorStatus(), api.events(), api.collectorStatus(),
      ]);
      setData({
        overview: overview as RichOverview,
        timeline: (timeline.points || []) as RichTimeline[],
        narratives: narratives.narratives || [],
        network: network as RichNetwork,
        demographics,
        connectors: connectors.connectors || [],
        events: events.events || [],
        collector,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load SIH26152 requirement intelligence.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && !data && !loading) void load();
  }, [open]);

  useEffect(() => {
    const refresh = () => { if (open) void load(); };
    window.addEventListener('nexus:workspace-updated', refresh);
    return () => window.removeEventListener('nexus:workspace-updated', refresh);
  }, [open]);

  const eventPlatforms = useMemo(() => {
    const map = new Map<string, { events: number; roots: number; reactions: number; live: number }>();
    for (const event of data?.events || []) {
      const row = map.get(event.platform) || { events: 0, roots: 0, reactions: 0, live: 0 };
      row.events += 1;
      if (isReaction(event)) row.reactions += 1; else row.roots += 1;
      if (event.source_mode === 'LIVE') row.live += 1;
      map.set(event.platform, row);
    }
    return map;
  }, [data?.events]);

  const keywordRows = useMemo(() => topTerms(data?.events || []), [data?.events]);

  const essentialCoverage = PLATFORM_TIERS.filter((row) => row.tier === 'ESSENTIAL').filter((row) => (data?.overview.platform_mix?.[row.platform] || 0) > 0).length;
  const reactionCount = data?.overview.reaction_events ?? data?.events.filter(isReaction).length ?? 0;
  const demographicCoverage = data ? Math.max(data.demographics.language.coverage, data.demographics.broad_geography.coverage, data.demographics.professional_interests.coverage, data.demographics.age_brackets.coverage) : 0;
  const networkEdges = data?.network.summary.edges || 0;
  const topNarrative = data?.narratives[0];
  const topTrend = topNarrative?.trend as RichTrend | undefined;

  const requirements = data ? [
    { id: 'A', title: 'Continuous Collection & Timeline', state: (data.overview.total_events > 0 && essentialCoverage === 2 ? 'STRONG' : data.overview.total_events > 0 ? 'PARTIAL' : 'EMPTY') as 'STRONG' | 'PARTIAL' | 'EMPTY', detail: `${data.overview.total_events} events · ${reactionCount} reactions · ${essentialCoverage}/2 essential platforms represented`, icon: Database },
    { id: 'B', title: 'Multi-Dimensional Sentiment', state: (data.overview.total_events > 0 && reactionCount > 0 ? 'STRONG' : data.overview.total_events > 0 ? 'PARTIAL' : 'EMPTY') as 'STRONG' | 'PARTIAL' | 'EMPTY', detail: `polarity + 8 emotions + stance + sarcasm · ${reactionCount} audience reactions`, icon: Activity },
    { id: 'C', title: 'Demographic Profiling', state: (demographicCoverage >= 0.5 ? 'STRONG' : data.overview.total_events > 0 ? 'PARTIAL' : 'EMPTY') as 'STRONG' | 'PARTIAL' | 'EMPTY', detail: `${data.demographics.unique_anonymized_users} pseudonymous users · max signal coverage ${pct(demographicCoverage)}`, icon: Users2 },
    { id: 'D', title: 'Real-Time Trends & Topics', state: (data.narratives.length > 0 ? 'STRONG' : 'EMPTY') as 'STRONG' | 'PARTIAL' | 'EMPTY', detail: `${data.narratives.length} narratives · ${keywordRows.filter((row) => row.delta > 0).length} rising visible terms · forecast ${topTrend?.momentum || '—'}`, icon: BarChart3 },
    { id: 'E', title: 'Link Analysis & Network Topology', state: (networkEdges > 0 ? 'STRONG' : (data.network.summary.nodes || 0) > 0 ? 'PARTIAL' : 'EMPTY') as 'STRONG' | 'PARTIAL' | 'EMPTY', detail: `${data.network.summary.nodes || 0} nodes · ${networkEdges} edges · ${data.network.summary.communities || 0} communities`, icon: Network },
  ] : [];

  const emotionMix = data?.overview.emotion_mix || {};
  const reaction = data?.overview.reaction_overview || {};
  const sourceSpan = (() => {
    if (!data?.events.length) return '—';
    const times = data.events.map((event) => +new Date(event.created_at)).filter(Number.isFinite);
    if (!times.length) return '—';
    const minutes = (Math.max(...times) - Math.min(...times)) / 60000;
    return minutes < 120 ? `${Math.round(minutes)} min` : `${(minutes / 60).toFixed(1)} h`;
  })();

  return (
    <>
      <button className="ps26152-launch" onClick={() => setOpen(true)} title="Open original problem statement coverage console">
        <ShieldCheck size={18} /><div><strong>PS26152 CORE</strong><span>5/5 requirement view</span></div>
      </button>

      {open && <div className="ps26152-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
        <section className="ps26152-modal" role="dialog" aria-modal="true" aria-label="SIH26152 original problem statement requirement console">
          <header className="ps26152-head">
            <div><span className="eyebrow">NTRO · SIH26152 · ORIGINAL REQUIREMENT VIEW</span><h2>Social Media Audience Intelligence — 5 Core Components</h2><p>Every card below maps directly to the original problem statement and current collected evidence.</p></div>
            <div className="ps26152-head-actions"><button onClick={() => void load()} disabled={loading}><RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh</button><button onClick={() => setOpen(false)}><X size={18} /></button></div>
          </header>

          {error && <div className="ps26152-error">{error}</div>}
          {!data && loading && <div className="ps26152-loading"><Sparkles size={24} /> Loading requirement intelligence…</div>}

          {data && <div className="ps26152-body">
            <div className="psreq-grid">{requirements.map((item) => <RequirementCard key={item.id} {...item} />)}</div>

            <section className="ps-section">
              <div className="ps-section-title"><div><span>A</span><div><strong>Continuous Data Collection & Timeline Management</strong><small>Posts + user interactions + comments + timestamped historical chronology</small></div></div><b className={data.collector.running ? 'live' : ''}><Radio size={12} /> {data.collector.running ? `LIVE WATCH · ${data.collector.cycles} cycles` : 'collector stopped'}</b></div>
              <div className="ps-mini-grid four"><div><span>Historical events</span><strong>{data.overview.total_events}</strong><small>full active workspace</small></div><div><span>Root posts</span><strong>{data.overview.root_content_events ?? '—'}</strong><small>author/original content</small></div><div><span>Comments / replies</span><strong>{reactionCount}</strong><small>audience opinion evidence</small></div><div><span>Observed time span</span><strong>{sourceSpan}</strong><small>{data.timeline.length} chronology buckets</small></div></div>
              <div className="ps-source-grid">
                {PLATFORM_TIERS.map((row) => {
                  const connector = data.connectors.find((item) => item.platform === row.platform);
                  const observed = Number(data.overview.platform_mix?.[row.platform] || 0);
                  const sample = eventPlatforms.get(row.platform);
                  return <div className={`ps-source-card ${observed ? 'observed' : ''}`} key={row.platform}><div><strong>{row.label}</strong><span>{row.tier}</span></div><b>{observed ? `${observed} observed` : 'no current evidence'}</b><small>{sample ? `${sample.reactions} reaction rows visible · ${sample.live} LIVE` : connector?.detail || 'Connector path available when configured.'}</small><em>{connector?.state || 'UNKNOWN'}</em></div>;
                })}
              </div>
              <div className="ps-trust"><ShieldCheck size={14} /> X + Telegram are the original essentials. NEXUS shows capability separately from current evidence and never relabels IMPORT/REPLAY as LIVE.</div>
            </section>

            <section className="ps-section">
              <div className="ps-section-title"><div><span>B</span><div><strong>Multi-Dimensional Sentiment Inference</strong><small>Nuanced emotion, sarcasm and supportive/against opinion movement over time</small></div></div><b>{reaction.risk_label || 'STABLE'} · risk {reaction.risk_score || 0}/100</b></div>
              <div className="ps-mini-grid four"><div><span>Audience negative</span><strong>{pct(reaction.overall_negative_share)}</strong><small>captured comments/replies only</small></div><div><span>Audience positive</span><strong>{pct(reaction.overall_positive_share)}</strong><small>root sentiment kept separate</small></div><div><span>Against stance</span><strong>{pct(reaction.overall_against_share)}</strong><small>supportive {pct(reaction.overall_supportive_share)}</small></div><div><span>Reaction coverage</span><strong>{pct(reaction.coverage)}</strong><small>{reaction.captured_reactions || reactionCount} reactions captured</small></div></div>
              <div className="ps-emotion-grid">{EMOTIONS.map((emotion) => <div key={emotion}><span>{emotion}</span><i><b style={{ width: pct(emotionMix[emotion]) }} /></i><strong>{pct(emotionMix[emotion])}</strong></div>)}</div>
              <div className="ps-timeline-list"><strong>Emotion / stance movement on the established timeline</strong>{data.timeline.slice(-8).map((point) => {
                const topEmotion = Object.entries(point.emotions || {}).sort((a, b) => b[1] - a[1])[0];
                return <div key={point.time}><time>{fmt(point.time)}</time><span>{point.count} events · {point.reaction_count || 0} reactions</span><b>{topEmotion ? `${topEmotion[0]} ${pct(topEmotion[1])}` : 'no emotion signal'}</b><em>support {pct(point.supportive_share)} · against {pct(point.against_share)} · sarcasm {pct(point.sarcasm_mean)}</em></div>;
              })}</div>
            </section>

            <section className="ps-section">
              <div className="ps-section-title"><div><span>C</span><div><strong>Automated Demographic Profiling</strong><small>Aggregate, anonymized audience signals with explicit coverage and suppression</small></div></div><b><ShieldCheck size={12} /> k-anonymity</b></div>
              <div className="ps-demo-grid">
                {[['Language', data.demographics.language], ['Broad geography', data.demographics.broad_geography], ['Professional interests', data.demographics.professional_interests], ['Age brackets', data.demographics.age_brackets]].map(([label, raw]) => {
                  const slice = raw as DemographicsResponse['language'];
                  return <div className="ps-demo-card" key={label as string}><div><strong>{label as string}</strong><b>{pct(slice.coverage)} coverage</b></div><div>{Object.entries(slice.counts).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([name, count]) => <span key={name}>{name.replaceAll('_', ' ')} <b>{count}</b></span>)}</div><small>{slice.method} · confidence {pct(slice.confidence)}</small></div>;
                })}
              </div>
              <div className="ps-trust"><ShieldCheck size={14} /> {data.demographics.privacy_note}</div>
            </section>

            <section className="ps-section">
              <div className="ps-section-title"><div><span>D</span><div><strong>Real-Time Trend & Topic Detection</strong><small>Identify, rank and predict rising narratives, viral terms and shifting discussion</small></div></div><b>{data.narratives.length} active narratives</b></div>
              {topNarrative ? <div className="ps-trend-hero"><div><span>TOP RANKED NARRATIVE</span><strong>{topNarrative.title}</strong><small>{topNarrative.event_count} events · score {topNarrative.trend.score.toFixed(2)} · {topNarrative.trend.status}</small></div><div><span>Momentum</span><strong>{topTrend?.momentum || '—'}</strong><small>velocity {topTrend?.velocity?.toFixed(2) ?? '—'}</small></div><div><span>Next 15-min forecast</span><strong>{topTrend?.predicted_next_bucket_volume ?? '—'}</strong><small>confidence {pct(topTrend?.forecast_confidence)}</small></div></div> : <div className="ps-empty">No narrative evidence yet.</div>}
              <div className="ps-keywords"><div className="ps-subtitle">Rising / shifting terms from visible evidence</div>{keywordRows.map((row) => <div key={row.term}><strong>{row.term}</strong><span>recent {row.recent}</span><span>previous {row.previous}</span><b className={row.delta > 0 ? 'up' : row.delta < 0 ? 'down' : ''}>{row.delta > 0 ? '+' : ''}{row.delta}</b></div>)}{!keywordRows.length && <small>No topic terms yet.</small>}</div>
            </section>

            <section className="ps-section">
              <div className="ps-section-title"><div><span>E</span><div><strong>Link Analysis & Network Topology</strong><small>Key opinion leaders, communities and how trend/sentiment spreads between user segments over time</small></div></div><b>{data.network.summary.nodes || 0} nodes · {data.network.summary.edges || 0} edges</b></div>
              <div className="ps-mini-grid four"><div><span>Communities</span><strong>{data.network.summary.communities || 0}</strong><small>structural user segments</small></div><div><span>High influence</span><strong>{data.network.summary.high_reach_nodes || 0}</strong><small>PageRank / reach role</small></div><div><span>Bridge nodes</span><strong>{data.network.summary.bridge_nodes || 0}</strong><small>connect separated segments</small></div><div><span>Direct / co-discussion</span><strong>{data.network.direct_observed_edges || 0} / {data.network.co_discussion_edges || 0}</strong><small>evidence strength separated</small></div></div>
              <div className="ps-link-grid">
                <div><div className="ps-subtitle">Key opinion-leader candidates</div>{(data.network.key_opinion_leader_candidates || data.network.nodes).slice(0, 6).map((node, index) => <div className="ps-node-row" key={node.id}><span>{index + 1}</span><div><strong>{node.label}</strong><small>{node.platform} · community #{node.community} · {node.role}</small></div><b>PR {node.pagerank.toFixed(3)}</b></div>)}</div>
                <div><div className="ps-subtitle">Cross-community influence flows</div>{(data.network.cross_community_flows || []).slice(0, 8).map((flow, index) => <div className="ps-flow-row" key={`${flow.source_community}-${flow.target_community}-${index}`}><strong>Community #{flow.source_community}</strong><ChevronRight size={13} /><strong>#{flow.target_community}</strong><span>{flow.edge_count} edges · weight {flow.weight.toFixed(2)}</span></div>)}{!(data.network.cross_community_flows || []).length && <small>No cross-community edges yet; use replies/mentions or the deterministic demo to expose propagation.</small>}</div>
              </div>
              <div className="ps-timeline-list"><strong>Observed community spread over time</strong>{(data.network.spread_timeline || []).slice(-8).map((point) => <div key={point.time}><time>{fmt(point.time)}</time><span>{Object.entries(point.communities).map(([community, count]) => `C${community}:${count}`).join(' · ') || 'no community activity'}</span><b>{Object.keys(point.communities).length} active segment(s)</b><em>timestamped propagation</em></div>)}</div>
              <div className="ps-edge-types">{Object.entries(data.network.edge_type_counts || {}).map(([type, count]) => <span key={type}>{type} <b>{count}</b></span>)}</div>
              <div className="ps-trust"><ShieldCheck size={14} /> {data.network.spread_method_note || 'High influence and bridge labels describe observed graph structure only; they do not imply identity, guilt, intent or coordination.'}</div>
            </section>
          </div>}
        </section>
      </div>}
    </>
  );
}
