#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
require_root; action=${1:-}; experiment_id=${2:-}; validate_experiment "$experiment_id"
directory=$(state_dir "$experiment_id"); file="$directory/disk-fill.bin"
case "$action" in
  inject) install -d -m 0750 "$directory"; fallocate -l "${FAULT_DISK_SIZE:-512M}" "$file"; record_truth "$experiment_id" disk_full inject ;;
  recover) [[ "$file" == /var/lib/kylin-aiops/faults/*/disk-fill.bin ]] || exit 70; rm -f -- "$file"; record_truth "$experiment_id" disk_full recover ;;
  *) echo "usage: $0 inject|recover EXPERIMENT_ID" >&2; exit 64 ;;
esac
