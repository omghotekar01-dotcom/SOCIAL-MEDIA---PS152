import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, CircleAlert, Filter, PlugZap, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { api, type ConnectorStatus } from './api';

type SourceMeta = {
  platform: string;
  label: string;
  official: string;
  freePath: string;
  env: string[];
  input: string;
  demoPriority: 'HIGH' | 'MEDIUM' | 'LOW';
  requirementTier: 'ESSENTIAL' | 'DESIRABLE' | 'APPRECIABLE' | 'EXTRA';
  note: string;
};
type ConnectionFilter = 'all' | 'priority' | 'ready' | 'setup';

const SOURCES: SourceMeta[] = [
  {
    platform: 'telegram', label: 'Telegram', official: 'Bot API for authorized channel/discussion updates',
    freePath: 'Monitored public-channel preview + local query filtering',
    env: ['TELEGRAM_PUBLIC_CHANNELS', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_CHAT_IDS'],
    input: 'Prototype Sources → Poll Bot comments now / Read public channel',
    demoPriority: 'HIGH', requirementTier: 'ESSENTIAL',
    note: 'Primary controlled live-demo source. Bot-visible linked discussion messages provide real comments/replies; public preview provides root channel evidence.',
  },
  {
    platform: 'x', label: 'X / Twitter', official: 'X API v2 recent search when authorized',
    freePath: 'Public Post oEmbed by explicit URL where available; disclosed IMPORT fallback',
    env: ['X_BEARER_TOKEN', 'X_PUBLIC_RSS_URL_TEMPLATE'], input: 'Known public Post URL or authorized keyword search',
    demoPriority: 'HIGH', requirementTier: 'ESSENTIAL',
    note: 'NEXUS does not claim unrestricted free X keyword/reply access when provider authorization is absent.',
  },
  {
    platform: 'instagram', label: 'Instagram', official: 'Meta Graph API / approved professional-account or hashtag access',
    freePath: 'Best-effort genuinely public profile path or IMPORT', env: ['META_ACCESS_TOKEN', 'META_INSTAGRAM_ACCOUNT_ID'],
    input: 'Authorized account / hashtag / public profile where permitted', demoPriority: 'MEDIUM', requirementTier: 'DESIRABLE',
    note: 'Authorized Meta access is the stable production path; fallback never bypasses login or private controls.',
  },
  {
    platform: 'facebook', label: 'Facebook', official: 'Meta Graph API for authorized Page', freePath: 'IMPORT / REPLAY',
    env: ['META_ACCESS_TOKEN', 'META_FACEBOOK_PAGE_ID'], input: 'Authorized Page', demoPriority: 'MEDIUM', requirementTier: 'DESIRABLE',
    note: 'Authorized Page data only; no unrestricted public-profile scraping claim.',
  },
  {
    platform: 'reddit', label: 'Reddit', official: 'OAuth app access when approved/configured', freePath: 'Public JSON where permitted',
    env: ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET'], input: 'Prototype Sources → topic → Append public mix',
    demoPriority: 'LOW', requirementTier: 'APPRECIABLE',
    note: 'Supplemental discussion coverage; anonymous/public endpoint policy can vary.',
  },
  {
    platform: 'youtube', label: 'YouTube', official: 'YouTube Data API v3 video + public comments/replies', freePath: 'yt-dlp public video metadata only',
    env: ['YOUTUBE_API_KEY'], input: 'Prototype Sources → exact public video URL → Load video + comments/replies',
    demoPriority: 'LOW', requirementTier: 'APPRECIABLE',
    note: 'Recommended live comment-volume proof. Exact URLs use fast-first official collection and continue provider-bounded comment/reply pagination in the background.',
  },
  {
    platform: 'bluesky', label: 'Bluesky', official: 'Public AT Protocol', freePath: 'Public search + public replies',
    env: [], input: 'Prototype Sources → topic → Append public mix', demoPriority: 'LOW', requirementTier: 'EXTRA',
    note: 'Useful zero-key additional public conversation source when the endpoint is reachable.',
  },
  {
    platform: 'mastodon', label: 'Mastodon', official: 'Instance API', freePath: 'Public instance search + status-context replies',
    env: ['MASTODON_BASE_URL'], input: 'Prototype Sources → topic → Append public mix', demoPriority: 'LOW', requirementTier: 'EXTRA',
    note: 'Instance policy varies; configured fallbacks are attempted where available.',
  },
];

const stateClass = (state: string) => {
  if (state === 'READY' || state === 'LIVE') return 'ready';
  if (state === 'ERROR') return 'error';
  if (state === 'CREDENTIALS_REQUIRED' || state === 'PERMISSION_REQUIRED' || state === 'NO_CREDITS') return 'warning';
  return 'info';
};

export default function ConnectionCenter() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statuses, setStatuses] = useState<ConnectorStatus[]>([]);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<ConnectionFilter>('all');

  const refresh = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.connectorStatus();
      setStatuses(result.connectors || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not read connector status.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  const byPlatform = useMemo(() => new Map(statuses.map((item) => [item.platform, item])), [statuses]);
  const isReady = (platform: string) => {
    const state = byPlatform.get(platform)?.state;
    return state === 'READY' || state === 'LIVE';
  };
  const liveReady = SOURCES.filter((source) => isReady(source.platform)).length;
  const setupCount = SOURCES.length - liveReady;
  const visibleSources = useMemo(() => SOURCES.filter((source) => {
    const ready = isReady(source.platform);
    if (filter === 'priority') return source.requirementTier === 'ESSENTIAL';
    if (filter === 'ready') return ready;
    if (filter === 'setup') return !ready;
    return true;
  }), [filter, byPlatform]);

  return (
    <>
      <button className="connection-launcher" type="button" onClick={() => setOpen(true)} title="Open source connections">
        <span className="utility-icon"><PlugZap size={17} /></span>
        <span><b>Connections</b><small>{liveReady}/{SOURCES.length} ready</small></span>
      </button>

      {open && <button className="utility-backdrop" aria-label="Close connection center" onClick={() => setOpen(false)} />}

      <aside className={`connection-drawer ${open ? 'open' : ''}`} aria-hidden={!open} aria-label="Connection Center" role="dialog" aria-modal={open ? 'true' : undefined}>
        <div className="utility-drawer-head">
          <div>
            <div className="drawer-kicker">SOURCE READINESS</div>
            <h2>Connection Center</h2>
            <p>Readiness/configuration only. Use Prototype Sources for actual live collection.</p>
          </div>
          <div className="drawer-head-actions">
            <button className="utility-square-btn" type="button" onClick={() => void refresh()} disabled={loading} title="Refresh connector status"><RefreshCw size={16} /></button>
            <button className="utility-square-btn" type="button" onClick={() => setOpen(false)} title="Close"><X size={17} /></button>
          </div>
        </div>

        <div className="drawer-trust-note"><ShieldCheck size={16} /><span>Secrets stay in local <code>.env</code>. A READY badge means the configured connector path is available to NEXUS; actual evidence counts are shown in Prototype Sources / PS26152 CORE.</span></div>
        {error && <div className="drawer-error">{error}</div>}

        <div className="connection-filter-bar" role="group" aria-label="Filter source connections">
          <span><Filter size={13} /> View</span>
          <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>All <b>{SOURCES.length}</b></button>
          <button className={filter === 'priority' ? 'active' : ''} onClick={() => setFilter('priority')} title="High priority requirement sources">Essential <b>{SOURCES.filter((source) => source.requirementTier === 'ESSENTIAL').length}</b></button>
          <button className={filter === 'ready' ? 'active' : ''} onClick={() => setFilter('ready')}>Ready <b>{liveReady}</b></button>
          <button className={filter === 'setup' ? 'active' : ''} onClick={() => setFilter('setup')}>Needs setup <b>{setupCount}</b></button>
        </div>

        <div className="connection-grid">
          {visibleSources.map((source) => {
            const status = byPlatform.get(source.platform);
            const state = status?.state || 'NOT_REPORTED';
            const ready = state === 'READY' || state === 'LIVE';
            return (
              <article className="connection-card" key={source.platform}>
                <div className="connection-card-head">
                  <span className={`connection-state-icon ${stateClass(state)}`}>{ready ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}</span>
                  <div><strong>{source.label}</strong><small>{source.requirementTier} · demo {source.demoPriority}</small></div>
                  <span className={`connection-state ${stateClass(state)}`}>{state.replaceAll('_', ' ')}</span>
                </div>
                <div className="connection-facts">
                  <div><span>Official / richer</span><b>{source.official}</b></div>
                  <div><span>Free / fallback</span><b>{source.freePath}</b></div>
                  <div><span>How to use</span><b>{source.input}</b></div>
                  {source.env.length > 0 && <div><span>Local .env</span><code>{source.env.join(', ')}</code></div>}
                </div>
                <p>{source.note}</p>
                {status?.detail && <div className="connection-backend-note">Backend: {status.detail}</div>}
              </article>
            );
          })}
          {!visibleSources.length && <div className="connection-empty">No sources match this readiness filter.</div>}
        </div>
      </aside>
    </>
  );
}
