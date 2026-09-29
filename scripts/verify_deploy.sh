#!/usr/bin/env bash
# Actual release/rollback integration test; no existing source code is corrupted.
set -euo pipefail
[[ $(uname -s) == Linux && $(hostname) == tradeops && $EUID == 0 ]] || exit 1
root=$(cd "$(dirname "$0")/.." && pwd)
fixture=$(mktemp -d /tmp/tradeops-release-test.XXXXXX)
trap 'rm -rf "$fixture"' EXIT
stamp=$(date -u +%Y%m%dT%H%M%S)
good="verified-$stamp"
broken="broken-$stamp"
echo "START deploy test $(date -u +%FT%TZ)"
/opt/tradeops/scripts/healthcheck.sh
TRADEOPS_SOURCE_DIR="$root" /opt/tradeops/scripts/deploy.sh "$good"
[[ $(basename "$(readlink -f /opt/tradeops/current)") == "$good" ]]
echo 'PASS good version deployed'
install -d "$fixture/services"
install -m 644 "$root"/services/*.py "$fixture/services/"
install -m 644 "$root/requirements.txt" "$fixture/requirements.txt"
printf '%s\n' 'raise RuntimeError("Intentional broken-release test: order service cannot start")' > "$fixture/services/order_service.py"
result=0
TRADEOPS_SOURCE_DIR="$fixture" /opt/tradeops/scripts/deploy.sh "$broken" || result=$?
[[ $result != 0 ]]
[[ $(basename "$(readlink -f /opt/tradeops/current)") == "$good" ]]
[[ -f /opt/tradeops/releases/$broken/.failed ]]
/opt/tradeops/scripts/healthcheck.sh
echo "PASS broken version rejected (exit=$result) and automatic rollback restored $good"
journalctl -u tradeops-orders --since '3 minutes ago' --no-pager
/opt/tradeops/scripts/rollback.sh
[[ $(basename "$(readlink -f /opt/tradeops/previous)") == "$good" ]]
echo 'PASS explicit rollback to previous healthy release'
# Two additional immutable deployments exercise last-three retention.
for suffix in retained-a retained-b; do
    TRADEOPS_SOURCE_DIR="$root" /opt/tradeops/scripts/deploy.sh "$suffix-$stamp"
done
count=$(find /opt/tradeops/releases -mindepth 2 -maxdepth 2 -name .tradeops-release | wc -l)
(( count == 3 ))
for name in current previous; do
    path=$(readlink -f "/opt/tradeops/$name")
    [[ -d $path && -f $path/.tradeops-release && ! -f $path/.failed ]]
    echo "$name=$path"
done
/opt/tradeops/scripts/healthcheck.sh
curl -fsS http://127.0.0.1:9002/health; echo
find /opt/tradeops/releases -mindepth 1 -maxdepth 1 -type d | sort
echo "PASS only last three managed releases retained; active and previous are healthy $(date -u +%FT%TZ)"
