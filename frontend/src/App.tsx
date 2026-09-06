import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BellRing,
  ChevronRight,
  Database,
  Download,
  ExternalLink,
  GitBranch,
  Globe2,
  Layers3,
  MessageCircle,
  Network as NetworkIcon,
  Play,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  Waypoints,
  Youtube,
  Zap,
} from 'lucide-react'
import {
  exportCsvUrl,
  importXUrl,
  ingestTelegram,
  ingestX,
  ingestYouTube,
  loadDashboard,
  seedDemo,
} from './api'
import type {
  Alert,
  DashboardBundle,
  DistributionItem,
  EventItem,
  Narrative,
  NetworkData,
  Trend,
} from './types'

const EMPTY_BUNDLE: DashboardBundle = {
  summary: {
    events: 0,
    unique_authors: 0,
    platforms: {},
    source_modes: {},
    narratives: 0,
    cross_platform_narratives: 0,
    rising_narratives: 0,
    active_alerts: 0,
    sentiment: {},
    stance: {},
    emotion: {},
    required_platform_coverage_pct: 0,
    latest_event_at: null,
    mode_label: 'EMPTY',
  },
  narratives: [],
  trends: [],
  network: { nodes: [], edges: [], communities: [], top_influence_nodes: [], top_bridge_nodes: [], metadata: { node_count: 0, edge_count: 0, meaning: '' } },
  demographics: { sample_size: 0, minimum_publishable_group: 10, publishable: false, language: [], broad_geography: [], professional_interests: [], explicit_age_brackets: [], coverage: {}, confidence: 0, privacy_note: '', age_note: '' },
  evidence: { event_count: 0, unique_pseudonymous_authors: 0, observed_platforms: [], required_platforms: ['x', 'telegram'], required_platforms_present: [], missing_required_platforms: ['x', 'telegram'], optional_platforms_present: [], required_platform_coverage_pct: 0, source_modes: {}, earliest_source_time: null, latest_source_time: null, latest_ingest_time: null, ingest_freshness_seconds: null, mean_analysis_confidence: 0, narratives: [], coverage_warning: 'No data loaded.', truthfulness_note: '' },
  alerts: [],
  events: [],
  platformStatus: {},
}

type Tab = 'command' | 'narratives' | 'lineage' | 'network' | 'audience' | 'evidence'

const nav: Array<{ id: Tab; label: string; icon: ReactNode }> = [
  { id: 'command', label: 'Command Center', icon: <Activity size={17} /> },
  { id: 'narratives', label: 'Narrative Explorer', icon: <Layers3 size={17} /> },
  { id: 'lineage', label: 'Lineage Graph', icon: <Waypoints size={17} /> },
  { id: 'network', label: 'Influence Network', icon: <NetworkIcon size={17} /> },
  { id: 'audience', label: 'Audience Intelligence', icon: <Users size={17} /> },
  { id: 'evidence', label: 'Evidence & Reports', icon: <ShieldCheck size={17} /> },
]

