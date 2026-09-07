import { useEffect, useMemo, useState } from 'react';
import { Boxes, CircleDot, GitBranch, Network, RefreshCw, ShieldCheck, Users2, Waypoints } from 'lucide-react';
import { api, type GraphNode, type NetworkResponse } from './api';

type Props = { network: NetworkResponse | null };
type RoleFilter = 'all' | 'high' | 'bridge';

type CommunityDetail = {
  community: number;
  events: number;
  authors: number;
  first_observed_at: string;
  last_observed_at: string;
  sentiment_mix: Record<string, number>;
  stance_mix: Record<string, number>;
  platform_mix: Record<string, number>;
};

type CrossCommunityFlow = {
  source_community: number;
  target_community: number;
  weight: number;
  edge_count: number;
  types: Record<string, number>;
};

type SpreadPoint = {
  time: string;
  communities: Record<string, number>;
  sentiment_balance: Record<string, number>;
};

type RichNetwork = NetworkResponse & {
  edge_type_counts?: Record<string, number>;
  direct_observed_edges?: number;
  co_discussion_edges?: number;
  key_opinion_leader_candidates?: GraphNode[];
  communities_detail?: CommunityDetail[];
  cross_community_flows?: CrossCommunityFlow[];
  spread_timeline?: SpreadPoint[];
  spread_method_note?: string;
};

const WIDTH = 1000;
const HEIGHT = 620;

const platformColors: Record<string, string> = {
  x: '#31363f', telegram: '#2a9ddd', youtube: '#ef476f', instagram: '#b85ac7', facebook: '#4d7de3',
  bluesky: '#3a9bf0', reddit: '#f26a3d', mastodon: '#6c63d9', replay: '#b58a2a', unknown: '#8291a6',
};

function nodeColor(platform: string) {
  return platformColors[platform] || platformColors.unknown;
}

function positionNodes(nodes: GraphNode[]) {
  const groups = new Map<number, GraphNode[]>();
  for (const node of nodes) {
    const list = groups.get(node.community || 0) || [];
    list.push(node);
    groups.set(node.community || 0, list);
  }

  const communities = [...groups.entries()].sort((a, b) => b[1].length - a[1].length);
  const centerX = WIDTH / 2;
  const centerY = HEIGHT / 2;
  const communityRadius = communities.length <= 1 ? 0 : 210;
  const result = new Map<string, { x: number; y: number }>();

  communities.forEach(([community, members], cIndex) => {
    const cAngle = communities.length <= 1 ? 0 : (cIndex / communities.length) * Math.PI * 2 - Math.PI / 2;
    const cx = centerX + Math.cos(cAngle) * communityRadius;
    const cy = centerY + Math.sin(cAngle) * communityRadius * 0.72;
    const localRadius = Math.min(95, 34 + members.length * 4.5);
    members.forEach((node, nIndex) => {
      if (members.length === 1) {
        result.set(node.id, { x: cx, y: cy });
        return;
      }
      const angle = (nIndex / members.length) * Math.PI * 2 + community * 0.37;
      const ring = localRadius * (0.58 + (nIndex % 3) * 0.18);
      result.set(node.id, { x: cx + Math.cos(angle) * ring, y: cy + Math.sin(angle) * ring });
    });
  });
  return result;
}

function centrality(node: GraphNode) {
  return Math.max(node.pagerank || 0, node.betweenness || 0, node.degree_centrality || 0);
}

