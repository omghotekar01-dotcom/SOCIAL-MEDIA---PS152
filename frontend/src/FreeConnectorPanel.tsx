import { type CSSProperties, useState } from 'react';
import { BadgeCheck, Radio, ShieldCheck, Wifi, X as CloseIcon } from 'lucide-react';
import { API_BASE } from './api';

type ActionName = 'telegram' | 'youtube' | 'bluesky' | 'reddit' | 'mastodon' | 'instagram' | 'instagramTag' | 'x' | 'mix' | 'verify';

const buttonStyle: CSSProperties = {
  border: '1px solid rgba(130,155,210,.28)', background: 'rgba(15,23,42,.84)', color: '#e9f0ff', borderRadius: 10,
  padding: '8px 11px', cursor: 'pointer', fontSize: 12, fontWeight: 700,
};
const primaryButtonStyle: CSSProperties = {
  ...buttonStyle, border: '1px solid rgba(101,199,255,.55)', background: 'linear-gradient(135deg,rgba(32,99,194,.95),rgba(73,65,196,.95))',
};
const inputStyle: CSSProperties = {
  minWidth: 180, flex: 1, border: '1px solid rgba(130,155,210,.28)', background: '#0b1220', color: '#eef4ff', borderRadius: 10,
  padding: '9px 11px', outline: 'none',
};

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

