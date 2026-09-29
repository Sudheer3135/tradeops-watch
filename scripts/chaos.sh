#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -s) == Linux && $(hostname) == tradeops && $EUID == 0 ]] || { echo 'REFUSED: requires sudo inside Linux VM named tradeops'; exit 1; }
mkdir -p /var/lib/tradeops
rule=(-o lo -p tcp --dport 9001 -m comment --comment tradeops-chaos -j REJECT)
fix_port() { while iptables -C OUTPUT "${rule[@]}" 2>/dev/null; do iptables -D OUTPUT "${rule[@]}"; done; }
fix_delay() { if [[ -f /var/lib/tradeops/net-delay ]]; then tc qdisc del dev lo root 2>/dev/null || true; rm -f /var/lib/tradeops/net-delay; fi; }
fix_cpu() { systemctl stop tradeops-chaos-cpu.service 2>/dev/null || true; }
case "${1:-}" in
kill-feed) pid=$(systemctl show tradeops-feed -p MainPID --value); if [[ ! $pid =~ ^[0-9]+$ ]] || (( pid <= 1 )); then echo "Feed has no running PID"; exit 1; fi; kill -9 "$pid"; echo 'Killed feed; systemd restarts after 5s. Undo: fix-feed' ;;
stop-feed) systemctl stop tradeops-feed; echo 'Feed stopped. Undo: fix-feed' ;;
fix-feed) systemctl start tradeops-feed ;;
fill-disk)
    [[ ! -e /var/lib/tradeops/disk-fill ]] || { echo 'Already filled; run fix-disk'; exit 1; }
    read -r size used available < <(df -B1 --output=size,used,avail / | tail -1)
    target=$((size * 87 / 100 - used))
    maximum=$((available - 600*1024*1024))
    (( target > maximum )) && target=$maximum
    (( target > 0 )) || { echo 'Insufficient safe space or disk already above target'; exit 1; }
    fallocate -l "$target" /var/lib/tradeops/disk-fill
    df -h /; echo 'Disk filled toward 87%; at least 600 MiB reserved at allocation. Undo: fix-disk'
    ;;
fix-disk) rm -f /var/lib/tradeops/disk-fill ;;
cpu-spike)
    systemctl reset-failed tradeops-chaos-cpu.service 2>/dev/null || true
    # The child bash must expand nproc and i, not this parent shell.
    # shellcheck disable=SC2016
    systemd-run --unit=tradeops-chaos-cpu --collect --property=RuntimeMaxSec=125 /usr/bin/timeout 120 /bin/bash -c 'for ((i=0;i<$(nproc);i++)); do yes > /dev/null & done; wait'
    echo 'CPU workers run for 120s, systemd also enforces 125s limit. Undo: fix-cpu'
    ;;
fix-cpu) fix_cpu ;;
block-port) iptables -C OUTPUT "${rule[@]}" 2>/dev/null || iptables -I OUTPUT 1 "${rule[@]}"; echo 'Loopback TCP 9001 rejected. Undo: fix-port' ;;
fix-port) fix_port ;;
net-delay)
    [[ ! -f /var/lib/tradeops/net-delay ]] || { echo 'Delay already installed'; exit 1; }
    # add refuses to overwrite an existing root qdisc.
    tc qdisc add dev lo root netem delay 500ms
    touch /var/lib/tradeops/net-delay
    echo 'Loopback delay 500ms (affects both services). Undo: fix-delay'
    ;;
fix-delay) fix_delay ;;
cleanup) fix_cpu; fix_port; fix_delay; rm -f /var/lib/tradeops/disk-fill; systemctl start tradeops-feed tradeops-orders; echo 'All TradeOps chaos changes removed' ;;
*) echo 'Usage: chaos.sh {kill-feed|stop-feed|fix-feed|fill-disk|fix-disk|cpu-spike|fix-cpu|block-port|fix-port|net-delay|fix-delay|cleanup}'; exit 2 ;;
esac
