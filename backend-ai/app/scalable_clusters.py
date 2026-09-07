from __future__ import annotations

from typing import Any

from .analytics import cluster_events


def _is_reaction(event) -> bool:
    event_type = str(event.event_type or "").lower()
    return bool(event.parent_event_id) or "comment" in event_type or "reply" in event_type or event_type in {
        "response",
        "replied_to",
    }


def scalable_assign_clusters(store) -> dict[str, list[Any]]:
    """Cluster root content, then inherit the root narrative for reactions.

    Running TF-IDF pairwise clustering across thousands of comments is both slow
    and conceptually wrong for conversation analytics: replies belong to the
    conversation they react to. This implementation clusters only root posts and
    propagates that narrative id to comments/replies through parent/conversation
    links. It keeps large YouTube/Telegram conversations responsive while
    preserving every reaction for sentiment/emotion/stance aggregation.
    """
    events = store.list_events(limit=None)
    if not events:
        return {}

    roots = [event for event in events if not _is_reaction(event)]
    if not roots:
        return {}

    clusters = cluster_events(roots)
    source_cluster: dict[tuple[str, str], str] = {}
    conversation_cluster: dict[tuple[str, str], str] = {}

    for cluster_id, members in clusters.items():
        for event in members:
            source_cluster[(event.platform, event.source_event_id)] = cluster_id
            if event.conversation_id:
                conversation_cluster[(event.platform, event.conversation_id)] = cluster_id
            if event.narrative_cluster_id != cluster_id:
                store.update_derived(event.id, {"narrative_cluster_id": cluster_id})

    # Direct replies-to-replies can form a chain. Iterate a few times so a child
    # can inherit a cluster after its parent has been resolved.
    unresolved = [event for event in events if _is_reaction(event)]
    for _ in range(4):
        if not unresolved:
            break
        next_unresolved = []
        progress = False
        for event in unresolved:
            cluster_id = None
            if event.parent_event_id:
                cluster_id = source_cluster.get((event.platform, event.parent_event_id))
            if not cluster_id and event.conversation_id:
                cluster_id = conversation_cluster.get((event.platform, event.conversation_id))
            if not cluster_id:
                next_unresolved.append(event)
                continue
            source_cluster[(event.platform, event.source_event_id)] = cluster_id
            if event.narrative_cluster_id != cluster_id:
                store.update_derived(event.id, {"narrative_cluster_id": cluster_id})
            progress = True
        unresolved = next_unresolved
        if not progress:
            break

    return {
        cluster_id: store.list_events(limit=None, narrative_id=cluster_id)
        for cluster_id in clusters
    }
