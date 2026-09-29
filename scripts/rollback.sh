#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=deploy_common.sh
source "$(dirname "$0")/deploy_common.sh"
require_deploy_vm
current=$(readlink -f /opt/tradeops/current)
previous=$(readlink -f /opt/tradeops/previous || true)
if ! valid_release "$current" || ! valid_release "$previous" || [[ -f $previous/.failed ]]; then
    echo 'No valid previous release available'; exit 1;
fi
switched=0
on_exit() {
    local status=$1
    trap - EXIT
    if (( switched )); then
        set +e
        deploy_log ERROR "Manual rollback failed or interrupted; restoring $(basename "$current")"
        set_release_link "$current" current
        set_release_link "$previous" previous
        systemctl restart tradeops-feed tradeops-orders
        if wait_for_health 360; then
            deploy_log INFO "Restored $(basename "$current") after failed rollback"
        else
            deploy_log ERROR 'Restoration failed health checks; escalate immediately'
        fi
        (( status != 0 )) || status=1
    fi
    exit "$status"
}
trap 'on_exit "$?"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
deploy_log INFO "Manual rollback $(basename "$current") -> $(basename "$previous")"
switched=1
set_release_link "$previous" current
set_release_link "$current" previous
systemctl restart tradeops-feed tradeops-orders
wait_for_health 360
switched=0
deploy_log INFO "Manual rollback passed; current=$(basename "$previous")"
prune_releases
