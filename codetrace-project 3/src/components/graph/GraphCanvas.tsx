import { useEffect, useImperativeHandle, useRef, forwardRef } from 'react';
import cytoscape, { type Core } from 'cytoscape';
import type { GraphData, GraphNodeType, GraphRelType } from '../../types';
import { useApp } from '../../hooks/useApp';

export const NODE_STYLE: Record<GraphNodeType, { label: string; color: string; shape: string }> = {
  repository: { label: 'Repository', color: '#94a3b8', shape: 'round-rectangle' },
  file: { label: 'Code file', color: '#8b78ff', shape: 'round-rectangle' },
  function: { label: 'Function / class', color: '#a78bfa', shape: 'ellipse' },
  code_entity: { label: 'Code entity', color: '#a78bfa', shape: 'ellipse' },
  configuration_key: { label: 'Configuration', color: '#c084fc', shape: 'hexagon' },
  commit: { label: 'Commit', color: '#22d3ee', shape: 'diamond' },
  evidence: { label: 'Evidence', color: '#64748b', shape: 'rectangle' },
  decision_record: { label: 'Decision record', color: '#4ade80', shape: 'hexagon' },
  code_change: { label: 'Code change', color: '#22d3ee', shape: 'diamond' },
  code_excerpt: { label: 'Code excerpt', color: '#64748b', shape: 'rectangle' },
  decision: { label: 'Decision', color: '#4ade80', shape: 'hexagon' },
  pull_request: { label: 'Pull request', color: '#60a5fa', shape: 'octagon' },
  issue: { label: 'Issue', color: '#fbbf24', shape: 'triangle' },
  discussion: { label: 'Discussion', color: '#fbbf24', shape: 'triangle' },
  comment: { label: 'Comment', color: '#fbbf24', shape: 'ellipse' },
  documentation: { label: 'Documentation', color: '#38bdf8', shape: 'rectangle' },
  incident: { label: 'Incident', color: '#f87171', shape: 'star' },
  person: { label: 'Person', color: '#fb7185', shape: 'ellipse' },
};

export interface GraphHandle { zoom: (f: number) => void; fit: () => void; reset: () => void }
export type Selection = { kind: 'node' | 'edge'; id: string } | null;

interface Props {
  data: GraphData;
  nodeTypes: Set<GraphNodeType>;
  relTypes: Set<GraphRelType>;
  showLabels: boolean;
  query: string;
  selection: Selection;
  onSelect: (s: Selection) => void;
}

