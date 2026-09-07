import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  Database,
  GitBranch,
  Languages,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  Zap,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  API_BASE,
  api,
  type ConnectorStatus,
  type DemographicsResponse,
  type NarrativeSummary,
  type NetworkResponse,
  type SocialEvent,
} from './api';


type Tab = 'command' | 'emotion' | 'trends' | 'demographics' | 'network' | 'evidence';

interface IntelligenceSummary {
  total_events: number;
  primary_emotion?: string;
  emotion_mix: Record<string, number>;
  stance_mix: Record<string, number>;
  toxicity_mix: Record<string, number>;
  sarcasm: { average: number; high_probability_events: number };
  languages: Record<string, number>;
  code_mixed_events: number;
  platforms: Record<string, number>;
  emotion_timeline: Array<{ time: string; emotions: Record<string, number>; total: number }>;
  confidence: number;
  method?: string;
}

interface Overview {
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

interface QueryResponse {
  question: string;
  answer: string;
  evidence: Array<[string, string | number]>;
  scope: string;
  event_count: number;
}

const emotionLabels: Record<string, string> = {
  joy_excitement: 'Joy / Excitement',
  anger_frustration: 'Anger / Frustration',
  sadness: 'Sadness',
  fear_anxiety: 'Fear / Anxiety',
  surprise_shock: 'Surprise / Shock',
  trust_confidence: 'Trust / Confidence',
  disgust_aversion: 'Disgust / Aversion',
  neutral_informational: 'Neutral / Informational',
};

const tabs: Array<{ id: Tab; label: string; icon: typeof Activity }> = [
  { id: 'command', label: 'Command Center', icon: Activity },
  { id: 'emotion', label: 'Emotion Observatory', icon: BrainCircuit },
  { id: 'trends', label: 'Trend Radar', icon: Zap },
  { id: 'demographics', label: 'Audience Intelligence', icon: Users },
  { id: 'network', label: 'Network Intelligence', icon: Network },
  { id: 'evidence', label: 'Evidence Stream', icon: Database },
];

function pct(value: number | undefined): string {
  return `${Math.round((value || 0) * 100)}%`;
}

function compact(value: number): string {
  return new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}

function labelize(value: string): string {
  return emotionLabels[value] || value.replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase());
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

function MetricCard({ icon: Icon, label, value, hint }: { icon: typeof Activity; label: string; value: string; hint: string }) {
  return (
    <article className="nx-metric-card">
      <div className="nx-icon-box"><Icon size={18} /></div>
      <div>
        <span className="nx-eyebrow">{label}</span>
        <strong>{value}</strong>
        <small>{hint}</small>
      </div>
    </article>
  );
}

function SectionTitle({ icon: Icon, title, subtitle }: { icon: typeof Activity; title: string; subtitle: string }) {
  return (
    <div className="nx-section-title">
      <div className="nx-icon-box"><Icon size={18} /></div>
      <div><h2>{title}</h2><p>{subtitle}</p></div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="nx-empty"><Database size={28} /><p>{text}</p></div>;
}

function NetworkMiniMap({ data }: { data: NetworkResponse | null }) {
  const nodes = (data?.nodes || []).slice(0, 20);
  const ids = new Set(nodes.map((node) => node.id));
  const edges = (data?.edges || []).filter((edge) => ids.has(edge.source) && ids.has(edge.target)).slice(0, 35);
  const positions = useMemo(() => {
    const center = 190;
    const radius = 132;
    const map = new Map<string, { x: number; y: number }>();
    nodes.forEach((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(nodes.length, 1) - Math.PI / 2;
      map.set(node.id, { x: center + Math.cos(angle) * radius, y: center + Math.sin(angle) * radius });
    });
    return map;
  }, [nodes]);

  if (!nodes.length) return <EmptyState text="Seed or ingest data to generate the influence graph." />;

  return (
    <div className="nx-network-wrap">
      <svg viewBox="0 0 380 380" className="nx-network-svg" role="img" aria-label="Influence network preview">
        {edges.map((edge, index) => {
          const source = positions.get(edge.source);
          const target = positions.get(edge.target);
          if (!source || !target) return null;
          return <line key={`${edge.source}-${edge.target}-${index}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className="nx-edge" />;
        })}
        {nodes.map((node) => {
          const pos = positions.get(node.id)!;
          const radius = 6 + Math.min(10, (node.pagerank || 0) * 85);
          const isBridge = node.role?.toLowerCase().includes('bridge');
          return (
            <g key={node.id}>
              <circle cx={pos.x} cy={pos.y} r={radius} className={isBridge ? 'nx-node nx-node-bridge' : 'nx-node'} />
              <title>{`${node.label} • ${node.role}`}</title>
            </g>
          );
        })}
      </svg>
      <div className="nx-network-summary">
        <span><b>{data?.summary.nodes || 0}</b> nodes</span>
        <span><b>{data?.summary.edges || 0}</b> links</span>
        <span><b>{data?.summary.communities || 0}</b> communities</span>
        <span><b>{data?.summary.bridge_nodes || 0}</b> bridges</span>
      </div>
    </div>
  );
}

export default function IntelligenceApp() {
  const [tab, setTab] = useState<Tab>('command');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [intel, setIntel] = useState<IntelligenceSummary | null>(null);
  const [narratives, setNarratives] = useState<NarrativeSummary[]>([]);
  const [demographics, setDemographics] = useState<DemographicsResponse | null>(null);
  const [network, setNetwork] = useState<NetworkResponse | null>(null);
  const [events, setEvents] = useState<SocialEvent[]>([]);
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('Which emotion is dominant and what evidence supports it?');
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [querying, setQuerying] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [o, i, n, d, g, e, c] = await Promise.all([
        api.overview(),
        getJson<IntelligenceSummary>('/api/intelligence/summary'),
        api.narratives(),
        api.demographics(),
        api.network(),
        api.events(),
        api.connectorStatus(),
      ]);
      setOverview(o as Overview);
      setIntel(i);
      setNarratives(n.narratives);
      setDemographics(d);
      setNetwork(g);
      setEvents(e.events);
      setConnectors(c.connectors);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load analytics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const seed = async () => {
    setLoading(true);
    try {
      await api.seedDemo();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Demo seed failed');
      setLoading(false);
    }
  };

  const runQuery = async () => {
    if (!query.trim()) return;
    setQuerying(true);
    try {
      const result = await postJson<QueryResponse>('/api/intelligence/query', { question: query, limit: 500 });
      setQueryResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed');
    } finally {
      setQuerying(false);
    }
  };

  const emotionData = useMemo(
    () => Object.entries(intel?.emotion_mix || {}).map(([name, value]) => ({ name: labelize(name), value: Math.round(value * 100) })),
    [intel],
  );

  const stanceData = useMemo(
    () => Object.entries(intel?.stance_mix || {}).map(([name, value]) => ({ name: labelize(name), value })),
    [intel],
  );

  const timelineData = useMemo(() => (intel?.emotion_timeline || []).map((point) => ({
    time: new Date(point.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    ...point.emotions,
  })), [intel]);

  const topEmotion = intel?.primary_emotion ? labelize(intel.primary_emotion) : 'No data';
  const liveConnectors = connectors.filter((connector) => connector.state === 'LIVE' || connector.state === 'READY').length;
  const topNarrative = narratives[0];

  const demographicCards = demographics ? [
    ['Language', demographics.language],
    ['Broad geography', demographics.broad_geography],
    ['Professional interests', demographics.professional_interests],
    ['Age brackets', demographics.age_brackets],
  ] as const : [];

  return (
    <div className="nx-app">
      <aside className="nx-sidebar">
        <div className="nx-brand">
          <div className="nx-brand-mark"><GitBranch size={20} /></div>
          <div><b>NEXUS</b><span>SIH26152</span></div>
        </div>
        <nav>
          {tabs.map(({ id, label, icon: Icon }) => (
            <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>
              <Icon size={18} /><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="nx-sidebar-foot">
          <div className="nx-status-dot" />
          <div><b>Evidence-aware</b><span>LIVE / REPLAY labels preserved</span></div>
        </div>
      </aside>

      <main className="nx-main">
        <header className="nx-topbar">
          <div>
            <span className="nx-kicker">NTRO • SOCIAL MEDIA ANALYTICS</span>
            <h1>{tabs.find((item) => item.id === tab)?.label}</h1>
          </div>
          <div className="nx-actions">
            <button className="nx-btn nx-btn-ghost" onClick={() => void refresh()} disabled={loading}><RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh</button>
            <button className="nx-btn" onClick={() => void seed()}><Sparkles size={16} /> Load verified demo</button>
          </div>
        </header>

        {error && <div className="nx-error"><AlertTriangle size={17} /> {error}</div>}

        <section className="nx-metrics-grid">
          <MetricCard icon={Database} label="Collected events" value={compact(overview?.total_events || 0)} hint={`${Object.keys(overview?.platform_mix || {}).length} observed platforms`} />
          <MetricCard icon={BrainCircuit} label="Dominant emotion" value={topEmotion} hint={`Inference confidence ${pct(intel?.confidence)}`} />
          <MetricCard icon={Zap} label="Active narratives" value={String(overview?.active_narratives || 0)} hint={`${overview?.rising_narratives || 0} rising now`} />
          <MetricCard icon={Network} label="Influence topology" value={`${network?.summary.nodes || 0} nodes`} hint={`${network?.summary.communities || 0} communities • ${network?.summary.bridge_nodes || 0} bridges`} />
        </section>

        {tab === 'command' && (
          <>
            <section className="nx-grid nx-grid-2">
              <article className="nx-panel">
                <SectionTitle icon={BrainCircuit} title="Emotion pulse" subtitle="Eight-class emotion distribution across the current evidence set" />
                {emotionData.length ? (
                  <div className="nx-chart"><ResponsiveContainer width="100%" height={300}><BarChart data={emotionData} layout="vertical" margin={{ left: 30 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" domain={[0, 100]} /><YAxis dataKey="name" type="category" width={125} tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => [`${value}%`, 'Share']} /><Bar dataKey="value" radius={[0, 7, 7, 0]} /></BarChart></ResponsiveContainer></div>
                ) : <EmptyState text="No emotion evidence yet." />}
              </article>

              <article className="nx-panel">
                <SectionTitle icon={Network} title="Influence topology" subtitle="High-reach nodes, bridges and community structure" />
                <NetworkMiniMap data={network} />
              </article>
            </section>

            <section className="nx-grid nx-grid-2">
              <article className="nx-panel">
                <SectionTitle icon={Zap} title="Narrative radar" subtitle="Emerging topics ranked by burst, diversity, engagement and cross-platform spread" />
                <div className="nx-narrative-list">
                  {narratives.slice(0, 6).map((narrative, index) => (
                    <div className="nx-narrative" key={narrative.id}>
                      <span className="nx-rank">{String(index + 1).padStart(2, '0')}</span>
                      <div><b>{narrative.title}</b><small>{narrative.event_count} events • {Object.keys(narrative.platform_mix).join(' + ') || 'single source'}</small></div>
                      <div className={`nx-trend nx-trend-${narrative.trend.status.toLowerCase()}`}>{narrative.trend.status}<b>{pct(narrative.trend.score)}</b></div>
                    </div>
                  ))}
                  {!narratives.length && <EmptyState text="No narrative clusters yet." />}
                </div>
              </article>

              <article className="nx-panel">
                <SectionTitle icon={Search} title="Analyst query" subtitle="Ask over the currently collected evidence, not the open internet" />
                <div className="nx-query-box">
                  <textarea value={query} onChange={(event) => setQuery(event.target.value)} />
                  <button className="nx-btn" onClick={() => void runQuery()} disabled={querying}><Search size={16} /> {querying ? 'Analyzing…' : 'Analyze evidence'}</button>
                </div>
                {queryResult && (
                  <div className="nx-query-result">
                    <span className="nx-eyebrow">RESULT • {queryResult.event_count} EVENTS</span>
                    <p>{queryResult.answer}</p>
                    <small>{queryResult.scope}</small>
                  </div>
                )}
              </article>
            </section>
          </>
        )}

        {tab === 'emotion' && (
          <section className="nx-grid nx-grid-2">
            <article className="nx-panel nx-span-2">
              <SectionTitle icon={Activity} title="Emotion over time" subtitle="15-minute buckets reveal population-level emotional shifts" />
              {timelineData.length ? <div className="nx-chart nx-chart-large"><ResponsiveContainer width="100%" height={360}><LineChart data={timelineData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" /><YAxis allowDecimals={false} /><Tooltip />{Object.keys(intel?.emotion_mix || {}).slice(0, 6).map((key) => <Line key={key} type="monotone" dataKey={key} name={labelize(key)} strokeWidth={2} dot={false} />)}</LineChart></ResponsiveContainer></div> : <EmptyState text="Timeline appears after data ingestion." />}
            </article>
            <article className="nx-panel"><SectionTitle icon={BrainCircuit} title="Emotion distribution" subtitle="Primary and secondary emotional signals" /><div className="nx-chart"><ResponsiveContainer width="100%" height={300}><PieChart><Pie data={emotionData} dataKey="value" nameKey="name" innerRadius={66} outerRadius={105} paddingAngle={2}>{emotionData.map((_, i) => <Cell key={i} />)}</Pie><Tooltip formatter={(value) => [`${value}%`, 'Share']} /></PieChart></ResponsiveContainer></div></article>
            <article className="nx-panel"><SectionTitle icon={ShieldCheck} title="Context layers" subtitle="Stance, sarcasm, toxicity and code-mix are separate from emotion" /><div className="nx-context-grid"><div><span>Average sarcasm</span><b>{pct(intel?.sarcasm.average)}</b></div><div><span>High-sarcasm events</span><b>{intel?.sarcasm.high_probability_events || 0}</b></div><div><span>Code-mixed events</span><b>{intel?.code_mixed_events || 0}</b></div><div><span>Primary stance</span><b>{stanceData.sort((a, b) => b.value - a.value)[0]?.name || '—'}</b></div></div></article>
          </section>
        )}

        {tab === 'trends' && (
          <section className="nx-panel">
            <SectionTitle icon={Zap} title="Trend & narrative intelligence" subtitle="Velocity is combined with diversity, engagement, recency and cross-platform spread" />
            <div className="nx-trend-table">
              <div className="nx-trend-row nx-trend-head"><span>Narrative</span><span>Status</span><span>Events</span><span>Growth</span><span>Burst</span><span>Platforms</span><span>Score</span></div>
              {narratives.map((narrative) => <div className="nx-trend-row" key={narrative.id}><span><b>{narrative.title}</b><small>{narrative.id}</small></span><span><i className={`nx-pill nx-pill-${narrative.trend.status.toLowerCase()}`}>{narrative.trend.status}</i></span><span>{narrative.event_count}</span><span>{Math.round(narrative.trend.growth_rate * 100)}%</span><span>{narrative.trend.burst_zscore.toFixed(1)}σ</span><span>{narrative.trend.platform_count}</span><span><b>{pct(narrative.trend.score)}</b></span></div>)}
            </div>
            {!narratives.length && <EmptyState text="No trends are available yet." />}
          </section>
        )}

        {tab === 'demographics' && (
          <>
            <div className="nx-privacy-note"><ShieldCheck size={17} /><span>Only aggregate anonymized public-profile indicators are shown. No per-user demographic table is exposed.</span></div>
            <section className="nx-grid nx-grid-2">
              {demographicCards.map(([name, slice]) => (
                <article className="nx-panel" key={name}>
                  <SectionTitle icon={name === 'Language' ? Languages : Users} title={name} subtitle={`Coverage ${pct(slice.coverage)} • confidence ${pct(slice.confidence)}`} />
                  <div className="nx-bars">
                    {Object.entries(slice.counts).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([label, count]) => {
                      const max = Math.max(...Object.values(slice.counts), 1);
                      return <div className="nx-bar-row" key={label}><span>{labelize(label)}</span><div><i style={{ width: `${(count / max) * 100}%` }} /></div><b>{count}</b></div>;
                    })}
                  </div>
                  <small className="nx-method">{slice.method}</small>
                </article>
              ))}
            </section>
          </>
        )}

        {tab === 'network' && (
          <section className="nx-grid nx-grid-2">
            <article className="nx-panel"><SectionTitle icon={Network} title="Propagation graph" subtitle="Interactions, mentions, replies and shared narrative membership" /><NetworkMiniMap data={network} /></article>
            <article className="nx-panel"><SectionTitle icon={GitBranch} title="Influence ranking" subtitle="Transparent graph metrics instead of opaque influencer labels" /><div className="nx-node-list">{(network?.nodes || []).slice().sort((a, b) => b.pagerank - a.pagerank).slice(0, 12).map((node, index) => <div key={node.id}><span>{String(index + 1).padStart(2, '0')}</span><div><b>{node.label}</b><small>{node.role} • community {node.community}</small></div><strong>{node.pagerank.toFixed(3)}</strong></div>)}</div></article>
          </section>
        )}

        {tab === 'evidence' && (
          <section className="nx-panel">
            <SectionTitle icon={Database} title="Evidence stream" subtitle="Every conclusion remains traceable to a timestamped source item and mode" />
            <div className="nx-evidence-list">
              {events.slice(0, 100).map((event) => {
                const primary = Object.entries(event.emotion_scores || {}).sort((a, b) => b[1] - a[1])[0];
                return <article key={event.id}><div className="nx-evidence-meta"><i className={`nx-source nx-source-${event.source_mode.toLowerCase()}`}>{event.source_mode}</i><b>{event.platform.toUpperCase()}</b><span>{new Date(event.created_at).toLocaleString()}</span><span>{event.author_display || `user-${event.author_pseudo_id?.slice(0, 6) || 'anon'}`}</span></div><p>{event.text}</p><div className="nx-evidence-tags"><span>{primary ? labelize(primary[0]) : 'Unclassified'}</span><span>{labelize(event.stance_label || 'neutral')}</span><span>sarcasm {pct(event.sarcasm_probability || 0)}</span>{event.narrative_cluster_id && <span>{event.narrative_cluster_id}</span>}</div></article>;
              })}
              {!events.length && <EmptyState text="No evidence has been collected yet." />}
            </div>
          </section>
        )}

        <footer className="nx-footer">
          <span><ShieldCheck size={14} /> Public/authorized evidence only • anonymized analysis</span>
          <span>{liveConnectors}/{connectors.length || 0} connectors ready • {topNarrative ? `top narrative ${topNarrative.id}` : 'no active narrative'}</span>
        </footer>
      </main>
    </div>
  );
}
