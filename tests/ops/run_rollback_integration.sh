#!/usr/bin/env bash
# Run actual Compose health-failure rollback on an isolated runner, never on EC2.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP="$(mktemp -d)"
OLD="c39e5c50d936d45cade1e880737e3e34ab5ff70a"
BAD="1111111111111111111111111111111111111111"
PROJECT="chargepin-rollback-test-${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1}"

mkdir -p "$TEMP/ops/deploy-state"
cp "$ROOT/ops/deploy.py" "$TEMP/ops/deploy.py"
touch "$TEMP/.env"

# Minimal containers. Healthchecks pass only for the known-good SHA;
# the bad release keeps running but deliberately becomes unhealthy.
cat > "$TEMP/compose.prod.yml" <<'YAML'
services:
  backend:
    image: alpine:3.20
    command: ["sh", "-c", "sleep 600"]
    healthcheck:
      test: ["CMD-SHELL", "test \"$$CHARGEPIN_DEPLOY_SHA\" = \"c39e5c50d936d45cade1e880737e3e34ab5ff70a\""]
      interval: 2s
      timeout: 2s
      retries: 2
      start_period: 0s
    environment:
      CHARGEPIN_DEPLOY_SHA: "${CHARGEPIN_DEPLOY_SHA}"
  frontend:
    image: alpine:3.20
    command: ["sh", "-c", "sleep 600"]
    healthcheck:
      test: ["CMD-SHELL", "test \"$$CHARGEPIN_DEPLOY_SHA\" = \"c39e5c50d936d45cade1e880737e3e34ab5ff70a\""]
      interval: 2s
      timeout: 2s
      retries: 2
      start_period: 0s
    environment:
      CHARGEPIN_DEPLOY_SHA: "${CHARGEPIN_DEPLOY_SHA}"
YAML

export COMPOSE_PROJECT_NAME="$PROJECT"
cleanup() {
  CHARGEPIN_DEPLOY_SHA="$OLD" docker compose -f "$TEMP/compose.prod.yml" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$TEMP"
}
trap cleanup EXIT

echo "Deploying healthy baseline in isolated Docker project"
python3 "$TEMP/ops/deploy.py" "$OLD"

echo "Injecting unhealthy release; deployment must fail then rollback"
if python3 "$TEMP/ops/deploy.py" "$BAD"; then
  echo "FAIL: unhealthy release incorrectly reported success"
  exit 1
fi

[[ "$(cat "$TEMP/ops/deploy-state/last_successful_sha")" == "$OLD" ]] || {
  echo "FAIL: stable SHA was changed by failed rollout"
  exit 1
}

for service in backend frontend; do
  CID="$(CHARGEPIN_DEPLOY_SHA="$OLD" docker compose -f "$TEMP/compose.prod.yml" ps -q "$service")"
  [[ -n "$CID" ]] || { echo "FAIL: $service missing after rollback"; exit 1; }
  STATUS="$(docker inspect --format '{{.State.Health.Status}}' "$CID")"
  [[ "$STATUS" == "healthy" ]] || { echo "FAIL: $service is $STATUS"; exit 1; }
done

echo "PASS: actual Docker healthcheck failure triggered rollback to healthy baseline"
