#!/usr/bin/env python3
"""Poll synthetic prices; record fake orders, never real trades."""
import json
import logging
from logging.handlers import RotatingFileHandler
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger('orders')
log.setLevel(logging.INFO)
handler = RotatingFileHandler('/var/log/tradeops/order_service.log', maxBytes=2_000_000, backupCount=3)
handler.setFormatter(logging.Formatter('%(asctime)sZ | %(levelname)s | %(message)s', '%Y-%m-%dT%H:%M:%S'))
handler.formatter.converter = time.gmtime
log.addHandler(handler)
lock = threading.Lock()
state = {'feed_status': 'starting', 'orders_placed': 0, 'last_success': None}


def trade():
    previous = {}
    while True:
        start = time.monotonic()
        try:
            with urllib.request.urlopen('http://127.0.0.1:9001/prices', timeout=1.5) as response:
                prices = json.load(response)
            latency = (time.monotonic() - start) * 1000
            if latency > 400:
                raise TimeoutError('feed slow: %.2f ms' % latency)
            with lock:
                state.update(feed_status='ok', last_success=time.time())
                for symbol, price in prices.items():
                    side = 'BUY' if price <= previous.get(symbol, price) else 'SELL'
                    state['orders_placed'] += 1
                    log.info('order side=%s symbol=%s price=%.2f latency_ms=%.2f', side, symbol, price, latency)
            previous = prices
        except Exception as exc:
            with lock:
                state['feed_status'] = 'unreachable'
            log.error('feed unreachable: %s', exc)
        time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with lock:
            data = dict(state)
        status = 200 if data['feed_status'] == 'ok' else 503
        if self.path != '/health':
            status, data = 404, {'error': 'not found'}
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    threading.Thread(target=trade, daemon=True).start()
    log.info('orders listening on 127.0.0.1:9002')
    ThreadingHTTPServer(('127.0.0.1', 9002), Handler).serve_forever()
