#!/usr/bin/env python3
"""Synthetic prices only: this lab never connects to a broker."""
import json
import logging
from logging.handlers import RotatingFileHandler
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

log = logging.getLogger('feed')
log.setLevel(logging.INFO)

def configure_logging():
    handler = RotatingFileHandler('/var/log/tradeops/market_feed.log', maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)sZ | %(levelname)s | %(message)s', '%Y-%m-%dT%H:%M:%S'))
    handler.formatter.converter = time.gmtime
    log.addHandler(handler)

prices = dict(NIFTY=24000.0, BANKNIFTY=50000.0, RELIANCE=2900.0, TCS=4000.0, INFY=1900.0)
lock = threading.Lock()
PUBLISHED = Counter('tradeops_prices_published_total', 'Synthetic price updates', ['symbol'])
LAST_PRICE = Gauge('tradeops_last_price', 'Latest synthetic price', ['symbol'])
FEED_UP = Gauge('tradeops_feed_up', 'Price publisher is running')
for symbol, price in prices.items():
    PUBLISHED.labels(symbol)
    LAST_PRICE.labels(symbol).set(price)


def next_price(price, change=None):
    """One positive random-walk step; explicit change supports deterministic tests."""
    if change is None:
        change = random.uniform(-0.001, 0.001)
    return round(max(1, price * (1 + change)), 2)


def update():
    while True:
        with lock:
            for symbol in prices:
                prices[symbol] = next_price(prices[symbol])
                PUBLISHED.labels(symbol).inc()
                LAST_PRICE.labels(symbol).set(prices[symbol])
            FEED_UP.set(1)
            log.info('prices=%s', json.dumps(prices))
        time.sleep(1)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            payload = generate_latest()
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        with lock:
            data = dict(prices) if self.path == '/prices' else {'status': 'ok'}
        status = 200 if self.path in ('/prices', '/health') else 404
        payload = json.dumps(data if status == 200 else {'error': 'not found'}).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    configure_logging()
    threading.Thread(target=update, daemon=True).start()
    log.info('feed listening on 127.0.0.1:9001')
    ThreadingHTTPServer(('127.0.0.1', 9001), Handler).serve_forever()
