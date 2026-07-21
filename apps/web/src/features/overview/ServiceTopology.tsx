import { Background, Controls, MarkerType, ReactFlow } from '@xyflow/react'
import type { Edge, Node } from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import type { NodeInfo, TopologyEdge } from '../../api/types'

const stateColors = {
  root: '#ef4444',
  propagating: '#f59e0b',
  normal: '#22c55e',
} as const

const labels: Record<string, string> = { nginx: 'Nginx', java: 'Java 服务', mysql: 'MySQL' }
const positions: Record<string, { x: number; y: number }> = {
  'web-01': { x: 30, y: 90 },
  'app-01': { x: 300, y: 90 },
  'db-01': { x: 570, y: 90 },
}

interface Props {
  nodes: NodeInfo[]
  topology: TopologyEdge[]
  rootNode?: string
  propagationPath?: string[]
}

export function ServiceTopology({ nodes, topology, rootNode, propagationPath = [] }: Props) {
  const propagationNodes = new Set(propagationPath)
  const flowNodes: Node[] = nodes.map((node, index) => {
    const state = node.id === rootNode ? 'root' : propagationNodes.has(node.id) ? 'propagating' : 'normal'
    return {
      id: node.id,
      position: positions[node.id] ?? { x: 30 + (index % 3) * 270, y: 90 + Math.floor(index / 3) * 150 },
      data: { label: <div className="topology-node"><strong>{labels[node.service ?? ''] ?? node.service ?? node.id}</strong><small>{node.hostname}</small>{node.metrics && <small>{`CPU ${node.metrics.cpu_percent?.toFixed(1) ?? '-'}% · 内存 ${node.metrics.memory_percent?.toFixed(1) ?? '-'}%`}</small>}<span>{node.status === 'online' ? '在线' : '离线'}</span></div> },
      className: `flow-node flow-node-${state}`,
      style: { borderColor: stateColors[state] },
    }
  })
  const flowEdges: Edge[] = topology.map((edge, index) => ({
    id: `edge-${index}`,
    source: edge.source,
    target: edge.target,
    markerEnd: { type: MarkerType.ArrowClosed },
    animated: true,
    style: {
      stroke: propagationNodes.has(edge.source) && propagationNodes.has(edge.target)
        ? stateColors.propagating
        : '#2f78e6',
      strokeWidth: 2,
    },
  }))

  return (
    <section className="topology-panel" aria-label="服务拓扑">
      <div className="section-heading"><div><span>实时依赖</span><h2>服务拓扑</h2></div><span className="legend" aria-label="拓扑状态图例">
        <span className="legend-item"><i aria-label="根因颜色" style={{ backgroundColor: stateColors.root }} />根因</span>
        <span className="legend-item"><i aria-label="传播中颜色" style={{ backgroundColor: stateColors.propagating }} />传播中</span>
        <span className="legend-item"><i aria-label="正常颜色" style={{ backgroundColor: stateColors.normal }} />正常</span>
      </span></div>
      <div className="topology-canvas">
        <ReactFlow nodes={flowNodes} edges={flowEdges} fitView minZoom={0.7} maxZoom={1.2} nodesDraggable={false}>
          <Background color="#d9e2ec" gap={24} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </section>
  )
}
