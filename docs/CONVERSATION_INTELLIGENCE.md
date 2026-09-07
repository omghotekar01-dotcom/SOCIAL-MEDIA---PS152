# NEXUS Conversation & Public-Reaction Intelligence

NEXUS deliberately separates **what the root post says** from **what people say about it**. A post can be neutral while its replies become hostile, anxious, polarized or rapidly negative; the reverse can also happen.

## Evidence model

Every collected item is a `SocialEvent` with platform, source mode, source timestamp, author/pseudonym, text, conversation ID, optional parent-event ID, provenance and NLP inference. Replies/comments are linked to their root conversation whenever the provider exposes that relationship.

## Source coverage

| Platform | Root post path | Replies/comments path | Notes |
|---|---|---|---|
| Telegram | Public channel preview / Bot API | Bot-visible replies/messages | Public preview is channel-scoped, not global search. |
| X | Public Post oEmbed for explicit URLs / official API when configured | Official API when configured; otherwise Manual X Conversation Import | Manual evidence is always labelled `IMPORT`, never `LIVE`. |
| YouTube | Zero-key metadata or Data API | Official Data API comment threads | Zero-key metadata does not pretend to expose comments. |
| Instagram | Public-profile fallback or Meta Graph | Meta Graph comments for authorized professional-account data | Private/login controls are never bypassed. |
| Facebook | Authorized Page via Meta Graph | Meta Graph Page comments | Requires applicable Page permissions. |
| Reddit | OAuth/public search where permitted | Best-effort public comment thread; base post is retained if comments are blocked | Provider/network restrictions are surfaced honestly. |
| Bluesky | Public AT Protocol search | Public `getPostThread` replies | No paid key required for public endpoints. |
| Mastodon | Public instance search | Public status-context descendants when the instance permits it | NEXUS tries configured fallback instances. |

## Per-post intelligence

The Posts / Explorer screen shows two separate analyses:

1. **Content Intelligence** — sentiment, stance, sarcasm, emotions, topic terms, trend and narrative assignment for the selected evidence item itself.
2. **Public Reaction Intelligence** — computed from linked comments/replies only.

Reaction intelligence includes:

- captured comment/reply count,
- positive / negative / neutral distribution,
- supportive / against / unclear stance distribution,
- anger and anxiety signals,
- sarcasm level,
- evidence-bounded reaction-risk score,
- `STABLE`, `WATCH`, or `ESCALATING` direction,
- sample reactions and exact provenance.

The reaction score is descriptive, not an accusation. It does not infer guilt, intent or absolute internet-wide opinion.

## X without paid API access

For a public `/status/` URL, NEXUS first tries X oEmbed and canonicalizes copied links such as `?s=20`. Media/GIF-only embeds are retained even when X returns no readable caption.

If X refuses embed access for a specific post, the analyst can use **Manual X Conversation Import** in Social Sources:

- paste the original public X URL,
- paste the root post text/caption (or a disclosed media-only note),
- paste copied public replies one per line, optionally as `@user: reply text`,
- import them as linked `X / IMPORT` evidence.

The same sentiment, stance, narrative, timeline, network, evidence and reaction-intelligence pipeline then runs over those imported items, while provenance remains explicit.
