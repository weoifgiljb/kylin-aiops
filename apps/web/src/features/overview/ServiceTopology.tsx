import { Background, Controls, MarkerType, ReactFlow } from '@xyflow/react'
import type { Edge, Node } from '@xyflow/react'
import { Empty } from 'antd'
import '@xyflow/react/dist/style.css'

import type { NodeInfo, TopologyEdge, TopologyGroup, TopologyGroupEdge } from '../../api/types'

const stateColors = {
  root: '#ef4444',
  propagating: '#f59e0b',
  normal: '#22c55e',
} as const

const labels: Record<string, string> = { nginx: 'Nginx', java: 'Java 服务', mysql: 'MySQL', unassigned: '未分配服务' }
const statusLabels: Record<string, string> = { online: '在线', offline: '离线' }
const positions: Record<string, { x: number; y: number }> = {
  'web-01': { x: 30, y: 90 },
  'app-01': { x: 300, y: 90 },
  'db-01': { x: 570, y: 90 },
}

interface Props {
  nodes: NodeInfo[]
  topology: TopologyEdge[]
  topologyGroups?: TopologyGroup[]
  topologyGroupEdges?: TopologyGroupEdge[]
  rootNode?: string
  propagationPath?: string[]
  onSelectGroup?: (filter: { service: string; status: string }) => void
}

function groupDisplayName(service: string): string {
  return labels[service] ?? service
}

function statusDisplayName(status: string): string {
  return statusLabels[status] ?? status
}

function groupPositions(index: number): { x: number; y: number } {
  return { x: 40 + (index % 3) * 270, y: 70 + Math.floor(index / 3) * 155 }
}

function primaryGroupIds(groups: TopologyGroup[]): Map<string, string> {
  const primaryIds = new Map<string, TopologyGroup>()
  for (const group of groups) {
    const current = primaryIds.get(group.service)
    if (!current || group.count > current.count || (group.count === current.count && group.id < current.id)) {
      primaryIds.set(group.service, group)
    }
  }
  return new Map([...primaryIds].map(([service, group]) => [service, group.id]))
}

export function ServiceTopology({
  nodes,
  topology,
  topologyGroups = [],
  topologyGroupEdges = [],
  rootNode,
  propagationPath = [],
  onSelectGroup,
}: Props) {
  const hasAggregateTopology = topologyGroups.length > 0 || topologyGroupEdges.length > 0
  const propagationNodes = new Set(propagationPath)
  const physicalFlowNodes: Node[] = nodes.map((node, index) => {
    const state = node.id === rootNode ? 'root' : propagationNodes.has(node.id) ? 'propagating' : 'normal'
    return {
      id: node.id,
      position: positions[node.id] ?? { x: 30 + (index % 3) * 270, y: 90 + Math.floor(index / 3) * 150 },
      data: { label: <div className="topology-node"><strong>{labels[node.service ?? ''] ?? node.service ?? node.id}</strong><small>{node.hostname}</small>{node.metrics && <small>{`CPU ${node.metrics.cpu_percent?.toFixed(1) ?? '-'}% · 内存 ${node.metrics.memory_percent?.toFixed(1) ?? '-'}%`}</small>}<span>{node.status === 'online' ? '在线' : '离线'}</span></div> },
      className: `flow-node flow-node-${state}`,
      style: { borderColor: stateColors[state] },
    }
  })
  const physicalFlowEdges: Edge[] = topology.map((edge, index) => ({
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
  const aggregateFlowNodes: Node[] = topologyGroups.map((group, index) => ({
    id: group.id,
    position: groupPositions(index),
    data: {
      label: (
        <button
          type="button"
          className="topology-group-button"
          aria-label={`${groupDisplayName(group.service)} ${statusDisplayName(group.status)} ${group.count.toLocaleString('zh-CN')} 个节点`}
          onClick={() => onSelectGroup?.({ service: group.service, status: group.status })}
        >
          <strong>{groupDisplayName(group.service)}</strong>
          <span>{statusDisplayName(group.status)}</span>
          <small>{group.count.toLocaleString('zh-CN')} 个节点</small>
        </button>
      ),
    },
    className: `flow-node flow-node-group flow-node-${group.status}`,
    style: { borderColor: group.status === 'online' ? stateColors.normal : '#94a3b8' },
  }))
  const aggregatePrimaryGroupIds = primaryGroupIds(topologyGroups)
  const aggregateFlowEdges: Edge[] = topologyGroupEdges.flatMap((edge, index) => {
    const source = aggregatePrimaryGroupIds.get(edge.source_service)
    const target = aggregatePrimaryGroupIds.get(edge.target_service)
    if (!source || !target) return []
    return [{
      id: `group-edge-${index}`,
      source,
      target,
      label: `${edge.count.toLocaleString('zh-CN')} 条依赖`,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: '#2f78e6', strokeWidth: Math.min(5, 1 + Math.log2(edge.count + 1)) },
      labelStyle: { fill: '#486581', fontSize: 11 },
    }]
  })
  const flowNodes = hasAggregateTopology ? aggregateFlowNodes : physicalFlowNodes
  const flowEdges = hasAggregateTopology ? aggregateFlowEdges : physicalFlowEdges

  return (
    <section className="topology-panel" aria-label="服务拓扑">
      <div className="section-heading"><div><span>{hasAggregateTopology ? '服务状态摘要' : '实时依赖'}</span><h2>服务拓扑</h2></div>{hasAggregateTopology ? <span className="topology-hint">点击摘要查看节点明细</span> : <span className="legend" aria-label="拓扑状态图例">
        <span className="legend-item"><i aria-label="根因颜色" style={{ backgroundColor: stateColors.root }} />根因</span>
        <span className="legend-item"><i aria-label="传播中颜色" style={{ backgroundColor: stateColors.propagating }} />传播中</span>
        <span className="legend-item"><i aria-label="正常颜色" style={{ backgroundColor: stateColors.normal }} />正常</span>
      </span>}</div>
      <div className="topology-canvas">
        {flowNodes.length ? <ReactFlow nodes={flowNodes} edges={flowEdges} fitView minZoom={0.7} maxZoom={1.2} nodesDraggable={false}>
          <Background color="#d9e2ec" gap={24} />
          <Controls showInteractive={false} />
        </ReactFlow> : <div className="topology-empty"><Empty description="暂无可展示的服务拓扑" /></div>}
      </div>
    </section>
  )
}
