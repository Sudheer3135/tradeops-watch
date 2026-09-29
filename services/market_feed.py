#!/usr/bin/env python3
"""Synthetic prices only: this lab never connects to a broker."""
import json
import logging
from logging.handlers import RotatingFileHandler
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger('feed')
log.setLevel(logging.INFO)
handler = RotatingFileHandler('/var/log/tradeops/market_feed.log', maxBytes=2_000_000, backupCount=3)
handler.setFormatter(logging.Formatter('%(asctime)sZ | %(levelname)s | %(message)s', '%Y-%m-%dT%H:%M:%S'))
handler.formatter.converter = time.gmtime
log.addHandler(handler)
prices = dict(NIFTY=24000.0, BANKNIFTY=50000.0, RELIANCE=2900.0, TCS=4000.0, INFY=1900.0)
lock = threading.Lock()


def update():
    while True:
        with lock:
            for symbol in prices:
                prices[symbol] = round(max(1, prices[symbol] * (1 + random.uniform(-0.001, 0.001))), 2)
            log.info('prices=%s', json.dumps(prices))
        time.sleep(1)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
    threading.Thread(target=update, daemon=True).start()
    log.info('feed listening on 127.0.0.1:9001')
    ThreadingHTTPServer(('127.0.0.1', 9001), Handler).serve_forever()
