import { AlertTriangle, MessageCircle, ShieldCheck, Users2 } from 'lucide-react';
import type { SocialEvent } from './api';

type Props = {
  event: SocialEvent;
  events: SocialEvent[];
};

type ReactionSummary = {
  root: SocialEvent;
  reactions: SocialEvent[];
  sentiment: Record<string, number>;
  stance: Record<string, number>;
  negativeShare: number;
  positiveShare: number;
  againstShare: number;
  supportiveShare: number;
  anger: number;
  anxiety: number;
  sarcasm: number;
  riskScore: number;
  riskLabel: 'STABLE' | 'WATCH' | 'ESCALATING';
  confidence: number;
  verdict: string;
  flags: string[];
};

function reactionLike(event: SocialEvent) {
  const type = (event.event_type || '').toLowerCase();
  return Boolean(event.parent_event_id) || /comment|reply|replied_to|response/.test(type);
}

function findRoot(selected: SocialEvent, events: SocialEvent[]) {
  if (selected.parent_event_id) {
    const direct = events.find((event) => event.platform === selected.platform && event.source_event_id === selected.parent_event_id);
    if (direct) return direct;
  }
  const conversation = selected.conversation_id;
  if (conversation) {
    const candidates = events.filter((event) => event.platform === selected.platform && event.conversation_id === conversation);
    const root = candidates.find((event) => !reactionLike(event));
    if (root) return root;
  }
  return selected;
}

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function buildSummary(selected: SocialEvent, events: SocialEvent[]): ReactionSummary {
  const root = findRoot(selected, events);
  const conversation = root.conversation_id || selected.conversation_id || '';
  const reactions = events.filter((event) => {
    if (event.id === root.id || event.platform !== root.platform) return false;
    if (event.parent_event_id && event.parent_event_id === root.source_event_id) return true;
    if (conversation && event.conversation_id === conversation && reactionLike(event)) return true;
    return false;
  });

  const sentiment: Record<string, number> = { positive: 0, negative: 0, neutral: 0, unknown: 0 };
  const stance: Record<string, number> = { supportive: 0, against: 0, unclear: 0 };
  let anger = 0;
  let anxiety = 0;
  let sarcasm = 0;

  for (const reaction of reactions) {
    const sentimentKey = reaction.sentiment_label || 'unknown';
    sentiment[sentimentKey] = (sentiment[sentimentKey] || 0) + 1;
    const stanceKey = reaction.stance_label || 'unclear';
    stance[stanceKey] = (stance[stanceKey] || 0) + 1;
    anger += Number(reaction.emotion_scores?.anger || 0);
    anxiety += Number(reaction.emotion_scores?.anxiety || 0);
    sarcasm += Number(reaction.sarcasm_probability || 0);
  }

  const n = reactions.length;
  const negativeShare = n ? (sentiment.negative || 0) / n : 0;
  const positiveShare = n ? (sentiment.positive || 0) / n : 0;
  const againstShare = n ? (stance.against || 0) / n : 0;
  const supportiveShare = n ? (stance.supportive || 0) / n : 0;
  anger = n ? anger / n : 0;
  anxiety = n ? anxiety / n : 0;
  sarcasm = n ? sarcasm / n : 0;
  const volumeSignal = Math.min(1, n / 25);
  const polarized = positiveShare >= 0.25 && negativeShare >= 0.25 ? 1 : 0;
  const riskScore = Math.round(100 * Math.min(1,
    0.32 * negativeShare
    + 0.22 * againstShare
    + 0.18 * Math.max(anger, anxiety)
    + 0.10 * sarcasm
    + 0.10 * volumeSignal
    + 0.08 * polarized,
  ));
  const riskLabel: ReactionSummary['riskLabel'] = riskScore >= 60 ? 'ESCALATING' : riskScore >= 35 ? 'WATCH' : 'STABLE';
  const confidence = n ? Math.min(0.95, 0.35 + Math.log10(n + 1) * 0.32) : 0.15;

  let verdict = 'No audience replies/comments are captured for this post yet.';
  if (n) {
    if (negativeShare >= 0.55) verdict = 'Audience reaction is predominantly negative in the collected comments.';
    else if (positiveShare >= 0.55) verdict = 'Audience reaction is predominantly positive in the collected comments.';
    else if (polarized) verdict = 'Audience reaction is mixed/polarized across the collected comments.';
    else verdict = 'Audience reaction is mixed or neutral in the collected comments.';
  }

  const flags: string[] = [];
  if (negativeShare >= 0.55) flags.push('negative-reaction-dominant');
  if (againstShare >= 0.45) flags.push('opposition-elevated');
  if (anger >= 0.35) flags.push('anger-signal-elevated');
  if (anxiety >= 0.35) flags.push('anxiety-signal-elevated');
  if (sarcasm >= 0.35) flags.push('sarcasm-elevated');
  if (polarized) flags.push('polarized-opinion');
  if (n >= 20) flags.push('high-reply-volume');

  return {
    root,
    reactions,
    sentiment,
    stance,
    negativeShare,
    positiveShare,
    againstShare,
    supportiveShare,
    anger,
    anxiety,
    sarcasm,
    riskScore,
    riskLabel,
    confidence,
    verdict,
    flags,
  };
}

