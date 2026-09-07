import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, Bot, CheckCircle2, Database, GitBranch, Globe2, LoaderCircle, MessageCircle,
  Network, Play, Radio, RefreshCw, Search, ShieldCheck, Square, Users2, X, Youtube,
} from 'lucide-react';
import {
  API_BASE, api, isExactYouTubeTarget,
  type ConnectorStatus, type DemographicsResponse, type NetworkResponse, type Overview, type SocialEvent,
} from './api';

type RequirementState = 'STRONG' | 'PARTIAL' | 'EMPTY';

type Snapshot = {
  connectors: ConnectorStatus[];
  events: SocialEvent[];
  overview: Overview & {
    root_content_events?: number;
    reaction_events?: number;
    reaction_sentiment_mix?: Record<string, number>;
    reaction_stance_mix?: Record<string, number>;
  };
  network: NetworkResponse;
  demographics: DemographicsResponse;
  narratives: number;
  collector: { running: boolean; cycles: number; last_run_at?: string | null };
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

function isReaction(event: SocialEvent) {
  const type = String(event.event_type || '').toLowerCase();
  return Boolean(event.parent_event_id) || type.includes('comment') || type.includes('reply') || type.includes('response');
}

function connectorState(connectors: ConnectorStatus[], platform: string) {
  return connectors.find((item) => item.platform === platform);
}

function Requirement({ id, title, state, detail }: { id: string; title: string; state: RequirementState; detail: string }) {
  return (
    <div className={`psc-req psc-${state.toLowerCase()}`}>
      <span>{id}</span><div><strong>{title}</strong><small>{detail}</small></div><b>{state}</b>
    </div>
  );
}

export default function PrototypeSourceCenter() {
  const [open, setOpen] = useState(false);
  const [topic, setTopic] = useState('RiverLink');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [telegramChannel, setTelegramChannel] = useState('NexusSIHDemo');
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [connectors, events, overview, network, demographics, narratives, collector] = await Promise.all([
        api.connectorStatus(), api.events(), api.overview(), api.network(), api.demographics(), api.narratives(), api.collectorStatus(),
      ]);
      setSnapshot({
        connectors: connectors.connectors || [],
        events: events.events || [],
        overview: overview as Snapshot['overview'],
        network,
        demographics,
        narratives: narratives.narratives?.length || 0,
        collector,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to read NEXUS source status.');
    }
  }, []);

  useEffect(() => { if (open) void refresh(); }, [open, refresh]);
  useEffect(() => {
    if (!open && !snapshot?.collector.running) return;
    const timer = window.setInterval(() => void refresh(), snapshot?.collector.running ? 5000 : 12000);
    return () => window.clearInterval(timer);
  }, [open, snapshot?.collector.running, refresh]);
  useEffect(() => {
    const update = () => { if (open) void refresh(); };
    window.addEventListener('nexus:workspace-updated', update);
    return () => window.removeEventListener('nexus:workspace-updated', update);
  }, [open, refresh]);

  const run = async (label: string, fn: () => Promise<any>) => {
    setBusy(label); setError(''); setMessage('');
    try {
      const result = await fn();
      setMessage(`${label}: ${Number(result?.inserted || 0)} new evidence row(s)${result?.received !== undefined ? ` / ${Number(result.received || 0)} received` : ''}.`);
      window.dispatchEvent(new Event('nexus:workspace-updated'));
      await refresh();
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} failed.`);
      throw err;
    } finally { setBusy(null); }
  };

  const loadYouTube = async () => {
    const target = youtubeUrl.trim();
    if (!isExactYouTubeTarget(target)) {
      setError('Paste one exact public YouTube watch / youtu.be / Shorts / live / embed URL.');
      return;
    }
    await run('YouTube conversation loaded', async () => {
      const result = await api.searchWorkspace(target, { reset: true, limitPerSource: 15 });
      return { inserted: result.inserted, received: result.received };
    });
  };

  const pollTelegram = async () => {
    await run('Telegram Bot API poll', () => api.pollTelegram());
  };

  const loadTelegramPublic = async () => {
    const channel = telegramChannel.trim().replace(/^@/, '') || 'NexusSIHDemo';
    const query = topic.trim();
    await run('Telegram public channel', () => jsonRequest('/api/connectors/telegram/public', {
      method: 'POST', body: JSON.stringify({ channel: `${channel}||${query}`, limit: 50 }),
    }));
  };

  const appendPublicMix = async () => {
    const query = topic.trim();
    if (!query) return;
    await run('Public multi-source append', () => jsonRequest('/api/search/workspace', {
      method: 'POST',
      body: JSON.stringify({
        query,
        reset: false,
        limit_per_source: 30,
        enable_youtube: false,
        enable_bluesky: true,
        enable_reddit: true,
        enable_mastodon: true,
        telegram_channel: `${telegramChannel.trim().replace(/^@/, '') || 'NexusSIHDemo'}||${query}`,
        instagram_profile: null,
      }),
    }));
  };

  const startWatch = async () => {
    const query = topic.trim();
    if (!query) return;
    setBusy('Start Live Watch'); setError(''); setMessage('');
    try {
      const result = await api.startCollector(query, { telegram: true, x: false, youtube: false, interval: 60 });
      setMessage('Live Watch started: Telegram Bot + monitored Telegram + Bluesky + Reddit + Mastodon run every 60 seconds.');
      setSnapshot((current) => current ? { ...current, collector: result } as Snapshot : current);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start Live Watch.');
    } finally { setBusy(null); }
  };

  const stopWatch = async () => {
    setBusy('Stop Live Watch'); setError(''); setMessage('');
    try {
      await api.stopCollector();
      setMessage('Live Watch stopped. Collected evidence remains in the active workspace.');
      window.dispatchEvent(new Event('nexus:workspace-updated'));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not stop Live Watch.');
    } finally { setBusy(null); }
  };

  const stats = useMemo(() => {
    const events = snapshot?.events || [];
    const platformRows = (platform: string) => events.filter((event) => event.platform === platform);
    const summarize = (platform: string) => {
      const rows = platformRows(platform);
      return {
        events: rows.length,
        roots: rows.filter((event) => !isReaction(event)).length,
        reactions: rows.filter(isReaction).length,
        live: rows.filter((event) => event.source_mode === 'LIVE').length,
      };
    };
    const youtube = summarize('youtube');
    const telegram = summarize('telegram');
    const latestYoutubeRoot = events.find((event) => event.platform === 'youtube' && !isReaction(event));
    const profile = latestYoutubeRoot?.public_profile || {};
    return { youtube, telegram, profile };
  }, [snapshot?.events]);

  const req = useMemo(() => {
    if (!snapshot) return [];
    const events = snapshot.events.length;
    const reactions = snapshot.events.filter(isReaction).length;
    const demoCoverage = Math.max(
      snapshot.demographics.language.coverage || 0,
      snapshot.demographics.broad_geography.coverage || 0,
      snapshot.demographics.professional_interests.coverage || 0,
      snapshot.demographics.age_brackets.coverage || 0,
    );
    const edges = snapshot.network.summary.edges || 0;
    return [
      ['A', 'Collection + Timeline', events > 0 ? (reactions > 0 ? 'STRONG' : 'PARTIAL') : 'EMPTY', `${events} events · ${reactions} comments/replies`],
      ['B', 'Sentiment + Emotion', reactions > 0 ? 'STRONG' : events > 0 ? 'PARTIAL' : 'EMPTY', `${reactions} audience reactions available for polarity, 8 emotions, stance and sarcasm`],
      ['C', 'Demographics', demoCoverage >= 0.5 ? 'STRONG' : events > 0 ? 'PARTIAL' : 'EMPTY', `${snapshot.demographics.unique_anonymized_users} pseudonymous users · max signal coverage ${Math.round(demoCoverage * 100)}%`],
      ['D', 'Trends + Topics', snapshot.narratives > 0 ? 'STRONG' : events > 0 ? 'PARTIAL' : 'EMPTY', `${snapshot.narratives} ranked narrative(s)`],
      ['E', 'Link Analysis', edges > 0 ? 'STRONG' : (snapshot.network.summary.nodes || 0) > 0 ? 'PARTIAL' : 'EMPTY', `${snapshot.network.summary.nodes || 0} nodes · ${edges} edges · ${snapshot.network.summary.communities || 0} communities`],
    ] as Array<[string, string, RequirementState, string]>;
  }, [snapshot]);

  const youtubeConnector = connectorState(snapshot?.connectors || [], 'youtube');
  const telegramConnector = connectorState(snapshot?.connectors || [], 'telegram');
  const youtubeBg = String(stats.profile.background_collection_state || 'idle');
  const youtubeCaptured = Number(stats.profile.captured_comment_count || stats.youtube.reactions || 0);
  const youtubeReported = Number(stats.profile.reported_comment_count || 0);
  const youtubeStop = String(stats.profile.collection_stop_reason || '');

  return (
    <>
      <button className="psc-launch" type="button" onClick={() => setOpen(true)}>
        <Radio size={18} /><div><strong>Prototype Sources</strong><span>Telegram + YouTube + 5/5 health</span></div>
      </button>

      {open && <button className="psc-backdrop" aria-label="Close Prototype Source Center" onClick={() => setOpen(false)} />}
      <aside className={`psc-drawer ${open ? 'open' : ''}`} role="dialog" aria-modal={open ? 'true' : undefined} aria-hidden={!open}>
        <header className="psc-head">
          <div><span>SIH26152 · SIMPLE OPERATOR MODE</span><h2>Prototype Source Center</h2><p>Use these three steps for the live prototype. The 5/5 requirement health below updates from actual evidence.</p></div>
          <button onClick={() => setOpen(false)} title="Close"><X size={18} /></button>
        </header>

        <div className="psc-scroll">
          {error && <div className="psc-banner bad">{error}</div>}
          {message && <div className="psc-banner good"><CheckCircle2 size={14} />{message}</div>}

          <section className="psc-source psc-youtube">
            <div className="psc-source-head"><div><Youtube size={20} /><span><b>1. YouTube — Full Public Conversation</b><small>Best live source for large comment/reply analytics</small></span></div><em>{youtubeConnector?.state || 'UNKNOWN'}</em></div>
            <label><span>Exact YouTube URL</span><input value={youtubeUrl} onChange={(event) => setYoutubeUrl(event.target.value)} placeholder="https://www.youtube.com/watch?v=..." /></label>
            <button className="psc-primary" disabled={!!busy || !youtubeUrl.trim()} onClick={() => void loadYouTube()}>{busy === 'YouTube conversation loaded' ? <LoaderCircle className="psc-spin" size={15} /> : <Search size={15} />} Load video + comments/replies</button>
            <div className="psc-metrics">
              <div><span>Evidence</span><strong>{stats.youtube.events}</strong><small>{stats.youtube.roots} root · {stats.youtube.reactions} reactions</small></div>
              <div><span>Captured reactions</span><strong>{youtubeCaptured}</strong><small>{youtubeReported ? `${youtubeReported} reported by YouTube` : 'provider-reported count unavailable'}</small></div>
              <div><span>Background crawl</span><strong>{youtubeBg.toUpperCase()}</strong><small>{youtubeStop || 'fast-first then provider-bounded exhaustive'}</small></div>
            </div>
            <div className="psc-note"><ShieldCheck size={14} /> The screen becomes usable after the fast first batch. The server continues through public comment/reply pages in the background; provider limits, disabled comments or quota are disclosed rather than hidden.</div>
          </section>

          <section className="psc-source psc-telegram">
            <div className="psc-source-head"><div><Bot size={20} /><span><b>2. Telegram — Channel + Discussion Comments</b><small>Controlled live source for dependable jury demonstration</small></span></div><em>{telegramConnector?.state || 'UNKNOWN'}</em></div>
            <div className="psc-inline"><label><span>Public channel</span><input value={telegramChannel} onChange={(event) => setTelegramChannel(event.target.value)} placeholder="NexusSIHDemo" /></label><label><span>Topic filter</span><input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="RiverLink" /></label></div>
            <div className="psc-actions"><button disabled={!!busy} onClick={() => void pollTelegram()}><MessageCircle size={14} /> Poll Bot comments now</button><button disabled={!!busy} onClick={() => void loadTelegramPublic()}><Globe2 size={14} /> Read public channel</button></div>
            <div className="psc-metrics">
              <div><span>Telegram evidence</span><strong>{stats.telegram.events}</strong><small>{stats.telegram.roots} root · {stats.telegram.reactions} comments/replies</small></div>
              <div><span>LIVE rows</span><strong>{stats.telegram.live}</strong><small>Bot/public evidence only</small></div>
              <div><span>Continuous watch</span><strong>{snapshot?.collector.running ? 'RUNNING' : 'STOPPED'}</strong><small>{snapshot?.collector.running ? `${snapshot.collector.cycles} cycles` : 'one click below'}</small></div>
            </div>
            <div className="psc-note"><ShieldCheck size={14} /> For comments, the bot must be visible in the linked discussion group. Create a NEW channel post and comments after bot setup; Bot API polling is not arbitrary historical chat download.</div>
          </section>

          <section className="psc-source">
            <div className="psc-source-head"><div><Activity size={20} /><span><b>3. Extra Public Coverage + Continuous Watch</b><small>Bluesky, Reddit, Mastodon and monitored Telegram complement the two primary demo sources</small></span></div></div>
            <div className="psc-actions"><button disabled={!!busy || !topic.trim()} onClick={() => void appendPublicMix()}><Database size={14} /> Append public mix</button>{!snapshot?.collector.running ? <button className="psc-watch" disabled={!!busy || !topic.trim()} onClick={() => void startWatch()}><Play size={14} /> Start 60s Live Watch</button> : <button className="psc-stop" disabled={!!busy} onClick={() => void stopWatch()}><Square size={13} /> Stop Live Watch</button>}<button disabled={!!busy} onClick={() => void refresh()}><RefreshCw size={14} /> Refresh</button></div>
            <div className="psc-note"><Radio size={14} /> Live Watch uses Telegram Bot + monitored Telegram + Bluesky + Reddit + Mastodon by default. X remains explicit because unrestricted X search needs authorized API access.</div>
          </section>

          <section className="psc-health">
            <div className="psc-health-head"><div><ShieldCheck size={19} /><span><b>Original Problem Statement — 5/5 Health</b><small>Based on the active workspace, not hard-coded green checks</small></span></div></div>
            <div className="psc-req-grid">{req.map(([id, title, state, detail]) => <Requirement key={id} id={id} title={title} state={state} detail={detail} />)}</div>
            <div className="psc-health-links"><span><Database size={13} /> A: collection/timeline</span><span><Activity size={13} /> B: sentiment/emotion</span><span><Users2 size={13} /> C: demographics</span><span><GitBranch size={13} /> D: trends/topics</span><span><Network size={13} /> E: link topology</span></div>
            <div className="psc-note"><ShieldCheck size={14} /> Use the separate <b>PS26152 CORE</b> button for the full judge-facing A→E evidence view. This panel is the simple operator/checklist view.</div>
          </section>
        </div>
      </aside>
    </>
  );
}
