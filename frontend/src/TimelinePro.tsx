import { useEffect, useMemo, useState } from 'react';
import { Activity, Clock3, Database, Layers3, MessageCircle, ShieldCheck } from 'lucide-react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { SocialEvent, TimelinePoint } from './api';

type Props = {
  points: TimelinePoint[];
  events: SocialEvent[];
};

type RichTimelinePoint = TimelinePoint & {
  reaction_count?: number;
  root_count?: number;
  stance?: Record<string, number>;
  supportive_share?: number;
  against_share?: number;
  sarcasm_mean?: number;
  emotions?: Record<string, number>;
};

type TimelineRow = {
  rawTime: string;
  time: string;
  count: number;
  positive: number;
  negative: number;
  neutral: number;
  reactions: number;
  supportive: number;
  against: number;
  sarcasm: number;
  anxiety: number;
  anger: number;
  excitement: number;
  sadness: number;
  joy: number;
  disgust: number;
  surprise: number;
  trust: number;
  platforms: Record<string, number>;
};

type ThemeColors = {
  volume: string;
  positive: string;
  negative: string;
  neutral: string;
  grid: string;
  text: string;
  tooltipBg: string;
  tooltipBorder: string;
};

const LIGHT: ThemeColors = {
  volume: '#4f7cff',
  positive: '#16a879',
  negative: '#e05263',
  neutral: '#8b97a9',
  grid: '#dce3ee',
  text: '#64748b',
  tooltipBg: '#ffffff',
  tooltipBorder: '#dce3ee',
};

const DARK: ThemeColors = {
  volume: '#7aa2ff',
  positive: '#57d7ad',
  negative: '#ff8998',
  neutral: '#95a3b8',
  grid: '#2b3547',
  text: '#9aa8bb',
  tooltipBg: '#171e29',
  tooltipBorder: '#344155',
};

const EMOTION_LINES = [
  ['anxiety', '#e05263'],
  ['anger', '#f97316'],
  ['excitement', '#16a879'],
  ['sadness', '#64748b'],
  ['joy', '#22c55e'],
  ['disgust', '#7c3aed'],
  ['surprise', '#0ea5e9'],
  ['trust', '#2563eb'],
] as const;

function useChartTheme(): ThemeColors {
  const read = () => document.documentElement.dataset.theme === 'dark' ? DARK : LIGHT;
  const [colors, setColors] = useState<ThemeColors>(read);

  useEffect(() => {
    const observer = new MutationObserver(() => setColors(read()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });
    return () => observer.disconnect();
  }, []);

  return colors;
}

function isReaction(event: SocialEvent): boolean {
  const eventType = String(event.event_type || '').toLowerCase();
  return Boolean(event.parent_event_id)
    || eventType.includes('comment')
    || eventType.includes('reply')
    || eventType.includes('response');
}

function bucketEvents(events: SocialEvent[], minutes = 15): RichTimelinePoint[] {
  const bucketSize = minutes * 60 * 1000;
  const buckets = new Map<number, SocialEvent[]>();

  for (const event of events) {
    const timestamp = new Date(event.created_at).getTime();
    if (!Number.isFinite(timestamp)) continue;
    const key = Math.floor(timestamp / bucketSize) * bucketSize;
    const group = buckets.get(key) || [];
    group.push(event);
    buckets.set(key, group);
  }

  return [...buckets.entries()]
    .sort(([left], [right]) => left - right)
    .map(([timestamp, group]) => {
      const sentiments: Record<string, number> = {};
      const platforms: Record<string, number> = {};
      const stances: Record<string, number> = {};
      const emotionTotals: Record<string, number> = Object.fromEntries(
        EMOTION_LINES.map(([label]) => [label, 0]),
      );
      let reactionCount = 0;
      let sarcasmTotal = 0;

      for (const event of group) {
        const sentiment = event.sentiment_label || 'neutral';
        sentiments[sentiment] = (sentiments[sentiment] || 0) + 1;
        platforms[event.platform] = (platforms[event.platform] || 0) + 1;

        if (isReaction(event)) {
          reactionCount += 1;
          const stance = event.stance_label || 'unclear';
          stances[stance] = (stances[stance] || 0) + 1;
        }

        sarcasmTotal += Number(event.sarcasm_probability || 0);
        for (const [label] of EMOTION_LINES) {
          emotionTotals[label] += Number(event.emotion_scores?.[label] || 0);
        }
      }

      const emotions: Record<string, number> = {};
      for (const [label] of EMOTION_LINES) {
        emotions[label] = group.length ? emotionTotals[label] / group.length : 0;
      }

      return {
        time: new Date(timestamp).toISOString(),
        count: group.length,
        sentiments,
        platforms,
        reaction_count: reactionCount,
        root_count: group.length - reactionCount,
        stance: stances,
        supportive_share: reactionCount ? (stances.supportive || 0) / reactionCount : 0,
        against_share: reactionCount ? (stances.against || 0) / reactionCount : 0,
        sarcasm_mean: group.length ? sarcasmTotal / group.length : 0,
        emotions,
      };
    });
}

function compactTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function fullTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

function toRows(points: RichTimelinePoint[]): TimelineRow[] {
  return points.map((point) => ({
    rawTime: point.time,
    time: compactTime(point.time),
    count: Number(point.count || 0),
    positive: Number(point.sentiments?.positive || 0),
    negative: Number(point.sentiments?.negative || 0),
    neutral: Number(point.sentiments?.neutral || 0),
    reactions: Number(point.reaction_count || 0),
    supportive: Math.round(Number(point.supportive_share || 0) * 100),
    against: Math.round(Number(point.against_share || 0) * 100),
    sarcasm: Math.round(Number(point.sarcasm_mean || 0) * 100),
    anxiety: Math.round(Number(point.emotions?.anxiety || 0) * 100),
    anger: Math.round(Number(point.emotions?.anger || 0) * 100),
    excitement: Math.round(Number(point.emotions?.excitement || 0) * 100),
    sadness: Math.round(Number(point.emotions?.sadness || 0) * 100),
    joy: Math.round(Number(point.emotions?.joy || 0) * 100),
    disgust: Math.round(Number(point.emotions?.disgust || 0) * 100),
    surprise: Math.round(Number(point.emotions?.surprise || 0) * 100),
    trust: Math.round(Number(point.emotions?.trust || 0) * 100),
    platforms: point.platforms || {},
  }));
}

