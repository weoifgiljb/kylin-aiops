export function actionParameters(actionName: string): Record<string, string> {
  if (actionName === 'restart_demo_service') return { service: 'kylin-demo-app' }
  if (actionName === 'reload_nginx') return { service: 'nginx' }
  if (actionName === 'terminate_fault_db_sessions') return { db_user: 'ops_fault' }
  throw new Error('该恢复动作需要明确的实验上下文，不能从事件信息中猜测参数')
}
