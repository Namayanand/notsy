import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import './AgentGraph.css';

const AGENT_COLORS = {
  orchestrator: '#7c5bf5',
  planner: '#f472b6',
  tutor: '#60a5fa',
  evaluator: '#4ade80',
  motivator: '#fbbf24',
  retriever: '#a78bfa',
  memory: '#22d3d1'
};

const DEFAULT_COLOR = '#94a3b8';

export default function AgentGraph({ agents, tasks, onAgentClick }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth || 600;
    const height = svgRef.current.clientHeight || 400;

    // Create nodes from agents
    const nodes = (agents || []).map((agent, index) => {
      const name = agent.name?.toLowerCase() || '';
      let type = 'default';
      for (const [key] of Object.entries(AGENT_COLORS)) {
        if (name.includes(key)) {
          type = key;
          break;
        }
      }

      // Position nodes in a circle
      const angle = (index / Math.max(agents.length, 1)) * 2 * Math.PI;
      const radius = Math.min(width, height) * 0.35;
      const centerX = width / 2;
      const centerY = height / 2;

      return {
        ...agent,
        type,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        color: AGENT_COLORS[type] || DEFAULT_COLOR,
        status: getAgentStatus(agent.name, tasks)
      };
    });

    // Add orchestrator at center if not present
    if (!nodes.find(n => n.type === 'orchestrator')) {
      nodes.push({
        name: 'Orchestrator',
        url: import.meta.env.VITE_AI_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000',
        type: 'orchestrator',
        x: width / 2,
        y: height / 2,
        color: AGENT_COLORS.orchestrator,
        status: 'idle'
      });
    }

    // Create links from tasks
    const links = [];
    tasks.forEach(task => {
      const chain = task.agentChain ? JSON.parse(task.agentChain) : [];
      chain.forEach((step, index) => {
        if (index > 0) {
          const fromNode = nodes.find(n => n.name.toLowerCase().includes(chain[index - 1].agent?.toLowerCase() || ''));
          const toNode = nodes.find(n => n.name.toLowerCase().includes(step.agent?.toLowerCase() || ''));
          if (fromNode && toNode) {
            links.push({
              source: fromNode,
              target: toNode,
              status: task.status
            });
          }
        }
      });
    });

    // Clear and setup
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    // Add arrow marker
    svg.append('defs').append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#94a3b8');

    // Draw links
    const linkGroup = svg.append('g').attr('class', 'links');

    linkGroup.selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)
      .attr('stroke', d => d.status === 'working' ? '#60a5fa' : '#94a3b8')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', d => d.status === 'working' ? '5,5' : 'none')
      .attr('marker-end', 'url(#arrowhead)')
      .attr('opacity', 0.6);

    // Draw nodes
    const nodeGroup = svg.append('g').attr('class', 'nodes');

    const nodeElements = nodeGroup.selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('transform', d => `translate(${d.x}, ${d.y})`)
      .style('cursor', 'pointer')
      .on('click', (event, d) => onAgentClick?.(d));

    // Node circle
    nodeElements.append('circle')
      .attr('r', 20)
      .attr('fill', d => d.color)
      .attr('stroke', '#fff')
      .attr('stroke-width', 3)
      .attr('opacity', 0.9);

    // Status indicator
    nodeElements.append('circle')
      .attr('r', 6)
      .attr('cx', 14)
      .attr('cy', -14)
      .attr('fill', d => d.status === 'working' ? '#60a5ba' : d.status === 'completed' ? '#4ade80' : d.status === 'failed' ? '#f87171' : '#94a3b8')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    // Node label
    nodeElements.append('text')
      .attr('y', 35)
      .attr('text-anchor', 'middle')
      .attr('fill', '#1e293b')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .text(d => truncateName(d.name));

    // Add icon
    nodeElements.append('text')
      .attr('y', 5)
      .attr('text-anchor', 'middle')
      .attr('fill', '#fff')
      .attr('font-size', '14px')
      .text(d => getAgentIcon(d.type));

  }, [agents, tasks]);

  function getAgentStatus(agentName, tasks) {
    const recentTasks = tasks.filter(t => {
      try {
        const chain = t.agentChain ? JSON.parse(t.agentChain) : [];
        return chain.some(step => agentName?.toLowerCase().includes(step.agent?.toLowerCase() || ''));
      } catch {
        return false;
      }
    });

    if (recentTasks.some(t => t.status === 'working')) return 'working';
    if (recentTasks.some(t => t.status === 'completed')) return 'completed';
    if (recentTasks.some(t => t.status === 'failed')) return 'failed';
    return 'idle';
  }

  function getAgentIcon(type) {
    const icons = {
      orchestrator: '🎯',
      planner: '📋',
      tutor: '📖',
      evaluator: '✅',
      motivator: '💪',
      retriever: '🔍',
      memory: '🧠'
    };
    return icons[type] || '🤖';
  }

  function truncateName(name) {
    if (!name) return 'Unknown';
    return name.length > 15 ? name.slice(0, 12) + '...' : name;
  }

  return (
    <div className="agent-graph-container">
      <svg ref={svgRef} className="agent-graph-svg" />
    </div>
  );
}