export default function TimelinePro({ points, events }: Props) {
  const colors = useChartTheme();
  const fallback = useMemo(() => bucketEvents(events), [events]);
  const backendHasObservedVolume = points.some((point) => Number(point.count || 0) > 0);
  const effectivePoints = (backendHasObservedVolume ? points : fallback) as RichTimelinePoint[];
  const usedFallback = !backendHasObservedVolume && fallback.length > 0;
  const data = useMemo(() => toRows(effectivePoints), [effectivePoints]);
  const sparse = data.length <= 4;

  const total = data.reduce((sum, row) => sum + row.count, 0);
  const totalReactions = data.reduce((sum, row) => sum + row.reactions, 0);
  const peak = data.reduce(
    (best, row) => row.count > best.count ? row : best,
    data[0] || {
      rawTime: '', time: '—', count: 0, positive: 0, negative: 0, neutral: 0,
      reactions: 0, supportive: 0, against: 0, sarcasm: 0, anxiety: 0, anger: 0,
      excitement: 0, sadness: 0, joy: 0, disgust: 0, surprise: 0, trust: 0, platforms: {},
    },
  );
  const platformSet = new Set(
    effectivePoints.flatMap((point) => Object.keys(point.platforms || {})),
  );

  if (!data.length || total <= 0) {
    return (
      <section className="analysis-empty panel panel-large">
        <div className="analysis-empty-icon"><Clock3 size={26} /></div>
        <h2>No timeline evidence yet</h2>
        <p>Run Fresh Search, add a live source, or load Demo. NEXUS renders the timeline as soon as timestamped evidence exists.</p>
        <div className="analysis-empty-note"><ShieldCheck size={15} /> Timeline uses source timestamps, not browser arrival time.</div>
      </section>
    );
  }

  return (
    <div className="timeline-pro">
      <div className="analysis-summary-grid timeline-summary-grid">
        <div className="analysis-summary-card"><Database size={17} /><span>Events in timeline</span><strong>{total}</strong><small>{usedFallback ? 'rebuilt directly from evidence events' : 'backend timeline buckets'}</small></div>
        <div className="analysis-summary-card"><MessageCircle size={17} /><span>Audience reactions</span><strong>{totalReactions}</strong><small>comments / replies linked to chronology</small></div>
        <div className="analysis-summary-card"><Activity size={17} /><span>Peak bucket</span><strong>{peak.count}</strong><small>{peak.rawTime ? fullTime(peak.rawTime) : '—'}</small></div>
        <div className="analysis-summary-card"><Layers3 size={17} /><span>Platforms</span><strong>{platformSet.size}</strong><small>{data.length} timestamped 15-minute windows</small></div>
      </div>

      <section className="panel panel-large timeline-chart-card">
        <div className="analysis-section-head">
          <div><span className="eyebrow">Exact chronology</span><h2>Conversation volume & sentiment movement</h2><p>Volume bars and polarity lines preserve the chronology of collected evidence. Sparse searches show visible point markers.</p></div>
          <div className="timeline-legend" aria-label="Timeline legend"><span><i style={{ background: colors.volume }} />Volume</span><span><i style={{ background: colors.positive }} />Positive</span><span><i style={{ background: colors.negative }} />Negative</span><span><i style={{ background: colors.neutral }} />Neutral</span></div>
        </div>
        <div className="timeline-chart-shell">
          <ResponsiveContainer width="100%" height={390} minWidth={280}>
            <ComposedChart data={data} margin={{ top: 18, right: 18, bottom: 8, left: 0 }}>
              <CartesianGrid stroke={colors.grid} strokeDasharray="4 6" vertical={false} />
              <XAxis dataKey="time" stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={{ stroke: colors.grid }} minTickGap={28} />
              <YAxis allowDecimals={false} stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={false} width={34} />
              <Tooltip contentStyle={{ background: colors.tooltipBg, color: colors.text, border: `1px solid ${colors.tooltipBorder}`, borderRadius: 14 }} />
              <Bar isAnimationActive={false} dataKey="count" name="Volume" fill={colors.volume} radius={[7, 7, 2, 2]} maxBarSize={42} minPointSize={5} opacity={0.78} />
              <Line isAnimationActive={false} type="monotone" dataKey="positive" name="Positive" stroke={colors.positive} strokeWidth={2.5} dot={sparse ? { r: 4, fill: colors.positive, strokeWidth: 0 } : false} activeDot={{ r: 5 }} />
              <Line isAnimationActive={false} type="monotone" dataKey="negative" name="Negative" stroke={colors.negative} strokeWidth={2.5} dot={sparse ? { r: 4, fill: colors.negative, strokeWidth: 0 } : false} activeDot={{ r: 5 }} />
              <Line isAnimationActive={false} type="monotone" dataKey="neutral" name="Neutral" stroke={colors.neutral} strokeWidth={2} strokeDasharray="5 5" dot={sparse ? { r: 3.5, fill: colors.neutral, strokeWidth: 0 } : false} activeDot={{ r: 5 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel panel-large timeline-chart-card">
        <div className="analysis-section-head"><div><span className="eyebrow">SIH26152 · multi-dimensional sentiment</span><h2>Eight-emotion movement</h2><p>Anxiety, anger, excitement, sadness, joy, disgust, surprise and trust over the same source-timestamped chronology.</p></div></div>
        <div className="timeline-chart-shell">
          <ResponsiveContainer width="100%" height={370} minWidth={280}>
            <ComposedChart data={data} margin={{ top: 18, right: 18, bottom: 8, left: 0 }}>
              <CartesianGrid stroke={colors.grid} strokeDasharray="4 6" vertical={false} />
              <XAxis dataKey="time" stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={{ stroke: colors.grid }} minTickGap={28} />
              <YAxis domain={[0, 100]} stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={false} width={38} />
              <Tooltip contentStyle={{ background: colors.tooltipBg, color: colors.text, border: `1px solid ${colors.tooltipBorder}`, borderRadius: 14 }} />
              {EMOTION_LINES.map(([label, stroke]) => (
                <Line key={label} isAnimationActive={false} type="monotone" dataKey={label} name={label.charAt(0).toUpperCase() + label.slice(1)} stroke={stroke} strokeWidth={2} dot={sparse ? { r: 3.5, fill: stroke, strokeWidth: 0 } : false} activeDot={{ r: 5 }} />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel panel-large timeline-chart-card">
        <div className="analysis-section-head"><div><span className="eyebrow">SIH26152 · audience direction</span><h2>Emotion, stance & sarcasm fluctuation</h2><p>Supportive/against stance and sarcasm stay separate from raw positive/negative polarity.</p></div></div>
        <div className="timeline-chart-shell">
          <ResponsiveContainer width="100%" height={320} minWidth={280}>
            <ComposedChart data={data} margin={{ top: 18, right: 18, bottom: 8, left: 0 }}>
              <CartesianGrid stroke={colors.grid} strokeDasharray="4 6" vertical={false} />
              <XAxis dataKey="time" stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={{ stroke: colors.grid }} minTickGap={28} />
              <YAxis domain={[0, 100]} stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={false} width={38} />
              <Tooltip contentStyle={{ background: colors.tooltipBg, color: colors.text, border: `1px solid ${colors.tooltipBorder}`, borderRadius: 14 }} />
              <Line isAnimationActive={false} type="monotone" dataKey="supportive" name="Supportive stance %" stroke="#7c3aed" strokeWidth={2.2} dot={sparse ? { r: 4, fill: '#7c3aed', strokeWidth: 0 } : false} activeDot={{ r: 5 }} />
              <Line isAnimationActive={false} type="monotone" dataKey="against" name="Against stance %" stroke="#dc2626" strokeWidth={2.2} dot={sparse ? { r: 4, fill: '#dc2626', strokeWidth: 0 } : false} activeDot={{ r: 5 }} />
              <Line isAnimationActive={false} type="monotone" dataKey="sarcasm" name="Sarcasm %" stroke={colors.neutral} strokeWidth={2} strokeDasharray="5 5" dot={sparse ? { r: 3.5, fill: colors.neutral, strokeWidth: 0 } : false} activeDot={{ r: 5 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="analysis-trust-note"><ShieldCheck size={16} /><span>Emotion/stance lines are descriptive NLP signals within collected evidence. They are not clinical, identity, intent or wrongdoing classifications.</span></div>
      </section>

      <section className="panel timeline-bucket-card">
        <div className="analysis-section-head compact"><div><span className="eyebrow">Bucket detail</span><h3>Recent chronology</h3></div><span className="analysis-count-pill">{Math.min(12, data.length)} shown</span></div>
        <div className="timeline-bucket-list">
          {data.slice(-12).reverse().map((row) => (
            <div className="timeline-bucket-row" key={row.rawTime}>
              <time>{fullTime(row.rawTime)}</time>
              <strong>{row.count} event{row.count === 1 ? '' : 's'} · {row.reactions} reactions</strong>
              <div className="timeline-mini-sentiments"><span className="positive">+ {row.positive}</span><span className="negative">− {row.negative}</span><span className="neutral">• {row.neutral}</span></div>
              <div className="timeline-platform-mini">{Object.entries(row.platforms).map(([platform, count]) => <span key={platform}>{platform} {count}</span>)}</div>
            </div>
          ))}
        </div>
        <div className="analysis-trust-note"><ShieldCheck size={16} /><span>{usedFallback ? 'Backend timeline had no observed-volume buckets, so NEXUS rebuilt the chronology directly from collected evidence without inventing events.' : 'Exact source timestamps are preserved separately from ingestion time.'}</span></div>
      </section>
    </div>
  );
}
