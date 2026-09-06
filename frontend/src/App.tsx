import { type ChangeEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Database,
  Download,
  ExternalLink,
  GitBranch,
  Network,
  Play,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  Upload,
  Users,
  Waypoints,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  AlertItem,
  api,
  CollectorStatus,
  ConnectorStatus,
  DemographicSlice,
  DemographicsResponse,
  GraphNode,
  NarrativeDetail,
  NarrativeSummary,
  NetworkResponse,
  Overview,
  SocialEvent,
  TimelinePoint,
} from './api';

type Tab = 'overview' | 'timeline' | 'trends' | 'narrative' | 'network' | 'demographics' | 'alerts' | 'evidence';

const tabs: Array<{ id: Tab; label: string; icon: typeof Activity }> = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'timeline', label: 'Timeline', icon: Waypoints },
  { id: 'trends', label: 'Trends', icon: BarChart3 },
  { id: 'narrative', label: 'Narrative', icon: GitBranch },
  { id: 'network', label: 'Network', icon: Network },
  { id: 'demographics', label: 'Demographics', icon: Users },
  { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
  { id: 'evidence', label: 'Evidence', icon: Database },
];

const fmt = (value: string | number | null | undefined) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? String(value)
    : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};

const pct = (value: number | null | undefined) => `${Math.round((value || 0) * 100)}%`;

function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'live' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function SourceBadge({ mode }: { mode?: string }) {
  const tone = mode === 'LIVE' ? 'live' : mode === 'REPLAY' ? 'warn' : 'neutral';
  return <Badge tone={tone}>{mode || 'UNKNOWN'}</Badge>;
}

function PlatformBadge({ platform }: { platform: string }) {
  return <span className={`platform platform-${platform}`}>{platform.toUpperCase()}</span>;
}

function Metric({ label, value, helper, icon: Icon }: { label: string; value: string | number; helper?: string; icon: typeof Activity }) {
  return (
    <div className="metric-card">
      <div className="metric-icon"><Icon size={19} /></div>
      <div>
        <div className="metric-value">{value}</div>
        <div className="metric-label">{label}</div>
        {helper && <div className="metric-helper">{helper}</div>}
      </div>
    </div>
  );
}

function ConnectorStrip({ connectors }: { connectors: ConnectorStatus[] }) {
  return (
    <div className="connector-strip">
      {connectors.map((connector) => {
        const tone = connector.state === 'READY' || connector.state === 'LIVE' ? 'good' : connector.state === 'ERROR' ? 'bad' : 'warn';
        return (
          <div className="connector-item" key={connector.platform} title={connector.detail}>
            <span className={`connector-dot connector-${tone}`} />
            <strong>{connector.platform.toUpperCase()}</strong>
            <span>{connector.state.replaceAll('_', ' ')}</span>
          </div>
        );
      })}
    </div>
  );
}

function TrendCard({ narrative, onOpen }: { narrative: NarrativeSummary; onOpen: () => void }) {
  const tone = narrative.trend.status === 'VIRAL' ? 'bad' : narrative.trend.status === 'RISING' ? 'warn' : 'neutral';
  return (
    <button className="trend-card" onClick={onOpen}>
      <div className="trend-card-top">
        <div>
          <div className="eyebrow">{narrative.id} · {narrative.event_count} events</div>
          <h3>{narrative.title}</h3>
        </div>
        <Badge tone={tone}>{narrative.trend.status}</Badge>
      </div>
      <p>{narrative.representative_text}</p>
      <div className="trend-grid">
        <span><b>{narrative.trend.score.toFixed(2)}</b> score</span>
        <span><b>{narrative.trend.growth_rate >= 0 ? '+' : ''}{narrative.trend.growth_rate.toFixed(2)}</b> growth</span>
        <span><b>{narrative.trend.platform_count}</b> platforms</span>
        <span><b>{pct(narrative.trend.author_diversity)}</b> author diversity</span>
      </div>
      <div className="chip-row">
        {Object.entries(narrative.platform_mix).map(([platform, count]) => <span className="chip" key={platform}>{platform}: {count}</span>)}
        {Object.entries(narrative.source_modes).map(([mode, count]) => <span className="chip" key={mode}>{mode}: {count}</span>)}
      </div>
    </button>
  );
}

