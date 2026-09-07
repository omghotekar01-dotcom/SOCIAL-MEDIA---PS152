import { ExternalLink, Hash, MessageCircle, Play, Radio, ShieldCheck, UserRound } from 'lucide-react';
import type { SocialEvent } from './api';

type Props = {
  events: SocialEvent[];
  selectedId?: string | null;
  onSelect: (event: SocialEvent) => void;
};

const safeString = (value: unknown) => typeof value === 'string' && value.startsWith('http') ? value : '';

function profileValue(event: SocialEvent, key: string): string {
  return safeString(event.public_profile?.[key]);
}

function initials(value?: string | null) {
  const clean = (value || '?').replace(/^@/, '').trim();
  const parts = clean.split(/\s+/).filter(Boolean);
  return (parts.length > 1 ? `${parts[0][0]}${parts[1][0]}` : clean.slice(0, 2)).toUpperCase();
}

function youtubeVideoId(event: SocialEvent): string {
  if (event.platform !== 'youtube') return '';
  const explicit = String(event.public_profile?.video_id || event.conversation_id || '').trim();
  if (explicit) return explicit;
  const match = (event.url || '').match(/[?&]v=([^&]+)/);
  return match?.[1] || '';
}

function youtubeEmbed(event: SocialEvent): string {
  const explicit = profileValue(event, 'embed_url');
  if (explicit.includes('youtube.com/embed/')) return explicit;
  const videoId = youtubeVideoId(event);
  return videoId ? `https://www.youtube.com/embed/${encodeURIComponent(videoId)}` : '';
}

