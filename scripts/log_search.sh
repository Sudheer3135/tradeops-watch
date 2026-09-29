#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob
logs=(/var/log/tradeops/market_feed.log* /var/log/tradeops/order_service.log*)
case "${1:-}" in
errors)
    minutes=${2:-5}
    [[ $minutes =~ ^[0-9]+$ ]] || { echo 'minutes must be nonnegative integer' >&2; exit 2; }
    cutoff=$(date -u -d "$minutes minutes ago" +%FT%TZ)
    if ((${#logs[@]})); then awk -v since="$cutoff" '$1>=since && /\| ERROR \|/' "${logs[@]}" | sort; fi
    ;;
top-errors)
    if ((${#logs[@]})); then awk -F ' \\| ' '$2=="ERROR"{print $3}' "${logs[@]}" | sort | uniq -c | sort -nr | head -20; fi
    ;;
latency)
    if ((${#logs[@]})); then awk '/latency_ms=/{split($0,a,"latency_ms="); v=a[2]+0;s+=v;n++;if(v>m)m=v}END{if(n)printf "orders=%d average_ms=%.2f max_ms=%.2f\n",n,s/n,m;else print "No orders yet"}' "${logs[@]}"; fi
    ;;
follow) tail -F /var/log/tradeops/*.log ;;
alerts) [[ ! -f /var/log/tradeops/alerts.log ]] || { grep "^$(date -u +%F)" /var/log/tradeops/alerts.log || true; } ;;
*) echo 'Usage: log_search.sh {errors [minutes]|top-errors|latency|follow|alerts}'; exit 2 ;;
esac
