import { useEffect, useMemo, useState } from 'react';
import { Activity, GitBranch, Layers3, ShieldCheck } from 'lucide-react';
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
import type { NarrativeDetail } from './api';
import './narrative-graph.css';

type Props = {
  detail: NarrativeDetail;
};

type Bucket = {
  time: string;
  rawTime: number;
  newEvidence: number;
  cumulative: number;
  positive: number;
  negative: number;
  neutral: number;
};

type ChartTheme = {
  accent: string;
  positive: string;
  negative: string;
  neutral: string;
  grid: string;
  text: string;
  surface: string;
};

const LIGHT: ChartTheme = {
  accent: '#4f7cff',
  positive: '#16a879',
  negative: '#e05263',
  neutral: '#8b97a9',
  grid: '#dce3ee',
  text: '#64748b',
  surface: '#ffffff',
};

const DARK: ChartTheme = {
  accent: '#7aa2ff',
  positive: '#57d7ad',
  negative: '#ff8998',
  neutral: '#95a3b8',
  grid: '#2b3547',
  text: '#9aa8bb',
  surface: '#171e29',
};

function useChartTheme(): ChartTheme {
  const read = () => document.documentElement.dataset.theme === 'dark' ? DARK : LIGHT;
  const [theme, setTheme] = useState<ChartTheme>(read);

  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(read()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });
    return () => observer.disconnect();
  }, []);

  return theme;
}

function chooseBucketMs(timestamps: number[]): number {
  if (timestamps.length < 2) return 15 * 60 * 1000;
  const span = Math.max(...timestamps) - Math.min(...timestamps);
  if (span <= 2 * 60 * 60 * 1000) return 10 * 60 * 1000;
  if (span <= 24 * 60 * 60 * 1000) return 60 * 60 * 1000;
  if (span <= 7 * 24 * 60 * 60 * 1000) return 6 * 60 * 60 * 1000;
  return 24 * 60 * 60 * 1000;
}

function labelForTime(timestamp: number, bucketMs: number): string {
  const date = new Date(timestamp);
  if (bucketMs >= 24 * 60 * 60 * 1000) {
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }
  if (bucketMs >= 6 * 60 * 60 * 1000) {
    return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit' });
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function buildBuckets(detail: NarrativeDetail): Bucket[] {
  const valid = detail.lineage
    .map((item) => ({ item, ts: new Date(item.created_at).getTime() }))
    .filter((row) => Number.isFinite(row.ts))
    .sort((a, b) => a.ts - b.ts);

  if (!valid.length) return [];

  const bucketMs = chooseBucketMs(valid.map((row) => row.ts));
  const buckets = new Map<number, { count: number; positive: number; negative: number; neutral: number }>();

  for (const { item, ts } of valid) {
    const key = Math.floor(ts / bucketMs) * bucketMs;
    const bucket = buckets.get(key) || { count: 0, positive: 0, negative: 0, neutral: 0 };
    bucket.count += 1;
    const sentiment = String(item.sentiment || 'neutral').toLowerCase();
    if (sentiment === 'positive') bucket.positive += 1;
    else if (sentiment === 'negative') bucket.negative += 1;
    else bucket.neutral += 1;
    buckets.set(key, bucket);
  }

  let cumulative = 0;
  return [...buckets.entries()]
    .sort(([a], [b]) => a - b)
    .map(([timestamp, bucket]) => {
      cumulative += bucket.count;
      return {
        time: labelForTime(timestamp, bucketMs),
        rawTime: timestamp,
        newEvidence: bucket.count,
        cumulative,
        positive: bucket.positive,
        negative: bucket.negative,
        neutral: bucket.neutral,
      };
    });
}

export default function NarrativeGraph({ detail }: Props) {
  const theme = useChartTheme();
  const data = useMemo(() => buildBuckets(detail), [detail]);
  const sparse = data.length <= 4;
  const total = detail.lineage.length;
  const platforms = Object.keys(detail.platform_mix || {}).length;
  const first = detail.lineage[0]?.created_at;
  const last = detail.lineage[detail.lineage.length - 1]?.created_at;

  if (!data.length) {
    return (
      <section className="narrative-graph-empty">
        <GitBranch size={22} />
        <strong>No timestamped lineage points yet</strong>
        <span>The evidence cards remain available below.</span>
      </section>
    );
  }

  return (
    <section className="narrative-graph-block" aria-label="Narrative propagation graph">
      <div className="narrative-graph-head">
        <div>
          <span className="eyebrow">Narrative propagation graph</span>
          <h3>How this narrative accumulated across the observed timeline</h3>
          <p>Bars show new evidence in each time bucket. The cumulative line shows observed narrative growth; sentiment lines show positive, negative and neutral evidence movement.</p>
        </div>
        <div className="narrative-graph-kpis">
          <span><Activity size={13} /><b>{total}</b> evidence</span>
          <span><Layers3 size={13} /><b>{platforms}</b> platforms</span>
        </div>
      </div>

      <div className="narrative-graph-shell">
        <ResponsiveContainer width="100%" height={360} minWidth={280}>
          <ComposedChart data={data} margin={{ top: 18, right: 20, bottom: 12, left: 0 }}>
            <CartesianGrid stroke={theme.grid} strokeDasharray="4 6" vertical={false} />
            <XAxis dataKey="time" tick={{ fill: theme.text, fontSize: 10 }} tickLine={false} axisLine={{ stroke: theme.grid }} minTickGap={24} />
            <YAxis allowDecimals={false} tick={{ fill: theme.text, fontSize: 10 }} tickLine={false} axisLine={false} width={38} />
            <Tooltip
              contentStyle={{ background: theme.surface, color: theme.text, border: `1px solid ${theme.grid}`, borderRadius: 12 }}
              labelStyle={{ color: theme.text, fontWeight: 800 }}
            />
            <Bar isAnimationActive={false} dataKey="newEvidence" name="New evidence" fill={theme.accent} opacity={0.35} radius={[6, 6, 2, 2]} minPointSize={5} maxBarSize={38} />
            <Line isAnimationActive={false} type="monotone" dataKey="cumulative" name="Cumulative evidence" stroke={theme.accent} strokeWidth={3} dot={sparse ? { r: 4, fill: theme.accent, strokeWidth: 0 } : false} activeDot={{ r: 5 }} />
            <Line isAnimationActive={false} type="monotone" dataKey="positive" name="Positive evidence" stroke={theme.positive} strokeWidth={2} dot={sparse ? { r: 3, fill: theme.positive, strokeWidth: 0 } : false} activeDot={{ r: 4 }} />
            <Line isAnimationActive={false} type="monotone" dataKey="negative" name="Negative evidence" stroke={theme.negative} strokeWidth={2} dot={sparse ? { r: 3, fill: theme.negative, strokeWidth: 0 } : false} activeDot={{ r: 4 }} />
            <Line isAnimationActive={false} type="monotone" dataKey="neutral" name="Neutral evidence" stroke={theme.neutral} strokeWidth={1.8} strokeDasharray="5 5" dot={sparse ? { r: 3, fill: theme.neutral, strokeWidth: 0 } : false} activeDot={{ r: 4 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="narrative-graph-foot">
        <ShieldCheck size={14} />
        <span>{first && last ? `Observed chronology: ${new Date(first).toLocaleString()} → ${new Date(last).toLocaleString()}. ` : ''}This graph describes only the collected dataset; it does not claim the narrative's global origin.</span>
      </div>
    </section>
  );
}