function xEmbedDoc(event: SocialEvent): string {
  if (event.platform !== 'x') return '';
  const raw = typeof event.public_profile?.oembed_html === 'string' ? event.public_profile.oembed_html.trim() : '';
  if (!raw) return '';
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>html,body{margin:0;background:#050a12;color:#fff;min-height:100%;display:grid;place-items:center}body{padding:12px;box-sizing:border-box}.twitter-tweet{max-width:550px!important;width:100%!important}</style></head><body>${raw}<script async src="https://platform.x.com/widgets.js" charset="utf-8"></script></body></html>`;
}

function avatarUrl(event: SocialEvent) {
  return profileValue(event, 'avatar_url') || profileValue(event, 'profile_pic_url');
}

function thumbnailUrl(event: SocialEvent) {
  const explicit = profileValue(event, 'thumbnail_url');
  if (explicit) return explicit;
  const videoId = youtubeVideoId(event);
  if (videoId) return `https://i.ytimg.com/vi/${encodeURIComponent(videoId)}/hqdefault.jpg`;
  const media = profileValue(event, 'media_url');
  const mediaKind = String(event.public_profile?.media_kind || '');
  return media && mediaKind !== 'video' ? media : '';
}

function prettyKey(key: string) {
  return key.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function numberValue(value: number | string | null | undefined) {
  if (typeof value === 'number') return value.toLocaleString();
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

function MiniAvatar({ event, large = false }: { event: SocialEvent; large?: boolean }) {
  const avatar = avatarUrl(event);
  const className = large ? 'post-avatar post-avatar-large' : 'post-avatar';
  if (avatar) return <img className={className} src={avatar} alt="" referrerPolicy="no-referrer" />;
  return <div className={`${className} post-avatar-fallback`}>{initials(event.author_display || event.author_pseudo_id)}</div>;
}

function SourcePills({ event }: { event: SocialEvent }) {
  return (
    <div className="post-pill-row">
      <span className={`post-pill post-platform post-platform-${event.platform}`}>{event.platform.toUpperCase()}</span>
      <span className={`post-pill ${event.source_mode === 'LIVE' ? 'post-pill-live' : 'post-pill-replay'}`}>{event.source_mode}</span>
      <span className="post-pill">{event.event_type.replaceAll('_', ' ')}</span>
    </div>
  );
}

export default function PostExplorer({ events, selectedId, onSelect }: Props) {
  const selected = events.find((event) => event.id === selectedId) || events[0] || null;

  if (!selected) {
    return (
      <div className="post-empty">
        <Radio size={30} />
        <h3>No posts in this workspace</h3>
        <p>Run a fresh search or seed the deterministic demo. New searches replace the previous result pool.</p>
      </div>
    );
  }

  const embed = youtubeEmbed(selected);
  const xDoc = xEmbedDoc(selected);
  const thumbnail = thumbnailUrl(selected);
  const avatar = avatarUrl(selected);
  const connector = String(selected.public_profile?.connector || 'unknown');
  const searchQuery = String(selected.public_profile?.search_query || '—');
  const sessionId = String(selected.public_profile?.search_session_id || '—');
  const engagement = Object.entries(selected.engagement || {}).filter(([, value]) => value !== null && value !== undefined);
  const emotions = Object.entries(selected.emotion_scores || {}).filter(([, value]) => Number(value) > 0);

  return (
    <div className="post-explorer">
      <aside className="post-result-rail">
        <div className="post-result-head">
          <div>
            <span>RESULTS</span>
            <strong>{events.length} observed posts</strong>
          </div>
          <ShieldCheck size={17} />
        </div>
        <div className="post-result-list">
          {events.slice(0, 250).map((event) => {
            const thumb = thumbnailUrl(event);
            const isActive = event.id === selected.id;
            return (
              <button key={event.id} className={`post-result-card ${isActive ? 'active' : ''}`} onClick={() => onSelect(event)}>
                <div className="post-result-media">
                  {thumb ? <img src={thumb} alt="" referrerPolicy="no-referrer" /> : <MiniAvatar event={event} />}
                  {event.platform === 'youtube' && <span className="post-play-dot"><Play size={11} fill="currentColor" /></span>}
                </div>
                <div className="post-result-copy">
                  <div className="post-result-top"><span>{event.platform}</span><span>{event.source_mode}</span></div>
                  <strong>{event.author_display || event.author_pseudo_id || 'Unknown author'}</strong>
                  <p>{event.text}</p>
                  <small>{new Date(event.created_at).toLocaleString()}</small>
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      <section className="post-detail-stage">
        <div className="post-media-panel">
          {embed ? (
            <iframe
              className="post-video-frame"
              src={embed}
              title="Selected YouTube evidence"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
            />
          ) : xDoc ? (
            <iframe
              className="post-video-frame"
              srcDoc={xDoc}
              title="Selected X public Post"
              sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
            />
          ) : thumbnail ? (
            <img className="post-main-image" src={thumbnail} alt="Selected post media" referrerPolicy="no-referrer" />
          ) : (
            <div className="post-media-placeholder">
              <div className="post-media-platform">{selected.platform.toUpperCase()}</div>
              <MessageCircle size={40} />
              <span>Source did not expose embeddable media for this event.</span>
            </div>
          )}
        </div>

        <div className="post-primary-card">
          <div className="post-author-row">
            {avatar ? <img className="post-avatar post-avatar-large" src={avatar} alt="" referrerPolicy="no-referrer" /> : <MiniAvatar event={selected} large />}
            <div className="post-author-copy">
              <SourcePills event={selected} />
              <h2>{selected.author_display || selected.author_pseudo_id || 'Unknown author'}</h2>
              <p>{new Date(selected.created_at).toLocaleString()} · language {selected.language || 'unknown'}</p>
            </div>
            {selected.url && !selected.url.includes('example.invalid') && (
              <a className="post-open-source" href={selected.url} target="_blank" rel="noreferrer">
                Open original <ExternalLink size={15} />
              </a>
            )}
          </div>

          <div className="post-text-full">{selected.text}</div>

          {(selected.hashtags.length > 0 || selected.mentions.length > 0) && (
            <div className="post-tag-area">
              {selected.hashtags.map((tag) => <span key={`h-${tag}`}><Hash size={12} />{tag}</span>)}
              {selected.mentions.map((mention) => <span key={`m-${mention}`}><UserRound size={12} />@{mention}</span>)}
            </div>
          )}
        </div>

        <div className="post-metric-grid">
          {engagement.length ? engagement.map(([key, value]) => (
            <div className="post-stat" key={key}><span>{prettyKey(key)}</span><strong>{numberValue(value)}</strong></div>
          )) : <div className="post-stat"><span>Engagement</span><strong>Not exposed</strong></div>}
        </div>

        <div className="post-analysis-grid">
          <section className="post-info-card">
            <div className="post-card-title"><span>AI ANALYSIS</span><strong>Content intelligence</strong></div>
            <div className="post-fact"><span>Sentiment</span><strong>{selected.sentiment_label || 'unknown'} {selected.sentiment_score != null ? `(${selected.sentiment_score.toFixed(3)})` : ''}</strong></div>
            <div className="post-fact"><span>Stance</span><strong>{selected.stance_label || 'unclear'} {selected.stance_confidence != null ? `· ${Math.round(selected.stance_confidence * 100)}%` : ''}</strong></div>
            <div className="post-fact"><span>Sarcasm probability</span><strong>{selected.sarcasm_probability != null ? `${Math.round(selected.sarcasm_probability * 100)}%` : '—'}</strong></div>
            <div className="post-fact"><span>Quality score</span><strong>{selected.quality_score != null ? `${Math.round(selected.quality_score * 100)}%` : '—'}</strong></div>
            <div className="post-fact"><span>Trend score</span><strong>{selected.trend_score != null ? selected.trend_score.toFixed(3) : '—'}</strong></div>
            <div className="post-fact"><span>Narrative</span><strong>{selected.narrative_cluster_id || 'unassigned'}</strong></div>
            {emotions.length > 0 && <div className="post-chip-cloud">{emotions.map(([key, value]) => <span key={key}>{prettyKey(key)} {Math.round(Number(value) * 100)}%</span>)}</div>}
            {selected.topic_terms.length > 0 && <div className="post-chip-cloud">{selected.topic_terms.map((term) => <span key={term}>{term}</span>)}</div>}
          </section>

          <section className="post-info-card">
            <div className="post-card-title"><span>PROVENANCE</span><strong>Source & collection</strong></div>
            <div className="post-fact"><span>Connector</span><strong>{connector}</strong></div>
            <div className="post-fact"><span>Search query</span><strong>{searchQuery}</strong></div>
            <div className="post-fact"><span>Search session</span><strong className="mono-value">{sessionId}</strong></div>
            <div className="post-fact"><span>Connector run</span><strong className="mono-value">{selected.connector_run_id || '—'}</strong></div>
            <div className="post-fact"><span>Source event ID</span><strong className="mono-value">{selected.source_event_id}</strong></div>
            <div className="post-fact"><span>Internal evidence ID</span><strong className="mono-value">{selected.id}</strong></div>
            <div className="post-fact"><span>Conversation ID</span><strong className="mono-value">{selected.conversation_id || '—'}</strong></div>
            <div className="post-fact"><span>Parent event</span><strong className="mono-value">{selected.parent_event_id || '—'}</strong></div>
            <div className="post-fact"><span>Ingested at</span><strong>{selected.ingested_at ? new Date(selected.ingested_at).toLocaleString() : '—'}</strong></div>
            <div className="post-fact"><span>Inference</span><strong>{selected.inference_method || '—'}</strong></div>
          </section>
        </div>

        <details className="post-raw-card">
          <summary>Show raw public metadata & extracted URLs</summary>
          <div className="post-raw-grid">
            <div><strong>Public profile / media metadata</strong><pre>{JSON.stringify(selected.public_profile || {}, null, 2)}</pre></div>
            <div><strong>Extracted URLs</strong><pre>{JSON.stringify(selected.urls || [], null, 2)}</pre></div>
            <div><strong>Raw evidence hash</strong><pre>{selected.raw_hash || '—'}</pre></div>
          </div>
        </details>
      </section>
    </div>
  );
}
