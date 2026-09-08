import { type ChangeEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, AlertTriangle, BarChart3, CheckCircle2, Clock3, Database, Download, ExternalLink, GitBranch,
  Globe2, ListVideo, Network, Play, Radio, RefreshCw, Search, ShieldCheck, Sparkles, Upload, Users, Waypoints, Zap,
} from 'lucide-react';
import {
  type AlertItem, api, type CollectorStatus, type ConnectorStatus, type DemographicSlice, type DemographicsResponse,
  type NarrativeDetail, type NarrativeSummary, type NetworkResponse, type Overview, type SocialEvent, type TimelinePoint,
} from './api';
import EvidenceLedger from './EvidenceLedger';
import NarrativeGraph from './NarrativeGraph';
import NetworkPro from './NetworkPro';
import PostExplorer from './PostExplorer';
import TimelinePro from './TimelinePro';

type Tab = 'overview' | 'posts' | 'timeline' | 'trends' | 'narrative' | 'network' | 'demographics' | 'alerts' | 'evidence';

const tabs: Array<{ id: Tab; label: string; icon: typeof Activity }> = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'posts', label: 'Posts / Explorer', icon: ListVideo },
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
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};
const pct = (value: number | null | undefined) => `${Math.round((value || 0) * 100)}%`;

function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'live' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
function SourceBadge({ mode }: { mode?: string }) {
  return <Badge tone={mode === 'LIVE' ? 'live' : mode === 'REPLAY' ? 'warn' : 'neutral'}>{mode || 'UNKNOWN'}</Badge>;
}
function PlatformBadge({ platform }: { platform: string }) {
  return <span className={`platform platform-${platform}`}>{platform.toUpperCase()}</span>;
}
function Metric({ icon: Icon, label, value, helper }: { icon: typeof Activity; label: string; value: string | number; helper: string }) {
  return <div className="metric-card"><div className="metric-icon"><Icon size={19} /></div><div><div className="metric-value">{value}</div><div className="metric-label">{label}</div><div className="metric-helper">{helper}</div></div></div>;
}

function TrendCard({ narrative, onOpen }: { narrative: NarrativeSummary; onOpen: () => void }) {
  const tone = narrative.trend.status === 'VIRAL' ? 'bad' : narrative.trend.status === 'RISING' ? 'warn' : 'neutral';
  return (
    <button className="trend-card" onClick={onOpen}>
      <div className="trend-card-top"><div><div className="eyebrow">{narrative.id} · {narrative.event_count} events</div><h3>{narrative.title}</h3></div><Badge tone={tone}>{narrative.trend.status}</Badge></div>
      <p>{narrative.representative_text}</p>
      <div className="trend-grid"><span><b>{narrative.trend.score.toFixed(2)}</b> score</span><span><b>{narrative.trend.growth_rate >= 0 ? '+' : ''}{narrative.trend.growth_rate.toFixed(2)}</b> growth</span><span><b>{narrative.trend.platform_count}</b> platforms</span><span><b>{pct(narrative.trend.author_diversity)}</b> diversity</span></div>
      <div className="chip-row">{Object.entries(narrative.platform_mix).map(([platform, count]) => <span className="chip" key={platform}>{platform}: {count}</span>)}</div>
    </button>
  );
}

function DemographicCard({ title, slice }: { title: string; slice: DemographicSlice }) {
  const entries = Object.entries(slice.counts).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(([, value]) => value));
  return <section className="panel demographic-card"><div className="section-head compact"><h3>{title}</h3><Badge>{pct(slice.coverage)} coverage</Badge></div><div className="bars">{entries.map(([label, value]) => <div className="bar-row" key={label}><span>{label.replaceAll('_', ' ')}</span><div className="bar-track"><i style={{ width: `${value / max * 100}%` }} /></div><b>{value}</b></div>)}</div><div className="mini-note">Confidence {pct(slice.confidence)} · groups below k={slice.minimum_group_size} suppressed</div></section>;
}

