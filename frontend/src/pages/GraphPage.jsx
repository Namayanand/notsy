import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getGraph, generateGraph, deleteRelation } from '../api/graph';
import * as d3 from 'd3';
import './GraphPage.css';

const RELATION_TYPES = [
  { value: 'RELATED', label: 'Related', color: '#60a5fa' },
  { value: 'PREREQUISITE', label: 'Prerequisite', color: '#fbbf24' },
  { value: 'EXTENDS', label: 'Extends', color: '#4ade80' },
  { value: 'CONTRASTS', label: 'Contrasts', color: '#f472b6' },
];

export default function GraphPage() {
  const { id: nbId } = useParams();
  const navigate = useNavigate();
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    loadGraph();
  }, [nbId]);

  useEffect(() => {
    if (graph) {
      renderGraph();
    }
  }, [graph, dimensions]);

  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth || 800,
          height: 500,
        });
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const loadGraph = async () => {
    setLoading(true);
    try {
      const res = await getGraph(nbId);
      setGraph(res.data.data);
    } catch (err) {
      console.error('Failed to load graph', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await generateGraph(nbId);
      setGraph(res.data.data);
    } catch {
      alert('Failed to generate graph');
    } finally {
      setGenerating(false);
    }
  };

  const handleDeleteRelation = async (relationId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this relation?')) return;
    try {
      await deleteRelation(nbId, relationId);
      loadGraph();
    } catch {
      alert('Failed to delete relation');
    }
  };

  const renderGraph = () => {
    if (!svgRef.current || !graph) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { width, height } = dimensions;

    svg.attr('viewBox', `0 0 ${width} ${height}`);

    // Define gradients and filters
    const defs = svg.append('defs');

    // Glow filter
    const filter = defs.append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');

    filter.append('feGaussianBlur')
      .attr('stdDeviation', '4')
      .attr('result', 'coloredBlur');

    const feMerge = filter.append('feMerge');
    feMerge.append('feNodeIn').attr('in', 'coloredBlur');
    feMerge.append('feNodeIn').attr('in', 'SourceGraphic');

    // Node gradient
    const nodeGradient = defs.append('radialGradient')
      .attr('id', 'nodeGradient')
      .attr('cx', '30%')
      .attr('cy', '30%');

    nodeGradient.append('stop').attr('offset', '0%').attr('stop-color', '#9d82f7');
    nodeGradient.append('stop').attr('offset', '100%').attr('stop-color', '#5f3fd4');

    const nodes = (graph.nodes || []).map((n) => ({ ...n }));
    const edges = (graph.edges || []).map((e) => ({
      ...e,
      source: e.sourceTopicId,
      target: e.targetTopicId,
    }));

    if (nodes.length === 0) return;

    const getNodeColor = (status) => {
      switch (status) {
        case 'DONE': return { main: '#7c5bf5', glow: 'rgba(124, 91, 245, 0.6)' };
        case 'PROCESSING': return { main: '#60a5fa', glow: 'rgba(96, 165, 250, 0.6)' };
        case 'PENDING': return { main: '#fbbf24', glow: 'rgba(251, 191, 36, 0.6)' };
        case 'FAILED': return { main: '#f87171', glow: 'rgba(248, 113, 113, 0.6)' };
        default: return { main: '#7c5bf5', glow: 'rgba(124, 91, 245, 0.6)' };
      }
    };

    // Create zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom);

    const container = svg.append('g');

    // Arrow markers for edges
    edges.forEach((edge) => {
      const rt = RELATION_TYPES.find((r) => r.value === edge.relationshipType);
      if (!rt) return;

      defs.append('marker')
        .attr('id', `arrow-${edge.id}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 35)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', rt.color)
        .attr('opacity', 0.8);
    });

    // Draw edges
    const link = container
      .append('g')
      .selectAll('line')
      .data(edges)
      .join('line')
      .attr('stroke', (d) => {
        const rt = RELATION_TYPES.find((r) => r.value === d.relationshipType);
        return rt?.color || '#5a5a6e';
      })
      .attr('stroke-opacity', 0.5)
      .attr('stroke-width', (d) => Math.max(1, (d.strength || 0.5) * 3))
      .attr('marker-end', (d) => `url(#arrow-${d.id})`)
      .style('filter', 'url(#glow)');

    // Edge labels
    const edgeLabel = container
      .append('g')
      .selectAll('text')
      .data(edges)
      .join('text')
      .attr('font-size', '10px')
      .attr('fill', (d) => {
        const rt = RELATION_TYPES.find((r) => r.value === d.relationshipType);
        return rt?.color || '#9898a8';
      })
      .attr('text-anchor', 'middle')
      .attr('font-weight', '600')
      .attr('letter-spacing', '0.5px')
      .style('pointer-events', 'none')
      .text((d) => d.relationshipType || '');

    // Draw nodes
    const node = container
      .append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', 'graph-node')
      .style('cursor', 'pointer');

    // Outer glow circle
    node.append('circle')
      .attr('r', 38)
      .attr('fill', (d) => getNodeColor(d.embeddingStatus).glow)
      .attr('opacity', 0.3)
      .attr('class', 'node-glow');

    // Main circle
    node.append('circle')
      .attr('r', 28)
      .attr('fill', (d) => getNodeColor(d.embeddingStatus).main)
      .attr('stroke', 'rgba(255,255,255,0.2)')
      .attr('stroke-width', 2)
      .attr('class', 'node-main');

    // Inner highlight
    node.append('circle')
      .attr('r', 20)
      .attr('fill', 'none')
      .attr('stroke', 'rgba(255,255,255,0.15)')
      .attr('stroke-width', 1);

    // Node text
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', 'white')
      .attr('font-size', '10px')
      .attr('font-weight', '700')
      .attr('pointer-events', 'none')
      .text((d) => {
        const words = d.title?.split(' ') || [];
        return words.slice(0, 2).join('\n');
      });

    // Drag behavior
    const drag = d3.drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    node.call(drag);

    // Click handler
    node.on('click', (event, d) => {
      event.stopPropagation();
      setSelectedNode(d);
    });

    // Double-click to navigate
    node.on('dblclick', (event, d) => {
      navigate(`/notebooks/${nbId}/topics/${d.id}`);
    });

    // Hover effects
    node.on('mouseover', function (event, d) {
      d3.select(this).select('.node-main')
        .transition().duration(200)
        .attr('stroke', 'rgba(255,255,255,0.6)')
        .attr('stroke-width', 3);

      d3.select(this).select('.node-glow')
        .transition().duration(200)
        .attr('r', 45)
        .attr('opacity', 0.5);
    });

    node.on('mouseout', function () {
      d3.select(this).select('.node-main')
        .transition().duration(200)
        .attr('stroke', 'rgba(255,255,255,0.2)')
        .attr('stroke-width', 2);

      d3.select(this).select('.node-glow')
        .transition().duration(200)
        .attr('r', 38)
        .attr('opacity', 0.3);
    });

    // Force simulation
    const simulation = d3
      .forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id((d) => d.id).distance(150).strength(0.5))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(50));

    // Tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);

      edgeLabel
        .attr('x', (d) => (d.source.x + d.target.x) / 2)
        .attr('y', (d) => (d.source.y + d.target.y) / 2);

      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    // Initial zoom to fit
    svg.call(zoom.transform, d3.zoomIdentity.translate(0, 0).scale(1));
  };

  return (
    <div className="graph-page">
      <div className="graph-header">
        <div className="graph-title-area">
          <h2>Knowledge Graph</h2>
          <p>Visualize how your topics connect — double-click a node to open it</p>
        </div>
        <div className="graph-actions">
          <button className="btn-secondary" onClick={() => navigate(`/notebooks/${nbId}`)}>
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
              <path d="M12 5l-5 5 5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Back to Notebook
          </button>
          <button className="btn-primary generate-btn" onClick={handleGenerate} disabled={generating}>
            {generating ? (
              <>
                <div className="spinner spinner-sm" />
                Generating...
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Generate Relations
              </>
            )}
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="graph-legend">
        {RELATION_TYPES.map((rt) => (
          <div key={rt.value} className="legend-item">
            <div className="legend-color" style={{ background: rt.color, boxShadow: `0 0 8px ${rt.color}` }} />
            <span>{rt.label}</span>
          </div>
        ))}
        <div className="legend-divider" />
        <div className="legend-item">
          <div className="legend-node node-done" style={{ boxShadow: '0 0 8px rgba(124, 91, 245, 0.6)' }} />
          <span>Ready</span>
        </div>
        <div className="legend-item">
          <div className="legend-node node-pending" style={{ boxShadow: '0 0 8px rgba(251, 191, 36, 0.6)' }} />
          <span>Processing</span>
        </div>
        <div className="legend-hint">Scroll to zoom · Drag to pan · Double-click to open</div>
      </div>

      {/* Graph container */}
      <div className="graph-container" ref={containerRef}>
        {loading ? (
          <div className="graph-loading">
            <div className="graph-loading-visual">
              <div className="loading-atom">
                <div className="atom-nucleus" />
                <div className="atom-orbit atom-orbit-1" />
                <div className="atom-orbit atom-orbit-2" />
                <div className="atom-orbit atom-orbit-3" />
              </div>
            </div>
            <p>Loading knowledge graph...</p>
          </div>
        ) : (
          <svg ref={svgRef} className="graph-svg" />
        )}
        {(!graph || graph.nodes?.length === 0) && !loading && (
          <div className="graph-empty-overlay">
            <div className="graph-empty-content">
              <div className="empty-graph-visual">
                <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                  <circle cx="20" cy="25" r="8" stroke="var(--accent)" strokeWidth="2" strokeDasharray="4 2" />
                  <circle cx="50" cy="20" r="6" stroke="var(--accent)" strokeWidth="2" strokeDasharray="4 2" />
                  <circle cx="60" cy="45" r="7" stroke="var(--accent)" strokeWidth="2" strokeDasharray="4 2" />
                  <circle cx="30" cy="55" r="9" stroke="var(--accent)" strokeWidth="2" strokeDasharray="4 2" />
                  <path d="M26 28l18-8M47 26l10 15M56 42l-22 10" stroke="var(--accent)" strokeWidth="1.5" strokeDasharray="4 2" opacity="0.5" />
                </svg>
              </div>
              <h3>Your knowledge graph is empty</h3>
              <p>Create topics in your notebooks, then generate relations to see how everything connects.</p>
              <button className="btn-primary" onClick={() => navigate(`/notebooks/${nbId}`)}>
                Create First Topic
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Selected node detail */}
      {selectedNode && (
        <div className="node-detail animate-slide-in-right">
          <div className="node-detail-header">
            <h3>{selectedNode.title}</h3>
            <button className="btn-ghost" onClick={() => setSelectedNode(null)}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          {selectedNode.description && <p className="node-detail-desc">{selectedNode.description}</p>}
          <div className="node-detail-meta">
            <span className={`badge badge-${(selectedNode.embeddingStatus || 'pending').toLowerCase()}`}>
              {selectedNode.embeddingStatus}
            </span>
            {selectedNode.resourceCount != null && (
              <span className="node-resource-count">
                📚 {selectedNode.resourceCount} resources
              </span>
            )}
          </div>
          <button
            className="btn-primary open-topic-btn"
            onClick={() => navigate(`/notebooks/${nbId}/topics/${selectedNode.id}`)}
          >
            Open Topic
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M3 8h10M9 5l4 3-4 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      )}

      {/* Relations list */}
      {graph?.edges?.length > 0 && (
        <div className="relations-list">
          <div className="section-title">Relations ({graph.edges.length})</div>
          {graph.edges.map((edge) => (
            <div key={edge.id} className="relation-row">
              <div className="relation-ends">
                <span className="relation-node-title">
                  {graph.nodes.find((n) => n.id === edge.sourceTopicId)?.title || `#${edge.sourceTopicId}`}
                </span>
                <span
                  className="relation-type-badge"
                  style={{ color: RELATION_TYPES.find((r) => r.value === edge.relationshipType)?.color }}
                >
                  {edge.relationshipType}
                </span>
                <span className="relation-node-title">
                  {graph.nodes.find((n) => n.id === edge.targetTopicId)?.title || `#${edge.targetTopicId}`}
                </span>
              </div>
              {edge.description && <p className="relation-desc">{edge.description}</p>}
              <button className="btn-ghost btn-sm delete-rel-btn" onClick={(e) => handleDeleteRelation(edge.id, e)}>
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                  <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