export default function FreeConnectorPanel() {
  const [query, setQuery] = useState('#RiverLinkUpdate');
  const [target, setTarget] = useState('');
  const [busy, setBusy] = useState<ActionName | null>(null);
  const [message, setMessage] = useState<string>('');
  const [messageGood, setMessageGood] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const run = async (name: ActionName, fn: () => Promise<any>, reload = true) => {
    setBusy(name); setMessage(''); setMessageGood(false);
    try {
      const result = await fn();
      setMessageGood(true);
      setMessage(`${name.toUpperCase()}: ${result?.inserted ?? 0} new / ${result?.received ?? 0} received${reload ? ' · refreshing…' : ''}`);
      if (reload) window.setTimeout(() => window.location.reload(), 650);
    } catch (error) {
      setMessageGood(false);
      setMessage(error instanceof Error ? error.message : 'Connector failed.');
    } finally { setBusy(null); }
  };

  const runMix = async () => {
    if (!query.trim()) return;
    setBusy('mix');
    setMessage('Creating a fresh search workspace…');
    setMessageGood(false);
    try {
      const cleanTarget = target.trim().replace(/^@/, '');
      const result = await post('/api/search/workspace', {
        query: query.trim(),
        reset: true,
        limit_per_source: 15,
        enable_youtube: true,
        enable_bluesky: true,
        enable_reddit: true,
        enable_mastodon: true,
        telegram_channel: cleanTarget || null,
        instagram_profile: cleanTarget || null,
      });
      const sourceEntries = Object.entries(result?.sources || {}) as Array<[string, any]>;
      const ok = sourceEntries.filter(([, status]) => status?.state === 'OK').map(([name]) => name);
      const unavailable = sourceEntries.filter(([, status]) => status?.state !== 'OK').map(([name]) => name);
      setMessageGood(ok.length > 0);
      setMessage(`FRESH MIX: ${result?.inserted ?? 0} posts · OK ${ok.join(', ') || 'none'}${unavailable.length ? ` · unavailable ${unavailable.join(', ')}` : ''} · old topic cleared`);
      window.setTimeout(() => window.location.reload(), 800);
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
      setMessage(error instanceof Error ? error.message : 'Evidence verification failed.');
    } finally { setBusy(null); }
  };

  if (collapsed) {
    return <button onClick={() => setCollapsed(false)} style={{ ...buttonStyle, position: 'fixed', right: 16, bottom: 16, zIndex: 50, boxShadow: '0 14px 40px rgba(0,0,0,.35)' }} title="Open free/public connector controls"><Wifi size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} /> FREE SOURCES</button>;
  }

  const cleanHashtag = query.trim().replace(/^#/, '');

  return (
    <section style={{ position: 'relative', zIndex: 40, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, padding: '10px 16px', background: 'linear-gradient(90deg,#07101f,#0c1730)', color: '#eaf1ff', borderBottom: '1px solid rgba(120,150,210,.22)', fontFamily: 'Inter,system-ui,sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginRight: 5 }}><Radio size={15} /><strong style={{ fontSize: 12, letterSpacing: '.08em' }}>FREE SOURCE LAB</strong><span style={{ fontSize: 11, opacity: .65 }}>Fresh Mix replaces topic · single source buttons append</span></div>
      <input style={inputStyle} value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') void runMix(); }} placeholder="topic / #hashtag / search query" />
      <input style={{ ...inputStyle, maxWidth: 220 }} value={target} onChange={(e) => setTarget(e.target.value)} placeholder="channel/profile (optional)" />
      <button style={primaryButtonStyle} disabled={!!busy || !query.trim()} onClick={() => void runMix()}><Wifi size={13} style={{ verticalAlign: 'middle', marginRight: 5 }} />Fresh Free Mix</button>
      <button style={buttonStyle} disabled={!!busy || !target.trim()} onClick={() => run('telegram', () => post('/api/connectors/telegram/public', { channel: target.trim().replace(/^@/, ''), limit: 25 }))}>+ Telegram Public</button>
      <button style={buttonStyle} disabled={!!busy || !query.trim()} onClick={() => run('youtube', () => post('/api/connectors/youtube/free', { query: query.trim(), limit: 10 }))}>+ YouTube ₹0</button>
      <button style={buttonStyle} disabled={!!busy || !query.trim()} onClick={() => run('bluesky', () => post('/api/connectors/bluesky/search', { query: query.trim(), limit: 25 }))}>+ Bluesky</button>
      <button style={buttonStyle} disabled={!!busy || !query.trim()} onClick={() => run('reddit', () => post('/api/connectors/reddit/search', { query: query.trim(), limit: 25 }))}>+ Reddit</button>
      <button style={buttonStyle} disabled={!!busy || !query.trim()} onClick={() => run('mastodon', () => post('/api/connectors/mastodon/search', { query: query.trim(), limit: 25, base_url: null }))}>+ Mastodon</button>
      <button style={buttonStyle} disabled={!!busy || !cleanHashtag || cleanHashtag.includes(' ')} onClick={() => run('instagramTag', () => post('/api/connectors/instagram/hashtag', { hashtag: cleanHashtag, limit: 20 }))}>+ IG Hashtag API</button>
      <button style={buttonStyle} disabled={!!busy || !target.trim()} onClick={() => run('instagram', () => post('/api/connectors/instagram/public', { profile: target.trim().replace(/^@/, ''), limit: 12 }))}>+ Instagram Public</button>
      <button style={buttonStyle} disabled={!!busy || (!query.trim() && !target.trim())} onClick={() => run('x', () => post('/api/connectors/x/public', { query: query.trim(), target: target.trim(), limit: 25 }))}>+ X Public Bridge</button>
      <button style={buttonStyle} disabled={!!busy} onClick={() => void verifyEvidence()}><BadgeCheck size={13} style={{ verticalAlign: 'middle', marginRight: 5 }} />Verify Evidence</button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, opacity: .75 }} title="No connector may label replay/import as live."><ShieldCheck size={13} /> truthful source modes</div>
      {message && <span style={{ fontSize: 11, maxWidth: 560, color: messageGood ? '#7be0b3' : '#ffb0b7' }}>{message}</span>}
      <button aria-label="Collapse free connector controls" onClick={() => setCollapsed(true)} style={{ ...buttonStyle, padding: 7, marginLeft: 'auto' }}><CloseIcon size={13} /></button>
    </section>
  );
}
