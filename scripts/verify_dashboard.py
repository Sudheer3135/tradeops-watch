#!/usr/bin/env python3
"""Verify Grafana provisioning and execute every dashboard query via its proxies."""

import base64
import json
import platform
import time
import urllib.parse
import urllib.request
from pathlib import Path

if platform.system() != "Linux" or platform.node() != "tradeops":
    raise SystemExit("Run inside tradeops")
root = Path(__file__).resolve().parent.parent
password = next(
    line.split("=", 1)[1]
    for line in (root / "monitoring/.env").read_text().splitlines()
    if line.startswith("GRAFANA_ADMIN_PASSWORD=")
)
auth = "Basic " + base64.b64encode(("admin:" + password).encode()).decode()


def fetch(path):
    request = urllib.request.Request(
        "http://127.0.0.1:3000" + path, headers={"Authorization": auth}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


for attempt in range(30):
    try:
        result = fetch("/api/dashboards/uid/tradeops-overview")
        break
    except Exception:
        if attempt == 29:
            raise
        time.sleep(2)
assert result["meta"]["provisioned"]
model = result["dashboard"]
assert model["title"] == "TradeOps Overview"
rows = [p["title"] for p in model["panels"] if p["type"] == "row"]
assert rows == ["Service health", "Trading", "System", "Alerts", "Logs"]
print("PASS dashboard provisioned automatically; all five rows exist")
for uid in ("prometheus", "loki"):
    health = fetch(f"/api/datasources/uid/{uid}/health")
    assert health["status"] == "OK", health
    print("PASS Grafana datasource", uid, health["status"])
count = 0
for panel in model["panels"]:
    if panel["type"] == "row":
        continue
    for target in panel["targets"]:
        expression = target["expr"]
        uid = panel["datasource"]["uid"]
        if uid == "prometheus":
            path = "/api/v1/query?" + urllib.parse.urlencode({"query": expression})
        else:
            path = "/loki/api/v1/query_range?" + urllib.parse.urlencode(
                {
                    "query": expression,
                    "start": str(time.time_ns() - 3600 * 10**9),
                    "end": str(time.time_ns()),
                    "limit": 20,
                }
            )
        data = fetch(f"/api/datasources/proxy/uid/{uid}" + path)
        assert data["status"] == "success", data
        if uid == "prometheus" and panel["title"] != "Currently firing Prometheus alerts":
            assert data["data"]["result"], f"Missing live data: {panel['title']}"
        print("PASS", panel["title"], target["refId"], "series=", len(data["data"]["result"]))
        count += 1
print(f"PASS all {count} live panel queries through Grafana; no screenshots taken")
evidence = root / "docs/evidence/phase2"
evidence.mkdir(parents=True, exist_ok=True)
(evidence / "step6-dashboard-api.json").write_text(json.dumps(result, indent=2) + "\n")
