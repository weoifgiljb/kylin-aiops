#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
require_root; action=${1:-}; experiment_id=${2:-}; interface=${3:-}; validate_experiment "$experiment_id"
[[ "$interface" =~ ^(eth|ens|enp)[A-Za-z0-9_.-]{1,31}$ ]] || { echo "invalid interface" >&2; exit 64; }
directory=$(state_dir "$experiment_id")
case "$action" in
  inject)
    install -d -m 0750 "$directory"
    tc qdisc show dev "$interface" | grep -q 'netem' && { echo "existing netem rule; refusing" >&2; exit 65; }
    tc qdisc add dev "$interface" root handle 1: netem delay "${FAULT_DELAY:-200ms}" loss "${FAULT_LOSS:-5%}"
    printf '%s\n' "$interface" > "$directory/netem.interface"
    record_truth "$experiment_id" network_degradation inject
    ;;
  recover)
    [[ -f "$directory/netem.interface" ]] || { echo "no matching experiment rule" >&2; exit 66; }
    [[ "$(<"$directory/netem.interface")" == "$interface" ]] || { echo "interface mismatch" >&2; exit 66; }
    tc qdisc del dev "$interface" root handle 1: netem
    rm -f -- "$directory/netem.interface"
    record_truth "$experiment_id" network_degradation recover
    ;;
  *) echo "usage: $0 inject|recover EXPERIMENT_ID INTERFACE" >&2; exit 64 ;;
esac
