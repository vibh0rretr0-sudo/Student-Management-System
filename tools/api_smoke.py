"""Live API smoke test: log in as student + professor and hit every endpoint.

Runs against the live server (default http://127.0.0.1:5017). Verifies each
reachable endpoint returns HTTP < 500 and, for JSON endpoints, ok:true.
Endpoints that legitimately 4xx for role/ownership reasons are noted, not failed.
"""
import sys
import json
from pathlib import Path

import urllib.request
import urllib.error
import http.cookiejar

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5017"
DEMO_PASSWORD = "Jecrc@2026"


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        self.csrf = None

    def request(self, method, path, body=None, headers=None, raw=False):
        url = BASE + path
        data = None
        hdrs = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
        if self.csrf:
            hdrs["X-CSRF-Token"] = self.csrf
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            resp = self.opener.open(req, timeout=20)
            status = resp.status
            payload = resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            payload = e.read()
        if raw:
            return status, payload
        try:
            parsed = json.loads(payload)
        except Exception:
            parsed = {"_nonjson": payload[:200].decode("utf-8", "replace")}
        # The CSRF token is returned in the JSON body of /api/auth/csrf.
        if isinstance(parsed, dict):
            token = (parsed.get("data") or {}).get("csrf_token")
            if token:
                self.csrf = token
        return status, parsed


def login(client, role, identifier):
    status, body = client.request("GET", "/api/auth/csrf")
    status, body = client.request(
        "POST", "/api/auth/login",
        {"role": role, "identifier": identifier, "password": DEMO_PASSWORD},
    )
    return status, body


def main():
    results = []

    def check(client, method, path, body=None, label=None):
        status, body_out = client.request(method, path, body)
        ok = status < 500
        api_ok = True
        if isinstance(body_out, dict) and body_out.get("ok") is False:
            api_ok = False
        tag = "OK " if (ok and api_ok) else "FAIL"
        name = label or f"{method} {path}"
        detail = ""
        if not ok:
            detail = f" -> HTTP {status} {str(body_out)[:120]}"
        elif not api_ok:
            err = body_out.get("error", {})
            detail = f" -> ok:false {err.get('code')}: {err.get('message', '')[:80]}"
        results.append((tag, name, detail))
        return status, body_out

    # ---- Student -----------------------------------------------------
    sc = Client()
    st, body = login(sc, "student", "26CSAI001")
    results.append(("OK " if st == 200 else "FAIL", "student login 26CSAI001", f"-> {st}"))
    check(sc, "GET", "/api/common/me")
    check(sc, "GET", "/api/student/overview")
    check(sc, "GET", "/api/student/attendance?page=1&per_page=5")
    check(sc, "GET", "/api/student/timetable")
    check(sc, "GET", "/api/student/assignments")
    check(sc, "GET", "/api/student/announcements")
    check(sc, "GET", "/api/student/schedule/today")
    check(sc, "GET", "/api/student/profile")
    check(sc, "GET", "/api/common/notifications")
    check(sc, "GET", "/api/common/search?q=attend")
    check(sc, "GET", "/api/common/campus-images")
    # ownership: student must NOT reach a professor-only endpoint
    st2, b2 = sc.request("GET", "/api/professor/overview")
    blocked = st2 in (401, 403)
    results.append(("OK " if blocked else "FAIL",
                    "student blocked from /api/professor/overview", f"-> {st2}"))

    # ---- Professor ---------------------------------------------------
    pc = Client()
    st, body = login(pc, "professor", "rakesh.sharma")
    results.append(("OK " if st == 200 else "FAIL", "professor login rakesh.sharma", f"-> {st}"))
    check(pc, "GET", "/api/common/me")
    check(pc, "GET", "/api/professor/overview")
    check(pc, "GET", "/api/professor/batches")
    check(pc, "GET", "/api/professor/profile")
    check(pc, "GET", "/api/professor/schedule/today")
    check(pc, "GET", "/api/professor/announcements")
    check(pc, "GET", "/api/professor/assignments")
    # pick real ids for the deeper endpoints
    _, batches = pc.request("GET", "/api/professor/batches")
    batch_id = None
    subject_id = None
    if isinstance(batches, dict) and batches.get("data"):
        items = batches["data"].get("batches") or batches["data"].get("items") or []
        if items:
            batch_id = items[0].get("id")
            subs = items[0].get("subjects") or []
            if subs:
                subject_id = subs[0].get("id")
    if batch_id:
        check(pc, "GET", f"/api/professor/students?batch_id={batch_id}")
        check(pc, "GET", f"/api/professor/attendance?batch_id={batch_id}&date=2026-10-23")
    _, assigns = pc.request("GET", "/api/professor/assignments")
    aid = None
    if isinstance(assigns, dict) and assigns.get("data"):
        aitems = assigns["data"].get("items") or assigns["data"].get("assignments") or []
        if aitems:
            aid = aitems[0].get("id")
    if aid:
        check(pc, "GET", f"/api/professor/assignments/{aid}/submissions")
        check(pc, "GET", f"/api/professor/assignments/{aid}/download")
    # role isolation: professor must NOT reach student-only endpoint
    st2, b2 = pc.request("GET", "/api/student/overview")
    blocked = st2 in (401, 403)
    results.append(("OK " if blocked else "FAIL",
                    "professor blocked from /api/student/overview", f"-> {st2}"))

    # ---- Anonymous ---------------------------------------------------
    ac = Client()
    st, b = ac.request("GET", "/api/student/overview")
    results.append(("OK " if st in (401, 403) else "FAIL",
                    "anon blocked from /api/student/overview", f"-> {st}"))

    # ---- Report ------------------------------------------------------
    fails = 0
    for tag, name, detail in results:
        if tag == "FAIL":
            fails += 1
        print(f"[{tag}] {name}{detail}")
    print(f"\n=== {len(results) - fails}/{len(results)} checks passed, {fails} failed ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
