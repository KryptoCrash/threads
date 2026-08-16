#!/usr/bin/env python3
"""Threads app server: serves threads.html and a token-gated sync API.

GET  /            -> the app (threads.html)
GET  /api?token=X -> {"ok": true, "data": <threads state>}
POST /api         -> body {"token": X, "data": <threads state>} ; atomic write

Data lives in threads.json next to this script, so local tools (and Claude)
can read it directly. Token is read from ~/.config/threads-server/token.
"""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(BASE, 'threads.html')
DATA = os.path.join(BASE, 'threads.json')
TOKEN = open(os.path.expanduser('~/.config/threads-server/token')).read().strip()
LOCK = threading.Lock()
EMPTY = {"version": 1, "threads": [], "tombstones": {}}


def read_data():
    try:
        with open(DATA) as f:
            return json.load(f)
    except Exception:
        return EMPTY


def write_data(obj):
    fd, tmp = tempfile.mkstemp(dir=BASE, prefix='.threads-', suffix='.tmp')
    with os.fdopen(fd, 'w') as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, DATA)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype='application/json'):
        raw = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ('/', '/index.html', '/threads', '/threads/'):
            with open(APP, 'rb') as f:
                self._send(200, f.read(), 'text/html; charset=utf-8')
        elif u.path == '/api':
            q = parse_qs(u.query)
            if q.get('token', [''])[0] != TOKEN:
                self._send(403, json.dumps({"ok": False, "error": "bad token"}))
                return
            with LOCK:
                self._send(200, json.dumps({"ok": True, "data": read_data()}))
        else:
            self._send(404, json.dumps({"ok": False, "error": "not found"}))

    def do_POST(self):
        if urlparse(self.path).path != '/api':
            self._send(404, json.dumps({"ok": False, "error": "not found"}))
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        except Exception:
            self._send(400, json.dumps({"ok": False, "error": "bad json"}))
            return
        if body.get('token') != TOKEN:
            self._send(403, json.dumps({"ok": False, "error": "bad token"}))
            return
        data = body.get('data')
        if not isinstance(data, dict) or not isinstance(data.get('threads'), list):
            self._send(400, json.dumps({"ok": False, "error": "not a threads payload"}))
            return
        with LOCK:
            write_data(data)
        self._send(200, json.dumps({"ok": True}))

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


if __name__ == '__main__':
    port = int(os.environ.get('THREADS_PORT', '8787'))
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
