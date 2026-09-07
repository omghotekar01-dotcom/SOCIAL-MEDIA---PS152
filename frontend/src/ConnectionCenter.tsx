import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ChevronDown, ChevronUp, CircleAlert, PlugZap, RefreshCw, ShieldCheck } from 'lucide-react';
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
    platform: 'telegram',
    label: 'Telegram',
    official: 'Bot API for authorized channel/chat updates',
    freePath: 'Monitored public-channel preview + local query filtering',
    env: ['TELEGRAM_PUBLIC_CHANNELS', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_CHAT_IDS'],
    input: 'Fresh Search uses configured channels automatically; manual input accepts public channel username',
    demoPriority: 'HIGH',
    note: 'Primary SIH source. Configure comma-separated public channel usernames once; every Fresh Search then includes query-matching Telegram posts at zero API cost. Bot API is the best controlled live-demo addition.',
  },
  {
    platform: 'x',
    label: 'X / Twitter',
    official: 'X API v2 recent search (pay-per-use)',
    freePath: 'Official public Post oEmbed by explicit URL; optional permitted RSS/Atom bridge',
    env: ['X_BEARER_TOKEN', 'X_PUBLIC_RSS_URL_TEMPLATE'],
    input: 'Free: public X Post URL(s). Paid: keyword/hashtag query.',
    demoPriority: 'HIGH',
    note: 'Primary SIH source. Free mode ingests known public Post URLs through X oEmbed and renders the official embed. Automatic keyword search needs X API credits; NEXUS does not falsely claim free global X search.',
  },
  {
    platform: 'youtube',
    label: 'YouTube',
    official: 'YouTube Data API v3',
    freePath: 'yt-dlp public video metadata',
    env: ['YOUTUBE_API_KEY'],
    input: 'Search topic / keyword',
    demoPriority: 'HIGH',
    note: 'Zero-key mode is metadata-first. Add the API key for official search and comments.',
  },
  {
    platform: 'instagram',
    label: 'Instagram',
    official: 'Meta Graph API / approved hashtag access',
    freePath: 'Best-effort public-profile fallback or IMPORT',
    env: ['META_ACCESS_TOKEN', 'META_INSTAGRAM_ACCOUNT_ID'],
    input: 'Public username or one hashtag',
    demoPriority: 'MEDIUM',
    note: 'Anonymous access is unstable. Authorized Meta access is the production path; public fallback never bypasses login/private controls.',
  },
  {
    platform: 'facebook',
    label: 'Facebook',
    official: 'Meta Graph API for authorized Page',
    freePath: 'IMPORT / REPLAY',
    env: ['META_ACCESS_TOKEN', 'META_FACEBOOK_PAGE_ID'],
    input: 'Authorized Page',
    demoPriority: 'LOW',
    note: 'Optional source. Keep the core demo independent of broad Facebook access.',
  },
  {
    platform: 'bluesky',
    label: 'Bluesky',
    official: 'Public AT Protocol',
    freePath: 'Public search (zero-key)',
    env: [],
    input: 'Search topic / keyword',
    demoPriority: 'HIGH',
    note: 'Excellent zero-key cross-platform live source when the public endpoint is reachable.',
  },
  {
    platform: 'reddit',
    label: 'Reddit',
    official: 'OAuth app access when needed',
    freePath: 'Low-volume public JSON where permitted',
    env: ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET'],
    input: 'Search topic / keyword',
    demoPriority: 'LOW',
    note: 'Treat as bonus coverage because public access may return 403/429 depending on network policy.',
  },
  {
    platform: 'mastodon',
    label: 'Mastodon',
    official: 'Instance API',
    freePath: 'Public instance search',
    env: ['MASTODON_BASE_URL'],
    input: 'Search topic / keyword',
    demoPriority: 'MEDIUM',
    note: 'Instance policy varies. Switch the configured instance if anonymous search is disabled.',
  },
];

