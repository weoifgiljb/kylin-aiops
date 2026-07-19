import { describe, expect, it } from 'vitest'

import { actionParameters } from './actionParameters'

describe('actionParameters', () => {
  it('builds only allowlisted fixed parameters', () => {
    expect(actionParameters('restart_demo_service')).toEqual({ service: 'kylin-demo-app' })
    expect(actionParameters('terminate_fault_db_sessions')).toEqual({ db_user: 'ops_fault' })
  })

  it('requires explicit experiment data for scoped recovery actions', () => {
    expect(() => actionParameters('clear_fault_netem')).toThrow(/实验上下文/)
  })
})
