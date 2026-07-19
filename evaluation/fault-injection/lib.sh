#!/usr/bin/env bash
set -euo pipefail

require_root() {
  [[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "must run as root" >&2; exit 77; }
}

validate_experiment() {
  [[ ${1:-} =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$ ]] || {
    echo "invalid experiment id" >&2
    exit 64
  }
}

state_dir() {
  printf '/var/lib/kylin-aiops/faults/%s' "$1"
}

record_truth() {
  local experiment_id=$1 fault_type=$2 action=$3
  local directory
  directory=$(state_dir "$experiment_id")
  install -d -m 0750 "$directory"
  printf '{"experiment_id":"%s","fault_type":"%s","action":"%s","timestamp":"%s"}\n' \
    "$experiment_id" "$fault_type" "$action" "$(date --iso-8601=seconds)" >> "$directory/truth.jsonl"
}
