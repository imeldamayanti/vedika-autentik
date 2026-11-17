"""Serve the website for local demos with caching turned off.

python3 -m http.server sends no Cache-Control header, so Chrome reuses an old app-v3.js after the code
changes, even on a normal reload. Usage: python3 tools/web.py PORT (serves the current directory on 127.0.0.1).
"""

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(NoCacheHandler, directory="."))
    print(f"Serving http://localhost:{port} (tanpa cache)", flush=True)
    server.serve_forever()
