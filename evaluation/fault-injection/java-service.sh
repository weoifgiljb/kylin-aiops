#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
require_root; action=${1:-}; experiment_id=${2:-}; validate_experiment "$experiment_id"
case "$action" in
  inject) systemctl stop kylin-demo-app.service; record_truth "$experiment_id" java_service_down inject ;;
  recover) systemctl start kylin-demo-app.service; record_truth "$experiment_id" java_service_down recover ;;
  *) echo "usage: $0 inject|recover EXPERIMENT_ID" >&2; exit 64 ;;
esac
