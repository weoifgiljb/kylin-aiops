#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
require_root; action=${1:-}; experiment_id=${2:-}; validate_experiment "$experiment_id"
directory=$(state_dir "$experiment_id")
case "$action" in
  inject)
    install -d -m 0750 "$directory"
    systemd-run --unit="kylin-aiops-db-${experiment_id}.service" --property=RuntimeMaxSec=300 \
      /usr/local/libexec/kylin-aiops/open-ops-fault-connections "$experiment_id"
    record_truth "$experiment_id" mysql_connection_exhaustion inject
    ;;
  recover)
    systemctl stop "kylin-aiops-db-${experiment_id}.service" 2>/dev/null || true
    /usr/local/libexec/kylin-aiops/terminate-fault-db-sessions ops_fault
    record_truth "$experiment_id" mysql_connection_exhaustion recover
    ;;
  *) echo "usage: $0 inject|recover EXPERIMENT_ID" >&2; exit 64 ;;
esac