const stateTone = (state: string) => {
  if (state === 'READY' || state === 'LIVE') return '#6ee7b7';
  if (state === 'CREDENTIALS_REQUIRED' || state === 'PERMISSION_REQUIRED' || state === 'NO_CREDITS') return '#fbbf24';
  if (state === 'ERROR') return '#fb7185';
  return '#93c5fd';
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
    <section style={{ background: '#07111f', borderBottom: '1px solid rgba(120,150,210,.2)', color: '#eaf1ff', fontFamily: 'Inter,system-ui,sans-serif' }}>
      <div style={{ minHeight: 46, display: 'flex', alignItems: 'center', gap: 10, padding: '7px 16px' }}>
        <PlugZap size={16} />
        <strong style={{ fontSize: 12, letterSpacing: '.08em' }}>CONNECTION CENTER</strong>
        <span style={{ fontSize: 11, opacity: .7 }}>{liveReady}/{SOURCES.length} official connector states ready/live · free fallbacks shown below</span>
        <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, opacity: .72 }}>
          <ShieldCheck size={13} /> secrets stay in local .env
        </span>
        <button onClick={() => void refresh()} disabled={loading} title="Refresh connector status" style={{ border: '1px solid #2b3a52', background: '#0d1727', color: '#dbeafe', borderRadius: 8, padding: '6px 8px', cursor: 'pointer' }}>
          <RefreshCw size={13} />
        </button>
        <button onClick={() => setOpen((value) => !value)} style={{ border: '1px solid #2b3a52', background: '#0d1727', color: '#dbeafe', borderRadius: 8, padding: '6px 9px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 5 }}>
          {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />} {open ? 'Hide' : 'Open'}
        </button>
      </div>

      {open && (
        <div style={{ padding: '6px 16px 16px' }}>
          <div style={{ padding: 11, borderRadius: 10, background: '#0b1728', border: '1px solid #26364e', fontSize: 11, lineHeight: 1.5, marginBottom: 10 }}>
            <strong>How to read this:</strong> the status badge reflects the backend's official/richer connector state. The <b>Free/fallback</b> line shows what NEXUS can still do without that credential. For X, a yellow credentials badge can coexist with free public-Post oEmbed because oEmbed fetches explicit Post URLs, not global keyword search. Never paste API tokens into this website or commit them to GitHub; put them only in local <code>.env</code>.
          </div>
          {error && <div style={{ color: '#fda4af', fontSize: 11, marginBottom: 10 }}>{error}</div>}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(285px,1fr))', gap: 10 }}>
            {SOURCES.map((source) => {
              const status = byPlatform.get(source.platform);
              const state = status?.state || 'NOT_REPORTED';
              const ready = state === 'READY' || state === 'LIVE';
              return (
                <article key={source.platform} style={{ border: '1px solid #24344c', background: '#0b1423', borderRadius: 12, padding: 13 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {ready ? <CheckCircle2 size={16} color="#6ee7b7" /> : <CircleAlert size={16} color={stateTone(state)} />}
                    <strong>{source.label}</strong>
                    <span style={{ marginLeft: 'auto', fontSize: 9, fontWeight: 800, color: stateTone(state), border: `1px solid ${stateTone(state)}55`, padding: '3px 6px', borderRadius: 999 }}>{state.replaceAll('_', ' ')}</span>
                  </div>
                  <div style={{ marginTop: 9, display: 'grid', gap: 5, fontSize: 10, color: '#a8b6cc' }}>
                    <div><b style={{ color: '#d8e4f6' }}>Official:</b> {source.official}</div>
                    <div><b style={{ color: '#d8e4f6' }}>Free/fallback:</b> {source.freePath}</div>
                    <div><b style={{ color: '#d8e4f6' }}>Input:</b> {source.input}</div>
                    <div><b style={{ color: '#d8e4f6' }}>Demo priority:</b> {source.demoPriority}</div>
                    {source.env.length > 0 && <div><b style={{ color: '#d8e4f6' }}>Local .env:</b> <code>{source.env.join(', ')}</code></div>}
                  </div>
                  <p style={{ margin: '9px 0 0', fontSize: 10, lineHeight: 1.45, color: '#9aabc3' }}>{source.note}</p>
                  {status?.detail && <p style={{ margin: '6px 0 0', fontSize: 9, lineHeight: 1.4, color: '#6f819d' }}>Backend: {status.detail}</p>}
                </article>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
