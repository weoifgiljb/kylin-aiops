#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
require_root; action=${1:-}; experiment_id=${2:-}; validate_experiment "$experiment_id"
unit="kylin-aiops-memory-${experiment_id}.service"
case "$action" in
  inject) systemd-run --unit="$unit" --property=MemoryMax=768M --property=RuntimeMaxSec=300 stress-ng --vm 1 --vm-bytes 640M; record_truth "$experiment_id" memory_pressure inject ;;
  recover) systemctl stop "$unit" 2>/dev/null || true; record_truth "$experiment_id" memory_pressure recover ;;
  *) echo "usage: $0 inject|recover EXPERIMENT_ID" >&2; exit 64 ;;
esac
