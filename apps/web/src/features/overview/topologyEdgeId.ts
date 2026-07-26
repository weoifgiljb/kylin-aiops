export function topologyGroupEdgeId(sourceService: string, targetService: string): string {
  return `group-edge-${encodeURIComponent(JSON.stringify([sourceService, targetService]))}`
}
