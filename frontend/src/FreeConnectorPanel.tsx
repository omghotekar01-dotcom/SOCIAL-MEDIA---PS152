import { useEffect, useState } from 'react';
import { BadgeCheck, LoaderCircle, Radio, ShieldCheck, Wifi, X as CloseIcon } from 'lucide-react';
import { API_BASE } from './api';

type ActionName = 'telegram' | 'youtube' | 'bluesky' | 'reddit' | 'mastodon' | 'instagram' | 'instagramTag' | 'x' | 'mix' | 'verify';

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
  const [query, setQuery] = useState('#RiverLinkUpdate');
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

  const runMix = async () => {
    if (!query.trim()) return;
    setBusy('mix'); setMessage('Creating a fresh multi-source workspace…'); setMessageGood(false);
    try {
      const rawTarget = target.trim();
      const targetIsX = X_POST_RE.test(rawTarget);
      const cleanTarget = rawTarget.replace(/^@/, '');
      const result = await post('/api/search/workspace', {
        query: query.trim(), reset: true, limit_per_source: 15,
        enable_youtube: true, enable_bluesky: true, enable_reddit: true, enable_mastodon: true,
        telegram_channel: !targetIsX && cleanTarget ? cleanTarget : null,
        instagram_profile: !targetIsX && cleanTarget && cleanTarget.length <= 30 ? cleanTarget : null,
      });

      let totalInserted = Number(result?.inserted || 0);
      const sourceEntries = Object.entries(result?.sources || {}) as Array<[string, any]>;
      const ok = sourceEntries.filter(([, status]) => status?.state === 'OK').map(([name]) => name);
      const unavailable = sourceEntries.filter(([, status]) => status?.state !== 'OK').map(([name]) => name);

      if (targetIsX) {
        try {
          const xResult = await post('/api/connectors/x/public', { query: query.trim(), target: rawTarget, limit: 25 });
          totalInserted += Number(xResult?.inserted || 0);
          if (!ok.includes('x')) ok.push('x');
        } catch {
          unavailable.push('x');
        }
      }

      setMessageGood(ok.length > 0);
      setMessage(`FRESH MIX: ${totalInserted} posts · OK ${ok.join(', ') || 'none'}${unavailable.length ? ` · unavailable ${[...new Set(unavailable)].join(', ')}` : ''} · old topic cleared · workspace updated`);
      refreshWorkspace();
    } catch (error) {
      setMessageGood(false);
      setMessage(error instanceof Error ? error.message : 'Fresh workspace search failed.');
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
  const busyLabel = busy ? busy === 'mix' ? 'Building fresh workspace…' : `Running ${busy}…` : '';

  return (
    <>
      <button className="free-source-launcher" type="button" onClick={() => setOpen(true)} title="Open free/public source controls">
        <span className="utility-icon"><Wifi size={17} /></span>
        <span><b>Free Sources</b><small>Live collection lab</small></span>
      </button>

      {open && <button className="utility-backdrop free-source-backdrop" aria-label="Close free source lab" onClick={() => setOpen(false)} />}

      <aside className={`free-source-drawer ${open ? 'open' : ''}`} aria-hidden={!open} aria-label="Free Source Lab" role="dialog" aria-modal={open ? 'true' : undefined}>
        <div className="utility-drawer-head free-source-head">
          <div>
            <div className="drawer-kicker">COLLECTION LAB</div>
            <h2>Free Source Lab</h2>
            <p>Start a clean multi-source search or append one source to the current workspace.</p>
          </div>
          <button className="utility-square-btn" type="button" onClick={() => setOpen(false)} title="Close"><CloseIcon size={17} /></button>
        </div>

        <div className="free-source-form">
          <label><span>Search topic</span><input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') void runMix(); }} placeholder="topic / #hashtag / search query" /></label>
          <label><span>Optional target</span><input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Telegram / Instagram target or public X Post URL(s)" /><small>{targetLooksX ? 'X public Post URL detected — official oEmbed fallback will be used.' : 'Leave blank to use configured Telegram channels and zero-key search sources.'}</small></label>
          <button className="free-primary" disabled={!!busy || !query.trim()} onClick={() => void runMix()}>{busy === 'mix' ? <LoaderCircle className="spin-icon" size={14} /> : <Wifi size={14} />} {busy === 'mix' ? 'Building…' : 'Fresh Free Mix'}</button>
        </div>

        {busy && <div className="free-source-busy"><LoaderCircle className="spin-icon" size={14} /><span>{busyLabel}</span></div>}

        <div className="free-source-actions">
          <button disabled={!!busy || !target.trim() || targetLooksX} onClick={() => run('telegram', () => post('/api/connectors/telegram/public', { channel: `${target.trim().replace(/^@/, '')}||${query.trim()}`, limit: 25 }))}>+ Telegram</button>
          <button disabled={!!busy || !query.trim()} onClick={() => run('youtube', () => post('/api/connectors/youtube/free', { query: query.trim(), limit: 10 }))}>+ YouTube ₹0</button>
          <button disabled={!!busy || !query.trim()} onClick={() => run('bluesky', () => post('/api/connectors/bluesky/search', { query: query.trim(), limit: 25 }))}>+ Bluesky</button>
          <button disabled={!!busy || !query.trim()} onClick={() => run('reddit', () => post('/api/connectors/reddit/search', { query: query.trim(), limit: 25 }))}>+ Reddit</button>
          <button disabled={!!busy || !query.trim()} onClick={() => run('mastodon', () => post('/api/connectors/mastodon/search', { query: query.trim(), limit: 25, base_url: null }))}>+ Mastodon</button>
          <button disabled={!!busy || !cleanHashtag || cleanHashtag.includes(' ')} onClick={() => run('instagramTag', () => post('/api/connectors/instagram/hashtag', { hashtag: cleanHashtag, limit: 20 }))}>+ IG Hashtag</button>
          <button disabled={!!busy || !target.trim() || targetLooksX || target.trim().replace(/^@/, '').length > 30} onClick={() => run('instagram', () => post('/api/connectors/instagram/public', { profile: target.trim().replace(/^@/, ''), limit: 12 }))}>+ Instagram</button>
          <button disabled={!!busy || (!query.trim() && !target.trim())} onClick={() => run('x', () => post('/api/connectors/x/public', { query: query.trim(), target: target.trim(), limit: 25 }))}>+ X URL / Bridge</button>
          <button disabled={!!busy} onClick={() => void verifyEvidence()}><BadgeCheck size={14} /> Verify Evidence</button>
        </div>

        <div className="drawer-trust-note"><ShieldCheck size={15} /><span>LIVE, IMPORT and REPLAY remain explicitly separated. No fallback is relabelled as official access.</span></div>
        {message && <div className={`free-source-message ${messageGood ? 'good' : 'bad'}`}><Radio size={14} />{message}</div>}
      </aside>
    </>
  );
}
