import { Activity, AlertTriangle, BarChart3, LoaderCircle, MessageCircleMore, ShieldCheck, Users2, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { API_BASE } from './api';

type ReactionConversation = {
  root_event_id?: string;
  platform?: string;
  reaction_count?: number;
  negative_share?: number;
  positive_share?: number;
  against_share?: number;
  supportive_share?: number;
  risk_score?: number;
  risk_label?: string;
  verdict?: string;
  flags?: string[];
};

type ReactionOverview = {
  conversations?: number;
  conversations_with_reactions?: number;
  captured_reactions?: number;
  overall_negative_share?: number;
  overall_positive_share?: number;
  overall_against_share?: number;
  overall_supportive_share?: number;
  risk_score?: number;
  risk_label?: string;
  escalating_conversations?: number;
  watch_conversations?: number;
  coverage?: number;
  note?: string;
  top_conversations?: ReactionConversation[];
};

type OverviewPayload = {
  total_events?: number;
  root_content_events?: number;
  reaction_events?: number;
  sentiment_mix?: Record<string, number>;
  root_sentiment_mix?: Record<string, number>;
  reaction_sentiment_mix?: Record<string, number>;
  reaction_stance_mix?: Record<string, number>;
  sentiment_separation_note?: string;
  emotion_mix?: Record<string, number>;
  reaction_overview?: ReactionOverview;
};

const pct = (value?: number) => `${Math.round((value || 0) * 100)}%`;
const emotionLabels = ['anxiety', 'anger', 'excitement', 'sadness', 'joy', 'disgust', 'surprise', 'trust'];

function distributionShare(counts: Record<string, number> | undefined, key: string) {
  const safe = counts || {};
  const total = Object.values(safe).reduce((sum, value) => sum + Number(value || 0), 0);
  return total ? Number(safe[key] || 0) / total : 0;
}

async function loadOverview(): Promise<OverviewPayload> {
  const response = await fetch(`${API_BASE}/api/overview`);
  if (!response.ok) throw new Error(`Audience overview failed: HTTP ${response.status}`);
  return response.json();
}

export default function AudiencePulsePanel() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setData(await loadOverview());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load audience intelligence.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) void refresh();
  }, [open, refresh]);

  useEffect(() => {
    const onWorkspace = () => { if (open) void refresh(); };
    window.addEventListener('nexus:workspace-updated', onWorkspace);
    return () => window.removeEventListener('nexus:workspace-updated', onWorkspace);
  }, [open, refresh]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const reaction = data?.reaction_overview || {};
  const riskLabel = String(reaction.risk_label || 'STABLE');
  const emotions = useMemo(() => {
    const mix = data?.emotion_mix || {};
    return emotionLabels.map((label) => [label, Number(mix[label] || 0)] as const);
  }, [data]);

  const rootPositive = distributionShare(data?.root_sentiment_mix, 'positive');
  const rootNegative = distributionShare(data?.root_sentiment_mix, 'negative');
  const rootNeutral = distributionShare(data?.root_sentiment_mix, 'neutral');
  const audiencePositive = distributionShare(data?.reaction_sentiment_mix, 'positive');
  const audienceNegative = distributionShare(data?.reaction_sentiment_mix, 'negative');
  const audienceNeutral = distributionShare(data?.reaction_sentiment_mix, 'neutral');

  return (
    <>
      <button className="audience-pulse-launcher" type="button" onClick={() => setOpen(true)} title="Open audience intelligence">
        <span className="utility-icon"><Activity size={17} /></span>
        <span><b>Audience Pulse</b><small>Comments · emotion · direction</small></span>
      </button>

      {open && <button className="utility-backdrop audience-pulse-backdrop" aria-label="Close audience pulse" onClick={() => setOpen(false)} />}
      <aside className={`audience-pulse-drawer ${open ? 'open' : ''}`} role="dialog" aria-modal={open ? 'true' : undefined} aria-hidden={!open}>
        <div className="audience-pulse-head">
          <div><span>AUDIENCE INTELLIGENCE</span><h2>Public reaction pulse</h2><p>Root-post NLP and audience comments are deliberately separated.</p></div>
          <div className="audience-pulse-head-actions">
            <button type="button" onClick={() => void refresh()} title="Refresh">{loading ? <LoaderCircle className="spin-icon" size={16} /> : <BarChart3 size={16} />}</button>
            <button type="button" onClick={() => setOpen(false)} title="Close"><X size={17} /></button>
          </div>
        </div>

        {error && <div className="audience-pulse-error"><AlertTriangle size={15} />{error}</div>}

        <div className="audience-risk-hero">
          <div><span>REACTION DIRECTION</span><strong className={`audience-risk-${riskLabel.toLowerCase()}`}>{riskLabel}</strong><small>Evidence-bounded attention signal</small></div>
          <div><strong>{reaction.risk_score || 0}</strong><span>/100</span></div>
        </div>

        <div className="audience-pulse-metrics">
          <div><MessageCircleMore size={15} /><span>Captured reactions</span><strong>{reaction.captured_reactions || 0}</strong><small>comments / replies</small></div>
          <div><Users2 size={15} /><span>Conversations covered</span><strong>{reaction.conversations_with_reactions || 0}/{reaction.conversations || 0}</strong><small>{pct(reaction.coverage)} coverage</small></div>
          <div><span>AUDIENCE NEGATIVE</span><strong>{pct(reaction.overall_negative_share)}</strong><small>positive {pct(reaction.overall_positive_share)}</small></div>
          <div><span>AUDIENCE STANCE</span><strong>{pct(reaction.overall_against_share)} against</strong><small>{pct(reaction.overall_supportive_share)} supportive</small></div>
        </div>

        <section className="audience-pulse-section">
          <div className="audience-pulse-section-title"><div><span>CONTENT VS AUDIENCE</span><strong>Overall sentiment, kept separate</strong></div><small>{data?.sentiment_separation_note || 'Root content is not public opinion.'}</small></div>
          <div className="audience-sentiment-compare">
            <div><span>ROOT POSTS / CONTENT</span><strong>{data?.root_content_events || 0} items</strong><p><b>{pct(rootPositive)}</b> positive · <b>{pct(rootNegative)}</b> negative · <b>{pct(rootNeutral)}</b> neutral</p></div>
            <div><span>COMMENTS / REPLIES</span><strong>{data?.reaction_events || 0} reactions</strong><p><b>{pct(audiencePositive)}</b> positive · <b>{pct(audienceNegative)}</b> negative · <b>{pct(audienceNeutral)}</b> neutral</p></div>
          </div>
        </section>

        <section className="audience-pulse-section">
          <div className="audience-pulse-section-title"><div><span>8-DIMENSION EMOTION LAYER</span><strong>Observed emotional mix</strong></div><small>{data?.total_events || 0} events</small></div>
          <div className="audience-emotion-grid">
            {emotions.map(([label, value]) => (
              <div key={label}><span>{label}</span><i><b style={{ width: pct(Math.min(1, value)) }} /></i><strong>{pct(value)}</strong></div>
            ))}
          </div>
        </section>

        <section className="audience-pulse-section">
          <div className="audience-pulse-section-title"><div><span>HIGHER-ATTENTION CONVERSATIONS</span><strong>What needs analyst review</strong></div><small>{reaction.escalating_conversations || 0} escalating · {reaction.watch_conversations || 0} watch</small></div>
          <div className="audience-conversation-list">
            {(reaction.top_conversations || []).slice(0, 5).map((item, index) => (
              <article key={`${item.root_event_id || 'conversation'}-${index}`}>
                <div><span>{String(item.platform || 'source').toUpperCase()} · {item.reaction_count || 0} reactions</span><strong>{item.risk_label || 'STABLE'} · {item.risk_score || 0}/100</strong></div>
                <p>{item.verdict || 'Captured reaction summary.'}</p>
                <div className="audience-conversation-chips"><span>{pct(item.negative_share)} negative</span><span>{pct(item.against_share)} against</span>{(item.flags || []).slice(0, 2).map((flag) => <span key={flag}>{flag.replaceAll('-', ' ')}</span>)}</div>
              </article>
            ))}
            {!(reaction.top_conversations || []).length && <div className="audience-empty"><ShieldCheck size={15} /><span>No linked comments/replies yet. NEXUS will not infer public opinion from root posts alone.</span></div>}
          </div>
        </section>

        <div className="audience-pulse-trust"><ShieldCheck size={14} /><span>{reaction.note || 'Audience reaction is bounded to captured comments/replies and does not imply wrongdoing, intent, or internet-wide opinion.'}</span></div>
      </aside>
    </>
  );
}
