#!/usr/bin/env bash
set -euo pipefail
bundle=$(cd "$(dirname "$0")/../.." && pwd)
cd "$bundle"
sha256sum --check SHA256SUMS
docker load -i images/kylin-aiops-images.tar
python3 -m venv /opt/kylin-aiops/venv
/opt/kylin-aiops/venv/bin/pip install --no-index --find-links wheels .
install -d -m 0750 /etc/kylin-aiops /var/lib/kylin-aiops /var/log/kylin-aiops
echo "bundle verified and installed; create .env and agent.env before enabling services"
