import { useEffect, useState } from 'react';
import { BadgeCheck, Bot, ClipboardPaste, DatabaseZap, LoaderCircle, MessageSquareText, Radio, ShieldCheck, Wifi, X as CloseIcon } from 'lucide-react';
import { API_BASE } from './api';

type ActionName =
  | 'telegram' | 'telegramBot'
  | 'youtube' | 'youtubeOfficial'
  | 'bluesky' | 'reddit' | 'mastodon'
  | 'instagram' | 'instagramTag' | 'instagramMeta' | 'facebookMeta'
  | 'x' | 'xOfficial' | 'xManual' | 'mix' | 'allAvailable' | 'verify';

const X_POST_RE = /https?:\/\/(?:(?:www|mobile)\.)?(?:x\.com|twitter\.com)\/[A-Za-z0-9_]+\/status\/\d+/i;

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

function canonicalXUrl(raw: string) {
  try {
    const parsed = new URL(raw.trim());
    const host = parsed.hostname.replace(/^www\./, '').replace(/^mobile\./, '').replace(/^twitter\.com$/i, 'x.com');
    return `https://${host}${parsed.pathname.replace(/\/$/, '')}`;
  } catch {
    return raw.trim().split('?')[0];
  }
}

function statusIdFromUrl(raw: string) {
  return raw.match(/\/status\/(\d+)/i)?.[1] || `manual-${Date.now()}`;
}

function authorFromUrl(raw: string) {
  try {
    const parsed = new URL(raw.trim());
    return parsed.pathname.split('/').filter(Boolean)[0] || 'x-user';
  } catch {
    return 'x-user';
  }
}

function parseManualReplies(raw: string) {
  return raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const match = line.match(/^@?([A-Za-z0-9_]{1,30})\s*(?::|\||—|-)\s*(.+)$/);
      return match
        ? { author: match[1], text: match[2].trim(), index }
        : { author: `reply-${index + 1}`, text: line, index };
    });
}

