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
