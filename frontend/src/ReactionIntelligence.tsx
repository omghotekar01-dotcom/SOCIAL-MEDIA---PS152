import { AlertTriangle, MessageCircle, ShieldCheck, Users2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { API_BASE, type SocialEvent } from './api';

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

type FullReaction = {
  root_event_id?: string;
  reaction_count?: number;
  negative_share?: number;
  positive_share?: number;
  against_share?: number;
  supportive_share?: number;
  emotion_means?: Record<string, number>;
  sarcasm_mean?: number;
  risk_score?: number;
  risk_label?: 'STABLE' | 'WATCH' | 'ESCALATING';
  confidence?: number;
  verdict?: string;
  flags?: string[];
};

type ProviderCommentState = {
  label: string;
  detail: string;
  tone: 'good' | 'warn' | 'bad' | 'info';
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

function providerCommentState(root: SocialEvent, visibleCaptured: number): ProviderCommentState | null {
  if (root.platform !== 'youtube') return null;

  const profile = root.public_profile || {};
  const state = String(profile.comments_state || '').toLowerCase();
  const note = String(profile.comments_note || '').trim();
  const reported = Number(profile.reported_comment_count || root.engagement?.comments || 0);
  const captured = Number(profile.captured_comment_count ?? visibleCaptured);
  const complete = Boolean(profile.collection_complete);
  const coverage = Number(profile.coverage_ratio);
  const connector = String(profile.connector || '');
  const metadataOnly = root.source_event_id.startsWith('free:') || /yt_dlp|public_metadata/i.test(connector);

  if (metadataOnly) {
    return {
      label: 'METADATA ONLY — COMMENTS NOT REQUESTED',
      detail: 'This record came from the zero-key YouTube metadata path. Re-run the exact URL through Fresh Search/Data API on the updated build to collect public comments and replies.',
      tone: 'warn',
    };
  }
  if (state === 'available' || captured > 0) {
    const coverageText = Number.isFinite(coverage) && reported > 0 ? ` · ${Math.round(coverage * 100)}% of reported count` : '';
    return {
      label: `COMMENTS AVAILABLE · ${captured} CAPTURED${complete ? ' · COMPLETE' : ''}`,
      detail: note || `YouTube Data API returned ${captured} public comment/reply event${captured === 1 ? '' : 's'}${coverageText}.`,
      tone: complete ? 'good' : 'warn',
    };
  }
  if (state === 'disabled') {
    return {
      label: 'COMMENTS DISABLED BY YOUTUBE/CREATOR',
      detail: note || 'YouTube returned commentsDisabled for this video, so there are no public comment rows available through the Data API.',
      tone: 'bad',
    };
  }
  if (state === 'empty') {
    return {
      label: 'NO PUBLIC COMMENTS REPORTED',
      detail: 'The official video metadata reports zero public comments for this video.',
      tone: 'info',
    };
  }
  if (state === 'no_rows_returned') {
    return {
      label: 'COMMENTS REPORTED, BUT NO ROWS RETURNED',
      detail: `YouTube reports ${reported} comment${reported === 1 ? '' : 's'}, but commentThreads returned no public rows in this request.`,
      tone: 'warn',
    };
  }
  if (state === 'rate_limited') {
    return {
      label: 'YOUTUBE COMMENTS RATE LIMITED',
      detail: note || 'The YouTube comment endpoint rate-limited this request. The root video is preserved but audience analysis is incomplete.',
      tone: 'bad',
    };
  }
  if (state === 'forbidden' || state === 'unavailable') {
    return {
      label: 'YOUTUBE COMMENT API UNAVAILABLE',
      detail: note || 'The official comment endpoint could not return public comments for this video. Check API permissions/quota and the video comment state.',
      tone: 'bad',
    };
  }
  if (state === 'pending') {
    return {
      label: 'COMMENT COLLECTION STATE PENDING',
      detail: 'The video was ingested but its final comment availability state was not resolved. Re-run on the latest build; this state should not persist after the connector finishes.',
      tone: 'warn',
    };
  }
  return null;
}

function buildSummary(selected: SocialEvent, events: SocialEvent[]): ReactionSummary {
  const root = findRoot(selected, events);
  const conversation = root.conversation_id || selected.conversation_id || '';
  const reactions = events.filter((candidate) => {
    if (candidate.id === root.id || candidate.platform !== root.platform) return false;
    if (candidate.parent_event_id && candidate.parent_event_id === root.source_event_id) return true;
    if (conversation && candidate.conversation_id === conversation && reactionLike(candidate)) return true;
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
  const local = useMemo(() => buildSummary(event, events), [event, events]);
  const [full, setFull] = useState<FullReaction | null>(null);

  useEffect(() => {
    let cancelled = false;
    setFull(null);
    void fetch(`${API_BASE}/api/overview`)
      .then((response) => response.ok ? response.json() : null)
      .then((payload) => {
        if (cancelled || !payload) return;
        const rows = payload?.reaction_overview?.top_conversations || [];
        const match = rows.find((row: FullReaction) => row.root_event_id === local.root.id);
        if (match) setFull(match);
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [local.root.id]);

  const n = Number(full?.reaction_count ?? local.reactions.length);
  const negativeShare = Number(full?.negative_share ?? local.negativeShare);
  const positiveShare = Number(full?.positive_share ?? local.positiveShare);
  const againstShare = Number(full?.against_share ?? local.againstShare);
  const supportiveShare = Number(full?.supportive_share ?? local.supportiveShare);
  const anger = Number(full?.emotion_means?.anger ?? local.anger);
  const anxiety = Number(full?.emotion_means?.anxiety ?? local.anxiety);
  const sarcasm = Number(full?.sarcasm_mean ?? local.sarcasm);
  const riskScore = Number(full?.risk_score ?? local.riskScore);
  const riskLabel = (full?.risk_label ?? local.riskLabel) as ReactionSummary['riskLabel'];
  const confidence = Number(full?.confidence ?? local.confidence);
  const verdict = String(full?.verdict ?? local.verdict);
  const flags = full?.flags ?? local.flags;
  const providerState = providerCommentState(local.root, n);

  return (
    <section className="reaction-card">
      <div className="reaction-head">
        <div>
          <span className="reaction-kicker">PUBLIC REACTION INTELLIGENCE</span>
          <h3>What people are saying around this post</h3>
          <p>Post-level NLP is kept separate from comment/reply opinion. Aggregate metrics use the complete backend conversation population when available.</p>
        </div>
        <div className={`reaction-risk reaction-risk-${riskLabel.toLowerCase()}`}>
          <span>{riskLabel}</span>
          <strong>{riskScore}</strong>
          <small>reaction risk / 100</small>
        </div>
      </div>

      {providerState && (
        <div className={`reaction-provider-state reaction-provider-${providerState.tone}`}>
          {providerState.tone === 'bad' ? <AlertTriangle size={16} /> : <ShieldCheck size={16} />}
          <div><strong>{providerState.label}</strong><span>{providerState.detail}</span></div>
        </div>
      )}

      <div className="reaction-verdict">
        {riskLabel === 'ESCALATING' ? <AlertTriangle size={17} /> : <ShieldCheck size={17} />}
        <div><strong>{verdict}</strong><span>{n} captured reaction{n === 1 ? '' : 's'} · confidence {pct(confidence)}{full ? ' · full backend aggregate' : ' · visible-row aggregate'}</span></div>
      </div>

      <div className="reaction-grid">
        <div className="reaction-metric"><MessageCircle size={15} /><span>Comments / replies</span><strong>{n}</strong><small>linked to this conversation</small></div>
        <div className="reaction-metric"><Users2 size={15} /><span>Negative / positive</span><strong>{pct(negativeShare)} / {pct(positiveShare)}</strong><small>comment sentiment distribution</small></div>
        <div className="reaction-metric"><span>STANCE</span><strong>{pct(againstShare)} against</strong><small>{pct(supportiveShare)} supportive</small></div>
        <div className="reaction-metric"><span>EMOTION</span><strong>{pct(Math.max(anger, anxiety))}</strong><small>max anger/anxiety signal</small></div>
      </div>

      {n > 0 ? (
        <>
          <div className="reaction-bars">
            <div><span>Negative</span><i><b style={{ width: pct(negativeShare) }} /></i><strong>{pct(negativeShare)}</strong></div>
            <div><span>Positive</span><i><b style={{ width: pct(positiveShare) }} /></i><strong>{pct(positiveShare)}</strong></div>
            <div><span>Against stance</span><i><b style={{ width: pct(againstShare) }} /></i><strong>{pct(againstShare)}</strong></div>
            <div><span>Sarcasm</span><i><b style={{ width: pct(sarcasm) }} /></i><strong>{pct(sarcasm)}</strong></div>
          </div>
          {flags.length > 0 && <div className="reaction-flags">{flags.map((flag) => <span key={flag}>{flag.replaceAll('-', ' ')}</span>)}</div>}
          <div className="reaction-samples">
            {local.reactions.slice(0, 5).map((reaction) => (
              <div key={reaction.id}>
                <div><strong>{reaction.author_display || reaction.author_pseudo_id || 'Unknown author'}</strong><span>{reaction.sentiment_label || 'unknown'} · {reaction.stance_label || 'unclear'} · {reaction.source_mode}</span></div>
                <p>{reaction.text}</p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="reaction-empty"><ShieldCheck size={15} /><span>No comments/replies are currently linked to this evidence item. NEXUS will not infer public opinion from the root post alone. The provider-state message above explains whether comments were disabled, unavailable, or simply not requested by the selected connector.</span></div>
      )}

      <div className="reaction-trust"><ShieldCheck size={14} /> The score is evidence-bounded and descriptive. It indicates reaction direction/attention in collected comments, not wrongdoing, intent, or absolute internet-wide opinion.</div>
    </section>
  );
}
