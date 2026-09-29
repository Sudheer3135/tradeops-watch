#!/usr/bin/env python3
"""Real metrics/API regression, including a short controlled feed outage."""

import json
import platform
import subprocess
import time
import urllib.error
import urllib.request

from prometheus_client.parser import text_string_to_metric_families

if platform.system() != "Linux" or platform.node() != "tradeops":
    raise SystemExit("Run inside tradeops as root with the project virtualenv")


def get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as response:
        return response.read().decode()


def metrics(port):
    return {
        (sample.name, tuple(sorted(sample.labels.items()))): sample.value
        for family in text_string_to_metric_families(get(port, "/metrics"))
        for sample in family.samples
    }


def value(data, name):
    return data[(name, ())]


before_feed = metrics(9001)
before_orders = metrics(9002)
prices = json.loads(get(9001, "/prices"))
assert set(prices) == {"NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "INFY"}
assert all(price > 0 for price in prices.values())
assert value(before_feed, "tradeops_feed_up") == 1
assert value(before_orders, "tradeops_last_successful_price_fetch_timestamp") > 0
assert json.loads(get(9001, "/health")) == {"status": "ok"}
initial = json.loads(get(9002, "/health"))
assert set(initial) == {"feed_status", "orders_placed", "last_success"}
time.sleep(3)
after_feed, after_orders = metrics(9001), metrics(9002)
for symbol in prices:
    key = ("tradeops_prices_published_total", (("symbol", symbol),))
    assert after_feed[key] > before_feed[key]
    assert after_feed[("tradeops_last_price", (("symbol", symbol),))] > 0
assert value(after_orders, "tradeops_order_latency_seconds_count") > value(
    before_orders, "tradeops_order_latency_seconds_count"
)
assert json.loads(get(9002, "/health"))["orders_placed"] > initial["orders_placed"]
for side in ("BUY", "SELL"):
    assert ("tradeops_orders_total", (("side", side),)) in after_orders
for port in (9001, 9002):
    try:
        get(port, "/missing")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("Unknown path must remain 404")
print(
    "PASS counters advance, gauges exist, histogram records cycles, original routes/schema preserved",
    flush=True,
)

try:
    subprocess.run(["systemctl", "stop", "tradeops-feed"], check=True)
    time.sleep(3)
    failed = metrics(9002)
    assert value(failed, "tradeops_feed_errors_total") > value(
        after_orders, "tradeops_feed_errors_total"
    )
    try:
        get(9002, "/health")
    except urllib.error.HTTPError as exc:
        assert exc.code == 503
        assert json.loads(exc.read())["feed_status"] == "unreachable"
    else:
        raise AssertionError("Degraded orders must return HTTP 503")
    print("PASS feed outage increments errors; /metrics stays 200 while /health is 503", flush=True)
finally:
    subprocess.run(["systemctl", "start", "tradeops-feed"], check=True)
    time.sleep(4)
assert json.loads(get(9002, "/health"))["feed_status"] == "ok"
print("PASS feed recovered and orders resumed")
print(get(9001, "/metrics"))
print(get(9002, "/metrics"))
