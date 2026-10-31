import { X } from 'lucide-react';
import type { GraphData, GraphNode, GraphRelationship } from '../../types';
import { SourceLink, StatusBadge } from '../ui';
import { NODE_STYLE } from './GraphCanvas';

interface Props {
  data: GraphData;
  node?: GraphNode;
  edge?: GraphRelationship;
  onClose: () => void;
  onSelectNode: (id: string) => void;
}

export function GraphDetails({ data, node, edge, onClose, onSelectNode }: Props) {
  const byId = (id: string) => data.nodes.find((n) => n.id === id)!;
  return (
    <aside className="card h-full overflow-y-auto p-4" aria-label="Graph details">
      <div className="mb-3 flex items-start justify-between"><h2 className="text-sm font-medium">{node ? 'Node details' : 'Relationship'}</h2><button aria-label="Close details" className="btn !p-1" onClick={onClose}><X size={13} /></button></div>
      {node && (
        <div className="space-y-3 text-sm">
          <div><div className="font-medium">{node.label}</div><span className="text-xs" style={{ color: NODE_STYLE[node.type].color }}>{NODE_STYLE[node.type].label}</span></div>
          <p className="text-muted">{node.description}</p>
          {node.timestamp && <div className="text-xs text-muted">Timestamp: {node.timestamp}</div>}
          <div>
            <div className="mb-1 text-xs font-medium text-muted">Connected entities</div>
            <ul className="space-y-1">
              {data.edges.filter((e) => e.source === node.id || e.target === node.id).map((e) => {
                const other = byId(e.source === node.id ? e.target : e.source);
                return <li key={e.id}><button className="text-left text-xs hover:underline" onClick={() => onSelectNode(other.id)}><span className="text-cyan">{e.type}</span> · {other.label}</button></li>;
              })}
            </ul>
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-muted">Related evidence</div>
            <ul className="space-y-1.5">{node.evidence.length ? node.evidence.map((id) => <li key={id} className="rounded-md border border-line p-2 text-xs"><code>{id}</code><div className="mt-1"><StatusBadge status="partial" /></div></li>) : <li className="text-xs text-muted">No linked evidence IDs.</li>}</ul>
          </div>
          {node.url && <SourceLink url={node.url} />}
        </div>
      )}
      {edge && (
        <div className="space-y-3 text-sm">
          <div className="font-medium text-cyan">{edge.type}</div>
          <div className="text-xs">{byId(edge.source).label} → {byId(edge.target).label}</div>
          <div className="rounded-md border border-line p-2 text-xs"><div className="mb-1 font-medium text-muted">Supporting evidence</div>{edge.evidence}</div>
        </div>
      )}
    </aside>
  );
}
