import { useMemo, useState } from 'react';
import { Download, ExternalLink, Filter, Search, ShieldCheck } from 'lucide-react';
import type { SocialEvent } from './api';

type Props = {
  events: SocialEvent[];
  onOpenEvent: (id: string) => void;
};

type SortOrder = 'newest' | 'oldest';

type ModeFilter = 'all' | 'LIVE' | 'REPLAY' | 'IMPORT';

function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

function quoteCsv(value: unknown) {
  const raw = String(value ?? '');
  return `"${raw.replaceAll('"', '""')}"`;
}

function downloadCsv(events: SocialEvent[]) {
  const header = ['id', 'platform', 'source_mode', 'created_at', 'author', 'text', 'sentiment', 'stance', 'narrative', 'connector', 'source_url'];
  const rows = events.map((event) => [
    event.id,
    event.platform,
    event.source_mode,
    event.created_at,
    event.author_display || event.author_pseudo_id || '',
    event.text,
    event.sentiment_label || '',
    event.stance_label || '',
    event.narrative_cluster_id || '',
    String(event.public_profile?.connector || ''),
    event.url || '',
  ]);
  const csv = [header, ...rows].map((row) => row.map(quoteCsv).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `nexus-evidence-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function PlatformPill({ platform }: { platform: string }) {
  return <span className={`platform platform-${platform}`}>{platform.toUpperCase()}</span>;
}

export default function EvidenceLedger({ events, onOpenEvent }: Props) {
  const [search, setSearch] = useState('');
  const [platform, setPlatform] = useState('all');
  const [mode, setMode] = useState<ModeFilter>('all');
  const [sort, setSort] = useState<SortOrder>('newest');

  const platforms = useMemo(() => [...new Set(events.map((event) => event.platform))].sort(), [events]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const rows = events.filter((event) => {
      if (platform !== 'all' && event.platform !== platform) return false;
      if (mode !== 'all' && event.source_mode !== mode) return false;
      if (!q) return true;
      const haystack = [
        event.text,
        event.author_display,
        event.author_pseudo_id,
        event.platform,
        event.sentiment_label,
        event.stance_label,
        event.narrative_cluster_id,
        event.source_event_id,
        event.id,
        event.public_profile?.connector,
        ...(event.hashtags || []),
        ...(event.topic_terms || []),
      ].filter(Boolean).join(' ').toLowerCase();
      return haystack.includes(q);
    });
    return rows.sort((a, b) => {
      const delta = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      return sort === 'oldest' ? delta : -delta;
    });
  }, [events, search, platform, mode, sort]);

  const liveCount = events.filter((event) => event.source_mode === 'LIVE').length;
  const originalCount = events.filter((event) => event.url && !event.url.includes('example.invalid')).length;

  if (!events.length) {
    return (
      <section className="analysis-empty panel panel-large">
        <div className="analysis-empty-icon"><ShieldCheck size={27} /></div>
        <h2>No evidence records yet</h2>
        <p>Collect a live/public source, import an export, or load Demo. Evidence appears here only after it exists in the active workspace.</p>
      </section>
    );
  }

  return (
    <div className="evidence-pro">
      <div className="analysis-summary-grid evidence-summary-grid">
        <div className="analysis-summary-card"><span>Total evidence</span><strong>{events.length}</strong><small>current workspace only</small></div>
        <div className="analysis-summary-card"><span>LIVE records</span><strong>{liveCount}</strong><small>{events.length ? `${Math.round(liveCount / events.length * 100)}% of evidence` : '—'}</small></div>
        <div className="analysis-summary-card"><span>Platforms</span><strong>{platforms.length}</strong><small>{platforms.join(', ') || 'none'}</small></div>
        <div className="analysis-summary-card"><span>Original URLs</span><strong>{originalCount}</strong><small>source links retained</small></div>
      </div>

      <section className="panel panel-large evidence-ledger-card">
        <div className="analysis-section-head evidence-head-pro">
          <div><span className="eyebrow">Source traceability</span><h2>Evidence ledger</h2><p>Search, filter, sort, export, or open any exact evidence record without a fixed-width layout.</p></div>
          <button className="evidence-export-btn" onClick={() => downloadCsv(filtered)} disabled={!filtered.length}><Download size={15} /> Export visible CSV</button>
        </div>

        <div className="evidence-toolbar">
          <label className="evidence-search"><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search text, author, hashtag, ID, narrative…" /></label>
          <label className="evidence-select"><span><Filter size={13} /> Platform</span><select value={platform} onChange={(event) => setPlatform(event.target.value)}><option value="all">All platforms</option>{platforms.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label className="evidence-select"><span>Mode</span><select value={mode} onChange={(event) => setMode(event.target.value as ModeFilter)}><option value="all">All modes</option><option value="LIVE">LIVE</option><option value="REPLAY">REPLAY</option><option value="IMPORT">IMPORT</option></select></label>
          <label className="evidence-select"><span>Sort</span><select value={sort} onChange={(event) => setSort(event.target.value as SortOrder)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
          <span className="analysis-count-pill">{filtered.length} visible</span>
        </div>

        <div className="evidence-table-shell">
          <table className="evidence-pro-table">
            <thead><tr><th>Source</th><th>Observed time</th><th>Author</th><th>Evidence</th><th>Analysis</th><th>Provenance</th><th /></tr></thead>
            <tbody>
              {filtered.slice(0, 500).map((event) => {
                const connector = String(event.public_profile?.connector || 'unknown');
                const hasOriginal = Boolean(event.url && !event.url.includes('example.invalid'));
                return (
                  <tr key={event.id} onDoubleClick={() => onOpenEvent(event.id)}>
                    <td data-label="Source"><div className="evidence-source-cell"><PlatformPill platform={event.platform} /><span className={`evidence-mode evidence-mode-${event.source_mode.toLowerCase()}`}>{event.source_mode}</span><small>{event.event_type.replaceAll('_', ' ')}</small></div></td>
                    <td data-label="Observed time"><time>{formatTime(event.created_at)}</time><small>{event.ingested_at ? `Ingested ${formatTime(event.ingested_at)}` : ''}</small></td>
                    <td data-label="Author"><strong className="evidence-author">{event.author_display || event.author_pseudo_id || 'Unknown'}</strong><small className="mono-value">{event.author_pseudo_id || '—'}</small></td>
                    <td data-label="Evidence"><p className="evidence-pro-text">{event.text}</p>{event.hashtags?.length > 0 && <div className="evidence-tag-line">{event.hashtags.slice(0, 5).map((tag) => <span key={tag}>#{tag}</span>)}</div>}</td>
                    <td data-label="Analysis"><div className="evidence-analysis-cell"><span>{event.sentiment_label || 'unknown'}</span><span>{event.stance_label || 'unclear'}</span>{event.narrative_cluster_id && <small>{event.narrative_cluster_id}</small>}</div></td>
                    <td data-label="Provenance"><div className="evidence-provenance-cell"><strong>{connector}</strong><small className="mono-value">{event.source_event_id}</small><small className="mono-value">{event.id}</small></div></td>
                    <td className="evidence-actions-cell"><button onClick={() => onOpenEvent(event.id)}>Inspect</button>{hasOriginal && <a href={event.url!} target="_blank" rel="noreferrer" title="Open original source"><ExternalLink size={14} /></a>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!filtered.length && <div className="evidence-no-results"><Search size={18} /><strong>No evidence matches these filters.</strong><span>Clear search or change source/mode filters.</span></div>}
        </div>

        <div className="analysis-trust-note"><ShieldCheck size={16} /><span>LIVE, REPLAY and IMPORT are never merged into one undisclosed source mode. Original source IDs, internal evidence IDs, timestamps and connector provenance remain inspectable.</span></div>
      </section>
    </div>
  );
}