export default function ReactionIntelligence({ event, events }: Props) {
  const summary = buildSummary(event, events);
  const n = summary.reactions.length;

  return (
    <section className="reaction-card">
      <div className="reaction-head">
        <div>
          <span className="reaction-kicker">PUBLIC REACTION INTELLIGENCE</span>
          <h3>What people are saying around this post</h3>
          <p>Post-level NLP is kept separate from comment/reply opinion so NEXUS does not confuse the author's message with public reaction.</p>
        </div>
        <div className={`reaction-risk reaction-risk-${summary.riskLabel.toLowerCase()}`}>
          <span>{summary.riskLabel}</span>
          <strong>{summary.riskScore}</strong>
          <small>reaction risk / 100</small>
        </div>
      </div>

      <div className="reaction-verdict">
        {summary.riskLabel === 'ESCALATING' ? <AlertTriangle size={17} /> : <ShieldCheck size={17} />}
        <div><strong>{summary.verdict}</strong><span>{n} captured reaction{n === 1 ? '' : 's'} · confidence {pct(summary.confidence)}</span></div>
      </div>

      <div className="reaction-grid">
        <div className="reaction-metric"><MessageCircle size={15} /><span>Comments / replies</span><strong>{n}</strong><small>linked to this conversation</small></div>
        <div className="reaction-metric"><Users2 size={15} /><span>Negative / positive</span><strong>{pct(summary.negativeShare)} / {pct(summary.positiveShare)}</strong><small>comment sentiment distribution</small></div>
        <div className="reaction-metric"><span>STANCE</span><strong>{pct(summary.againstShare)} against</strong><small>{pct(summary.supportiveShare)} supportive</small></div>
        <div className="reaction-metric"><span>EMOTION</span><strong>{pct(Math.max(summary.anger, summary.anxiety))}</strong><small>max anger/anxiety signal</small></div>
      </div>

      {n > 0 ? (
        <>
          <div className="reaction-bars">
            <div><span>Negative</span><i><b style={{ width: pct(summary.negativeShare) }} /></i><strong>{pct(summary.negativeShare)}</strong></div>
            <div><span>Positive</span><i><b style={{ width: pct(summary.positiveShare) }} /></i><strong>{pct(summary.positiveShare)}</strong></div>
            <div><span>Against stance</span><i><b style={{ width: pct(summary.againstShare) }} /></i><strong>{pct(summary.againstShare)}</strong></div>
            <div><span>Sarcasm</span><i><b style={{ width: pct(summary.sarcasm) }} /></i><strong>{pct(summary.sarcasm)}</strong></div>
          </div>
          {summary.flags.length > 0 && <div className="reaction-flags">{summary.flags.map((flag) => <span key={flag}>{flag.replaceAll('-', ' ')}</span>)}</div>}
          <div className="reaction-samples">
            {summary.reactions.slice(0, 5).map((reaction) => (
              <div key={reaction.id}>
                <div><strong>{reaction.author_display || reaction.author_pseudo_id || 'Unknown author'}</strong><span>{reaction.sentiment_label || 'unknown'} · {reaction.stance_label || 'unclear'} · {reaction.source_mode}</span></div>
                <p>{reaction.text}</p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="reaction-empty"><ShieldCheck size={15} /><span>No comments/replies are currently linked to this evidence item. NEXUS will not infer public opinion from the root post alone. Use a provider comment connector or Manual X Conversation Import when required.</span></div>
      )}

      <div className="reaction-trust"><ShieldCheck size={14} /> The score is evidence-bounded and descriptive. It indicates reaction direction/attention in collected comments, not wrongdoing, intent, or absolute internet-wide opinion.</div>
    </section>
  );
}
