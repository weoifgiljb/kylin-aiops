export function incidentSourceMeta(source: string) {
  if (source === 'manual') return { label: '人工', color: 'blue' }
  if (source === 'alert') return { label: '告警', color: 'gold' }
  if (source === 'load-data') return { label: '批量加载数据', color: 'cyan' }
  return { label: source ? `未知来源（${source}）` : '未知来源', color: 'default' }
}
