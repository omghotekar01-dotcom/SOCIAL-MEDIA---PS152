import { Activity, CircleStop, LoaderCircle, Play, Radio, ShieldCheck, TimerReset, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { API_BASE } from './api';

type CollectorStatus = {
  running: boolean;
  cycles: number;
  last_run_at?: string | null;
  last_result?: {
    inserted?: number;
    received?: number;
    platforms?: Record<string, { state?: string; connector?: string; received?: number; inserted?: number; duplicates?: number; detail?: string }>;
  };
  note?: string;
  config?: Record<string, unknown> | null;
};

type Toggles = {
  telegram_public: boolean;
  bluesky: boolean;
  reddit: boolean;
  mastodon: boolean;
  youtube_free: boolean;
  x_official: boolean;
  youtube_official: boolean;
  instagram_authorized: boolean;
  facebook_authorized: boolean;
};

async function jsonRequest(path: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  const raw = await response.text();
  let payload: any = null;
  try { payload = raw ? JSON.parse(raw) : null; } catch { payload = raw; }
  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(typeof detail === 'string' ? detail : detail?.message || raw || `HTTP ${response.status}`);
  }
  return payload;
}

export default function LiveWatchPanel() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('RiverLink');
  const [interval, setIntervalValue] = useState(60);
  const [status, setStatus] = useState<CollectorStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [toggles, setToggles] = useState<Toggles>({
    telegram_public: true,
    bluesky: true,
    reddit: true,
    mastodon: true,
    youtube_free: false,
    x_official: false,
    youtube_official: false,
    instagram_authorized: false,
    facebook_authorized: false,
  });
  const previousCycles = useRef(0);

  const refresh = useCallback(async () => {
    try {
      const next = await jsonRequest('/api/collector/status');
      setStatus(next);
      if (Number(next?.cycles || 0) > previousCycles.current) {
        previousCycles.current = Number(next.cycles || 0);
        window.dispatchEvent(new Event('nexus:workspace-updated'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to read collector status.');
    }
  }, []);

  useEffect(() => {
    if (open) void refresh();
  }, [open, refresh]);

  useEffect(() => {
    if (!open && !status?.running) return;
    const timer = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(timer);
  }, [open, status?.running, refresh]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const setToggle = (key: keyof Toggles) => setToggles((current) => ({ ...current, [key]: !current[key] }));

  const start = async () => {
    const clean = query.trim();
    if (!clean) return;
    setBusy(true); setError('');
    try {
      const next = await jsonRequest('/api/collector/start', {
        method: 'POST',
        body: JSON.stringify({
          query: clean,
          interval_seconds: Math.max(60, Math.min(3600, interval)),
          enable_telegram: false,
          enable_telegram_public: toggles.telegram_public,
          enable_bluesky: toggles.bluesky,
          enable_reddit: toggles.reddit,
          enable_mastodon: toggles.mastodon,
          enable_youtube_free: toggles.youtube_free,
          enable_x: toggles.x_official,
          enable_youtube: toggles.youtube_official,
          enable_instagram_authorized: toggles.instagram_authorized,
          enable_facebook_authorized: toggles.facebook_authorized,
        }),
      });
      setStatus(next);
      previousCycles.current = Number(next?.cycles || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start continuous collector.');
    } finally { setBusy(false); }
  };

  const stop = async () => {
    setBusy(true); setError('');
    try {
      const next = await jsonRequest('/api/collector/stop', { method: 'POST', body: '{}' });
      setStatus(next);
      window.dispatchEvent(new Event('nexus:workspace-updated'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not stop collector.');
    } finally { setBusy(false); }
  };

  const platforms = Object.entries(status?.last_result?.platforms || {});

  return (
    <>
      <button className={`live-watch-launcher ${status?.running ? 'running' : ''}`} type="button" onClick={() => setOpen(true)} title="Continuous multi-source collection">
        <span className="utility-icon">{status?.running ? <Radio size={17} /> : <TimerReset size={17} />}</span>
        <span><b>{status?.running ? 'Live Watch ON' : 'Live Watch'}</b><small>{status?.running ? `${status.cycles} cycles · ${query}` : 'Continuous public collection'}</small></span>
      </button>

      {open && <button className="utility-backdrop live-watch-backdrop" aria-label="Close live watch" onClick={() => setOpen(false)} />}
      <aside className={`live-watch-drawer ${open ? 'open' : ''}`} role="dialog" aria-modal={open ? 'true' : undefined} aria-hidden={!open}>
        <div className="live-watch-head">
          <div><span>CONTINUOUS COLLECTION</span><h2>Live Watch</h2><p>Run low-cost/public sources repeatedly while premium/authorized providers stay explicit opt-ins.</p></div>
          <button type="button" onClick={() => setOpen(false)} title="Close"><X size={17} /></button>
        </div>

        <div className={`live-watch-state ${status?.running ? 'on' : ''}`}>
          <div><Activity size={17} /><span>{status?.running ? 'RUNNING' : 'STOPPED'}</span></div>
          <strong>{status?.cycles || 0} cycles</strong>
          <small>{status?.last_run_at ? `Last cycle ${new Date(status.last_run_at).toLocaleString()}` : 'No cycle has completed yet'}</small>
        </div>

        {error && <div className="live-watch-error">{error}</div>}

        <div className="live-watch-form">
          <label><span>Monitored topic / query</span><input value={query} disabled={status?.running || busy} onChange={(event) => setQuery(event.target.value)} placeholder="topic, phrase or #hashtag" /></label>
          <label><span>Cycle interval (seconds)</span><input type="number" min={60} max={3600} step={30} disabled={status?.running || busy} value={interval} onChange={(event) => setIntervalValue(Number(event.target.value || 60))} /><small>Minimum 60 seconds. X/YouTube official calls remain off unless you enable them.</small></label>
        </div>

        <section className="live-watch-section">
          <div><span>DEFAULT PUBLIC / LOW-COST SOURCES</span><strong>Safe continuous layer</strong></div>
          <div className="live-watch-toggle-grid">
            {([
              ['telegram_public', 'Telegram monitored channels'],
              ['bluesky', 'Bluesky + replies'],
              ['reddit', 'Reddit + comments'],
              ['mastodon', 'Mastodon + replies'],
              ['youtube_free', 'YouTube zero-key metadata'],
            ] as Array<[keyof Toggles, string]>).map(([key, label]) => (
              <button type="button" key={key} className={toggles[key] ? 'active' : ''} disabled={status?.running || busy} onClick={() => setToggle(key)}><i />{label}</button>
            ))}
          </div>
        </section>

        <section className="live-watch-section live-watch-premium">
          <div><span>AUTHORIZED / QUOTA / PAID PATHS</span><strong>Off by default</strong></div>
          <div className="live-watch-toggle-grid">
            {([
              ['x_official', 'X official recent search'],
              ['youtube_official', 'YouTube Data API'],
              ['instagram_authorized', 'Instagram authorized'],
              ['facebook_authorized', 'Facebook Page authorized'],
            ] as Array<[keyof Toggles, string]>).map(([key, label]) => (
              <button type="button" key={key} className={toggles[key] ? 'active warn' : ''} disabled={status?.running || busy} onClick={() => setToggle(key)}><i />{label}</button>
            ))}
          </div>
        </section>

        <div className="live-watch-actions">
          {!status?.running ? <button className="live-watch-start" disabled={busy || !query.trim()} onClick={() => void start()}>{busy ? <LoaderCircle className="spin-icon" size={15} /> : <Play size={15} />} Start continuous collection</button> : <button className="live-watch-stop" disabled={busy} onClick={() => void stop()}>{busy ? <LoaderCircle className="spin-icon" size={15} /> : <CircleStop size={15} />} Stop collector</button>}
          <button className="live-watch-refresh" disabled={busy} onClick={() => void refresh()}><TimerReset size={14} /> Refresh status</button>
        </div>

        <section className="live-watch-section">
          <div><span>LAST CYCLE</span><strong>Per-source truth</strong></div>
          <div className="live-watch-results">
            {platforms.map(([platform, item]) => (
              <div key={platform} className={`live-watch-result state-${String(item.state || 'unknown').toLowerCase()}`}>
                <div><strong>{platform.replaceAll('_', ' ')}</strong><span>{item.state || 'UNKNOWN'}</span></div>
                <small>{item.connector || 'connector'} · {item.inserted || 0} new / {item.received || 0} received{item.duplicates ? ` · ${item.duplicates} duplicates` : ''}</small>
                {item.detail && <p>{item.detail}</p>}
              </div>
            ))}
            {!platforms.length && <div className="live-watch-empty">No collector cycle has reported source results yet.</div>}
          </div>
        </section>

        <div className="live-watch-trust"><ShieldCheck size={14} /><span>{status?.note || 'A failed provider is isolated to that source. NEXUS never converts blocked provider access into fake LIVE evidence.'}</span></div>
      </aside>
    </>
  );
}
