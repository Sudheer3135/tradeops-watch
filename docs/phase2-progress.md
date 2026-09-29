# Phase 2 progress

## Step 0: baseline reviewed
Read README, LEARNING, services, scripts, units, all four runbooks and all six
incident reports before changing code. Both services and the original Bash
health check passed in the actual Ubuntu VM. See `evidence/phase2/step0-health.txt`.

The VM initially has 2 CPUs, 2 GB RAM and a 10 GB disk. Phase 2 raises RAM to
4 GB. Application listeners remain on loopback; monitoring uses Linux host
networking inside the VM to reach them without exposing the application ports.
The Mac source is transferred into the VM because Desktop mounts were blocked.

The requested review gates are after Step 3 and after Step 7. Later steps are
not claimed complete until implemented and verified.

## Step 1: verified
Docker Engine 29.8.1 and Compose 5.5.1 are installed from the official arm64
repository. All seven pinned images started; readiness, both HTTP probes,
both TCP probes and all seven initial scrape targets passed. The VM reports
about 858 MiB used RAM of 3901 MiB at this sample; root disk is 66% used.
See `evidence/phase2/step1-readiness.txt` and `step1-resources-images.txt`.
Alloy's pipeline, the full dashboard, and Telegram remain for Steps 5, 6 and 4.

## Step 2: verified
Both services now expose the requested metrics using prometheus-client 0.26.0
in `/opt/tradeops/venv`. The installer passed twice. Real regression checks
confirmed increasing counters, histogram observations, original JSON fields,
HTTP 404 behavior, HTTP 503 during a brief feed outage, and automatic retries.
The unchanged Phase 1 monitoring/log/handover checks passed. Prometheus now
scrapes all nine configured targets successfully. Evidence: `step2-*.txt`.

## Step 3: verified; review continuation authorized
Ten alert rules passed promtool syntax/config validation and eleven synthetic
unit cases (all rules, waiting periods, exact disk boundaries, recent-start
expiry, and a transient failure). All ten live rules evaluate without errors.
Real recent-start P3 alerts reached Alertmanager, and a historical sample survived
a Prometheus container restart. Phase 1 health remains good. See `step3-*` evidence.

The user replied `continue` after the rule-validation update. This authorizes
continuation beyond this checkpoint. The separate review gate after Step 7 remains.
Synthetic rule tests are not real incident reports; full fault runs remain Step 9.

## Step 4: verified, with Telegram delivery pending credentials
Severity routes passed amtool checks. A synthetic API test verified same-service
inhibition and confirmed a different service remains active; test alerts were
then resolved. The optional token-file receiver configuration passed amtool in
a network-disabled container. Actual Telegram delivery remains untested because
no bot credentials were provided. See `step4-*` evidence and `telegram-setup.md`.

## Step 5: verified
Alloy validates and tails the actual `.log` files. Loki queries confirmed feed
and orders labels and parsed ERROR levels from real existing logs. All eight
LogQL examples executed successfully; empty results are recorded honestly when
no matching event occurred in the chosen window. No synthetic log entries were
inserted. See `step5-*` evidence; examples are in README and LEARNING.

## Step 6: verified
TradeOps Overview is automatically provisioned with all five required rows.
Grafana reports both data sources healthy, and all 19 panel queries execute
successfully through Grafana's own data-source proxies. The alerts panel was
empty because no alerts were firing at that sample. Verification is API-based;
no screenshot or visual rendering review is claimed. See `step6-*` evidence.

## Step 7: verified; continuation authorized
The installer migrated services to `/opt/tradeops/current` and passed another
rerun without creating a duplicate release. Real tests passed: good deployment,
a deliberately broken order service, health-gate rejection, automatic rollback,
manual rollback, and retention of three managed releases while protecting the
active/previous targets. The final Phase 1 healthcheck returned 0 and all nine
Prometheus targets were up. The real ServiceDown P1 fired during the failed
deployment and cleared after recovery; only expected recent-start P3 remained.
Loki contains the real ERROR deployment/rollback log records.

Evidence: `step7-deploy-rollback.txt`, `step7-final-health.txt`,
`step7-final-stack.txt`, both during/after alert API snapshots, and
`step7-loki-deployment-errors.json`. The broken code was confined to a temporary
fixture; the source repository's application code was not damaged.

The user approved continuation after this review. No screenshots were taken.

## Step 8: verified locally
The push/pull-request workflow runs the same `scripts/ci_check.sh` that passed
in Ubuntu: ShellCheck on every shell script, Ruff lint/format, 39 pytest cases,
Compose validation, Prometheus config/rules plus eleven rule cases, and
Alertmanager config validation. Python imports are safe for unit testing; alert
formatting and handover parsing share tested validation. See `step8-ci.txt`.
GitHub-hosted CI is pending publication; no Git remote is configured.
After the Step 9 script changes, the same `ci_check.sh` passed again inside
Ubuntu with the pinned tools (ruff 0.11.13, ShellCheck 0.9.0): `step9-ci.txt`.

## Step 9: verified
All seven faults ran against the live stack. For each one the verifier waited
for a clean baseline, injected the fault, saw the expected alert firing in both
Prometheus and Alertmanager, queried Grafana and Loki, applied the runbook fix,
saw the alert disappear from both APIs, and waited for the Bash check to return
0. fill-disk, cpu-spike and slow-feed passed in the first run.

That first run then aborted during kill-feed. The baseline had zero alerts;
the fault was injected at 17:03:26 UTC and the verifier then crashed with
`BrokenPipeError` because its terminal output closed. Its `finally` block ran
cleanup. The verifier now writes its own log, survives a closed terminal, puts
timeouts with named blocking alerts on every wait, and requires a cleared alert
to be absent in every state. kill-feed, stop-feed, block-port and net-delay then
passed. The aborted files are kept in `evidence/phase2/kill-feed-aborted-20260929/`.

During stop-feed Alertmanager marked both feed HealthProbeFailed alerts
`suppressed` by the ServiceDown/feed fingerprint while FeedErrorsHigh/orders
stayed active: `evidence/phase2/stop-feed/inhibition.json`. Cleanup and a final
healthy check are in `step9-safety-baseline.txt` and `step9-final-health.txt`.
Seven reports were generated as `incidents/phase2-20260929-*.md` and checked
against every timeline timestamp, alert snapshot and link.

## Step 10: documentation complete
LEARNING.md has the full file guide and questions 26–50. The spoken demo and
resume bullets were checked against evidence; README marks the current status
and links every evidence file.

## Publication and screenshots
The repository was published and the first hosted GitHub Actions run passed.
Twenty screenshots were captured with headless Chromium (times in
`docs/screenshots/README.md`). While capturing them, Grafana was repeatedly
OOM-killed at its 512 MiB container limit (kernel log: memory cgroup out of
memory, five container restarts). The limit is now 1 GiB; total container
limits (about 2.7 GB) still fit the 3.8 GB VM. The capture also exposed that
the checklist windows overlapped the next drill; each window now ends one
second before the next fault, and the incident reports were regenerated.