function fmt(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

export default function NetworkPro({ network: initialNetwork }: Props) {
  const [workspaceNetwork, setWorkspaceNetwork] = useState<NetworkResponse | null>(initialNetwork);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(initialNetwork?.nodes?.[0]?.id || null);
  const [filter, setFilter] = useState<RoleFilter>('all');
  const [showLabels, setShowLabels] = useState(true);

  const refreshGlobal = async () => {
    setRefreshing(true);
    try {
      const result = await api.network();
      setWorkspaceNetwork(result);
      setSelectedId((current) => result.nodes.some((node) => node.id === current) ? current : result.nodes[0]?.id || null);
    } catch {
      // Keep the last valid graph visible; the surrounding app already reports backend failures.
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => { void refreshGlobal(); }, []);

  const network = (workspaceNetwork || initialNetwork) as RichNetwork | null;
  const allNodes = network?.nodes || [];

  const filteredNodes = useMemo(() => {
    if (filter === 'high') return allNodes.filter((node) => node.role === 'High Reach Node');
    if (filter === 'bridge') return allNodes.filter((node) => node.role === 'Bridge Node');
    return allNodes;
  }, [allNodes, filter]);

  const nodeIds = useMemo(() => new Set(filteredNodes.map((node) => node.id)), [filteredNodes]);
  const edges = useMemo(() => (network?.edges || []).filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)).slice(0, 160), [network, nodeIds]);
  const positions = useMemo(() => positionNodes(filteredNodes), [filteredNodes]);
  const selected = filteredNodes.find((node) => node.id === selectedId) || filteredNodes[0] || null;
  const ranked = useMemo(() => [...filteredNodes].sort((a, b) => (b.pagerank + b.betweenness) - (a.pagerank + a.betweenness)), [filteredNodes]);
  const maxCentrality = Math.max(0.00001, ...filteredNodes.map(centrality));

  if (!network || !allNodes.length) {
    return (
      <section className="analysis-empty panel panel-large">
        <div className="analysis-empty-icon"><Network size={27} /></div>
        <h2>No interaction network yet</h2>
        <p>NEXUS needs observed authors plus mentions, replies, public relationships, shared domains, or co-discussion evidence before it can draw relationships.</p>
        <button className="evidence-export-btn" onClick={() => void refreshGlobal()} disabled={refreshing}><RefreshCw size={14} /> {refreshing ? 'Refreshing…' : 'Refresh graph'}</button>
        <div className="analysis-empty-note"><ShieldCheck size={15} /> An empty graph is shown honestly instead of inventing relationships.</div>
      </section>
    );
  }

  return (
    <div className="network-pro">
      <div className="analysis-summary-grid network-summary-grid">
        <div className="analysis-summary-card"><Users2 size={17} /><span>Observed nodes</span><strong>{network.summary.nodes || 0}</strong><small>authors in current workspace</small></div>
        <div className="analysis-summary-card"><GitBranch size={17} /><span>Observed edges</span><strong>{network.summary.edges || 0}</strong><small>{network.direct_observed_edges || 0} direct · {network.co_discussion_edges || 0} co-discussion</small></div>
        <div className="analysis-summary-card"><Boxes size={17} /><span>Communities</span><strong>{network.summary.communities || 0}</strong><small>structural user segments</small></div>
        <div className="analysis-summary-card"><CircleDot size={17} /><span>Bridge / reach</span><strong>{(network.summary.bridge_nodes || 0) + (network.summary.high_reach_nodes || 0)}</strong><small>key influence candidates</small></div>
      </div>

      <section className="panel panel-large network-workbench">
        <div className="analysis-section-head network-head">
          <div><span className="eyebrow">Whole-workspace relationship graph</span><h2>Community & influence map</h2><p>Nodes are grouped by detected community. Size reflects observed graph centrality; color identifies platform.</p></div>
          <div className="network-controls">
            <div className="network-filter-group">
              <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>All {allNodes.length}</button>
              <button className={filter === 'high' ? 'active' : ''} onClick={() => setFilter('high')}>High reach {network.summary.high_reach_nodes || 0}</button>
              <button className={filter === 'bridge' ? 'active' : ''} onClick={() => setFilter('bridge')}>Bridge {network.summary.bridge_nodes || 0}</button>
            </div>
            <button className={`network-label-toggle ${showLabels ? 'active' : ''}`} onClick={() => setShowLabels((value) => !value)}>{showLabels ? 'Labels on' : 'Labels off'}</button>
            <button className="network-label-toggle" disabled={refreshing} onClick={() => void refreshGlobal()}><RefreshCw size={12} /> {refreshing ? 'Refreshing' : 'Refresh'}</button>
          </div>
        </div>

        <div className="network-pro-layout">
          <div className="network-pro-canvas-wrap">
            <svg className="network-pro-canvas" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Observed social interaction graph">
              <defs><filter id="nodeShadow" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="3" stdDeviation="4" floodOpacity="0.16" /></filter></defs>
              {edges.map((edge, index) => {
                const source = positions.get(edge.source);
                const target = positions.get(edge.target);
                if (!source || !target) return null;
                const opacity = Math.min(0.72, 0.14 + Number(edge.weight || 0) * 0.13);
                return <line key={`${edge.source}-${edge.target}-${index}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className="network-pro-edge" style={{ opacity }} strokeWidth={Math.min(3.2, 0.8 + Number(edge.weight || 0) * 0.55)} />;
              })}
              {filteredNodes.map((node, index) => {
                const p = positions.get(node.id);
                if (!p) return null;
                const isSelected = selected?.id === node.id;
                const score = centrality(node) / maxCentrality;
                const radius = 9 + score * 10 + (node.role === 'Bridge Node' ? 3 : 0);
                const labelVisible = showLabels && (isSelected || index < 12 || node.role !== 'Participant');
                return (
                  <g key={node.id} className={`network-pro-node ${isSelected ? 'selected' : ''}`} onClick={() => setSelectedId(node.id)} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') setSelectedId(node.id); }}>
                    {isSelected && <circle cx={p.x} cy={p.y} r={radius + 7} className="network-pro-selection-ring" />}
                    <circle cx={p.x} cy={p.y} r={radius} fill={nodeColor(node.platform)} className="network-pro-dot" filter="url(#nodeShadow)" />
                    <circle cx={p.x} cy={p.y} r={Math.max(3, radius * 0.34)} className="network-pro-core" />
                    {labelVisible && <text x={p.x + radius + 7} y={p.y + 4}>{node.label.slice(0, 22)}</text>}
                    <title>{`${node.label} · ${node.platform} · ${node.role}`}</title>
                  </g>
                );
              })}
            </svg>
            {!edges.length && <div className="network-no-edges"><ShieldCheck size={14} /> Nodes are visible, but this filtered view contains no observed relationships.</div>}
            <div className="network-platform-legend">{[...new Set(filteredNodes.map((node) => node.platform))].map((platform) => <span key={platform}><i style={{ background: nodeColor(platform) }} />{platform}</span>)}</div>
          </div>

          <aside className="network-inspector">
            <div className="network-inspector-head"><span className="eyebrow">Node inspector</span><h3>{selected?.label || 'Select a node'}</h3>{selected && <div className="network-node-meta"><span className={`platform platform-${selected.platform}`}>{selected.platform.toUpperCase()}</span><span className={`network-role role-${selected.role.replaceAll(' ', '-').toLowerCase()}`}>{selected.role}</span></div>}</div>
            {selected && <>
              <p className="network-explanation">{selected.explanation}</p>
              <div className="network-metric-list">
                <div><span>PageRank</span><strong>{selected.pagerank.toFixed(4)}</strong><i><b style={{ width: `${Math.min(100, selected.pagerank / maxCentrality * 100)}%` }} /></i></div>
                <div><span>Betweenness</span><strong>{selected.betweenness.toFixed(4)}</strong><i><b style={{ width: `${Math.min(100, selected.betweenness / maxCentrality * 100)}%` }} /></i></div>
                <div><span>Degree centrality</span><strong>{selected.degree_centrality.toFixed(4)}</strong><i><b style={{ width: `${Math.min(100, selected.degree_centrality / maxCentrality * 100)}%` }} /></i></div>
                <div><span>Community</span><strong>#{selected.community}</strong></div>
              </div>
            </>}
            <div className="network-ranked-list">
              <div className="network-ranked-title">Key opinion-leader candidates</div>
              {(network.key_opinion_leader_candidates || ranked).slice(0, 8).map((node, index) => <button key={node.id} className={selected?.id === node.id ? 'active' : ''} onClick={() => setSelectedId(node.id)}><span>{index + 1}</span><div><strong>{node.label}</strong><small>{node.platform} · {node.role}</small></div><b>{node.pagerank.toFixed(3)}</b></button>)}
            </div>
          </aside>
        </div>

        <div className="analysis-trust-note"><ShieldCheck size={16} /><span>High Reach Node and Bridge Node describe position in the observed graph only. They do not imply identity, intent, guilt, coordination, or real-world influence beyond collected evidence.</span></div>
      </section>

      <section className="panel panel-large ps-network-spread-card">
        <div className="analysis-section-head"><div><span className="eyebrow">SIH26152 · propagation analysis</span><h2>How trend & sentiment spread between user segments</h2><p>Communities act as structural user segments. Timestamped activity and cross-community edges expose observed propagation paths over time.</p></div><Waypoints size={20} /></div>
        <div className="ps-network-spread-grid">
          <div className="ps-network-block"><strong>Relationship evidence types</strong><div className="ps-network-chips">{Object.entries(network.edge_type_counts || {}).map(([type, count]) => <span key={type}>{type.replaceAll('-', ' ')} <b>{count}</b></span>)}</div><small>Direct observed edges (reply / mention / public-follow): {network.direct_observed_edges || 0}. Co-discussion edges: {network.co_discussion_edges || 0}.</small></div>
          <div className="ps-network-block"><strong>Cross-community flows</strong><div className="ps-network-flow-list">{(network.cross_community_flows || []).slice(0, 8).map((flow, index) => <div key={`${flow.source_community}-${flow.target_community}-${index}`}><span>C{flow.source_community}</span><b>→</b><span>C{flow.target_community}</span><em>{flow.edge_count} edges · w {flow.weight.toFixed(2)}</em></div>)}{!(network.cross_community_flows || []).length && <small>No cross-community edge is observed yet.</small>}</div></div>
        </div>
        <div className="ps-network-spread-timeline"><strong>Segment adoption chronology</strong>{(network.spread_timeline || []).slice(-12).map((point) => <div key={point.time}><time>{fmt(point.time)}</time><span>{Object.entries(point.communities).map(([community, count]) => `Community ${community}: ${count}`).join(' · ') || 'No activity'}</span><b>{Object.keys(point.communities).length} active segment(s)</b></div>)}</div>
        <div className="ps-network-community-list">{(network.communities_detail || []).slice(0, 8).map((community) => {
          const sentiments = community.sentiment_mix || {};
          const total = Object.values(sentiments).reduce((sum, value) => sum + value, 0);
          const negative = total ? Math.round((sentiments.negative || 0) / total * 100) : 0;
          const positive = total ? Math.round((sentiments.positive || 0) / total * 100) : 0;
          return <div key={community.community}><strong>Community #{community.community}</strong><span>{community.authors} authors · {community.events} events</span><small>first {fmt(community.first_observed_at)} · +{positive}% / −{negative}% sentiment</small></div>;
        })}</div>
        <div className="analysis-trust-note"><ShieldCheck size={16} /><span>{network.spread_method_note || 'Spread analysis is bounded to timestamped observed/co-discussion evidence and does not imply coordination or intent.'}</span></div>
      </section>
    </div>
  );
}
