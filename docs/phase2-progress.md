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