function TimelineView({ points }: { points: TimelinePoint[] }) {
  const data = points.map((point) => ({
    time: new Date(point.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    count: point.count,
    negative: point.sentiments.negative || 0,
    positive: point.sentiments.positive || 0,
    neutral: point.sentiments.neutral || 0,
  }));
  return (
    <section className="panel panel-large">
      <div className="section-head">
        <div><div className="eyebrow">Chronology</div><h2>Conversation timeline</h2></div>
        <div className="legend"><span>Volume</span><span>Negative</span><span>Positive</span></div>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={380}>
          <AreaChart data={data} margin={{ left: 0, right: 16, top: 12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
            <XAxis dataKey="time" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ background: '#11182a', border: '1px solid #2a3550', borderRadius: 12 }} />
            <Area type="monotone" dataKey="count" stroke="#77a7ff" fill="#77a7ff" fillOpacity={0.12} strokeWidth={3} />
            <Line type="monotone" dataKey="negative" stroke="#ff7c88" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="positive" stroke="#54d8a7" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="coverage-callout"><ShieldCheck size={18} /> Exact source timestamps are stored separately from ingestion time.</div>
    </section>
  );
}

function NetworkGraph({ network }: { network: NetworkResponse | null }) {
  const nodes = (network?.nodes || []).slice(0, 32);
  const ids = new Set(nodes.map((n) => n.id));
  const edges = (network?.edges || []).filter((edge) => ids.has(edge.source) && ids.has(edge.target)).slice(0, 90);
  const width = 900;
  const height = 520;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.37;
  const positions = new Map<string, { x: number; y: number }>();
  nodes.forEach((node, index) => {
    const communityOffset = (node.community || 0) * 0.35;
    const angle = (index / Math.max(1, nodes.length)) * Math.PI * 2 + communityOffset;
    const r = radius * (0.72 + (index % 4) * 0.08);
    positions.set(node.id, { x: centerX + Math.cos(angle) * r, y: centerY + Math.sin(angle) * r });
  });

  if (!network || !nodes.length) return <div className="empty">No network data yet. Seed or ingest events first.</div>;

  return (
    <div className="network-layout">
      <div className="network-canvas">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Observed interaction network">
          {edges.map((edge, index) => {
            const a = positions.get(edge.source);
            const b = positions.get(edge.target);
            if (!a || !b) return null;
            return <line key={`${edge.source}-${edge.target}-${index}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="network-edge" strokeWidth={Math.min(3, 0.7 + edge.weight)} />;
          })}
          {nodes.map((node) => {
            const p = positions.get(node.id)!;
            const size = 7 + Math.min(12, node.pagerank * 95);
            return (
              <g key={node.id} className="network-node">
                <circle cx={p.x} cy={p.y} r={size} className={`network-dot role-${node.role.replaceAll(' ', '-').toLowerCase()}`} />
                <text x={p.x + size + 4} y={p.y + 4}>{node.label.slice(0, 18)}</text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="network-rank">
        <div className="eyebrow">Observed graph</div>
        <h3>Influence & bridge nodes</h3>
        {nodes.slice(0, 8).map((node: GraphNode) => (
          <div className="rank-row" key={node.id}>
            <div><strong>{node.label}</strong><span>{node.explanation}</span></div>
            <Badge tone={node.role === 'Bridge Node' ? 'warn' : node.role === 'High Reach Node' ? 'good' : 'neutral'}>{node.role}</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

function DemographicSliceCard({ title, slice }: { title: string; slice: DemographicSlice }) {
  const entries = Object.entries(slice.counts).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(([, value]) => value));
  return (
    <div className="panel demographic-card">
      <div className="section-head compact"><h3>{title}</h3><Badge>{pct(slice.coverage)} coverage</Badge></div>
      <div className="bars">
        {entries.map(([label, value]) => (
          <div className="bar-row" key={label}>
            <span>{label.replaceAll('_', ' ')}</span>
            <div className="bar-track"><i style={{ width: `${(value / max) * 100}%` }} /></div>
            <b>{value}</b>
          </div>
        ))}
      </div>
      <div className="mini-note">Confidence {pct(slice.confidence)} · groups below k={slice.minimum_group_size} suppressed</div>
    </div>
  );
}

function NarrativeView({ detail }: { detail: NarrativeDetail | null }) {
  if (!detail) return <div className="empty">Select a narrative from Trends to inspect its evidence-backed lineage.</div>;
  return (
    <div className="narrative-layout">
      <section className="panel panel-large">
        <div className="section-head">
          <div><div className="eyebrow">{detail.id} · Narrative lineage</div><h2>{detail.title}</h2></div>
          <div className="chip-row">
            <Badge tone={detail.trend.status === 'RISING' || detail.trend.status === 'VIRAL' ? 'warn' : 'neutral'}>{detail.trend.status}</Badge>
            <a className="btn btn-secondary" href={api.narrativeCsvUrl(detail.id)}><Download size={14} /> CSV</a>
            <a className="btn btn-secondary" href={api.narrativeJsonUrl(detail.id)}><Download size={14} /> JSON</a>
          </div>
        </div>
        <p className="lead">{detail.representative_text}</p>
        <div className="callout"><ShieldCheck size={18} /><span>{detail.origin_claim}</span></div>
        <div className="lineage">
          {detail.lineage.slice(0, 40).map((item, index) => (
            <div className="lineage-item" key={item.event_id}>
              <div className="lineage-axis"><span>{index + 1}</span></div>
              <div className="lineage-card">
                <div className="row-between">
                  <div className="chip-row"><PlatformBadge platform={item.platform} /><SourceBadge mode={item.source_mode} /></div>
                  <span className="muted">{fmt(item.created_at)}</span>
                </div>
                <strong>{item.author || item.author_pseudo_id || 'Unknown author'}</strong>
                <p>{item.text}</p>
                <div className="chip-row"><span className="chip">sentiment: {item.sentiment || 'unknown'}</span><span className="chip">stance: {item.stance || 'unknown'}</span></div>
                {item.source_url && item.source_url.startsWith('http') && !item.source_url.includes('example.invalid') && (
                  <a href={item.source_url} target="_blank" rel="noreferrer">Open source <ExternalLink size={13} /></a>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
      <aside className="panel narrative-side">
        <div className="eyebrow">Why it matters</div>
        <h3>Trend decomposition</h3>
        {[
          ['Trend score', detail.trend.score.toFixed(2)],
          ['Growth', `${detail.trend.growth_rate >= 0 ? '+' : ''}${detail.trend.growth_rate.toFixed(2)}`],
          ['Burst z-score', detail.trend.burst_zscore.toFixed(2)],
          ['Author diversity', pct(detail.trend.author_diversity)],
          ['Platforms', detail.trend.platform_count],
        ].map(([label, value]) => <div className="fact-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}
        <hr />
        <div className="eyebrow">Platform mix</div>
        <div className="chip-row">{Object.entries(detail.platform_mix).map(([k, v]) => <span className="chip" key={k}>{k}: {v}</span>)}</div>
        <div className="eyebrow spaced">Sentiment mix</div>
        <div className="chip-row">{Object.entries(detail.sentiment_mix).map(([k, v]) => <span className="chip" key={k}>{k}: {v}</span>)}</div>
      </aside>
    </div>
  );
}

function App() {
  const [tab, setTab] = useState<Tab>('overview');
  const [query, setQuery] = useState('#RiverLinkUpdate');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([]);
  const [timelinePoints, setTimelinePoints] = useState<TimelinePoint[]>([]);
  const [narratives, setNarratives] = useState<NarrativeSummary[]>([]);
  const [selectedNarrativeId, setSelectedNarrativeId] = useState<string | null>(null);
  const [narrativeDetail, setNarrativeDetail] = useState<NarrativeDetail | null>(null);
  const [network, setNetwork] = useState<NetworkResponse | null>(null);
  const [demographics, setDemographics] = useState<DemographicsResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [events, setEvents] = useState<SocialEvent[]>([]);
  const [collector, setCollector] = useState<CollectorStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const importRef = useRef<HTMLInputElement>(null);

  const loadAll = useCallback(async () => {
    try {
      setError(null);
      const [status, overviewData, timeData, narrativeData, networkData, demographicData, alertData, eventData, collectorData] = await Promise.all([
        api.connectorStatus(), api.overview(), api.timeline(), api.narratives(), api.network(), api.demographics(), api.alerts(), api.events(), api.collectorStatus(),
      ]);
      setConnectors(status.connectors);
      setOverview(overviewData);
      setTimelinePoints(timeData.points);
      setNarratives(narrativeData.narratives);
      setNetwork(networkData);
      setDemographics(demographicData);
      setAlerts(alertData.alerts);
      setEvents(eventData.events);
      setCollector(collectorData);
      const preferred = selectedNarrativeId || narrativeData.narratives[0]?.id || null;
      if (preferred) {
        setSelectedNarrativeId(preferred);
        try { setNarrativeDetail(await api.narrative(preferred)); } catch { setNarrativeDetail(null); }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to reach NEXUS backend.');
    }
  }, [selectedNarrativeId]);

  useEffect(() => { void loadAll(); }, []); // intentionally initial load only

  useEffect(() => {
    if (!collector?.running) return;
    const timer = window.setInterval(() => void loadAll(), 15000);
    return () => window.clearInterval(timer);
  }, [collector?.running, loadAll]);

  const action = async (label: string, fn: () => Promise<unknown>) => {
    setLoading(true); setError(null); setNotice(null);
    try {
      await fn();
      setNotice(label);
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed.');
    } finally {
      setLoading(false);
    }
  };

  const openNarrative = async (id: string) => {
    setSelectedNarrativeId(id);
    setLoading(true);
    try {
      setNarrativeDetail(await api.narrative(id));
      setNetwork(await api.network(id));
      setTab('narrative');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load narrative.');
    } finally {
      setLoading(false);
    }
  };

  const importJson = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setLoading(true); setError(null); setNotice(null);
    try {
      const parsed = JSON.parse(await file.text());
      const rows = Array.isArray(parsed) ? parsed : parsed.events;
      if (!Array.isArray(rows)) throw new Error('JSON must be an event array or an object with an events array.');
      await api.importEvents(rows);
      setNotice(`Imported ${rows.length} event record(s). They are labelled IMPORT/REPLAY, never LIVE.`);
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed.');
    } finally {
      setLoading(false);
    }
  };

  const platformEntries = useMemo(
    () => Object.entries(overview?.platform_mix || {}).sort((a, b) => b[1] - a[1]),
    [overview],
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={21} /></div>
          <div><strong>NEXUS</strong><span>Narrative & Influence Intelligence · SIH26152</span></div>
        </div>
        <div className="top-actions">
          <div className="query-box"><Search size={17} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Monitor a topic or phrase" /></div>
          <button className="btn btn-secondary" disabled={loading} onClick={() => action('Telegram live poll complete', api.pollTelegram)}><Radio size={16} /> Telegram</button>
          <button className="btn btn-secondary" disabled={loading || !query.trim()} onClick={() => action('X live search complete', () => api.searchX(query.trim()))}>X Live</button>
          <button className="btn btn-secondary" disabled={loading || !query.trim()} onClick={() => action('YouTube live search complete', () => api.searchYouTube(query.trim()))}>YouTube</button>
          <button className="btn btn-primary" disabled={loading} onClick={() => action('Demo narrative seeded', api.seedDemo)}><Play size={16} /> Seed Demo</button>
        </div>
      </header>

      <ConnectorStrip connectors={connectors} />

      {error && <div className="banner banner-error"><AlertTriangle size={18} /><span>{error}</span><button onClick={() => setError(null)}>×</button></div>}
      {notice && <div className="banner banner-success"><ShieldCheck size={18} /><span>{notice}</span><button onClick={() => setNotice(null)}>×</button></div>}

      <div className="body-grid">
        <aside className="sidebar">
          <div className="sidebar-label">ANALYST CONSOLE</div>
          {tabs.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`nav-item ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}>
              <Icon size={18} /><span>{label}</span>{id === 'alerts' && alerts.length > 0 && <i>{alerts.length}</i>}
            </button>
          ))}
          <div className="sidebar-foot">
            <ShieldCheck size={17} />
            <div><strong>Evidence mode</strong><span>LIVE / REPLAY / IMPORT always disclosed.</span></div>
          </div>
        </aside>

        <main className="content">
          {loading && <div className="loading-line"><span /></div>}

          {tab === 'overview' && (
            <>
              <div className="page-head">
                <div><div className="eyebrow">Cross-platform intelligence</div><h1>What is moving — and why?</h1><p>Track narrative emergence, mutation, sentiment and influence with source-level evidence.</p></div>
                <button className="icon-btn" onClick={() => void loadAll()} title="Refresh"><RefreshCw size={18} /></button>
              </div>

              <div className="metric-grid">
                <Metric icon={Database} label="Observed events" value={overview?.total_events || 0} helper="one normalized chronology" />
                <Metric icon={GitBranch} label="Narratives" value={overview?.active_narratives || 0} helper="semantic + temporal clusters" />
                <Metric icon={Activity} label="Rising" value={overview?.rising_narratives || 0} helper="burst & acceleration detected" />
                <Metric icon={AlertTriangle} label="Evidence alerts" value={overview?.alerts || 0} helper="each alert links to evidence" />
              </div>

              <section className="panel" style={{ marginBottom: 14 }}>
                <div className="section-head compact">
                  <div><div className="eyebrow">Collection control</div><h3>Live connectors & continuous monitoring</h3></div>
                  <Badge tone={collector?.running ? 'live' : 'neutral'}>{collector?.running ? `RUNNING · ${collector.cycles} cycles` : 'STOPPED'}</Badge>
                </div>
                <div className="chip-row" style={{ gap: 8 }}>
                  <button className="btn btn-secondary" disabled={loading} onClick={() => action('Instagram sync complete', () => api.syncMeta('instagram'))}>Instagram</button>
                  <button className="btn btn-secondary" disabled={loading} onClick={() => action('Facebook Page sync complete', () => api.syncMeta('facebook'))}>Facebook</button>
                  <button className="btn btn-secondary" disabled={loading} onClick={() => importRef.current?.click()}><Upload size={15} /> Import JSON</button>
                  <input ref={importRef} type="file" accept="application/json,.json" hidden onChange={(e) => void importJson(e)} />
                  {!collector?.running ? (
                    <button className="btn btn-primary" disabled={loading} onClick={() => action('Continuous Telegram collection started', () => api.startCollector(query.trim() || '#RiverLinkUpdate', { telegram: true, x: false, youtube: false, interval: 60 }))}><Radio size={15} /> Start continuous</button>
                  ) : (
                    <button className="btn btn-secondary" disabled={loading} onClick={() => action('Continuous collection stopped', api.stopCollector)}><Square size={14} /> Stop collection</button>
                  )}
                </div>
                <div className="coverage-callout"><ShieldCheck size={17} /><span>Continuous mode defaults to free Telegram only. X and YouTube polling stay opt-in to protect credits/quota. Meta buttons require authorized app/account permissions.</span></div>
              </section>

              <div className="overview-grid">
                <section className="panel panel-span-2">
                  <div className="section-head"><div><div className="eyebrow">Priority narratives</div><h2>Ranked by explainable trend score</h2></div><button className="text-btn" onClick={() => setTab('trends')}>View all →</button></div>
                  <div className="trend-list">
                    {(overview?.top_narratives || []).slice(0, 4).map((n) => <TrendCard key={n.id} narrative={n} onOpen={() => void openNarrative(n.id)} />)}
                    {!overview?.top_narratives?.length && <div className="empty"><Sparkles size={30} /><h3>No events yet</h3><p>Use Seed Demo for a deterministic jury flow, or connect a live source.</p></div>}
                  </div>
                </section>
                <aside className="panel">
                  <div className="eyebrow">Coverage truth</div><h2>Data composition</h2>
                  <div className="platform-stack">
                    {platformEntries.map(([platform, count]) => <div className="platform-stat" key={platform}><PlatformBadge platform={platform} /><strong>{count}</strong></div>)}
                  </div>
                  <hr />
                  <div className="eyebrow">Source modes</div>
                  <div className="chip-row">{Object.entries(overview?.source_modes || {}).map(([mode, count]) => <span className="chip" key={mode}>{mode}: {count}</span>)}</div>
                  <div className="coverage-callout"><ShieldCheck size={18} /><span>{overview?.coverage_note || 'Coverage is always bounded by configured connectors.'}</span></div>
                </aside>
              </div>
            </>
          )}

          {tab === 'timeline' && <><div className="page-head"><div><div className="eyebrow">Exact chronology</div><h1>Timeline & sentiment movement</h1><p>See when volume changes and whether emotion shifts with it.</p></div></div><TimelineView points={timelinePoints} /></>}

          {tab === 'trends' && <><div className="page-head"><div><div className="eyebrow">Real-time trend engine</div><h1>Emerging narratives</h1><p>Ranked using growth, burst, diversity, cross-platform presence, engagement and recency.</p></div></div><div className="trend-list standalone">{narratives.map((n) => <TrendCard key={n.id} narrative={n} onOpen={() => void openNarrative(n.id)} />)}</div></>}

          {tab === 'narrative' && <><div className="page-head"><div><div className="eyebrow">Evidence-backed story</div><h1>Narrative lineage</h1><p>Earliest observed evidence → variants → amplification → sentiment change.</p></div></div><NarrativeView detail={narrativeDetail} /></>}

          {tab === 'network' && <><div className="page-head"><div><div className="eyebrow">Link analysis</div><h1>How influence moved</h1><p>Centrality and bridge roles describe observed network position — never guilt or intent.</p></div><div className="chip-row"><span className="chip">nodes {network?.summary.nodes || 0}</span><span className="chip">edges {network?.summary.edges || 0}</span><span className="chip">communities {network?.summary.communities || 0}</span></div></div><section className="panel panel-large"><NetworkGraph network={network} /></section></>}

          {tab === 'demographics' && demographics && <><div className="page-head"><div><div className="eyebrow">Aggregate only</div><h1>Audience signals without individual profiling</h1><p>{demographics.privacy_note}</p></div><Badge tone="good"><ShieldCheck size={13} /> k-anonymity guard</Badge></div><div className="demographic-grid"><DemographicSliceCard title="Language" slice={demographics.language} /><DemographicSliceCard title="Broad geography" slice={demographics.broad_geography} /><DemographicSliceCard title="Professional interests" slice={demographics.professional_interests} /><DemographicSliceCard title="Age brackets" slice={demographics.age_brackets} /></div></>}

          {tab === 'alerts' && <><div className="page-head"><div><div className="eyebrow">Explainable alerts</div><h1>Why the system raised attention</h1><p>No black-box alarm: each alert includes trigger components, coverage warning and evidence IDs.</p></div></div><div className="alert-list">{alerts.map((alert) => <div className="panel alert-card" key={alert.alert_id}><div className="section-head compact"><div><div className="eyebrow">{fmt(alert.triggered_at)} · confidence {pct(alert.confidence)}</div><h3>{alert.title}</h3></div><Badge tone={alert.severity === 'high' ? 'bad' : 'warn'}>{alert.severity}</Badge></div><ul>{alert.why_triggered.map((why) => <li key={why}>{why}</li>)}</ul><div className="callout"><ShieldCheck size={16} /><span>{alert.coverage_warning}</span></div><div className="row-between"><span className="muted">{alert.evidence_event_ids.length} evidence events · score {alert.trend_score.toFixed(2)}</span><button className="text-btn" onClick={() => void openNarrative(alert.narrative_id)}>Open evidence →</button></div></div>)}{!alerts.length && <div className="empty">No narrative currently crosses the alert threshold.</div>}</div></>}

          {tab === 'evidence' && <><div className="page-head"><div><div className="eyebrow">Source traceability</div><h1>Evidence ledger</h1><p>Every event retains platform, original timestamp, source mode and source URL where available.</p></div></div><section className="panel table-panel"><div className="evidence-table"><div className="evidence-row evidence-head"><span>Source</span><span>Time</span><span>Author</span><span>Text</span><span>Inference</span></div>{events.slice(0, 200).map((event) => <div className="evidence-row" key={event.id}><span><PlatformBadge platform={event.platform} /> <SourceBadge mode={event.source_mode} /></span><span>{fmt(event.created_at)}</span><span>{event.author_display || event.author_pseudo_id || '—'}</span><span className="evidence-text">{event.text}</span><span><Badge>{event.sentiment_label || 'unknown'}</Badge> <Badge>{event.stance_label || 'unclear'}</Badge>{event.url && !event.url.includes('example.invalid') && <a className="source-link" href={event.url} target="_blank" rel="noreferrer"><ExternalLink size={13} /></a>}</span></div>)}</div></section></>}
        </main>
      </div>
    </div>
  );
}

export default App;