function NarrativePanel({ detail, onOpenEvent }: { detail: NarrativeDetail | null; onOpenEvent: (id: string) => void }) {
  if (!detail) return <div className="analysis-empty panel panel-large"><div className="analysis-empty-icon"><GitBranch size={25} /></div><h2>Select a narrative</h2><p>Open a narrative from Trends to inspect its chronological evidence lineage.</p></div>;
  return (
    <div className="narrative-layout">
      <section className="panel panel-large">
        <div className="section-head"><div><div className="eyebrow">{detail.id} · evidence lineage</div><h2>{detail.title}</h2></div><div className="chip-row"><Badge tone={detail.trend.status === 'RISING' || detail.trend.status === 'VIRAL' ? 'warn' : 'neutral'}>{detail.trend.status}</Badge><a className="btn btn-secondary" href={api.narrativeCsvUrl(detail.id)}><Download size={14} /> CSV</a><a className="btn btn-secondary" href={api.narrativeJsonUrl(detail.id)}><Download size={14} /> JSON</a></div></div>
        <p className="lead">{detail.representative_text}</p><div className="callout"><ShieldCheck size={17} /><span>{detail.origin_claim}</span></div>
        <NarrativeGraph detail={detail} />
        <div className="lineage">{detail.lineage.slice(0, 60).map((item, index) => <div className="lineage-item" key={item.event_id}><div className="lineage-axis"><span>{index + 1}</span></div><div className="lineage-card"><div className="row-between"><div className="chip-row"><PlatformBadge platform={item.platform} /><SourceBadge mode={item.source_mode} /></div><span className="muted">{fmt(item.created_at)}</span></div><strong>{item.author || item.author_pseudo_id || 'Unknown author'}</strong><p>{item.text}</p><div className="row-between"><div className="chip-row"><span className="chip">sentiment: {item.sentiment || 'unknown'}</span><span className="chip">stance: {item.stance || 'unknown'}</span></div><button className="text-btn" onClick={() => onOpenEvent(item.event_id)}>Inspect post →</button></div>{item.source_url && item.source_url.startsWith('http') && !item.source_url.includes('example.invalid') && <a href={item.source_url} target="_blank" rel="noreferrer">Open source <ExternalLink size={13} /></a>}</div></div>)}</div>
      </section>
      <aside className="panel narrative-side"><div className="eyebrow">Trend decomposition</div><h3>Why it ranks</h3>{[['Trend score', detail.trend.score.toFixed(2)], ['Growth', `${detail.trend.growth_rate >= 0 ? '+' : ''}${detail.trend.growth_rate.toFixed(2)}`], ['Burst z-score', detail.trend.burst_zscore.toFixed(2)], ['Author diversity', pct(detail.trend.author_diversity)], ['Platforms', detail.trend.platform_count]].map(([label, value]) => <div className="fact-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}<hr /><div className="eyebrow">Platform mix</div><div className="chip-row">{Object.entries(detail.platform_mix).map(([key, value]) => <span className="chip" key={key}>{key}: {value}</span>)}</div></aside>
    </div>
  );
}

export default function AppPro() {
  const [tab, setTab] = useState<Tab>('overview');
  const [query, setQuery] = useState('RiverLink');
  const [activeQuery, setActiveQuery] = useState('RiverLink · demo-ready');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [narratives, setNarratives] = useState<NarrativeSummary[]>([]);
  const [narrative, setNarrative] = useState<NarrativeDetail | null>(null);
  const [network, setNetwork] = useState<NetworkResponse | null>(null);
  const [demographics, setDemographics] = useState<DemographicsResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [events, setEvents] = useState<SocialEvent[]>([]);
  const [collector, setCollector] = useState<CollectorStatus | null>(null);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [selectedNarrativeId, setSelectedNarrativeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingTab, setLoadingTab] = useState<Tab | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const queryRef = useRef<HTMLInputElement>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const initialLoadStarted = useRef(false);
  const viewRequestId = useRef(0);

  const applyEvents = useCallback((eventData: { events: SocialEvent[] }) => {
    const rows = eventData.events || [];
    setEvents(rows);
    setSelectedEventId((current) => rows.some((item) => item.id === current) ? current : rows[0]?.id || null);
    const inferred = String(rows[0]?.public_profile?.search_query || '').trim();
    if (inferred) setActiveQuery(inferred);
  }, []);

  const loadCore = useCallback(async (eventLimit = 250) => {
    try {
      setError(null);
      const [status, eventData, collectorData] = await Promise.all([
        api.connectorStatus(), api.events(eventLimit), api.collectorStatus(),
      ]);
      setConnectors(status.connectors || []);
      applyEvents(eventData);
      setCollector(collectorData);
      return eventData;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reach NEXUS backend.');
      return null;
    }
  }, [applyEvents]);

  const loadTabData = useCallback(async (target: Tab) => {
    const requestId = ++viewRequestId.current;
    setLoadingTab(target);
    try {
      if (target === 'overview') {
        const data = await api.overview();
        if (requestId === viewRequestId.current) setOverview(data);
      } else if (target === 'posts' || target === 'evidence') {
        const data = await api.events(2000);
        if (requestId === viewRequestId.current) applyEvents(data);
      } else if (target === 'timeline') {
        const [timelineData, eventData] = await Promise.all([api.timeline(), api.events(700)]);
        if (requestId === viewRequestId.current) {
          setTimeline(timelineData.points || []);
          applyEvents(eventData);
        }
      } else if (target === 'trends') {
        const data = await api.narratives();
        if (requestId === viewRequestId.current) setNarratives(data.narratives || []);
      } else if (target === 'narrative') {
        if (!selectedNarrativeId) return;
        const detail = await api.narrative(selectedNarrativeId);
        if (requestId === viewRequestId.current) {
          setNarrative(detail);
          setNetwork(detail.network);
        }
      } else if (target === 'network') {
        const data = await api.network(selectedNarrativeId || undefined);
        if (requestId === viewRequestId.current) setNetwork(data);
      } else if (target === 'demographics') {
        const data = await api.demographics();
        if (requestId === viewRequestId.current) setDemographics(data);
      } else if (target === 'alerts') {
        const data = await api.alerts();
        if (requestId === viewRequestId.current) setAlerts(data.alerts || []);
      }
    } catch (err) {
      if (requestId === viewRequestId.current) setError(err instanceof Error ? err.message : `Unable to load ${target}.`);
    } finally {
      if (requestId === viewRequestId.current) setLoadingTab(null);
    }
  }, [applyEvents, selectedNarrativeId]);

  const loadAll = useCallback(async () => {
    await loadCore(250);
    void loadTabData(tab);
  }, [loadCore, loadTabData, tab]);

  const changeTab = useCallback((next: Tab) => {
    setTab(next);
    void loadTabData(next);
  }, [loadTabData]);

  useEffect(() => {
    if (initialLoadStarted.current) return;
    initialLoadStarted.current = true;
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!collector?.running) return;
    const timer = window.setInterval(() => {
      void loadCore(250);
      void loadTabData(tab);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [collector?.running, loadCore, loadTabData, tab]);

  useEffect(() => { const onKey = (event: KeyboardEvent) => { const target = event.target as HTMLElement | null; const typing = target?.tagName === 'INPUT' || target?.tagName === 'TEXTAREA' || target?.isContentEditable; if (((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') || (event.key === '/' && !typing)) { event.preventDefault(); queryRef.current?.focus(); queryRef.current?.select(); } }; window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey); }, []);

  const action = async (label: string, fn: () => Promise<unknown>) => {
    setLoading(true); setError(null); setNotice(null);
    try {
      await fn();
      setNotice(label);
      await loadCore(250);
      void loadTabData(tab);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed.');
    } finally {
      setLoading(false);
    }
  };

  const freshSearch = async () => {
    const clean = query.trim(); if (!clean) return;
    setLoading(true); setError(null); setNotice(null);
    setActiveQuery(clean); setSelectedNarrativeId(null); setNarrative(null); setSelectedEventId(null); setEvents([]); setTab('posts');
    try {
      const result = await api.searchWorkspace(clean, { reset: true, limitPerSource: 15 });
      const ok = Object.entries(result.sources).filter(([, status]) => status.state === 'OK').map(([name]) => name);
      const failed = Object.entries(result.sources).filter(([, status]) => status.state !== 'OK').map(([name]) => name);
      setNotice(`Fresh search: ${result.inserted} post(s) · OK ${ok.join(', ') || 'none'}${failed.length ? ` · unavailable ${failed.join(', ')}` : ''}`);
      await loadCore(250);
      void loadTabData('posts');
      void api.overview().then(setOverview).catch(() => undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fresh search failed.');
    } finally {
      setLoading(false);
    }
  };

  const openNarrative = async (id: string) => {
    setLoading(true); setError(null); setSelectedNarrativeId(id); setTab('narrative');
    try {
      const detail = await api.narrative(id);
      setNarrative(detail);
      setNetwork(detail.network);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load narrative.');
    } finally {
      setLoading(false);
    }
  };

  const openPost = (id: string) => {
    setSelectedEventId(id);
    setTab('posts');
    void loadTabData('posts');
  };

  const importJson = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; event.target.value = ''; if (!file) return;
    setLoading(true);
    try {
      const parsed = JSON.parse(await file.text()); const rows = Array.isArray(parsed) ? parsed : parsed.events;
      if (!Array.isArray(rows)) throw new Error('JSON must contain an event array.');
      await api.importEvents(rows);
      setNotice(`Imported ${rows.length} record(s) as IMPORT/REPLAY.`);
      await loadCore(250);
      void loadTabData(tab);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed.');
    } finally {
      setLoading(false);
    }
  };

  const platformEntries = useMemo(() => Object.entries(overview?.platform_mix || {}).sort((a, b) => b[1] - a[1]), [overview]);
  const liveCount = events.filter((event) => event.source_mode === 'LIVE').length;
  const readyCount = connectors.filter((item) => item.state === 'READY' || item.state === 'LIVE').length;
  const latest = events[0]?.created_at || overview?.latest_event_at || null;

  return (
    <div className="app-shell app-pro-shell">
      <header className="topbar"><div className="brand"><div className="brand-mark"><Sparkles size={21} /></div><div><strong>NEXUS</strong><span>Narrative & Influence Intelligence · SIH26152</span></div></div><div className="top-actions"><label className="query-box"><Search size={16} /><input ref={queryRef} value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void freshSearch(); }} placeholder="Search topic, phrase or #hashtag" /></label><button className="btn btn-primary" disabled={loading || !query.trim()} onClick={() => void freshSearch()}><Search size={14} /> Fresh Search</button><button className="btn btn-secondary" disabled={loading} onClick={() => action('Demo workspace loaded', api.seedDemo)}><Play size={14} /> Demo</button></div></header>
      <div className="connector-strip">{connectors.map((connector) => <div className="connector-item" key={connector.platform} title={connector.detail}><span className={`connector-dot connector-${connector.state === 'READY' || connector.state === 'LIVE' ? 'good' : connector.state === 'ERROR' ? 'bad' : 'warn'}`} /><strong>{connector.platform.toUpperCase()}</strong><span>{connector.state.replaceAll('_', ' ')}</span></div>)}</div>
      {error && <div className="banner banner-error"><AlertTriangle size={17} /><span>{error}</span><button onClick={() => setError(null)}>×</button></div>}{notice && <div className="banner banner-success"><CheckCircle2 size={17} /><span>{notice}</span><button onClick={() => setNotice(null)}>×</button></div>}
      <div className="body-grid"><aside className="sidebar"><div className="sidebar-label">ANALYST CONSOLE</div>{tabs.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${tab === id ? 'active' : ''}`} onClick={() => changeTab(id)}><Icon size={18} /><span>{label}</span>{id === 'alerts' && alerts.length > 0 && <i>{alerts.length}</i>}</button>)}<div className="sidebar-foot"><ShieldCheck size={16} /><div><strong>Active workspace</strong><span>{activeQuery}</span><span>LIVE / REPLAY / IMPORT disclosed</span></div></div></aside>
        <main className="content">{(loading || loadingTab === tab) && <div className="loading-line"><span /></div>}
          {tab === 'overview' && <><div className="page-head"><div><div className="eyebrow">Workspace · {activeQuery}</div><h1>Social intelligence command center</h1><p>One clean workspace for live evidence, narratives, chronology, link analysis and source traceability.</p></div><button className="icon-btn" onClick={() => void loadAll()} title="Refresh"><RefreshCw size={18} /></button></div><div className="metric-grid"><Metric icon={Database} label="Observed events" value={overview?.total_events || events.length} helper="active workspace only" /><Metric icon={Zap} label="LIVE evidence" value={`${liveCount}/${events.length}`} helper="currently hydrated evidence" /><Metric icon={Globe2} label="Platforms" value={platformEntries.length} helper="distinct observed sources" /><Metric icon={CheckCircle2} label="Connectors ready" value={`${readyCount}/${connectors.length || 0}`} helper="current readiness states" /></div><div className="overview-grid"><section className="panel panel-span-2"><div className="section-head"><div><div className="eyebrow">Priority narratives</div><h2>What is moving now</h2></div><button className="text-btn" onClick={() => changeTab('trends')}>View all →</button></div><div className="trend-list">{(overview?.top_narratives || []).slice(0, 4).map((item) => <TrendCard key={item.id} narrative={item} onOpen={() => void openNarrative(item.id)} />)}{!overview?.top_narratives?.length && <div className="empty"><Sparkles size={28} /><h3>{loadingTab === 'overview' ? 'Loading intelligence…' : 'No narrative evidence yet'}</h3><p>{loadingTab === 'overview' ? 'Core evidence is already available while overview analytics finishes.' : 'Run Fresh Search or load Demo.'}</p></div>}</div></section><aside className="panel"><div className="eyebrow">Workspace pulse</div><h2>Coverage truth</h2><div className="fact-row"><span>Latest evidence</span><strong>{fmt(latest)}</strong></div><div className="fact-row"><span>Collector</span><strong>{collector?.running ? `LIVE · ${collector.cycles} cycles` : 'Stopped'}</strong></div><div className="platform-stack">{platformEntries.map(([platform, count]) => <div className="platform-stat" key={platform}><PlatformBadge platform={platform} /><strong>{count}</strong></div>)}</div><div className="chip-row pro-overview-actions"><button className="btn btn-secondary" onClick={() => importRef.current?.click()}><Upload size={14} /> Import</button><input hidden ref={importRef} type="file" accept="application/json,.json" onChange={(event) => void importJson(event)} /><button className="btn btn-secondary" disabled={loading || !query.trim()} onClick={() => action('X official evidence appended', () => api.searchX(query.trim()))}>+ X official</button><button className="btn btn-secondary" disabled={loading || !query.trim()} onClick={() => action('YouTube official evidence appended', () => api.searchYouTube(query.trim()))}>+ YouTube official</button></div><div className="coverage-callout"><ShieldCheck size={16} /><span>{overview?.coverage_note || 'Conclusions are bounded by collected evidence.'}</span></div></aside></div></>}
          {tab === 'posts' && <><div className="page-head"><div><div className="eyebrow">Observed social feed · {activeQuery}</div><h1>Posts / Explorer</h1><p>Inspect media, source metadata, engagement, analysis and exact provenance.</p></div><Badge tone="good">{events.length}{loadingTab === 'posts' ? '+' : ''} results</Badge></div><PostExplorer events={events} selectedId={selectedEventId} onSelect={(event) => setSelectedEventId(event.id)} /></>}
          {tab === 'timeline' && <><div className="page-head"><div><div className="eyebrow">Exact chronology</div><h1>Timeline & sentiment movement</h1><p>A theme-safe chronology that remains visible for sparse searches and can rebuild from collected evidence when needed.</p></div></div><TimelinePro points={timeline} events={events} /></>}
          {tab === 'trends' && <><div className="page-head"><div><div className="eyebrow">Explainable trend engine</div><h1>Emerging narratives</h1><p>Ranked by growth, burst, diversity, cross-platform presence, engagement and recency.</p></div></div><div className="trend-list standalone">{narratives.map((item) => <TrendCard key={item.id} narrative={item} onOpen={() => void openNarrative(item.id)} />)}{!narratives.length && <div className="empty">{loadingTab === 'trends' ? 'Loading narrative rankings in the background…' : 'No narratives in the current workspace.'}</div>}</div></>}
          {tab === 'narrative' && <><div className="page-head"><div><div className="eyebrow">Evidence-backed story</div><h1>Narrative lineage & propagation</h1><p>Visible propagation graph plus earliest observed evidence, variants and amplification — bounded to the collected dataset.</p></div></div><NarrativePanel detail={narrative} onOpenEvent={openPost} /></>}
          {tab === 'network' && <><div className="page-head"><div><div className="eyebrow">Link analysis</div><h1>Community & influence network</h1><p>Interactive structural analysis of observed authors and relationships, without identity or intent claims.</p></div></div><NetworkPro network={network} /></>}
          {tab === 'demographics' && <><div className="page-head"><div><div className="eyebrow">Aggregate only</div><h1>Privacy-conscious audience signals</h1><p>{demographics?.privacy_note || 'Only aggregate anonymized signals are shown.'}</p></div><Badge tone="good"><ShieldCheck size={12} /> k-anonymity</Badge></div>{demographics ? <div className="demographic-grid"><DemographicCard title="Language" slice={demographics.language} /><DemographicCard title="Broad geography" slice={demographics.broad_geography} /><DemographicCard title="Professional interests" slice={demographics.professional_interests} /><DemographicCard title="Age brackets" slice={demographics.age_brackets} /></div> : <div className="empty">{loadingTab === 'demographics' ? 'Loading demographic aggregates…' : 'No demographic aggregates yet.'}</div>}</>}
          {tab === 'alerts' && <><div className="page-head"><div><div className="eyebrow">Explainable alerts</div><h1>Attention signals</h1><p>Every alert exposes why it fired and which evidence supports it.</p></div></div><div className="alert-list">{alerts.map((alert) => <section className="panel alert-card" key={alert.alert_id}><div className="section-head compact"><div><div className="eyebrow">{fmt(alert.triggered_at)} · confidence {pct(alert.confidence)}</div><h3>{alert.title}</h3></div><Badge tone={alert.severity === 'high' ? 'bad' : 'warn'}>{alert.severity}</Badge></div><ul>{alert.why_triggered.map((why) => <li key={why}>{why}</li>)}</ul>{alert.coverage_warning && <div className="callout"><ShieldCheck size={15} /><span>{alert.coverage_warning}</span></div>}<div className="row-between"><span className="muted">{alert.evidence_event_ids.length} evidence events · score {alert.trend_score.toFixed(2)}</span><button className="text-btn" onClick={() => void openNarrative(alert.narrative_id)}>Open evidence →</button></div></section>)}{!alerts.length && <div className="empty">{loadingTab === 'alerts' ? 'Loading explainable alerts…' : 'No narrative currently crosses the alert threshold.'}</div>}</div></>}
          {tab === 'evidence' && <><div className="page-head"><div><div className="eyebrow">Source traceability</div><h1>Evidence ledger</h1><p>Responsive, searchable, filterable and exportable evidence records with exact provenance.</p></div></div><EvidenceLedger events={events} onOpenEvent={openPost} /></>}
        </main></div>
    </div>
  );
}