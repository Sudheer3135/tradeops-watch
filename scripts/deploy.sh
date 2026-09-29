#!/usr/bin/env bash
# Deploy immutable application code; operational recovery scripts remain stable.
set -euo pipefail
# shellcheck source=deploy_common.sh
source "$(dirname "$0")/deploy_common.sh"
require_deploy_vm
version=${1:-}
[[ $version =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] || {
    echo 'Usage: deploy.sh <version> (letters, digits, dot, underscore, hyphen; max 64)'; exit 2;
}
source_root=${TRADEOPS_SOURCE_DIR:-/home/ubuntu/tradeops-watch}
target="/opt/tradeops/releases/$version"
old=$(readlink -f /opt/tradeops/current)
old_previous=
if [[ -L /opt/tradeops/previous ]]; then old_previous=$(readlink -f /opt/tradeops/previous); fi
valid_release "$old" || { echo 'Install a baseline release first'; exit 1; }
[[ ! -e $target && ! -L $target ]] || { echo 'Release already exists; use a new version'; exit 1; }
for file in services/market_feed.py services/order_service.py requirements.txt; do
    [[ -f $source_root/$file ]] || { echo "Missing source file: $file"; exit 1; }
done
cmp -s "$source_root/requirements.txt" /opt/tradeops/requirements.txt || {
    echo 'Dependency changes require an installer/venv update; code-only rollback uses pinned shared dependencies'; exit 1;
}
switched=0
on_exit() {
    local status=$1
    trap - EXIT
    if (( switched )); then
        set +e
        deploy_log ERROR "Deploy $version failed or was interrupted (exit=$status); automatic rollback to $(basename "$old")"
        touch "$target/.failed"
        if set_release_link "$old" current; then
            if [[ -n $old_previous ]]; then set_release_link "$old_previous" previous; else rm -f /opt/tradeops/previous; fi
            systemctl restart tradeops-feed tradeops-orders
            if wait_for_health 360; then
                deploy_log INFO "Automatic rollback recovered $(basename "$old")"
            else
                deploy_log ERROR 'Rollback health failed; escalate and inspect journalctl immediately'
            fi
        else
            deploy_log ERROR 'Could not restore current symlink; escalate immediately'
        fi
        prune_releases
        (( status != 0 )) || status=1
    fi
    exit "$status"
}
trap 'on_exit "$?"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
install -d "$target/services" "$target/scripts" "$target/runbooks"
install -m 644 "$source_root"/services/*.py "$target/services/"
install -m 644 "$source_root/requirements.txt" "$target/requirements.txt"
if [[ -d $source_root/scripts ]]; then
    find "$source_root/scripts" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) -exec install -m 755 {} "$target/scripts/" \;
fi
if [[ -d $source_root/runbooks ]]; then install -m 644 "$source_root"/runbooks/*.md "$target/runbooks/"; fi
date -u +%FT%TZ > "$target/.tradeops-release"
deploy_log INFO "Deploy $version from $source_root; previous=$(basename "$old")"
switched=1
set_release_link "$old" previous
set_release_link "$target" current
systemctl restart tradeops-feed tradeops-orders
if ! wait_for_health 45; then
    deploy_log ERROR "Rejecting $version: service/resource health gate did not pass"
    exit 1
fi
switched=0
deploy_log INFO "Deploy $version passed healthcheck; current=$target"
prune_releases
