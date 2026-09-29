#!/usr/bin/env bash
# Run in Ubuntu with Python dev dependencies and Docker installed; no chaos.
set -euo pipefail
cd "$(dirname "$0")/.."
find scripts -name '*.sh' -print0 | xargs -0 shellcheck -x -P scripts
python3 -m ruff check services scripts tests
python3 -m ruff format --check services scripts tests
python3 -m pytest -q
GRAFANA_ADMIN_PASSWORD=ci-validation-only docker compose --env-file monitoring/.env.example -f monitoring/docker-compose.yml config --quiet
docker run --rm --network none --entrypoint promtool -v "$PWD/monitoring/prometheus:/etc/prometheus:ro" prom/prometheus:v3.15.0 check config /etc/prometheus/prometheus.yml
docker run --rm --network none --entrypoint promtool -v "$PWD/monitoring/prometheus:/etc/prometheus:ro" prom/prometheus:v3.15.0 check rules /etc/prometheus/rules/tradeops-alerts.yml
docker run --rm --network none --entrypoint promtool -v "$PWD/monitoring/prometheus:/etc/prometheus:ro" prom/prometheus:v3.15.0 test rules /etc/prometheus/rules-tests.yml
docker run --rm --network none --entrypoint amtool -v "$PWD/monitoring/alertmanager:/etc/alertmanager:ro" prom/alertmanager:v0.34.1 check-config /etc/alertmanager/alertmanager.yml
echo 'PASS all CI checks'
