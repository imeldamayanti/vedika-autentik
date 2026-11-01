#!/usr/bin/env python3
"""Server lokal untuk PoC Gemini Live.

Menyajikan index.html dan endpoint GET /token yang membuat token sementara
(sekali pakai, kedaluwarsa cepat) dari GEMINI_API_KEY di backend/.env.
Key tidak pernah dikirim ke browser dan tidak pernah dicetak.

Pakai: python3 tools/gemini-live/server.py   (lalu buka http://localhost:8766)
"""
import datetime
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FOLDER = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(FOLDER, "..", "..", "backend", ".env")
PORT = int(os.environ.get("PORT", "8766"))
URL_TOKEN = "https://generativelanguage.googleapis.com/v1beta/auth_tokens"


def baca_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        for baris in open(ENV, encoding="utf-8"):
            if baris.startswith("GEMINI_API_KEY="):
                return baris.split("=", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return ""


def buat_token(key):
    sekarang = datetime.datetime.now(datetime.timezone.utc)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    isi = {
        "uses": 1,
        "expireTime": iso(sekarang + datetime.timedelta(minutes=15)),
        "newSessionExpireTime": iso(sekarang + datetime.timedelta(minutes=2)),
    }
    req = urllib.request.Request(
        URL_TOKEN,
        data=json.dumps(isi).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=20))["name"]


class Penangan(BaseHTTPRequestHandler):
    def kirim(self, kode, tipe, isi):
        self.send_response(kode)
        self.send_header("Content-Type", tipe)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(isi)))
        self.end_headers()
        self.wfile.write(isi)

    def do_GET(self):
        if self.path == "/token":
            key = baca_key()
            if not key:
                return self.kirim(500, "application/json", b'{"galat":"GEMINI_API_KEY belum ada di backend/.env"}')
            try:
                token = buat_token(key)
            except urllib.error.HTTPError as e:
                # hanya kode status; isi respons tidak diteruskan
                return self.kirim(502, "application/json", json.dumps({"galat": f"Google menolak (HTTP {e.code})"}).encode())
            except Exception:
                return self.kirim(502, "application/json", b'{"galat":"gagal menghubungi Google"}')
            return self.kirim(200, "application/json", json.dumps({"token": token}).encode())
        if self.path in ("/", "/index.html"):
            return self.kirim(200, "text/html; charset=utf-8", open(os.path.join(FOLDER, "index.html"), "rb").read())
        self.kirim(404, "text/plain", b"tidak ada")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"Gemini Live PoC: http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Penangan).serve_forever()
