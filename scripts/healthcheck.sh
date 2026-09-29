#!/usr/bin/env bash
# Thresholds may be overridden for a supervised demo; cron uses these defaults.
CPU_THRESHOLD=${CPU_THRESHOLD:-85}
MEM_THRESHOLD=${MEM_THRESHOLD:-85}
DISK_THRESHOLD=${DISK_THRESHOLD:-85}
ERROR_THRESHOLD=${ERROR_THRESHOLD:-5}
COOLDOWN=${COOLDOWN:-600}
set -uo pipefail
# shellcheck source=alert_format.sh
source "$(dirname "$0")/alert_format.sh"
[[ $EUID == 0 ]] || { echo 'Run with sudo'; exit 2; }
mkdir -p /var/lib/tradeops /var/log/tradeops
exec 9>/var/lib/tradeops/healthcheck.lock
flock -w 15 9 || { echo "Another health check is still running; no result collected"; exit 1; }
# Optional root-owned runtime configuration is not present in the repository.
# shellcheck disable=SC1091
[[ ! -f /etc/tradeops/alert.env ]] || source /etc/tradeops/alert.env
now=$(date -u +%s)
active=$(mktemp /var/lib/tradeops/active.XXXXXX)
rc=0
alert() {
    local severity=$1 check=$2 details=$3 book=$4 last=0 line
    [[ $severity == P1 ]] && rc=2
    [[ $severity != P1 && $rc == 0 ]] && rc=1
    printf '%s|%s|%s\n' "$severity" "$check" "$details" >> "$active"
    [[ ! -f /var/lib/tradeops/last-$check ]] || read -r last < "/var/lib/tradeops/last-$check"
    if (( now - last >= COOLDOWN )); then
        line=$(format_alert_line "$(date -u +%FT%TZ)" "$severity" "$check" "$details" "runbooks/$book.md")
        echo "$line" | tee -a /var/log/tradeops/alerts.log
        echo "$now" > "/var/lib/tradeops/last-$check"
        if [[ -n ${TELEGRAM_BOT_TOKEN:-} && -n ${TELEGRAM_CHAT_ID:-} ]]; then
            curl -fsS --max-time 4 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" --data-urlencode "text=$line" >/dev/null 2>&1 || true
        fi
    fi
}
for pair in feed:9001 orders:9002; do
    name=${pair%:*}; port=${pair#*:}
    systemctl is-active --quiet "tradeops-$name" || alert P1 "service-$name" 'service inactive' service-down
    ss -tulpn | awk '{print $5}' | grep -qE ":${port}$" || alert P1 "port-$port" 'port not listening' port-blocked
    curl -fsS --max-time 2 "http://127.0.0.1:$port/health" >/dev/null 2>&1 || alert P1 "http-$port" 'health endpoint failed or degraded' port-blocked
    # systemd may restart faster than cron: detect a recent abnormal exit too.
    restarts=$(systemctl show "tradeops-$name" -p NRestarts --value)
    old=0; [[ ! -f /var/lib/tradeops/restarts-$name ]] || read -r old < "/var/lib/tradeops/restarts-$name"
    [[ $restarts =~ ^[0-9]+$ ]] && (( restarts > old )) && alert P2 "restart-$name" "automatic restarts increased $old -> $restarts" service-down
    echo "$restarts" > "/var/lib/tradeops/restarts-$name"
done
read -r total1 idle1 < <(awk '/^cpu / {s=0;for(i=2;i<=9;i++)s+=$i; print s,$5+$6}' /proc/stat)
sleep 1
read -r total2 idle2 < <(awk '/^cpu / {s=0;for(i=2;i<=9;i++)s+=$i; print s,$5+$6}' /proc/stat)
cpu=$((100*(total2-total1-idle2+idle1)/(total2-total1)))
mem=$(awk '/MemTotal/{t=$2}/MemAvailable/{a=$2}END{printf "%.0f",100*(t-a)/t}' /proc/meminfo)
disk=$(df --output=pcent / | tail -1 | tr -dc '0-9')
(( cpu >= CPU_THRESHOLD )) && alert P2 cpu "CPU $cpu% >= $CPU_THRESHOLD%" high-cpu
(( mem >= MEM_THRESHOLD )) && alert P2 memory "Memory $mem% >= $MEM_THRESHOLD%" high-cpu
(( disk >= DISK_THRESHOLD )) && alert P2 disk "Disk $disk% >= $DISK_THRESHOLD%" disk-full
errors=$(/opt/tradeops/scripts/log_search.sh errors 5 | wc -l)
(( errors > ERROR_THRESHOLD )) && alert P2 error-rate "$errors errors in last 5 minutes > $ERROR_THRESHOLD" service-down
mv "$active" /var/lib/tradeops/active-alerts
printf '%s\n' "$now" > /var/lib/tradeops/last-check
printf '%s | healthcheck exit=%s CPU=%s%% memory=%s%% disk=%s%% errors=%s\n' "$(date -u +%FT%TZ)" "$rc" "$cpu" "$mem" "$disk" "$errors"
exit "$rc"
