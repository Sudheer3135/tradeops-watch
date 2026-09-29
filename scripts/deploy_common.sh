#!/usr/bin/env bash
# Shared transaction helpers, sourced by deploy.sh and rollback.sh.
require_deploy_vm() {
    [[ $(uname -s) == Linux && $(hostname) == tradeops && $EUID == 0 ]] || {
        echo 'Run with sudo inside the tradeops Ubuntu VM'; exit 1;
    }
    mkdir -p /opt/tradeops/releases /var/lib/tradeops /var/log/tradeops
    exec 8>/var/lib/tradeops/deploy.lock
    flock -w 15 8 || { echo 'Another deployment is running'; exit 1; }
    touch /var/log/tradeops/deploy.log
    chown tradeops:tradeops /var/log/tradeops/deploy.log
}
deploy_log() {
    local level=$1
    shift
    printf '%s | %s | %s\n' "$(date -u +%FT%TZ)" "$level" "$*" | tee -a /var/log/tradeops/deploy.log
}
set_release_link() {
    local target=$1 name=$2 temporary="/opt/tradeops/.$2.$$"
    ln -s "$target" "$temporary"
    mv -Tf "$temporary" "/opt/tradeops/$name"
}
valid_release() {
    local target=$1
    [[ $target == /opt/tradeops/releases/* && -d $target && ! -L $target && -f $target/.tradeops-release ]]
}
wait_for_health() {
    local duration=$1 deadline=$((SECONDS + $1)) result
    # Give the feed and the next order fetch a chance to become ready.
    sleep 4
    while true; do
        result=0
        /opt/tradeops/scripts/healthcheck.sh || result=$?
        if (( result == 0 )); then return 0; fi
        if (( SECONDS >= deadline )); then
            deploy_log ERROR "Health gate failed after ${duration}s; healthcheck exit=$result"
            return 1
        fi
        sleep 3
    done
}
prune_releases() {
    python3 - <<'PY'
from pathlib import Path
import shutil
root = Path('/opt/tradeops/releases')
protected = set()
for name in ('current', 'previous'):
    link = Path('/opt/tradeops') / name
    if link.is_symlink():
        protected.add(link.resolve())
managed = sorted((p for p in root.iterdir() if p.is_dir() and not p.is_symlink() and (p / '.tradeops-release').is_file()), key=lambda p: (p / '.tradeops-release').stat().st_mtime_ns, reverse=True)
keep = set(protected)
for path in managed:
    if len(keep) < 3:
        keep.add(path)
for path in managed:
    if path not in keep:
        shutil.rmtree(path)
        print('Pruned old managed release:', path.name)
PY
}
