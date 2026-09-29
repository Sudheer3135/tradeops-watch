#!/usr/bin/env bash
# Shared with monitoring and tested independently without root or side effects.
format_alert_line() {
    local timestamp=$1 severity=$2 check=$3 details=$4 runbook=$5 field
    [[ $severity =~ ^P[123]$ ]] || return 2
    for field in "$timestamp" "$check" "$details" "$runbook"; do
        [[ -n $field && $field != *'|'* && $field != *$'\n'* ]] || return 2
    done
    printf '%s | %s | %s | %s | %s\n' "$timestamp" "$severity" "$check" "$details" "$runbook"
}
