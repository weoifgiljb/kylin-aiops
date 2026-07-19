import { Background, Controls, MarkerType, ReactFlow } from '@xyflow/react'
import type { Edge, Node } from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import type { NodeInfo, TopologyEdge } from '../../api/types'

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
}

export function ServiceTopology({ nodes, topology, rootNode }: Props) {
  const flowNodes: Node[] = nodes.map((node) => ({
    id: node.id,
    position: positions[node.id] ?? { x: 0, y: 0 },
    data: { label: <div className="topology-node"><strong>{labels[node.service ?? ''] ?? node.service}</strong><small>{node.hostname}</small><span>{node.status === 'online' ? '在线' : '离线'}</span></div> },
    className: node.id === rootNode ? 'flow-node flow-node-root' : 'flow-node',
  }))
  const flowEdges: Edge[] = topology.map((edge, index) => ({
    id: `edge-${index}`,
    source: edge.source,
    target: edge.target,
    markerEnd: { type: MarkerType.ArrowClosed },
    animated: true,
    style: { stroke: '#2f78e6', strokeWidth: 2 },
  }))

  return (
    <section className="topology-panel" aria-label="服务拓扑">
      <div className="section-heading"><div><span>实时依赖</span><h2>服务拓扑</h2></div><span className="legend">● 根因 · ● 传播中 · ● 正常</span></div>
      <div className="topology-canvas">
        <ReactFlow nodes={flowNodes} edges={flowEdges} fitView minZoom={0.7} maxZoom={1.2} nodesDraggable={false}>
          <Background color="#d9e2ec" gap={24} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </section>
  )
}
