"""HTTP server entrypoint (plain stdlib http.server — no framework).

Run from the project root:
    python backend/server.py
Then open http://127.0.0.1:8000 (config.py sets host/port).
"""
import sys
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Make `backend` importable when launched as a script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
import backend.routes  # noqa: E402,F401  (importing registers every route)
from backend.routes.helpers import Request, dispatch  # noqa: E402

MAX_BODY_BYTES = 1_000_000


class SMSHandler(BaseHTTPRequestHandler):
    server_version = "SMSServer/1.0"

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_HEAD(self):
        self._handle()

    def _handle(self):
        try:
            request = self._build_request()
        except _BodyTooLarge:
            self._send(_plain(413, "Request body too large."))
            return
        except Exception:
            traceback.print_exc()
            self._send(_plain(400, "Malformed request."))
            return
        self._send(dispatch(request))

    def _build_request(self):
        parsed = urllib.parse.urlsplit(self.path)
        body = ""
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            if length > MAX_BODY_BYTES:
                raise _BodyTooLarge()
            body = self.rfile.read(length).decode("utf-8", errors="replace")
        return Request(
            self.command,
            urllib.parse.unquote(parsed.path),
            parsed.query,
            body,
            self.headers,
        )

    def _send(self, response):
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        for name, value in response.headers:
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response.body)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}")


class _BodyTooLarge(Exception):
    pass


def _plain(status, message):
    from backend.routes.helpers import Response

    return Response(status, message, "text/plain; charset=utf-8")


def main():
    server = ThreadingHTTPServer((config.HOST, config.PORT), SMSHandler)
    print(f"SMS running at http://{config.HOST}:{config.PORT}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