function App() {
  const [tab, setTab] = useState<Tab>('command')
  const [bundle, setBundle] = useState<DashboardBundle>(EMPTY_BUNDLE)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedNarrative, setSelectedNarrative] = useState<string>('')
  const [query, setQuery] = useState('Pune Metro heavy rain closure')
  const [xUrl, setXUrl] = useState('')
  const [actionNote, setActionNote] = useState('')
  const [actionBusy, setActionBusy] = useState(false)

  const refresh = async (autoSeed = false) => {
    setLoading(true)
    setError('')
    try {
      let data = await loadDashboard()
      if (autoSeed && data.summary.events === 0) {
        await seedDemo()
        data = await loadDashboard()
      }
      setBundle(data)
      if (!selectedNarrative && data.narratives[0]) setSelectedNarrative(data.narratives[0].id)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const chosenNarrative = bundle.narratives.find((item) => item.id === selectedNarrative) ?? bundle.narratives[0]

  const execute = async (label: string, task: () => Promise<Record<string, unknown>>) => {
    setActionBusy(true)
    setActionNote(`${label}…`)
    try {
      const result = await task()
      const status = result.connector_status as { detail?: string; state?: string } | undefined
      setActionNote(status?.detail ? `${status.state ?? 'DONE'} · ${status.detail}` : `${label} completed.`)
      await refresh(false)
    } catch (err) {
      setActionNote(err instanceof Error ? err.message : String(err))
    } finally {
      setActionBusy(false)
    }
  }

  const resetDemo = async () => {
    setActionBusy(true)
    try {
      await seedDemo()
      setActionNote('REPLAY dataset reset. The same analytics pipeline used for live connectors is now running on deterministic SIH evidence.')
      await refresh(false)
    } catch (err) {
      setActionNote(err instanceof Error ? err.message : String(err))
    } finally {
      setActionBusy(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark"><Sparkles size={20} /></div>
          <div>
            <div className="brand-name">NEXUS</div>
            <div className="brand-sub">Narrative Intelligence</div>
          </div>
        </div>
        <div className="ps-chip">SIH26152 · NTRO</div>
        <nav className="nav-list">
          {nav.map((item) => (
            <button key={item.id} className={`nav-item ${tab === item.id ? 'active' : ''}`} onClick={() => setTab(item.id)}>
              {item.icon}<span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="mode-card">
            <div className="mode-top"><Radio size={14} /><span>DATA MODE</span></div>
            <strong>{bundle.summary.mode_label}</strong>
            <small>{bundle.summary.mode_label.includes('REPLAY') ? 'Historical/demo data — never presented as live.' : 'Source mode is attached to every event.'}</small>
          </div>
          <div className="tiny-note">Track ideas, not just hashtags.</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <div className="eyebrow">REAL-TIME NARRATIVE & INFLUENCE INTELLIGENCE</div>
            <h1>{nav.find((item) => item.id === tab)?.label}</h1>
          </div>
          <div className="top-actions">
            <span className={`mode-pill ${bundle.summary.mode_label.toLowerCase().includes('live') ? 'live' : 'replay'}`}>
              <span className="pulse-dot" /> {bundle.summary.mode_label}
            </span>
            <button className="icon-btn" onClick={() => void refresh(false)} title="Refresh" disabled={loading}><RefreshCw size={17} className={loading ? 'spin' : ''} /></button>
          </div>
        </header>

        {error && (
          <div className="error-banner"><AlertTriangle size={18} /><div><strong>Backend unavailable</strong><span>{error}</span></div></div>
        )}

        <section className="workspace">
          {tab === 'command' && <CommandCenter bundle={bundle} loading={loading} onNavigate={setTab} />}
          {tab === 'narratives' && <NarrativeExplorer bundle={bundle} selected={chosenNarrative} onSelect={(id) => setSelectedNarrative(id)} onOpenLineage={() => setTab('lineage')} />}
          {tab === 'lineage' && <LineageView bundle={bundle} narrative={chosenNarrative} onSelect={setSelectedNarrative} />}
          {tab === 'network' && <NetworkView data={bundle.network} />}
          {tab === 'audience' && <AudienceView bundle={bundle} />}
          {tab === 'evidence' && <EvidenceView bundle={bundle} />}
        </section>

        <ConnectorDock
          query={query}
          setQuery={setQuery}
          xUrl={xUrl}
          setXUrl={setXUrl}
          note={actionNote}
          busy={actionBusy}
          onDemo={() => void resetDemo()}
          onTelegram={() => void execute('Polling Telegram', ingestTelegram)}
          onX={() => void execute('Querying official X API', () => ingestX(query))}
          onXUrl={() => void execute('Importing public X URL', () => importXUrl(xUrl))}
          onYouTube={() => void execute('Querying YouTube', () => ingestYouTube(query))}
        />
      </main>
    </div>
  )
}

function CommandCenter({ bundle, loading, onNavigate }: { bundle: DashboardBundle; loading: boolean; onNavigate: (tab: Tab) => void }) {
  const topTrend = bundle.trends[0]
  const topAlert = bundle.alerts[0]
  const dominantSentiment = Object.entries(bundle.summary.sentiment).sort((a, b) => b[1] - a[1])[0]
  return (
    <div className={loading ? 'loading-soft' : ''}>
      <div className="metric-grid">
        <MetricCard label="Observed Events" value={bundle.summary.events} helper={`${bundle.summary.unique_authors} pseudonymous authors`} icon={<Database size={18} />} />
        <MetricCard label="Active Narratives" value={bundle.summary.narratives} helper={`${bundle.summary.cross_platform_narratives} cross-platform`} icon={<Layers3 size={18} />} />
        <MetricCard label="Rising Narratives" value={bundle.summary.rising_narratives} helper={topTrend ? `${topTrend.velocity_ratio.toFixed(2)}× top velocity` : 'Waiting for events'} icon={<Zap size={18} />} />
        <MetricCard label="Required Coverage" value={`${bundle.summary.required_platform_coverage_pct.toFixed(0)}%`} helper="X + Telegram observed coverage" icon={<ShieldCheck size={18} />} />
      </div>

      <div className="two-col command-top">
        <article className="panel hero-panel">
          <div className="panel-kicker"><BellRing size={15} /> EARLY WARNING</div>
          {topAlert ? (
            <>
              <div className="alert-title-row"><span className={`severity ${topAlert.severity.toLowerCase()}`}>{topAlert.severity}</span><span>Confidence {(topAlert.confidence * 100).toFixed(0)}%</span></div>
              <h2>{topAlert.title}</h2>
              <p>{topAlert.why_triggered[0]}</p>
              <div className="alert-strip">
                <InfoAtom label="Narrative" value={topAlert.narrative_id} />
                <InfoAtom label="Trend score" value={topAlert.trend_score.toFixed(2)} />
                <InfoAtom label="Platforms" value={Object.keys(topAlert.platform_mix).join(' → ')} />
              </div>
              <button className="text-action" onClick={() => onNavigate('lineage')}>Trace this narrative <ChevronRight size={15} /></button>
            </>
          ) : (
            <EmptyState label="No trend alert has crossed the explainable threshold yet." />
          )}
        </article>

        <article className="panel">
          <div className="panel-header"><div><span className="panel-kicker"><Activity size={15} /> SIGNAL STATE</span><h3>What is moving now?</h3></div></div>
          {topTrend ? (
            <div className="trend-focus">
              <div className="trend-score-ring"><strong>{Math.round(topTrend.trend_score * 100)}</strong><span>/100</span></div>
              <div className="trend-copy"><div className={`status-chip ${topTrend.status.toLowerCase()}`}>{topTrend.status}</div><h4>{topTrend.title}</h4><p>{topTrend.reason}</p></div>
            </div>
          ) : <EmptyState label="Load events to calculate velocity, acceleration and burst score." />}
          <div className="micro-grid">
            <InfoAtom label="Dominant sentiment" value={dominantSentiment ? `${dominantSentiment[0]} · ${dominantSentiment[1]}` : '—'} />
            <InfoAtom label="Alerts" value={String(bundle.summary.active_alerts)} />
            <InfoAtom label="Platforms" value={String(Object.keys(bundle.summary.platforms).length)} />
          </div>
        </article>
      </div>

      <div className="three-col">
        <article className="panel span-two">
          <div className="panel-header"><div><span className="panel-kicker"><Waypoints size={15} /> NARRATIVE LIFECYCLE</span><h3>Observed propagation path</h3></div><button className="text-action" onClick={() => onNavigate('narratives')}>Explore all</button></div>
          <NarrativePath narrative={bundle.narratives[0]} events={bundle.events} />
        </article>
        <article className="panel">
          <div className="panel-header"><div><span className="panel-kicker"><BarChart3 size={15} /> SENTIMENT</span><h3>Current distribution</h3></div></div>
          <DistributionBars items={recordToDistribution(bundle.summary.sentiment)} compact />
          <p className="subtle-note">Sentiment is a model signal with uncertainty — not a statement of user intent.</p>
        </article>
      </div>

      <div className="two-col">
        <article className="panel">
          <div className="panel-header"><div><span className="panel-kicker"><GitBranch size={15} /> STRUCTURAL INFLUENCE</span><h3>Bridge & influence nodes</h3></div><button className="text-action" onClick={() => onNavigate('network')}>Open network</button></div>
          <RankList nodes={bundle.network.top_influence_nodes.slice(0, 5)} />
        </article>
        <article className="panel evidence-mini">
          <div className="panel-header"><div><span className="panel-kicker"><ShieldCheck size={15} /> EVIDENCE LEDGER</span><h3>Coverage before certainty</h3></div><button className="text-action" onClick={() => onNavigate('evidence')}>Inspect evidence</button></div>
          <CoverageGrid bundle={bundle} />
          <p>{bundle.evidence.coverage_warning}</p>
        </article>
      </div>
    </div>
  )
}

function NarrativeExplorer({ bundle, selected, onSelect, onOpenLineage }: { bundle: DashboardBundle; selected?: Narrative; onSelect: (id: string) => void; onOpenLineage: () => void }) {
  const selectedEvents = selected ? bundle.events.filter((event) => event.narrative_cluster_id === selected.id) : []
  return (
    <div className="split-view">
      <div className="narrative-list panel">
        <div className="panel-header"><div><span className="panel-kicker"><Layers3 size={15} /> SEMANTIC CLUSTERS</span><h3>Ideas, not exact hashtags</h3></div></div>
        {bundle.narratives.map((item) => (
          <button key={item.id} className={`narrative-card ${selected?.id === item.id ? 'selected' : ''}`} onClick={() => onSelect(item.id)}>
            <div className="narrative-card-top"><span>{item.id}</span><span className={item.cross_platform ? 'cross' : ''}>{item.cross_platform ? 'CROSS-PLATFORM' : 'SINGLE SOURCE'}</span></div>
            <strong>{item.title}</strong>
            <p>{item.sample_text}</p>
            <div className="tag-row">{item.platforms.map((platform) => <PlatformTag key={platform} platform={platform} />)}</div>
            <div className="card-stats"><span>{item.event_count} events</span><span>{item.mutation_count} mutations</span><span>{Math.round(item.cluster_confidence * 100)}% cluster confidence</span></div>
          </button>
        ))}
        {!bundle.narratives.length && <EmptyState label="No narratives yet." />}
      </div>

      <div className="detail-stack">
        {selected ? (
          <>
            <article className="panel narrative-detail">
              <div className="panel-header"><div><span className="panel-kicker">{selected.id} · ORIGIN {selected.origin_platform.toUpperCase()}</span><h2>{selected.title}</h2></div><button className="primary-btn small" onClick={onOpenLineage}>Open lineage <Waypoints size={15} /></button></div>
              <p className="lead-copy">{selected.sample_text}</p>
              <div className="detail-metrics">
                <InfoAtom label="First observed" value={timeLabel(selected.first_observed)} />
                <InfoAtom label="Last observed" value={timeLabel(selected.last_observed)} />
                <InfoAtom label="Authors" value={String(selected.author_count)} />
                <InfoAtom label="Cross-platform hops" value={String(selected.cross_platform_hops)} />
              </div>
              <div className="keyword-cloud">{selected.topic_terms.slice(0, 10).map((term) => <span key={term}>{term}</span>)}</div>
            </article>
            <article className="panel">
              <div className="panel-header"><div><span className="panel-kicker">SOURCE EVIDENCE</span><h3>Chronological members</h3></div></div>
              <div className="event-feed">
                {selectedEvents.map((event) => <EventRow key={event.id} event={event} />)}
              </div>
            </article>
          </>
        ) : <article className="panel"><EmptyState label="Select a narrative to inspect its evidence." /></article>}
      </div>
    </div>
  )
}

function LineageView({ bundle, narrative, onSelect }: { bundle: DashboardBundle; narrative?: Narrative; onSelect: (id: string) => void }) {
  const members = narrative ? bundle.events.filter((event) => event.narrative_cluster_id === narrative.id).sort((a, b) => a.created_at.localeCompare(b.created_at)) : []
  return (
    <div>
      <div className="lineage-toolbar panel">
        <div><span className="panel-kicker"><Waypoints size={15} /> TIME-AWARE NARRATIVE LINEAGE</span><h3>Origin → mutation → cross-platform migration</h3></div>
        <select value={narrative?.id ?? ''} onChange={(event) => onSelect(event.target.value)}>
          {bundle.narratives.map((item) => <option value={item.id} key={item.id}>{item.id} · {item.title}</option>)}
        </select>
      </div>
      {narrative ? (
        <article className="panel lineage-canvas">
          <div className="lineage-summary">
            <div><span>Earliest observed</span><strong>{narrative.origin_platform.toUpperCase()} · {timeLabel(narrative.first_observed)}</strong></div>
            <div><span>Platform migration</span><strong>{narrative.platforms.join(' → ')}</strong></div>
            <div><span>Mutation points</span><strong>{narrative.mutation_count}</strong></div>
            <div><span>Semantic cluster confidence</span><strong>{Math.round(narrative.cluster_confidence * 100)}%</strong></div>
          </div>
          <div className="lineage-track">
            {members.map((event, index) => {
              const edge = index > 0 ? narrative.lineage[index - 1] : undefined
              return (
                <div className="lineage-step" key={event.id}>
                  {index > 0 && (
                    <div className={`lineage-link ${edge?.cross_platform ? 'cross-link' : ''}`}>
                      <span>{edge ? `${Math.round(edge.semantic_similarity * 100)}% semantic match` : 'related'}</span>
                      {edge?.mutation && <em>MUTATION</em>}
                    </div>
                  )}
                  <div className={`lineage-node ${index === 0 ? 'origin' : ''}`}>
                    <div className="node-head"><PlatformTag platform={event.platform} /><span>{timeLabel(event.created_at)}</span>{index === 0 && <b>EARLIEST OBSERVED</b>}</div>
                    <p>{event.text}</p>
                    <div className="node-foot"><span>{event.author_display ?? 'Pseudonymous source'}</span><span>{event.sentiment_label ?? 'unknown'} sentiment</span><span>{event.stance_label ?? 'unknown'} stance</span></div>
                  </div>
                </div>
              )
            })}
          </div>
          <div className="method-note"><ShieldCheck size={16} /><span>Lineage means chronological semantic association inside observed data. NEXUS does not claim causal transmission where the platform does not expose it.</span></div>
        </article>
      ) : <article className="panel"><EmptyState label="No narrative lineage available." /></article>}
    </div>
  )
}

function NetworkView({ data }: { data: NetworkData }) {
  return (
    <div className="two-col network-layout">
      <article className="panel network-panel">
        <div className="panel-header"><div><span className="panel-kicker"><NetworkIcon size={15} /> OBSERVED TOPOLOGY</span><h3>Interaction & propagation network</h3></div><span className="counter-chip">{data.metadata.node_count} nodes · {data.metadata.edge_count} edges</span></div>
        <NetworkCanvas data={data} />
        <p className="subtle-note">{data.metadata.meaning}</p>
      </article>
      <div className="detail-stack">
        <article className="panel"><div className="panel-header"><div><span className="panel-kicker">STRUCTURAL INFLUENCE</span><h3>Highest-ranked observed nodes</h3></div></div><RankList nodes={data.top_influence_nodes.slice(0, 7)} /></article>
        <article className="panel"><div className="panel-header"><div><span className="panel-kicker">BRIDGE NODES</span><h3>Connectors between communities</h3></div></div><RankList nodes={data.top_bridge_nodes.slice(0, 6)} bridge /></article>
      </div>
    </div>
  )
}

function AudienceView({ bundle }: { bundle: DashboardBundle }) {
  const demo = bundle.demographics
  return (
    <div>
      <article className="panel privacy-banner"><ShieldCheck size={24} /><div><span className="panel-kicker">PRIVACY BY DESIGN</span><h3>Aggregate audience intelligence — never individual sensitive-trait profiling</h3><p>{demo.privacy_note}</p></div><div className="confidence-badge"><span>coverage confidence</span><strong>{Math.round(demo.confidence * 100)}%</strong></div></article>
      <div className="metric-grid audience-metrics">
        <MetricCard label="Sample Size" value={demo.sample_size} helper={`k-anonymity minimum ${demo.minimum_publishable_group}`} icon={<Users size={18} />} />
        <MetricCard label="Language Coverage" value={`${(demo.coverage.language_pct ?? 0).toFixed(0)}%`} helper="Detected or public self-declared" icon={<MessageCircle size={18} />} />
        <MetricCard label="Geo Coverage" value={`${(demo.coverage.geography_pct ?? 0).toFixed(0)}%`} helper="Broad public profile labels only" icon={<Globe2 size={18} />} />
        <MetricCard label="Interest Coverage" value={`${(demo.coverage.professional_interest_pct ?? 0).toFixed(0)}%`} helper="Aggregate bio-category signals" icon={<Sparkles size={18} />} />
      </div>
      <div className="two-col">
        <DistributionPanel title="Language distribution" subtitle="Observed public/detected language" items={demo.language} />
        <DistributionPanel title="Broad geography" subtitle="Only explicit broad public location labels" items={demo.broad_geography} />
        <DistributionPanel title="Professional interests" subtitle="Aggregate categories from public bio terms" items={demo.professional_interests} />
        <DistributionPanel title="Explicit age brackets" subtitle="Never guessed — shown only when source data explicitly supplies a bracket" items={demo.explicit_age_brackets} note={demo.age_note} />
      </div>
    </div>
  )
}

function EvidenceView({ bundle }: { bundle: DashboardBundle }) {
  return (
    <div>
      <div className="two-col evidence-top">
        <article className="panel"><div className="panel-header"><div><span className="panel-kicker"><ShieldCheck size={15} /> SOURCE COVERAGE</span><h3>What NEXUS actually observed</h3></div><strong className="coverage-number">{bundle.evidence.required_platform_coverage_pct.toFixed(0)}%</strong></div><CoverageGrid bundle={bundle} /><p className="coverage-warning">{bundle.evidence.coverage_warning}</p></article>
        <article className="panel"><div className="panel-header"><div><span className="panel-kicker"><Database size={15} /> AUDIT LEDGER</span><h3>Freshness & inference context</h3></div><a className="primary-btn small" href={exportCsvUrl()}><Download size={15} /> Export CSV</a></div><div className="audit-grid"><InfoAtom label="Observed events" value={String(bundle.evidence.event_count)} /><InfoAtom label="Pseudonymous authors" value={String(bundle.evidence.unique_pseudonymous_authors)} /><InfoAtom label="Mean analysis confidence" value={`${Math.round(bundle.evidence.mean_analysis_confidence * 100)}%`} /><InfoAtom label="Latest source event" value={bundle.evidence.latest_source_time ? timeLabel(bundle.evidence.latest_source_time) : '—'} /></div><div className="truth-note"><AlertTriangle size={17} /><span>{bundle.evidence.truthfulness_note}</span></div></article>
      </div>
      <article className="panel">
        <div className="panel-header"><div><span className="panel-kicker">NARRATIVE EVIDENCE STATES</span><h3>Confidence without a fake “truth oracle”</h3></div></div>
        <div className="evidence-table">
          <div className="evidence-row head"><span>Narrative</span><span>State</span><span>Platforms</span><span>Events</span><span>Confidence</span><span>Reason</span></div>
          {bundle.evidence.narratives.map((item) => {
            const title = bundle.narratives.find((narrative) => narrative.id === item.narrative_id)?.title ?? item.narrative_id
            return <div className="evidence-row" key={item.narrative_id}><span><b>{item.narrative_id}</b><small>{title}</small></span><span><StateChip state={item.credibility_state} /></span><span className="tag-row">{item.platforms.map((platform) => <PlatformTag key={platform} platform={platform} />)}</span><span>{item.event_count}</span><span>{Math.round(item.mean_analysis_confidence * 100)}%</span><span>{item.state_reason}</span></div>
          })}
        </div>
      </article>
    </div>
  )
}

function ConnectorDock(props: { query: string; setQuery: (value: string) => void; xUrl: string; setXUrl: (value: string) => void; note: string; busy: boolean; onDemo: () => void; onTelegram: () => void; onX: () => void; onXUrl: () => void; onYouTube: () => void }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`connector-dock ${open ? 'open' : ''}`}>
      <button className="dock-toggle" onClick={() => setOpen((value) => !value)}><Radio size={16} /><span>Data Sources</span><ChevronRight size={15} /></button>
      {open && <div className="dock-body">
        <div className="dock-copy"><strong>Run the same pipeline on live or replay evidence.</strong><span>Missing credentials never break the deterministic jury demo.</span></div>
        <label><Search size={15} /><input value={props.query} onChange={(event) => props.setQuery(event.target.value)} placeholder="Monitored phrase / query" /></label>
        <div className="dock-buttons">
          <button onClick={props.onDemo} disabled={props.busy}><Play size={14} /> Reset SIH Replay</button>
          <button onClick={props.onTelegram} disabled={props.busy}><MessageCircle size={14} /> Telegram Live</button>
          <button onClick={props.onX} disabled={props.busy}><span className="x-glyph">𝕏</span> X Official</button>
          <button onClick={props.onYouTube} disabled={props.busy}><Youtube size={14} /> YouTube</button>
        </div>
        <label><ExternalLink size={15} /><input value={props.xUrl} onChange={(event) => props.setXUrl(event.target.value)} placeholder="Optional public X status URL" /><button onClick={props.onXUrl} disabled={props.busy || !props.xUrl}>Import URL</button></label>
        {props.note && <div className="action-note">{props.busy && <RefreshCw size={13} className="spin" />}{props.note}</div>}
      </div>}
    </div>
  )
}

function MetricCard({ label, value, helper, icon }: { label: string; value: string | number; helper: string; icon: ReactNode }) {
  return <article className="metric-card"><div className="metric-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{helper}</small></div></article>
}

function InfoAtom({ label, value }: { label: string; value: string }) {
  return <div className="info-atom"><span>{label}</span><strong>{value}</strong></div>
}

function PlatformTag({ platform }: { platform: string }) {
  return <span className={`platform-tag ${platform.toLowerCase()}`}>{platform}</span>
}

function EventRow({ event }: { event: EventItem }) {
  return <div className="event-row"><div className="event-time">{timeLabel(event.created_at)}</div><div className="event-main"><div className="event-meta"><PlatformTag platform={event.platform} /><span className={`source-badge ${event.source_mode.toLowerCase()}`}>{event.source_mode}</span><span>{event.author_display ?? 'Pseudonymous source'}</span></div><p>{event.text}</p><div className="tag-row"><span>{event.sentiment_label ?? 'unknown'} sentiment</span><span>{event.stance_label ?? 'unknown'} stance</span>{typeof event.sarcasm_probability === 'number' && <span>{Math.round(event.sarcasm_probability * 100)}% sarcasm signal</span>}{event.url && <a href={event.url} target="_blank" rel="noreferrer">source <ExternalLink size={12} /></a>}</div></div></div>
}

function NarrativePath({ narrative, events }: { narrative?: Narrative; events: EventItem[] }) {
  if (!narrative) return <EmptyState label="No narrative evidence loaded." />
  const members = events.filter((event) => event.narrative_cluster_id === narrative.id).slice(0, 7)
  return <div className="mini-path">{members.map((event, index) => <div className="mini-path-item" key={event.id}><div className={`mini-dot ${index === 0 ? 'origin' : ''}`}>{index + 1}</div><div><PlatformTag platform={event.platform} /><strong>{index === 0 ? 'Earliest observed' : index === members.length - 1 ? 'Latest observed' : 'Narrative evolution'}</strong><p>{event.text}</p><span>{timeLabel(event.created_at)}</span></div>{index < members.length - 1 && <ChevronRight className="mini-arrow" size={18} />}</div>)}</div>
}

function DistributionBars({ items, compact = false }: { items: DistributionItem[]; compact?: boolean }) {
  const max = Math.max(1, ...items.map((item) => item.count))
  return <div className={`bar-list ${compact ? 'compact' : ''}`}>{items.length ? items.map((item) => <div className="bar-row" key={item.label}><div className="bar-label"><span>{humanize(item.label)}</span><strong>{item.percentage.toFixed(0)}%</strong></div><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(3, (item.count / max) * 100)}%` }} /></div></div>) : <EmptyState label="Not enough publishable aggregate data." />}</div>
}

function DistributionPanel({ title, subtitle, items, note }: { title: string; subtitle: string; items: DistributionItem[]; note?: string }) {
  return <article className="panel"><div className="panel-header"><div><span className="panel-kicker">AGGREGATE · K-ANONYMOUS</span><h3>{title}</h3><p>{subtitle}</p></div></div><DistributionBars items={items} />{note && <p className="subtle-note">{note}</p>}</article>
}

function CoverageGrid({ bundle }: { bundle: DashboardBundle }) {
  const all = ['x', 'telegram', 'instagram', 'facebook', 'youtube', 'reddit']
  return <div className="coverage-grid">{all.map((platform) => { const observed = bundle.evidence.observed_platforms.includes(platform); const required = bundle.evidence.required_platforms.includes(platform); return <div key={platform} className={`coverage-source ${observed ? 'observed' : ''}`}><PlatformTag platform={platform} /><strong>{observed ? 'OBSERVED' : 'NOT IN CURRENT DATA'}</strong><span>{required ? 'official essential' : 'optional / desirable'}</span></div> })}</div>
}

function RankList({ nodes, bridge = false }: { nodes: NetworkData['nodes']; bridge?: boolean }) {
  return <div className="rank-list">{nodes.length ? nodes.map((node, index) => <div className="rank-row" key={node.id}><span className="rank-number">{String(index + 1).padStart(2, '0')}</span><div className="rank-copy"><strong>{node.label}</strong><span>{node.platform} · community {node.community ?? '—'}</span></div><div className="rank-score"><strong>{((bridge ? node.bridge_score : node.structural_influence_score) * 100).toFixed(1)}</strong><span>{bridge ? 'bridge' : 'structural'}</span></div></div>) : <EmptyState label="No interaction network yet." />}</div>
}

function NetworkCanvas({ data }: { data: NetworkData }) {
  const nodes = data.nodes.slice(0, 24)
  const positioned = useMemo(() => nodes.map((node, index) => { const angle = (index / Math.max(1, nodes.length)) * Math.PI * 2 - Math.PI / 2; const ring = index < 6 ? 135 : 195; return { ...node, x: 310 + Math.cos(angle) * ring, y: 250 + Math.sin(angle) * ring } }), [nodes])
  const positions = new Map(positioned.map((node) => [node.id, node]))
  return <div className="network-canvas"><svg viewBox="0 0 620 500" role="img" aria-label="Observed interaction graph">{data.edges.slice(0, 70).map((edge, index) => { const source = positions.get(edge.source); const target = positions.get(edge.target); if (!source || !target) return null; return <line key={`${edge.source}-${edge.target}-${index}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className="network-edge" strokeWidth={Math.min(3, .5 + edge.weight / 2)} /> })}{positioned.map((node) => { const radius = 8 + Math.min(16, node.structural_influence_score * 100); return <g key={node.id} className="network-node"><circle cx={node.x} cy={node.y} r={radius} /><text x={node.x} y={node.y + radius + 13} textAnchor="middle">{node.label.slice(0, 17)}</text><title>{`${node.label} — structural influence ${node.structural_influence_score.toFixed(3)}; bridge ${node.bridge_score.toFixed(3)}`}</title></g> })}</svg><div className="network-legend"><span><i className="legend-node" /> observed pseudonymous/public account</span><span><i className="legend-edge" /> interaction / analytical association</span></div></div>
}

function StateChip({ state }: { state: string }) {
  const normalized = state.toLowerCase().replaceAll(' ', '-')
  return <span className={`state-chip ${normalized}`}>{state}</span>
}

function EmptyState({ label }: { label: string }) {
  return <div className="empty-state"><Database size={20} /><span>{label}</span></div>
}

function recordToDistribution(record: Record<string, number>): DistributionItem[] {
  const total = Object.values(record).reduce((sum, value) => sum + value, 0)
  return Object.entries(record).sort((a, b) => b[1] - a[1]).map(([label, count]) => ({ label, count, percentage: total ? (count / total) * 100 : 0 }))
}

function humanize(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function timeLabel(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString([], { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export default App
