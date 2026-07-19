#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
require_root; action=${1:-}; experiment_id=${2:-}; validate_experiment "$experiment_id"
unit="kylin-aiops-cpu-${experiment_id}.service"
case "$action" in
  inject) systemd-run --unit="$unit" --property=RuntimeMaxSec=300 stress-ng --cpu 1 --cpu-load 90; record_truth "$experiment_id" cpu_saturation inject ;;
  recover) systemctl stop "$unit" 2>/dev/null || true; record_truth "$experiment_id" cpu_saturation recover ;;
  *) echo "usage: $0 inject|recover EXPERIMENT_ID" >&2; exit 64 ;;
esac