export default function FreeConnectorPanel() {
  const [query, setQuery] = useState('RiverLink');
  const [target, setTarget] = useState('');
  const [busy, setBusy] = useState<ActionName | null>(null);
  const [message, setMessage] = useState('');
  const [messageGood, setMessageGood] = useState(false);
  const [open, setOpen] = useState(false);
  const [xManualAuthor, setXManualAuthor] = useState('');
  const [xManualText, setXManualText] = useState('');
  const [xManualReplies, setXManualReplies] = useState('');

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
    setBusy('allAvailable'); setMessage('Trying every free, public and configured authorized connector…'); setMessageGood(false);
    const ok: string[] = [];
    const setup: string[] = [];
    let inserted = 0;

    const trySource = async (label: string, fn: () => Promise<any>) => {
      try {
        const result = await fn();
        inserted += Number(result?.inserted || 0);
        ok.push(label);
      } catch {
        setup.push(label);
      }
    };

    try {
      try {
        const base = await post('/api/search/workspace', workspaceBody(false));
        inserted += Number(base?.inserted || 0);
        for (const [name, status] of Object.entries(base?.sources || {}) as Array<[string, any]>) {
          (status?.state === 'OK' ? ok : setup).push(name);
        }
      } catch { setup.push('free-mix'); }

      if (X_POST_RE.test(target.trim())) {
        await trySource('x-oembed', () => post('/api/connectors/x/public', { query: query.trim(), target: target.trim(), limit: 25 }));
      }

      await trySource('telegram-bot', () => post('/api/connectors/telegram/poll', { max_updates: 50 }));
      await trySource('youtube-official', () => post('/api/connectors/youtube/search', { query: query.trim(), max_videos: 3, max_comments_per_video: 20 }));
      await trySource('x-official', () => post('/api/connectors/x/search', { query: query.trim(), max_results: 20 }));
      await trySource('instagram-meta', () => post('/api/connectors/meta/sync', { source: 'instagram', limit: 25 }));
      await trySource('facebook-meta', () => post('/api/connectors/meta/sync', { source: 'facebook', limit: 25 }));

      setMessageGood(ok.length > 0);
      setMessage(`ALL AVAILABLE: ${inserted} new · working ${[...new Set(ok)].join(', ') || 'none'}${setup.length ? ` · needs setup/restricted ${[...new Set(setup)].join(', ')}` : ''}`);
      refreshWorkspace();
    } finally { setBusy(null); }
  };

  const runManualXImport = async () => {
    if (!X_POST_RE.test(target.trim()) || !xManualText.trim()) return;
    setBusy('xManual'); setMessage('Importing copied X post and replies as disclosed IMPORT evidence…'); setMessageGood(false);
    try {
      const canonical = canonicalXUrl(target);
      const statusId = statusIdFromUrl(canonical);
      const author = (xManualAuthor.trim() || authorFromUrl(canonical)).replace(/^@/, '');
      const now = new Date();
      const rootSourceId = `manual:${statusId}`;
      const parsedReplies = parseManualReplies(xManualReplies);
      const commonProfile = {
        username: author,
        original_x_url: canonical,
        collection_scope: 'analyst_manual_public_x',
        evidence_entry_method: 'manual_transcription',
        provider_access_note: 'X API/oEmbed did not expose this conversation; analyst pasted public evidence.',
        search_query: query.trim() || null,
      };
      const events = [
        {
          platform: 'x', source_event_id: rootSourceId, event_type: 'manual_public_post', author_platform_id: author,
          author_display: author, text: xManualText.trim(), created_at: now.toISOString(), url: canonical,
          conversation_id: statusId, mentions: [], hashtags: [], urls: [], engagement: {},
          public_profile: { ...commonProfile, timestamp_source: 'import_time_fallback', manual_reply_count: parsedReplies.length },
          source_mode: 'IMPORT', connector_run_id: `x-manual-${Date.now()}`,
        },
        ...parsedReplies.map((reply, index) => ({
          platform: 'x', source_event_id: `manual-reply:${statusId}:${index + 1}`, event_type: 'reply',
          author_platform_id: reply.author, author_display: reply.author, text: reply.text,
          created_at: new Date(now.getTime() + (index + 1) * 1000).toISOString(), parent_event_id: rootSourceId,
          conversation_id: statusId, mentions: [], hashtags: [], urls: [], engagement: {},
          public_profile: { ...commonProfile, manual_reply_index: index + 1, timestamp_source: 'import_time_fallback' },
          source_mode: 'IMPORT', connector_run_id: `x-manual-${Date.now()}`,
        })),
      ];
      const result = await post('/api/ingest/replay', { events });
      setMessageGood(true);
      setMessage(`X MANUAL IMPORT: ${result?.inserted ?? 0} new / ${result?.received ?? events.length} received · ${parsedReplies.length} copied repl${parsedReplies.length === 1 ? 'y' : 'ies'} linked for reaction analysis`);
      refreshWorkspace();
    } catch (error) {
      setMessageGood(false);
      setMessage(error instanceof Error ? error.message : 'Manual X conversation import failed.');
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
  const busyLabel = busy ? busy === 'mix' ? 'Building fresh workspace…' : busy === 'allAvailable' ? 'Trying every available source path…' : busy === 'xManual' ? 'Importing copied X conversation…' : `Running ${busy}…` : '';

  return (
    <>
      <button className="free-source-launcher" type="button" onClick={() => setOpen(true)} title="Open social source controls">
        <span className="utility-icon"><Wifi size={17} /></span>
        <span><b>Social Sources</b><small>Live + authorized paths</small></span>
      </button>

      {open && <button className="utility-backdrop free-source-backdrop" aria-label="Close source lab" onClick={() => setOpen(false)} />}

      <aside className={`free-source-drawer ${open ? 'open' : ''}`} aria-hidden={!open} aria-label="Social Source Lab" role="dialog" aria-modal={open ? 'true' : undefined}>
        <div className="utility-drawer-head free-source-head">
          <div><div className="drawer-kicker">COLLECTION LAB</div><h2>Social Source Lab</h2><p>Collect root posts plus comments/replies wherever the provider exposes them. Restricted providers fall back to disclosed IMPORT instead of fake LIVE data.</p></div>
          <button className="utility-square-btn" type="button" onClick={() => setOpen(false)} title="Close"><CloseIcon size={17} /></button>
        </div>

        <div className="free-source-form">
          <label><span>Search topic</span><input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') void runMix(); }} placeholder="topic / #hashtag / search query" /></label>
          <label><span>Optional target</span><input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Telegram/Instagram username or public X Post URL" /><small>{targetLooksX ? 'Public X Post URL detected — NEXUS first tries public oEmbed. If X refuses it, use Manual X Conversation Import below.' : 'Blank target uses configured Telegram channels plus query-based public sources.'}</small></label>
          <div className="source-primary-actions"><button className="free-primary" disabled={!!busy || !query.trim()} onClick={() => void runMix()}>{busy === 'mix' ? <LoaderCircle className="spin-icon" size={14} /> : <Wifi size={14} />} Fresh Free Mix</button><button className="free-primary free-primary-secondary" disabled={!!busy || !query.trim()} onClick={() => void runAllAvailable()}>{busy === 'allAvailable' ? <LoaderCircle className="spin-icon" size={14} /> : <DatabaseZap size={14} />} Enrich All Available</button></div>
        </div>

        {busy && <div className="free-source-busy"><LoaderCircle className="spin-icon" size={14} /><span>{busyLabel}</span></div>}

        <div className="source-action-section"><div className="source-action-title">Telegram</div><div className="free-source-actions"><button disabled={!!busy || (!targetUsername && !query.trim()) || targetLooksX} onClick={() => run('telegram', () => post('/api/connectors/telegram/public', { channel: `${targetUsername || 'NexusSIHDemo'}||${query.trim()}`, limit: 25 }))}>+ Public channel</button><button disabled={!!busy} onClick={() => run('telegramBot', () => post('/api/connectors/telegram/poll', { max_updates: 50 }))}><Bot size={13} /> Bot API</button></div></div>

        <div className="source-action-section">
          <div className="source-action-title">X / Twitter</div>
          <div className="free-source-actions"><button disabled={!!busy || (!query.trim() && !target.trim())} onClick={() => run('x', () => post('/api/connectors/x/public', { query: query.trim(), target: target.trim(), limit: 25 }))}>+ URL / Bridge</button><button disabled={!!busy || !query.trim()} onClick={() => run('xOfficial', () => post('/api/connectors/x/search', { query: query.trim(), max_results: 20 }))}>+ Official search</button></div>
          {targetLooksX && (
            <div className="x-manual-import">
              <div className="x-manual-title"><ClipboardPaste size={14} /><div><strong>Manual X Conversation Import</strong><span>Guaranteed prototype fallback when X blocks oEmbed/API access. Saved as X · IMPORT.</span></div></div>
              <label><span>Author / username</span><input value={xManualAuthor} onChange={(event) => setXManualAuthor(event.target.value)} placeholder={`@${authorFromUrl(target)}`} /></label>
              <label><span>Copied root post text</span><textarea value={xManualText} onChange={(event) => setXManualText(event.target.value)} placeholder="Paste the exact public X post text/caption here…" rows={3} /></label>
              <label><span>Copied replies / opinions</span><textarea value={xManualReplies} onChange={(event) => setXManualReplies(event.target.value)} placeholder={'One reply per line. Optional format:\n@user1: This is wrong\n@user2: I agree with this\nThis looks suspicious'} rows={6} /><small>Each line becomes a linked X reply so sentiment, stance, emotions and public-reaction direction can be analysed separately from the root post.</small></label>
              <button className="x-manual-btn" disabled={!!busy || !xManualText.trim()} onClick={() => void runManualXImport()}>{busy === 'xManual' ? <LoaderCircle className="spin-icon" size={14} /> : <MessageSquareText size={14} />} Add post + replies to NEXUS</button>
              <div className="x-manual-disclosure"><ShieldCheck size={13} /> This is not labelled LIVE. The original X URL and manual-transcription provenance remain visible in Evidence.</div>
            </div>
          )}
        </div>

        <div className="source-action-section"><div className="source-action-title">YouTube</div><div className="free-source-actions"><button disabled={!!busy || !query.trim()} onClick={() => run('youtube', () => post('/api/connectors/youtube/free', { query: query.trim(), limit: 10 }))}>+ Zero-key</button><button disabled={!!busy || !query.trim()} onClick={() => run('youtubeOfficial', () => post('/api/connectors/youtube/search', { query: query.trim(), max_videos: 3, max_comments_per_video: 20 }))}>+ Data API</button></div></div>
        <div className="source-action-section"><div className="source-action-title">Open/public search</div><div className="free-source-actions"><button disabled={!!busy || !query.trim()} onClick={() => run('bluesky', () => post('/api/connectors/bluesky/search', { query: query.trim(), limit: 25 }))}>+ Bluesky</button><button disabled={!!busy || !query.trim()} onClick={() => run('reddit', () => post('/api/connectors/reddit/search', { query: query.trim(), limit: 25 }))}>+ Reddit</button><button disabled={!!busy || !query.trim()} onClick={() => run('mastodon', () => post('/api/connectors/mastodon/search', { query: query.trim(), limit: 25, base_url: null }))}>+ Mastodon</button></div></div>
        <div className="source-action-section"><div className="source-action-title">Instagram</div><div className="free-source-actions"><button disabled={!!busy || !cleanHashtag || cleanHashtag.includes(' ')} onClick={() => run('instagramTag', () => post('/api/connectors/instagram/hashtag', { hashtag: cleanHashtag, limit: 20 }))}>+ Hashtag API</button><button disabled={!!busy || !targetUsername || targetLooksX || targetUsername.length > 30} onClick={() => run('instagram', () => post('/api/connectors/instagram/public', { profile: targetUsername, limit: 12 }))}>+ Public profile</button><button disabled={!!busy} onClick={() => run('instagramMeta', () => post('/api/connectors/meta/sync', { source: 'instagram', limit: 25 }))}>+ Meta authorized</button></div></div>
        <div className="source-action-section"><div className="source-action-title">Facebook</div><div className="free-source-actions"><button disabled={!!busy} onClick={() => run('facebookMeta', () => post('/api/connectors/meta/sync', { source: 'facebook', limit: 25 }))}>+ Authorized Page</button></div></div>
        <div className="source-action-section"><div className="source-action-title">Evidence</div><div className="free-source-actions"><button disabled={!!busy} onClick={() => void verifyEvidence()}><BadgeCheck size={13} /> Verify certificates</button></div></div>

        <div className="drawer-trust-note"><ShieldCheck size={15} /><span>NEXUS separates root-post NLP from audience reaction. LIVE, IMPORT and REPLAY remain distinct. X reply collection requires official provider access or disclosed manual import; NEXUS never fabricates comments.</span></div>
        {message && <div className={`free-source-message ${messageGood ? 'good' : 'bad'}`}><Radio size={14} />{message}</div>}
      </aside>
    </>
  );
}
