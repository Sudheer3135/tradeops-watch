# Deployments and rollback

These commands run inside `multipass shell tradeops`. This is a single-VM
restart deployment, so there is a brief interruption; it is not blue-green or
zero-downtime deployment.

## Files and pointers

```text
/opt/tradeops/venv/                  pinned shared Python dependency
/opt/tradeops/scripts/               stable operational/recovery tools
/opt/tradeops/releases/<version>/    immutable service code and source snapshots
/opt/tradeops/current -> releases/...  code systemd starts
/opt/tradeops/previous -> releases/... last healthy rollback target
/var/log/tradeops/deploy.log          UTC deployment and rollback history
```

The installer creates a bootstrap release when migrating the earlier layout.
Running it again with unchanged service code restarts the same release. Changed
service code goes through the deployment health gate. Existing Phase 1 tools
keep their stable `/opt/tradeops/scripts/` paths. Scripts/runbooks are copied
into each release as a source snapshot; production operations tools are updated
by the installer, not by switching the application symlink.

## Deploy your source

First copy your updated Mac source into `/home/ubuntu/tradeops-watch` in the VM
using the documented transfer method. Then:

```bash
sudo /opt/tradeops/scripts/deploy.sh demo-v1
readlink -f /opt/tradeops/current
sudo /opt/tradeops/scripts/healthcheck.sh
sudo tail -n 20 /var/log/tradeops/deploy.log
```

Use a new version each time: existing release directories are never overwritten.
Only letters, digits, dots, underscores and hyphens are accepted. For an alternate
source folder, use `sudo env TRADEOPS_SOURCE_DIR=/path/to/source .../deploy.sh v2`.
The source must contain both services and `requirements.txt`.

The script copies code, atomically replaces symlinks, restarts services, and
runs the **original** healthcheck. It gives the new release up to 45 seconds to
pass. Nonzero health (including disk/CPU/error-rate warnings) rejects it and
restores the prior pointers and services automatically. The rollback gets up to
six minutes for trailing error-window warnings to clear; it never erases logs
to fake a healthy result. A failed deploy returns nonzero even after successful
recovery, so a caller cannot mistake the rejected version for a successful deploy.

SIGTERM/SIGINT and ordinary script errors trigger recovery after a switch.
SIGKILL or a VM power loss cannot be trapped; inspect the pointers and use the
manual rollback command after restart. A deployment lock prevents concurrent
changes. If recovery itself fails, the script prints an escalation message.

## Manual rollback

```bash
sudo /opt/tradeops/scripts/rollback.sh
readlink -f /opt/tradeops/current
sudo /opt/tradeops/scripts/healthcheck.sh
```

This swaps the current and previous healthy releases, restarts services, and
checks health. If that fails it restores the release that was active before the
rollback. A marked failed candidate is never selected as a manual rollback target.

After each completed transaction, cleanup retains three managed releases,
protecting the current and previous targets and keeping the newest remaining
candidate. Only directories carrying the project's release marker are eligible
for deletion. Failed candidates may remain briefly for diagnosis and are later
pruned by this same policy. Logs are retained separately and rotated by logrotate.

## Dependency scope

This implementation rolls back application code, not the VM or database.
`/opt/tradeops/venv` is shared and pinned to the installed requirements. Deploy
rejects a different requirements file; dependency upgrades need a separately
planned installer/venv update. It does not claim per-release dependency rollback.

## Actual verification

`step7-deploy-rollback.txt` records a good deployment, a real deliberately broken
order service, automatic recovery, explicit rollback, and retention checks.
The broken code exists only in a temporary source fixture; repository services
are not corrupted. Re-run the test only in this disposable lab:

```bash
sudo bash /home/ubuntu/tradeops-watch/scripts/verify_deploy.sh
```

This performs real restarts and release cleanup. Grafana's restart graph should
show those starts, and the logs panel should show ERROR deployment entries.
The P3 recent-start alert is expected for ten minutes after a deployment.
