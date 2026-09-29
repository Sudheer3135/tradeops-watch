#!/usr/bin/env bash
# Supplement the real chaos drills with monitor, cron and log checks.
set -euo pipefail
[[ $(uname -s) == Linux && $(hostname) == tradeops && $EUID == 0 ]] || exit 1
health=/opt/tradeops/scripts/healthcheck.sh
expected() {
    local want=$1 rc=0
    shift
    "$@" || rc=$?
    echo "EXPECTED=$want ACTUAL=$rc"
    [[ $rc == "$want" ]]
}
echo "MONITOR CHECKS $(date -u +%FT%TZ)"
expected 0 "$health"
echo 'Threshold override validates memory detection without exhausting the VM'
expected 1 env MEM_THRESHOLD=0 "$health"
before=$(grep -c ' | memory | ' /var/log/tradeops/alerts.log || true)
expected 1 env MEM_THRESHOLD=0 "$health"
after=$(grep -c ' | memory | ' /var/log/tradeops/alerts.log || true)
[[ $before == "$after" ]]
echo "DEDUP PASS memory notification count unchanged: $before -> $after"
expected 0 "$health"
/opt/tradeops/scripts/log_search.sh errors 5
/opt/tradeops/scripts/log_search.sh top-errors
/opt/tradeops/scripts/log_search.sh latency
/opt/tradeops/scripts/log_search.sh alerts
/opt/tradeops/scripts/handover_report.py --hours 8
logrotate -d /etc/logrotate.d/tradeops
systemctl is-enabled tradeops-feed tradeops-orders cron
systemctl is-active tradeops-feed tradeops-orders cron
systemctl show tradeops-feed tradeops-orders -p User -p Restart -p RestartUSec
ss -tulpn
cat /etc/cron.d/tradeops
cat /var/log/tradeops/cron.log
[[ -s /var/log/tradeops/cron.log ]]
echo 'PASS monitor checks'
