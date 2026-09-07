import { useEffect, useState } from 'react';
import { BadgeCheck, Bot, DatabaseZap, LoaderCircle, Radio, ShieldCheck, Wifi, X as CloseIcon } from 'lucide-react';
import { API_BASE } from './api';

type ActionName =
  | 'telegram' | 'telegramBot'
  | 'youtube' | 'youtubeOfficial'
  | 'bluesky' | 'reddit' | 'mastodon'
  | 'instagram' | 'instagramTag' | 'instagramMeta' | 'facebookMeta'
  | 'x' | 'xOfficial' | 'mix' | 'allAvailable' | 'verify';

const X_POST_RE = /https?:\/\/(?:www\.)?(?:x\.com|twitter\.com)\/[A-Za-z0-9_]+\/status\/\d+/i;

async function request(path: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE}${path}`, init);
  const raw = await response.text();
  let parsed: any = null;
  try { parsed = raw ? JSON.parse(raw) : null; } catch { parsed = raw; }
  if (!response.ok) {
    const detail = parsed?.detail;
    const message = typeof detail === 'string' ? detail : detail?.message || parsed?.message || raw || `HTTP ${response.status}`;
    throw new Error(message);
  }
  return parsed;
}

async function post(path: string, body: unknown) {
  return request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

function refreshWorkspace() {
  window.dispatchEvent(new Event('nexus:workspace-updated'));
}

export default function FreeConnectorPanel() {
  const [query, setQuery] = useState('RiverLink');
  const [target, setTarget] = useState('');
  const [busy, setBusy] = useState<ActionName | null>(null);
  const [message, setMessage] = useState('');
  const [messageGood, setMessageGood] = useState(false);
  const [open, setOpen] = useState(false);

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

  const run = async (name: ActionName, fn: () => Promise<any>, refresh = true) => {
    setBusy(name); setMessage(''); setMessageGood(false);
    try {
      const result = await fn();
      setMessageGood(true);
      setMessage(`${name.toUpperCase()}: ${result?.inserted ?? 0} new / ${result?.received ?? 0} received${refresh ? ' · workspace updated' : ''}`);
      if (refresh) refreshWorkspace();
    } catch (error) {
      setMessageGood(false);
      setMessage(error instanceof Error ? error.message : 'Connector failed.');
    } finally { setBusy(null); }
  };

  const workspaceBody = (reset: boolean) => {
    const rawTarget = target.trim();
    const targetIsX = X_POST_RE.test(rawTarget);
    const cleanTarget = rawTarget.replace(/^@/, '');
    return {
      query: query.trim(), reset, limit_per_source: 15,
      enable_youtube: true, enable_bluesky: true, enable_reddit: true, enable_mastodon: true,
      telegram_channel: !targetIsX && cleanTarget ? cleanTarget : null,
      instagram_profile: !targetIsX && cleanTarget && cleanTarget.length <= 30 ? cleanTarget : null,
    };
  };

  const runMix = async () => {
    if (!query.trim()) return;
    setBusy('mix'); setMessage('Creating a fresh multi-source workspace…'); setMessageGood(false);
    try {
      const rawTarget = target.trim();
      const targetIsX = X_POST_RE.test(rawTarget);
      const result = await post('/api/search/workspace', workspaceBody(true));
      let totalInserted = Number(result?.inserted || 0);
      const sourceEntries = Object.entries(result?.sources || {}) as Array<[string, any]>;
      const ok = sourceEntries.filter(([, status]) => status?.state === 'OK').map(([name]) => name);
      const unavailable = sourceEntries.filter(([, status]) => status?.state !== 'OK').map(([name]) => name);
      if (targetIsX) {
        try {
          const xResult = await post('/api/connectors/x/public', { query: query.trim(), target: rawTarget, limit: 25 });
          totalInserted += Number(xResult?.inserted || 0);
          if (!ok.includes('x')) ok.push('x');
        } catch { unavailable.push('x'); }
      }
      setMessageGood(ok.length > 0);
      setMessage(`FRESH MIX: ${totalInserted} posts · OK ${ok.join(', ') || 'none'}${unavailable.length ? ` · unavailable ${[...new Set(unavailable)].join(', ')}` : ''} · previous topic cleared`);
      refreshWorkspace();
    } catch (error) {
      setMessageGood(false);
      setMessage(error instanceof Error ? error.message : 'Fresh workspace search failed.');
    } finally { setBusy(null); }
  };

  const runAllAvailable = async () => {
    if (!query.trim()) return;
    setBusy('allAvailable'); setMessage('Trying every available connector path…'); setMessageGood(false);
    const ok: string[] = [];
    const setup: string[] = [];
    let inserted = 0;
    try {
      try {
        const base = await post('/api/search/workspace', workspaceBody(false));
        inserted += Number(base?.inserted || 0);
        for (const [name, status] of Object.entries(base?.sources || {}) as Array<[string, any]>) {
          (status?.state === 'OK' ? ok : setup).push(name);
        }
      } catch { setup.push('free-mix'); }

      const rawTarget = target.trim();
      if (X_POST_RE.test(rawTarget)) {
        try { const result = await post('/api/connectors/x/public', { query: query.trim(), target: rawTarget, limit: 25 }); inserted += Number(result?.inserted || 0); ok.push('x-oembed'); } catch { setup.push('x-oembed'); }
      }

      for (const source of ['instagram', 'facebook'] as const) {
        try { const result = await post('/api/connectors/meta/sync', { source, limit: 25 }); inserted += Number(result?.inserted || 0); ok.push(`${source}-meta`); } catch { setup.push(`${source}-meta`); }
      }

      setMessageGood(ok.length > 0);
      setMessage(`ALL AVAILABLE: ${inserted} new · working ${[...new Set(ok)].join(', ') || 'none'}${setup.length ? ` · needs setup/restricted ${[...new Set(setup)].join(', ')}` : ''}`);
      refreshWorkspace();
    } finally { setBusy(null); }
  };

  const verifyEvidence = async () => {
    setBusy('verify'); setMessage('Checking evidence certificates…'); setMessageGood(false);
    try {
      const result = await request('/api/certificates');
      const certificates: any[] = result?.certificates || [];
      const certified = certificates.filter((item) => item.decision === 'CERTIFIED').length;
      const abstain = certificates.filter((item) => item.decision === 'ABSTAIN').length;
      setMessageGood(certificates.length > 0);
      setMessage(`EVIDENCE VERIFY: ${certified} certified · ${abstain} abstain · ${certificates.length} narrative certificate(s)`);
    } catch (error) {
      setMessageGood(false);
      setMessage(error instanceof Error ? error.message : 'Evidence verification failed.');
    } finally { setBusy(null); }
  };

  const cleanHashtag = query.trim().replace(/^#/, '');
  const targetLooksX = X_POST_RE.test(target.trim());
  const targetUsername = target.trim().replace(/^@/, '');
  const busyLabel = busy ? busy === 'mix' ? 'Building fresh workspace…' : busy === 'allAvailable' ? 'Trying available sources…' : `Running ${busy}…` : '';

  return (
    <>
      <button className="free-source-launcher" type="button" onClick={() => setOpen(true)} title="Open social source controls">
        <span className="utility-icon"><Wifi size={17} /></span>
        <span><b>Social Sources</b><small>Live + authorized paths</small></span>
      </button>

      {open && <button className="utility-backdrop free-source-backdrop" aria-label="Close source lab" onClick={() => setOpen(false)} />}

      <aside className={`free-source-drawer ${open ? 'open' : ''}`} aria-hidden={!open} aria-label="Social Source Lab" role="dialog" aria-modal={open ? 'true' : undefined}>
        <div className="utility-drawer-head free-source-head">
          <div><div className="drawer-kicker">COLLECTION LAB</div><h2>Social Source Lab</h2><p>Every platform in NEXUS has its real available path here. Provider-restricted paths report setup requirements instead of faking success.</p></div>
          <button className="utility-square-btn" type="button" onClick={() => setOpen(false)} title="Close"><CloseIcon size={17} /></button>
        </div>

        <div className="free-source-form">
          <label><span>Search topic</span><input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') void runMix(); }} placeholder="topic / #hashtag / search query" /></label>
          <label><span>Optional target</span><input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Telegram/Instagram username or public X Post URL" /><small>{targetLooksX ? 'Public X Post URL detected — official oEmbed can ingest it without an X bearer token.' : 'Blank target uses configured Telegram channels plus query-based public sources.'}</small></label>
          <div className="source-primary-actions"><button className="free-primary" disabled={!!busy || !query.trim()} onClick={() => void runMix()}>{busy === 'mix' ? <LoaderCircle className="spin-icon" size={14} /> : <Wifi size={14} />} Fresh Free Mix</button><button className="free-primary free-primary-secondary" disabled={!!busy || !query.trim()} onClick={() => void runAllAvailable()}>{busy === 'allAvailable' ? <LoaderCircle className="spin-icon" size={14} /> : <DatabaseZap size={14} />} Enrich All Available</button></div>
        </div>

        {busy && <div className="free-source-busy"><LoaderCircle className="spin-icon" size={14} /><span>{busyLabel}</span></div>}

        <div className="source-action-section"><div className="source-action-title">Telegram</div><div className="free-source-actions"><button disabled={!!busy || (!targetUsername && !query.trim()) || targetLooksX} onClick={() => run('telegram', () => post('/api/connectors/telegram/public', { channel: `${targetUsername || 'NexusSIHDemo'}||${query.trim()}`, limit: 25 }))}>+ Public channel</button><button disabled={!!busy} onClick={() => run('telegramBot', () => post('/api/connectors/telegram/poll', { max_updates: 50 }))}><Bot size={13} /> Bot API</button></div></div>
        <div className="source-action-section"><div className="source-action-title">X / Twitter</div><div className="free-source-actions"><button disabled={!!busy || (!query.trim() && !target.trim())} onClick={() => run('x', () => post('/api/connectors/x/public', { query: query.trim(), target: target.trim(), limit: 25 }))}>+ URL / Bridge</button><button disabled={!!busy || !query.trim()} onClick={() => run('xOfficial', () => post('/api/connectors/x/search', { query: query.trim(), max_results: 20 }))}>+ Official search</button></div></div>
        <div className="source-action-section"><div className="source-action-title">YouTube</div><div className="free-source-actions"><button disabled={!!busy || !query.trim()} onClick={() => run('youtube', () => post('/api/connectors/youtube/free', { query: query.trim(), limit: 10 }))}>+ Zero-key</button><button disabled={!!busy || !query.trim()} onClick={() => run('youtubeOfficial', () => post('/api/connectors/youtube/search', { query: query.trim(), max_videos: 3, max_comments_per_video: 20 }))}>+ Data API</button></div></div>
        <div className="source-action-section"><div className="source-action-title">Open/public search</div><div className="free-source-actions"><button disabled={!!busy || !query.trim()} onClick={() => run('bluesky', () => post('/api/connectors/bluesky/search', { query: query.trim(), limit: 25 }))}>+ Bluesky</button><button disabled={!!busy || !query.trim()} onClick={() => run('reddit', () => post('/api/connectors/reddit/search', { query: query.trim(), limit: 25 }))}>+ Reddit</button><button disabled={!!busy || !query.trim()} onClick={() => run('mastodon', () => post('/api/connectors/mastodon/search', { query: query.trim(), limit: 25, base_url: null }))}>+ Mastodon</button></div></div>
        <div className="source-action-section"><div className="source-action-title">Instagram</div><div className="free-source-actions"><button disabled={!!busy || !cleanHashtag || cleanHashtag.includes(' ')} onClick={() => run('instagramTag', () => post('/api/connectors/instagram/hashtag', { hashtag: cleanHashtag, limit: 20 }))}>+ Hashtag API</button><button disabled={!!busy || !targetUsername || targetLooksX || targetUsername.length > 30} onClick={() => run('instagram', () => post('/api/connectors/instagram/public', { profile: targetUsername, limit: 12 }))}>+ Public profile</button><button disabled={!!busy} onClick={() => run('instagramMeta', () => post('/api/connectors/meta/sync', { source: 'instagram', limit: 25 }))}>+ Meta authorized</button></div></div>
        <div className="source-action-section"><div className="source-action-title">Facebook</div><div className="free-source-actions"><button disabled={!!busy} onClick={() => run('facebookMeta', () => post('/api/connectors/meta/sync', { source: 'facebook', limit: 25 }))}>+ Authorized Page</button></div></div>
        <div className="source-action-section"><div className="source-action-title">Evidence</div><div className="free-source-actions"><button disabled={!!busy} onClick={() => void verifyEvidence()}><BadgeCheck size={13} /> Verify certificates</button></div></div>

        <div className="drawer-trust-note"><ShieldCheck size={15} /><span>LIVE, IMPORT and REPLAY remain separate. X keyword search and Meta account/Page access require provider authorization; NEXUS never labels a blocked fallback as official live access.</span></div>
        {message && <div className={`free-source-message ${messageGood ? 'good' : 'bad'}`}><Radio size={14} />{message}</div>}
      </aside>
    </>
  );
}
