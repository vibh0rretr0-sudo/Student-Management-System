"""HTTP server entrypoint (plain stdlib http.server — no framework).

Run from the project root:
    python backend/server.py
Then open http://127.0.0.1:8000 (config.py sets host/port).

The life of a request (memorize this for the viva):

    browser -> TCP socket (ThreadingHTTPServer, one thread per request)
            -> _build_request()   parses path/query/body into a Request
            -> dispatch()         matches the URL against the route table
                                  (backend/routes/__init__.py) and calls
                                  the handler; handler exceptions become
                                  400/403/404/500 pages, never tracebacks
            -> _send()            writes status + headers + body back

The handler itself returns a Response object; it never touches the
socket. That separation is what keeps routes testable without a server.
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

# Reject bodies over ~1 MB: form posts here are tiny, and the cap stops
# a rogue client from exhausting memory (a hand-rolled DoS guard).
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
        # One try/except wraps the whole exchange: malformed input becomes
        # a plain 400/413 instead of an empty reply, and dispatch()'s own
        # error mapping turns handler exceptions into friendly pages.
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
        # urlsplit separates ?query from the path; unquote() then percent-
        # decodes ONLY the path (e.g. /students/6), leaving ?a=b&c=d intact
        # for the handler to parse.
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
        # Content-Length + no keep-alive trickery: one clean response per
        # connection keeps the client logic trivially correct.
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        for name, value in response.headers:
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response.body)

    def log_message(self, fmt, *args):
        # BaseHTTPRequestHandler calls this per request; printing to stdout
        # (redirected to a log file when run detached) gives a free audit trail.
        print(f"{self.address_string()} {fmt % args}")


class _BodyTooLarge(Exception):
    pass


def _plain(status, message):
    from backend.routes.helpers import Response

    return Response(status, message, "text/plain; charset=utf-8")


def main():
    # ThreadingHTTPServer = a thread per request, so one slow page never
    # blocks the rest of the app. Threading also means shared globals (the
    # session dict) must be lock-protected — see backend/auth.py.
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