export const GraphCanvas = forwardRef<GraphHandle, Props>(function GraphCanvas({ data, nodeTypes, relTypes, showLabels, query, selection, onSelect }, handle) {
  const el = useRef<HTMLDivElement>(null);
  const cy = useRef<Core | null>(null);
  const { theme } = useApp();
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useImperativeHandle(handle, () => ({
    zoom: (f) => cy.current && cy.current.zoom({ level: cy.current.zoom() * f, renderedPosition: { x: cy.current.width() / 2, y: cy.current.height() / 2 } }),
    fit: () => cy.current?.fit(undefined, 40),
    reset: () => { cy.current?.elements().removeClass('dim hl match'); cy.current?.layout({ name: 'cose', animate: false, padding: 40, nodeRepulsion: () => 9000, idealEdgeLength: () => 90 }).run(); onSelectRef.current(null); },
  }));

  useEffect(() => {
    const c = cytoscape({
      container: el.current,
      elements: [
        ...data.nodes.map((n) => ({ data: { id: n.id, label: n.label, type: n.type } })),
        ...data.edges.map((e) => ({ data: { id: e.id, source: e.source, target: e.target, label: e.type, rel: e.type } })),
      ],
      layout: { name: 'cose', animate: false, padding: 40, nodeRepulsion: () => 9000, idealEdgeLength: () => 90 },
      minZoom: 0.3, maxZoom: 3,
      style: [
        { selector: 'node', style: { label: 'data(label)', 'font-size': 10, 'text-valign': 'bottom', 'text-margin-y': 4, width: 26, height: 26, 'border-width': 1, 'border-color': '#0a0a0d', 'text-wrap': 'ellipsis', 'text-max-width': '90px' } },
        ...Object.entries(NODE_STYLE).map(([t, s]) => ({ selector: `node[type="${t}"]`, style: { 'background-color': s.color, shape: s.shape as never } })),
        { selector: 'edge', style: { width: 1.2, 'line-color': '#4b5563', 'target-arrow-color': '#4b5563', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'arrow-scale': 0.8, 'font-size': 8 } },
        { selector: 'edge[rel="SUPERSEDES"]', style: { 'line-style': 'dashed', 'line-color': '#fbbf24', 'target-arrow-color': '#fbbf24' } },
        { selector: 'edge[rel="EXPLAINS"]', style: { 'line-color': '#22d3ee', 'target-arrow-color': '#22d3ee' } },
        { selector: '.dim', style: { opacity: 0.15 } },
        { selector: '.hl', style: { 'line-color': '#22d3ee', 'target-arrow-color': '#22d3ee', width: 2.5, 'border-width': 2, 'border-color': '#22d3ee' } },
        { selector: '.match', style: { 'border-width': 3, 'border-color': '#ffffff' } },
        { selector: ':selected', style: { 'border-width': 3, 'border-color': '#ffffff' } },
      ],
    });
    c.on('tap', 'node', (e) => onSelectRef.current({ kind: 'node', id: e.target.id() }));
    c.on('tap', 'edge', (e) => onSelectRef.current({ kind: 'edge', id: e.target.id() }));
    c.on('tap', (e) => { if (e.target === c) onSelectRef.current(null); });
    cy.current = c;
    return () => { c.destroy(); cy.current = null; };
  }, [data]);

  // theme-aware label color
  useEffect(() => {
    cy.current?.style().selector('node').style({ color: theme === 'dark' ? '#c9c9d6' : '#303040' }).selector('edge').style({ color: theme === 'dark' ? '#8a8a9a' : '#606070' }).update();
  }, [theme, data]);

  // filters + labels
  useEffect(() => {
    const c = cy.current; if (!c) return;
    c.batch(() => {
      c.nodes().forEach((n) => { n.style('display', nodeTypes.has(n.data('type')) ? 'element' : 'none'); });
      c.edges().forEach((e) => { e.style('display', relTypes.has(e.data('rel')) && e.source().visible() && e.target().visible() ? 'element' : 'none'); });
      c.nodes().style('text-opacity', showLabels ? 1 : 0);
      c.edges().style('label', showLabels ? 'data(label)' : '');
    });
  }, [nodeTypes, relTypes, showLabels, data]);

  // search
  useEffect(() => {
    const c = cy.current; if (!c) return;
    c.nodes().removeClass('match');
    if (query.trim()) {
      const m = c.nodes().filter((n) => String(n.data('label')).toLowerCase().includes(query.toLowerCase()));
      m.addClass('match');
      if (m.length) c.animate({ fit: { eles: m, padding: 120 }, duration: 250 });
    }
  }, [query]);

  // selection highlight
  useEffect(() => {
    const c = cy.current; if (!c) return;
    c.elements().removeClass('dim hl').unselect();
    if (!selection) return;
    const ele = c.getElementById(selection.id);
    if (ele.empty()) return;
    const hood = selection.kind === 'node' ? ele.closedNeighborhood() : ele.connectedNodes().union(ele);
    c.elements().not(hood).addClass('dim');
    hood.edges().addClass('hl');
    if (selection.kind === 'edge') ele.addClass('hl');
    ele.select();
  }, [selection, data]);

  return <div ref={el} className="h-full w-full" role="img" aria-label="Interactive decision graph (sample data)" />;
});
