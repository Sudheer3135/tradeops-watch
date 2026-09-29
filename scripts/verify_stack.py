#!/usr/bin/env python3
"""Readiness and real HTTP/TCP probe checks inside the Ubuntu VM."""

import json
import platform
import time
import urllib.request

if platform.system() != "Linux" or platform.node() != "tradeops":
    raise SystemExit("Run inside the tradeops Ubuntu VM")

urls = {
    "prometheus": "http://127.0.0.1:9090/-/ready",
    "alertmanager": "http://127.0.0.1:9093/-/ready",
    "grafana": "http://127.0.0.1:3000/api/health",
    "loki": "http://127.0.0.1:3100/ready",
    "alloy": "http://127.0.0.1:12345/-/ready",
    "node_exporter": "http://127.0.0.1:9100/metrics",
    "blackbox_exporter": "http://127.0.0.1:9115/metrics",
}


def fetch(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read().decode()


for name, url in urls.items():
    for attempt in range(30):
        try:
            fetch(url)
            print(f"PASS {name} ready: {url}", flush=True)
            break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)

for service, port in (("feed", 9001), ("orders", 9002)):
    for module, target in (
        ("http_2xx", f"http://127.0.0.1:{port}/health"),
        ("tcp_connect", f"127.0.0.1:{port}"),
    ):
        data = fetch(f"http://127.0.0.1:9115/probe?module={module}&target={target}")
        assert "\nprobe_success 1\n" in data, data
        print(f"PASS {service} {module} probe_success=1", flush=True)

metrics = fetch(urls["node_exporter"])
assert "node_memory_MemTotal_bytes" in metrics
assert "node_filesystem_avail_bytes{" in metrics
print("PASS host memory and filesystem metrics exist")
targets = json.loads(fetch("http://127.0.0.1:9090/api/v1/targets"))["data"]["activeTargets"]
for target in targets:
    print(target["labels"], target["health"], target.get("lastError", ""))
assert targets and all(target["health"] == "up" for target in targets)
print("PASS all configured Prometheus scrape targets up")
