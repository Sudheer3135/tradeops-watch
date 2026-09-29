#!/usr/bin/env python3
"""Poll synthetic prices; record fake orders, never real trades."""

import json
import logging
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

log = logging.getLogger("orders")
log.setLevel(logging.INFO)


def configure_logging():
    handler = RotatingFileHandler(
        "/var/log/tradeops/order_service.log", maxBytes=2_000_000, backupCount=3
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)sZ | %(levelname)s | %(message)s", "%Y-%m-%dT%H:%M:%S")
    )
    handler.formatter.converter = time.gmtime
    log.addHandler(handler)


lock = threading.Lock()
state = {"feed_status": "starting", "orders_placed": 0, "last_success": None}
ORDERS = Counter("tradeops_orders_total", "Fake orders placed", ["side"])
for side in ("BUY", "SELL"):
    ORDERS.labels(side)
LATENCY = Histogram(
    "tradeops_order_latency_seconds",
    "Duration of each order-cycle feed fetch, including failed or slow attempts",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2),
)
FEED_ERRORS = Counter("tradeops_feed_errors_total", "Failed or slow feed fetches")
LAST_FETCH = Gauge(
    "tradeops_last_successful_price_fetch_timestamp", "Unix timestamp of last accepted price fetch"
)


def order_side(price, previous_price):
    return "BUY" if price <= previous_price else "SELL"


def trade():
    previous = {}
    while True:
        start = time.monotonic()
        try:
            with urllib.request.urlopen("http://127.0.0.1:9001/prices", timeout=1.5) as response:
                prices = json.load(response)
            latency = (time.monotonic() - start) * 1000
            if latency > 400:
                raise TimeoutError("feed slow: %.2f ms" % latency)
            with lock:
                state.update(feed_status="ok", last_success=time.time())
                LAST_FETCH.set(state["last_success"])
                for symbol, price in prices.items():
                    side = order_side(price, previous.get(symbol, price))
                    ORDERS.labels(side).inc()
                    state["orders_placed"] += 1
                    log.info(
                        "order side=%s symbol=%s price=%.2f latency_ms=%.2f",
                        side,
                        symbol,
                        price,
                        latency,
                    )
            previous = prices
        except Exception as exc:
            FEED_ERRORS.inc()
            with lock:
                state["feed_status"] = "unreachable"
            log.error("feed unreachable: %s", exc)
        finally:
            LATENCY.observe(time.monotonic() - start)
        time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            payload = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        with lock:
            data = dict(state)
        status = 200 if data["feed_status"] == "ok" else 503
        if self.path != "/health":
            status, data = 404, {"error": "not found"}
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    configure_logging()
    threading.Thread(target=trade, daemon=True).start()
    log.info("orders listening on 127.0.0.1:9002")
    ThreadingHTTPServer(("127.0.0.1", 9002), Handler).serve_forever()
