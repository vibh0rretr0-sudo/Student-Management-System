# Code Tour — how to read this project

A guided path through the codebase: what order to read in, what each file
does, and the ten functions that carry the design. Everything referenced
here exists in the code with viva-style comments already in place — this
tour is the index, the code is the textbook.

Companion docs: [`UI_GUIDE.md`](UI_GUIDE.md) (the design system),
[`OVERVIEW.md`](OVERVIEW.md) (purpose, architecture, key decisions).

---

## 1. The reading order (each layer only knows the one below it)

| Step | Read | You learn |
|---|---|---|
| 1 | `backend/server.py` | How a request enters: socket → `Request` → `dispatch()` → `Response` → socket |
| 2 | `backend/routes/helpers.py` | The route table, the `@route` decorator, and the exception-to-HTTP contract (400/403/404/500) |
| 3 | `backend/routes/template.py` + `frontend/templates/layout.html` | The 15-line template engine and the one-shell/many-pages layout |
| 4 | `backend/auth.py` | PBKDF2 hashing, constant-time compare, the in-memory session store |
| 5 | `backend/models/db.py`, then any model | The parameterized-SQL guarantee and the connect-per-query pattern |
| 6 | `backend/models/courses.py` → `students.py` → `attendance.py` → `assessments.py` → `stats.py` | The domain rules: ownership, roll uniqueness, professor double-booking, the 75% and missing=0 rules |
| 7 | `backend/cpp_engine.py` → `cpp_module/src/sms_engine.cpp` | The subprocess + TSV bridge and the pure-computation engine |
| 8 | `backend/routes/` (the eight modules) | Handlers as thin coordinators: validate → model → render |
| 9 | `frontend/static/css/style.css` + `docs/UI_GUIDE.md` | Zero-JS flat design: tokens, `:has()` theme toggle, entrance staggering, reduced-motion |
| 10 | `scripts/setup_db.py`, `scripts/build_cpp.py` | Reproducible setup: two-account DB security, warning-clean build |

## 2. The map

```
backend/
  server.py           entrypoint: ThreadingHTTPServer + error-safe request loop
  auth.py             password hashing + session store (thread-safe dict)
  cpp_engine.py       subprocess bridge: Python data → C++ → parsed results
  config.example.py   template for the git-ignored config.py
  models/             ALL SQL lives here (parameterized, nothing else)
    db.py             connection factory + fetch_all/fetch_one/execute
    professors.py     accounts + login verification
    students.py       CRUD, search, can_edit() permission rule
    courses.py        courses, sections, double-booking check, enrollment
    assessments.py    assignments, exams, marks, grade aggregates for C++
    attendance.py     day upserts, per-course counts for C++
    stats.py          dashboard aggregates (AVG/SUM pushed into SQL)
  routes/             URL → handler, one module per domain area
    helpers.py        Request/Response, route table, dispatch + error mapping
    template.py       {{placeholder}} engine + layout/page shell
    validation.py     parse/require helpers → ValueError → 400 page
    static_routes.py  /static/* serving with path-containment defense
    auth_routes.py    login/logout
    dashboard_routes.py  stat cards + the two CSS chart builders
    student_routes.py    list/detail/forms/delete
    course_routes.py     courses + enrollment, owner-gated
    assessment_routes.py assignments/exams + marks grids
    attendance_routes.py marking page + eligibility summary
    analytics_routes.py  grades / course rank / section rankings
cpp_module/
  src/sms_engine.cpp  the engine: grades | attendance | rank modes
  tests/              fixture inputs; outputs are hand-verified values
scripts/
  setup_db.py         root-only setup: creates sms DB + least-privilege sms_app
  build_cpp.py        g++ -std=c++14 -Wall -Wextra -O2
```

## 3. The ten functions to understand first

1. **`helpers.dispatch()`** — the heart of the app. Attaches the session
   user *before* routing (even 404 pages know who you are), matches
   method + pattern, and maps exceptions to pages in ONE place.
2. **`helpers.route()`** — self-registering decorator. Importing a route
   module is all it takes to add features; no central registry to edit.
3. **`server.SMSHandler._handle()`** — the safety net: malformed input
   becomes 400/413 instead of a dropped connection; handlers never touch
   the socket, which is why routes are testable without a server.
4. **`auth.verify_password()`** — PBKDF2 with `hmac.compare_digest`.
   The two security ideas worth explaining under pressure.
5. **`db.execute()`** — every write in the app flows through here;
   `%s` placeholders are the SQL-injection guarantee.
6. **`courses._ensure_professor_free()`** — interval-overlap SQL
   (`start < new_end AND new_start < end`), strict inequalities so
   back-to-back slots are legal; parameters *look* swapped but aren't.
   The rule: one professor cannot teach two overlapping slots in the
   same batch, while different professors still can.
7. **`assessments.course_grade_inputs()`** — the grading policy in SQL:
   two CROSS JOINs for course-wide denominators ("conducted"
   assessments), two LEFT JOINs for each student's percentage sums,
   `COALESCE` for the confirmed missing = 0 rule.
8. **`cpp_engine.compute_grades()`** — the bridge pattern all three
   wrappers share: build stdin lines, run, merge results back by
   `student_id`. Note `_clean()` neutralizing tabs in names.
9. **`sms_engine.cpp :: run_rank()`** — deterministic sort (final %
   desc, roll asc) plus competition ranking (1, 2, 2, 4) in one pass.
10. **`dashboard_routes._attendance_chart_html()`** — the CSS contract:
    Python emits `--w` (bar width) and `--i` (stagger index); the
    stylesheet animates them. The 75%-threshold marker renders only on
    bars actually below the cutoff.

## 4. The invariants that keep it honest

- **Every SQL statement is parameterized** — no string-built SQL anywhere.
- **Ownership is enforced server-side** in models/handlers, never by
  hiding links (hidden links are convenience; `can_edit`/`is_owner` are the law).
- **Missing data renders as "—", never as a fabricated 0** (stats → dashboard).
- **Boundaries are inclusive and pinned by fixtures**: 40.0 exactly passes,
  75.0% exactly is eligible.
- **Behavior is snapshot-tested**: routes/forms/links/permissions are
  captured and diffed before/after risky edits (the harness caught a
  double-rendered body once — that's what it's for).

## 5. Reading the git history as a syllabus

The commits narrate the build order: schema → models → routes → engine →
UI → restyle → audit. `git log --oneline` is effectively the project's
table of contents; each commit message states its intent.
