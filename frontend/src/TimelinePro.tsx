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

function useChartTheme() {
  const read = () => document.documentElement.dataset.theme === 'dark' ? DARK : LIGHT;
  const [colors, setColors] = useState<ThemeColors>(read);

  useEffect(() => {
    const observer = new MutationObserver(() => setColors(read()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  return colors;
}

function bucketEvents(events: SocialEvent[], minutes = 15): RichTimelinePoint[] {
  const buckets = new Map<number, SocialEvent[]>();
  const size = minutes * 60 * 1000;
  for (const event of events) {
    const time = new Date(event.created_at).getTime();
    if (!Number.isFinite(time)) continue;
    const key = Math.floor(time / size) * size;
    const group = buckets.get(key) || [];
    group.push(event);
    buckets.set(key, group);
  }

  return [...buckets.entries()]
    .sort(([a], [b]) => a - b)
    .map(([time, group]) => {
      const sentiments: Record<string, number> = {};
      const platforms: Record<string, number> = {};
      const stances: Record<string, number> = {};
      const emotions: Record<string, number> = { anxiety: 0, anger: 0, excitement: 0, sadness: 0, joy: 0, disgust: 0, surprise: 0, trust: 0 };
      let reactionCount = 0;
      let sarcasm = 0;
      for (const event of group) {
        const sentiment = event.sentiment_label || 'unknown';
        sentiments[sentiment] = (sentiments[sentiment] || 0) + 1;
        platforms[event.platform] = (platforms[event.platform] || 0) + 1;
        const reaction = Boolean(event.parent_event_id) || /comment|reply|response/.test((event.event_type || '').toLowerCase());
        if (reaction) {
          reactionCount += 1;
          const stance = event.stance_label || 'unclear';
          stances[stance] = (stances[stance] || 0) + 1;
        }
        sarcasm += Number(event.sarcasm_probability || 0);
        for (const key of Object.keys(emotions)) emotions[key] += Number(event.emotion_scores?.[key] || 0);
      }
      for (const key of Object.keys(emotions)) emotions[key] = group.length ? emotions[key] / group.length : 0;
      return {
        time: new Date(time).toISOString(),
        count: group.length,
        sentiments,
        platforms,
        reaction_count: reactionCount,
        root_count: group.length - reactionCount,
        stance: stances,
        supportive_share: reactionCount ? (stances.supportive || 0) / reactionCount : 0,
        against_share: reactionCount ? (stances.against || 0) / reactionCount : 0,
        sarcasm_mean: group.length ? sarcasm / group.length : 0,
        emotions,
      };
    });
}

function compactTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function fullTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

export default function TimelinePro({ points, events }: Props) {
  const colors = useChartTheme();
  const fallback = useMemo(() => bucketEvents(events), [events]);
  const effectivePoints = (points.length ? points : fallback) as RichTimelinePoint[];
  const usedFallback = points.length === 0 && fallback.length > 0;

  const data = useMemo(() => effectivePoints.map((point) => ({
    rawTime: point.time,
    time: compactTime(point.time),
    count: point.count,
    positive: point.sentiments.positive || 0,
    negative: point.sentiments.negative || 0,
    neutral: point.sentiments.neutral || 0,
    reactions: point.reaction_count || 0,
    supportive: Math.round(Number(point.supportive_share || 0) * 100),
    against: Math.round(Number(point.against_share || 0) * 100),
    sarcasm: Math.round(Number(point.sarcasm_mean || 0) * 100),
    anxiety: Math.round(Number(point.emotions?.anxiety || 0) * 100),
    anger: Math.round(Number(point.emotions?.anger || 0) * 100),
    excitement: Math.round(Number(point.emotions?.excitement || 0) * 100),
    joy: Math.round(Number(point.emotions?.joy || 0) * 100),
    trust: Math.round(Number(point.emotions?.trust || 0) * 100),
    platforms: point.platforms,
  })), [effectivePoints]);

  const total = data.reduce((sum, row) => sum + row.count, 0);
  const totalReactions = data.reduce((sum, row) => sum + row.reactions, 0);
  const peak = data.reduce((best, row) => row.count > best.count ? row : best, data[0] || { count: 0, time: '—', rawTime: '' });
  const platformSet = new Set(effectivePoints.flatMap((point) => Object.keys(point.platforms || {})));

  if (!data.length) {
    return (
      <section className="analysis-empty panel panel-large">
        <div className="analysis-empty-icon"><Clock3 size={26} /></div>
        <h2>No timeline evidence yet</h2>
        <p>Run Fresh Search, add a live source, or load the deterministic demo. The timeline will render as soon as at least one timestamped event is present.</p>
        <div className="analysis-empty-note"><ShieldCheck size={15} /> Timeline uses source timestamps, not browser arrival time.</div>
      </section>
    );
  }

  return (
    <div className="timeline-pro">
      <div className="analysis-summary-grid timeline-summary-grid">
        <div className="analysis-summary-card"><Database size={17} /><span>Events in timeline</span><strong>{total}</strong><small>{usedFallback ? 'rebuilt locally from evidence events' : 'backend timeline buckets'}</small></div>
        <div className="analysis-summary-card"><MessageCircle size={17} /><span>Audience reactions</span><strong>{totalReactions}</strong><small>comments / replies linked to chronology</small></div>
        <div className="analysis-summary-card"><Activity size={17} /><span>Peak bucket</span><strong>{peak.count}</strong><small>{peak.rawTime ? fullTime(peak.rawTime) : '—'}</small></div>
        <div className="analysis-summary-card"><Layers3 size={17} /><span>Platforms</span><strong>{platformSet.size}</strong><small>{data.length} timestamped 15-minute windows</small></div>
      </div>

      <section className="panel panel-large timeline-chart-card">
        <div className="analysis-section-head">
          <div><span className="eyebrow">Exact chronology</span><h2>Conversation volume & sentiment movement</h2><p>Volume bars and polarity lines preserve the chronology of the collected dataset.</p></div>
          <div className="timeline-legend" aria-label="Timeline legend">
            <span><i style={{ background: colors.volume }} />Volume</span>
            <span><i style={{ background: colors.positive }} />Positive</span>
            <span><i style={{ background: colors.negative }} />Negative</span>
            <span><i style={{ background: colors.neutral }} />Neutral</span>
          </div>
        </div>

        <div className="timeline-chart-shell">
          <ResponsiveContainer width="100%" height={390}>
            <ComposedChart data={data} margin={{ top: 18, right: 18, bottom: 8, left: 0 }}>
              <CartesianGrid stroke={colors.grid} strokeDasharray="4 6" vertical={false} />
              <XAxis dataKey="time" stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={{ stroke: colors.grid }} minTickGap={28} />
              <YAxis yAxisId="left" allowDecimals={false} stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={false} width={34} />
              <Tooltip cursor={{ fill: `${colors.volume}12` }} contentStyle={{ background: colors.tooltipBg, color: colors.text, border: `1px solid ${colors.tooltipBorder}`, borderRadius: 14, boxShadow: '0 16px 42px rgba(15,23,42,.14)' }} labelStyle={{ color: colors.text, fontWeight: 800, marginBottom: 6 }} />
              <Bar yAxisId="left" dataKey="count" name="Volume" fill={colors.volume} radius={[7, 7, 2, 2]} maxBarSize={42} minPointSize={5} opacity={0.78} />
              <Line yAxisId="left" type="monotone" dataKey="positive" name="Positive" stroke={colors.positive} strokeWidth={2.5} dot={{ r: 3, fill: colors.positive, strokeWidth: 0 }} activeDot={{ r: 5 }} />
              <Line yAxisId="left" type="monotone" dataKey="negative" name="Negative" stroke={colors.negative} strokeWidth={2.5} dot={{ r: 3, fill: colors.negative, strokeWidth: 0 }} activeDot={{ r: 5 }} />
              <Line yAxisId="left" type="monotone" dataKey="neutral" name="Neutral" stroke={colors.neutral} strokeWidth={2} strokeDasharray="5 5" dot={{ r: 2.5, fill: colors.neutral, strokeWidth: 0 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel panel-large timeline-chart-card">
        <div className="analysis-section-head">
          <div><span className="eyebrow">SIH26152 · multi-dimensional sentiment</span><h2>Emotion, stance & sarcasm fluctuation</h2><p>Nuanced audience signals are mapped to the same source-timestamped timeline instead of being shown only as one overall score.</p></div>
          <div className="timeline-legend"><span><i style={{ background: '#f97316' }} />Anger</span><span><i style={{ background: colors.negative }} />Anxiety</span><span><i style={{ background: colors.positive }} />Excitement</span><span><i style={{ background: '#7c3aed' }} />Supportive</span><span><i style={{ background: '#dc2626' }} />Against</span><span><i style={{ background: colors.neutral }} />Sarcasm</span></div>
        </div>
        <div className="timeline-chart-shell">
          <ResponsiveContainer width="100%" height={360}>
            <ComposedChart data={data} margin={{ top: 18, right: 18, bottom: 8, left: 0 }}>
              <CartesianGrid stroke={colors.grid} strokeDasharray="4 6" vertical={false} />
              <XAxis dataKey="time" stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={{ stroke: colors.grid }} minTickGap={28} />
              <YAxis domain={[0, 100]} unit="%" stroke={colors.text} tick={{ fill: colors.text, fontSize: 11 }} tickLine={false} axisLine={false} width={42} />
              <Tooltip formatter={(value: number | string) => [`${value}%`]} contentStyle={{ background: colors.tooltipBg, color: colors.text, border: `1px solid ${colors.tooltipBorder}`, borderRadius: 14 }} />
              <Line type="monotone" dataKey="anger" name="Anger" stroke="#f97316" strokeWidth={2.2} dot={false} />
              <Line type="monotone" dataKey="anxiety" name="Anxiety" stroke={colors.negative} strokeWidth={2.2} dot={false} />
              <Line type="monotone" dataKey="excitement" name="Excitement" stroke={colors.positive} strokeWidth={2.2} dot={false} />
              <Line type="monotone" dataKey="supportive" name="Supportive stance" stroke="#7c3aed" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="against" name="Against stance" stroke="#dc2626" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="sarcasm" name="Sarcasm" stroke={colors.neutral} strokeWidth={1.8} strokeDasharray="5 5" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="analysis-trust-note"><ShieldCheck size={16} /><span>Emotion/stance lines are descriptive NLP signals within collected posts/comments. They are not clinical, identity, intent or wrongdoing classifications.</span></div>
      </section>

      <section className="panel timeline-bucket-card">
        <div className="analysis-section-head compact"><div><span className="eyebrow">Bucket detail</span><h3>Recent chronology</h3></div><span className="analysis-count-pill">{Math.min(12, data.length)} shown</span></div>
        <div className="timeline-bucket-list">
          {data.slice(-12).reverse().map((row) => (
            <div className="timeline-bucket-row" key={row.rawTime}>
              <time>{fullTime(row.rawTime)}</time>
              <strong>{row.count} event{row.count === 1 ? '' : 's'} · {row.reactions} reactions</strong>
              <div className="timeline-mini-sentiments"><span className="positive">+ {row.positive}</span><span className="negative">− {row.negative}</span><span className="neutral">• {row.neutral}</span></div>
              <div className="timeline-platform-mini">{Object.entries(row.platforms || {}).map(([platform, count]) => <span key={platform}>{platform} {count}</span>)}</div>
            </div>
          ))}
        </div>
        <div className="analysis-trust-note"><ShieldCheck size={16} /><span>{usedFallback ? 'Backend timeline returned no points, so NEXUS reconstructed the same chronology from collected evidence without inventing events.' : 'Exact source timestamps are preserved separately from ingestion time. Zero-volume chart padding never becomes synthetic evidence.'}</span></div>
      </section>
    </div>
  );
}
