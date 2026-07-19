#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
bundle=${1:-"$repo/dist/kylin-aiops-offline"}
mkdir -p "$bundle/wheels" "$bundle/images" "$bundle/artifacts"

python -m pip download --dest "$bundle/wheels" "$repo[dev]"
cp "$repo/pyproject.toml" "$bundle/"
cp -a "$repo/apps" "$repo/services" "$repo/agents" "$repo/packages" "$repo/infra" \
  "$repo/evaluation" "$repo/lab" "$repo/tools" "$repo/docs" "$bundle/"

docker compose -f "$repo/infra/compose/compose.yml" build
images=$(docker compose -f "$repo/infra/compose/compose.yml" config --images | sort -u)
docker save -o "$bundle/images/kylin-aiops-images.tar" $images

[[ -f "$repo/infra/offline/artifacts/opentelemetry-javaagent.jar" ]] && \
  cp "$repo/infra/offline/artifacts/opentelemetry-javaagent.jar" "$bundle/artifacts/"
(cd "$bundle" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
echo "offline bundle prepared at $bundle"
