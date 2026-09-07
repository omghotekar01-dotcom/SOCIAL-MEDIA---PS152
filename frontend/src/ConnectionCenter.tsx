import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, CircleAlert, PlugZap, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { api, type ConnectorStatus } from './api';

type SourceMeta = {
  platform: string;
  label: string;
  official: string;
  freePath: string;
  env: string[];
  input: string;
  demoPriority: 'HIGH' | 'MEDIUM' | 'LOW';
  note: string;
};

const SOURCES: SourceMeta[] = [
  {
    platform: 'telegram', label: 'Telegram', official: 'Bot API for authorized channel/chat updates',
    freePath: 'Monitored public-channel preview + local query filtering',
    env: ['TELEGRAM_PUBLIC_CHANNELS', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_CHAT_IDS'],
    input: 'Fresh Search uses configured channels automatically; manual input accepts a public channel username',
    demoPriority: 'HIGH',
    note: 'Primary SIH source. Fresh Search automatically includes query-matching posts from configured public channels. Bot API remains an optional controlled live-demo path.',
  },
  {
    platform: 'x', label: 'X / Twitter', official: 'X API v2 recent search (pay-per-use)',
    freePath: 'Official public Post oEmbed by explicit URL; optional permitted RSS/Atom bridge',
    env: ['X_BEARER_TOKEN', 'X_PUBLIC_RSS_URL_TEMPLATE'], input: 'Free: public X Post URL(s). Paid: keyword/hashtag query.',
    demoPriority: 'HIGH',
    note: 'Known public Post URLs work through official oEmbed without claiming unrestricted free global X search.',
  },
  {
    platform: 'youtube', label: 'YouTube', official: 'YouTube Data API v3', freePath: 'yt-dlp public video metadata',
    env: ['YOUTUBE_API_KEY'], input: 'Search topic / keyword', demoPriority: 'HIGH',
    note: 'Zero-key mode is metadata-first. Add the API key for official search and richer comments.',
  },
  {
    platform: 'instagram', label: 'Instagram', official: 'Meta Graph API / approved hashtag access',
    freePath: 'Best-effort public-profile fallback or IMPORT', env: ['META_ACCESS_TOKEN', 'META_INSTAGRAM_ACCOUNT_ID'],
    input: 'Public username or one hashtag', demoPriority: 'MEDIUM',
    note: 'Authorized Meta access is the stable production path; fallback never bypasses login or private controls.',
  },
  {
    platform: 'facebook', label: 'Facebook', official: 'Meta Graph API for authorized Page', freePath: 'IMPORT / REPLAY',
    env: ['META_ACCESS_TOKEN', 'META_FACEBOOK_PAGE_ID'], input: 'Authorized Page', demoPriority: 'LOW',
    note: 'Optional source. The main demo remains independent of broad Facebook access.',
  },
  {
    platform: 'bluesky', label: 'Bluesky', official: 'Public AT Protocol', freePath: 'Public search (zero-key)',
    env: [], input: 'Search topic / keyword', demoPriority: 'HIGH',
    note: 'Useful zero-key cross-platform source when the public endpoint is reachable.',
  },
  {
    platform: 'reddit', label: 'Reddit', official: 'OAuth app access when needed', freePath: 'Low-volume public JSON where permitted',
    env: ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET'], input: 'Search topic / keyword', demoPriority: 'LOW',
    note: 'Bonus coverage because anonymous access can return 403/429 depending on network policy.',
  },
  {
    platform: 'mastodon', label: 'Mastodon', official: 'Instance API', freePath: 'Public instance search',
    env: ['MASTODON_BASE_URL'], input: 'Search topic / keyword', demoPriority: 'MEDIUM',
    note: 'Instance policy varies; use a compatible public instance when anonymous search is disabled.',
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

  const byPlatform = useMemo(() => new Map(statuses.map((item) => [item.platform, item])), [statuses]);
  const liveReady = SOURCES.filter((source) => {
    const state = byPlatform.get(source.platform)?.state;
    return state === 'READY' || state === 'LIVE';
  }).length;

  return (
    <>
      <button className="connection-launcher" type="button" onClick={() => setOpen(true)} title="Open source connections">
        <span className="utility-icon"><PlugZap size={17} /></span>
        <span><b>Connections</b><small>{liveReady}/{SOURCES.length} ready</small></span>
      </button>

      {open && <button className="utility-backdrop" aria-label="Close connection center" onClick={() => setOpen(false)} />}

      <aside className={`connection-drawer ${open ? 'open' : ''}`} aria-hidden={!open}>
        <div className="utility-drawer-head">
          <div>
            <div className="drawer-kicker">SOURCE CONTROL</div>
            <h2>Connection Center</h2>
            <p>Official access, free fallbacks and demo readiness in one place.</p>
          </div>
          <div className="drawer-head-actions">
            <button className="utility-square-btn" type="button" onClick={() => void refresh()} disabled={loading} title="Refresh connector status"><RefreshCw size={16} /></button>
            <button className="utility-square-btn" type="button" onClick={() => setOpen(false)} title="Close"><X size={17} /></button>
          </div>
        </div>

        <div className="drawer-trust-note"><ShieldCheck size={16} /><span>Secrets stay in your local <code>.env</code>. Status badges describe the richer/official path; each card separately shows the available free fallback.</span></div>
        {error && <div className="drawer-error">{error}</div>}

        <div className="connection-grid">
          {SOURCES.map((source) => {
            const status = byPlatform.get(source.platform);
            const state = status?.state || 'NOT_REPORTED';
            const ready = state === 'READY' || state === 'LIVE';
            return (
              <article className="connection-card" key={source.platform}>
                <div className="connection-card-head">
                  <span className={`connection-state-icon ${stateClass(state)}`}>{ready ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}</span>
                  <div><strong>{source.label}</strong><small>Priority {source.demoPriority}</small></div>
                  <span className={`connection-state ${stateClass(state)}`}>{state.replaceAll('_', ' ')}</span>
                </div>
                <div className="connection-facts">
                  <div><span>Official</span><b>{source.official}</b></div>
                  <div><span>Free / fallback</span><b>{source.freePath}</b></div>
                  <div><span>Input</span><b>{source.input}</b></div>
                  {source.env.length > 0 && <div><span>Local .env</span><code>{source.env.join(', ')}</code></div>}
                </div>
                <p>{source.note}</p>
                {status?.detail && <div className="connection-backend-note">Backend: {status.detail}</div>}
              </article>
            );
          })}
        </div>
      </aside>
    </>
  );
}
