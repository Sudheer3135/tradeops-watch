# Evidence-backed resume bullets

Use two or three bullets you can explain. These describe a personal lab, not
employment, production availability, actual exchange trading, or latency gains.

- Built a Linux operations lab with two Python services under systemd and a
  seven-container Prometheus, Alertmanager, Grafana, Loki and Alloy monitoring
  stack on an ARM64 Ubuntu VM; verified nine scrape targets, HTTP/TCP probes,
  and all 19 provisioned dashboard queries through Grafana APIs.
  Evidence: `docs/evidence/phase2/step1-readiness.txt`, `step2-*.txt`,
  `step6-*.txt`.
- Implemented versioned releases, health-gated deployment, automatic and manual
  rollback, and three-release retention; verified recovery from an intentionally
  broken application deployment using saved service, alert and log evidence.
  Evidence: `docs/evidence/phase2/step7-deploy-rollback.txt`,
  `step7-final-health.txt` and the Step 7 alert snapshots.
- Added a GitHub Actions workflow for ShellCheck, Ruff, 39 pytest cases, Compose
  validation and Prometheus/Alertmanager config checks; ran the same pipeline
  successfully inside Ubuntu, including eleven Prometheus rule test cases.
  Evidence: `docs/evidence/phase2/step8-ci.txt`. Describe hosted CI as pending
  until you push and observe a successful Actions run.

The final Phase 2 incident index records which real chaos scenarios completed;
use only its passed runs when discussing incident response. Do not claim
Telegram delivery, screenshot review, zero-downtime deployment, production HFT
experience, uptime percentages, or performance improvements: those were not
established by these tests.
