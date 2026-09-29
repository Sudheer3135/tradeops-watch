#!/usr/bin/env bash
# Real integration tests. Run only inside the disposable tradeops VM.
set -euo pipefail
[[ $(uname -s) == Linux && $(hostname) == tradeops && $EUID == 0 ]] || exit 1
root=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$root/docs/evidence"
chaos=/opt/tradeops/scripts/chaos.sh
health=/opt/tradeops/scripts/healthcheck.sh
trap '"$chaos" cleanup' EXIT
check() {
    local result=0
    "$health" || result=$?
    echo "HEALTHCHECK_EXIT=$result"
    return "$result"
}
healthy() {
    local attempt
    for attempt in $(seq 1 24); do
        if check; then
            curl -fsS --max-time 2 http://127.0.0.1:9001/health; echo
            curl -fsS --max-time 2 http://127.0.0.1:9002/health; echo
            return 0
        fi
        sleep 15
    done
    return 1
}
scenario() {
    local name=$1 fix=$2 rc=0
    echo "START $name $(date -u +%FT%TZ)"
    "$chaos" "$name"
    if [[ $name == kill-feed ]]; then sleep 6; else sleep 5; fi
    check || rc=$?
    (( rc > 0 )) || { echo 'FAIL: no fault detected'; return 1; }
    echo 'ACTIVE ALERTS'; cat /var/lib/tradeops/active-alerts
    echo 'RUNBOOK DIAGNOSTICS'
    case "$name" in
    kill-feed|stop-feed) systemctl --no-pager status tradeops-feed tradeops-orders || true; journalctl -u tradeops-feed -n 12 --no-pager ;;
    fill-disk) df -h /; du -sh /var/lib/tradeops /var/log/tradeops ;;
    cpu-spike) ps -eo pid,user,stat,pcpu,pmem,args --sort=-pcpu | head -12; free -m ;;
    block-port|net-delay) ss -tulpn; iptables -L OUTPUT -n -v; tc qdisc show dev lo; /opt/tradeops/scripts/log_search.sh errors 5 ;;
    esac
    echo "FIX $fix $(date -u +%FT%TZ)"
    "$chaos" "$fix"
    sleep 4
    healthy
    echo "PASS $name $(date -u +%FT%TZ)"
}
healthy > "$root/docs/evidence/baseline.txt" 2>&1
for pair in kill-feed:fix-feed stop-feed:fix-feed fill-disk:fix-disk cpu-spike:fix-cpu block-port:fix-port net-delay:fix-delay; do
    name=${pair%:*}
    scenario "$name" "${pair#*:}" > "$root/docs/evidence/$name.txt" 2>&1
    echo "PASS $name; evidence saved"
done
"$chaos" cleanup
healthy > "$root/docs/evidence/final-health.txt" 2>&1
/opt/tradeops/scripts/handover_report.py > "$root/docs/evidence/handover.txt"
