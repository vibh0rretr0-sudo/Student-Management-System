# Interview & Viva Prep — Student Management System

Every feature mapped to code, every design decision with its "why", and the
questions examiners actually ask. Read this the night before the demo.
For a guided reading path through the code itself, see the
[`CODE_TOUR.md`](CODE_TOUR.md).

---

## 1. The 30-second pitch (memorize the shape)

> "It's a Student Management System for professors — courses, students,
> assignments, exams, marks, grades, attendance, and ranking. I built it on a
> deliberately framework-free stack: the frontend is hand-written HTML/CSS
> rendered by a Python HTTP server I wrote on the standard library, data lives
> in a normalized MySQL schema accessed only through parameterized queries, and
> a compiled C++ module does the three number-crunching jobs — grade
> percentages, attendance eligibility, and ranking — called from Python as a
> subprocess over a simple text protocol. No JavaScript, no frameworks, no
> templating libraries — so I can explain every line."

---

## 2. Feature → code map

| Feature | Where it lives | What to point at |
|---|---|---|
| HTTP server | `backend/server.py` | `BaseHTTPRequestHandler` subclass, `ThreadingHTTPServer`, body-size limit, request logging |
| URL routing | `backend/routes/helpers.py` | `@route(method, regex)` decorator appending to `ROUTES`; `dispatch()` matches path, extracts named groups |
| Login/logout | `backend/routes/auth_routes.py` | POST /login → `verify_login` → cookie; logout clears session |
| Password storage | `backend/auth.py` | `hash_password` / `verify_password` — PBKDF2-SHA256, 390k iterations, per-user salt, `hmac.compare_digest` |
| Sessions (in-memory) | `backend/auth.py` | dict + `threading.Lock`, `secrets.token_urlsafe(32)` token, TTL check |
| Templates | `backend/routes/template.py` | `render()` = read file + `{{key}}` replace; `esc()` = `html.escape`; layout wraps pages |
| Student CRUD | `backend/routes/student_routes.py`, `backend/models/students.py` | list/search/add/edit/delete; roll uniqueness per section |
| Search & filters | `students.search()` | LIKE on name/roll + course/section filters, all parameterized |
| Courses + clash detection | `backend/models/courses.py` | `_ensure_no_clash` — interval overlap `a.start < b.end AND b.start < a.end` |
| Enrollment | `courses.enroll/unenroll`, `enrollable_students()` | section-scoped eligibility via NOT IN |
| Assignments/exams + marks | `backend/routes/assessment_routes.py` | marks grid per assessment; `_parse_marks` validates 0 ≤ marks ≤ max |
| Grades (C++) | `backend/cpp_engine.py` + `cpp_module/src/sms_engine.cpp` | `compute_grades()` → subprocess → parse; results stored in `grades` table |
| Attendance (C++) | `attendance_routes.py` + engine `attendance` mode | per-day radio-button marking; summary with 75% rule |
| Ranking (C++) | `analytics_routes.py` + engine `rank` mode | per-section input rows; `std::stable_sort` + competition ranking |
| Dashboard charts | `backend/routes/dashboard_routes.py` | Python computes values → `<div>` bars with inline `width:%` — CSS-only |
| Permission model | `students.can_edit()`, `_owned_course()` in routes | view-all/edit-own; 403 via `PermissionError` → `dispatch` |
| Validation | `backend/routes/validation.py` | `parse_date/decimal/int/time`, `require()`; `ValueError` → 400 page |
| DB setup | `scripts/setup_db.py` | root used once; creates least-privilege `sms_app`; writes `config.py` |

---

## 3. Design decisions — the "why" an examiner digs for

**Why no Flask/Django?** Two reasons: the brief required a framework-free
stack, and honestly — writing the router myself is what taught me what
frameworks actually do. I can now name what I gave up: middleware, ORM,
auto-escaping templates, prod-grade WSGI.

**Why C++ for exactly three functions?** Scoping was the point. The three
jobs (grade math, eligibility check, ranking sort) are pure computation over
in-memory data — a clean module boundary with a text protocol. It gives a
honest answer to "why C++ and not more Python?": demonstration of a compiled,
typed, systems-language component with a defined interface, not a claim that
Python couldn't compute a sort.

**Why subprocess and not a C++ extension or socket service?** Subprocess is
the simplest correct isolation: the engine is a black box reading stdin and
writing stdout, stateless, crash-isolated. An extension needs CPython ABI
knowledge; a socket service needs a second server to manage. Simplest thing
that works (Rules.md §1).

**Why TSV and not JSON?** No JSON parser in the engine — pulling in a library
would break the "no external libraries" constraint, and hand-rolling a parser
would bloat the module. TSV needs `getline` + `stoi/stod`. Names are sanitized
(tabs/newlines stripped) before they enter the protocol.

**Why PBKDF2 and not SHA-256(password)?** Plain SHA-256 is fast — an attacker
with the hash table can brute-force billions of guesses. PBKDF2 with 390,000
iterations and a unique salt makes each guess expensive and rainbow tables
useless. `hashlib.pbkdf2_hmac` is in the stdlib, so no new dependency.

**Why in-memory sessions (and what's the cost)?** Chosen for simplicity. The
cost: every login dies on server restart, and sessions don't scale past one
process. The upgrade path is a `sessions` table in MySQL — same cookie, one
query swap in `auth.get_session`.

**Why can every professor VIEW all students but only edit their own?**
Matches how colleges work: directory information is shared; grading authority
is not. Enforcement is server-side — the edit routes call `can_edit()` and
raise → 403 page — so hiding buttons in the UI is cosmetic, not the security
boundary. Edge case we handled: a freshly created student with zero
enrollments would be un-editable by anyone, so "unclaimed" students are
editable until they join a course.

**Why are marks per-assessment percentages, and what does "conducted" mean?**
Each assignment/exam contributes `marks/max × 100` and the average is over
*conducted* assessments — an assessment counts in the denominator once anyone
has marks recorded for it. Otherwise an unheld endterm would count as a zero
for every student and fail the whole class. But once an exam IS conducted, a
specific student's missing marks count as zero (the confirmed rule).

**Why is `grades` a table at all if it's computable?** It's a materialized
summary written when a professor opens the Grades page — the dashboard reads
it instead of re-invoking C++ for every page load. Raw data stays the source
of truth in submissions/exam_marks.

**Why MySQL and not SQLite?** The brief required a real client-server RDBMS
(DBMS coursework), and it gives concurrent access from the threaded server,
real user management (`sms_app` least privilege), and real `TIME`/`ENUM`/
constraint semantics.

**Why is config not in git?** `backend/config.py` holds the DB password; it's
in `.gitignore`, with `config.example.py` as the committed template and
`setup_db.py` writing it during setup.

---

## 4. Database — be ready to draw this

```
batches 1─* sections 1─* students
                 └─* courses *─1 professors
enrollments (student × course)          ← uniqueness (student, course)
assignments 1─* submissions (student)   ← uniqueness (assignment, student)
exams 1─* exam_marks (student)          ← uniqueness (exam, student)
grades (student × course × term)        ← C++ output, materialized
attendance (student × course × date)    ← ENUM('present','absent')
```

Key constraints to name-drop: `UNIQUE (section_id, roll_number)` (rolls are
per-section), `CHECK (end_time > start_time)`, `CHECK (max_marks > 0)`,
`ON DELETE CASCADE` from courses/students into child tables, `utf8mb4`,
InnoDB everywhere.

**Normalization story:** every table's non-key columns depend on the key —
e.g. section lives on `students`, not repeated per enrollment; course's
professor/term live on `courses`, not copied onto attendance rows. The one
deliberate denormalization is `grades` (computed data cached as rows).

---

## 5. Algorithm & complexity questions

**"What sort does ranking use?"** `std::stable_sort` — O(n log n)
comparisons, stable so equal-percentage students keep roll-number order.
Ranks are competition-style: equal percentages share a rank (1, 2, 2, 4).

**"How does the engine parse input?"** `std::getline` on '\t' into
`vector<string>`, `std::stoi/stod` with full-consumption checks; malformed
lines are skipped, not fatal. Output is fixed two-decimal via
`std::setprecision`.

**"What's the overlap check for course slots?"** Two half-open intervals
[a_start, a_end) and [b_start, b_end) overlap iff `a.start < b.end AND
b.start < a.end`. One indexed query on (section_id, day_of_week).

**"Is the SQL injection-safe?"** Every query goes through PyMySQL's
parameterization (`%s` placeholders + params tuple) — user input never
touches the SQL string. Also: path traversal on `/static` is blocked by
resolving and prefix-checking against the static root.

**"How does auth survive the threaded server?"** The session dict is guarded
by a `threading.Lock`; each request handler thread reads/writes under it.
Token comparison for passwords uses constant-time `hmac.compare_digest`.

---

## 6. Things that went wrong (say these — interviewers love them)

1. **Unheld exams counted as zeros** — my first grade run showed everyone
   failing because the not-yet-held Endterm divided their exam average. Fixed
   with the "conducted assessment" rule in the SQL aggregates. Lesson: define
   semantics before averaging.
2. **MySQL `TIME` columns arrived as `timedelta`** — slicing `[:5]` crashed.
   PyMySQL type mapping; fixed with an explicit formatter. Lesson: know your
   driver's type conversions.
3. **Login page loaded without CSS** — the static route was login-gated, so
   the stylesheet request redirected to HTML. Lesson: the auth boundary must
   exclude assets.
4. **A new student was un-editable by anyone** — permission rule had no owner
   for zero-enrollment students. Lesson: check your rules for degenerate
   cases, not just the happy path.

---

## 7. Two-minute demo script

1. Login as `vibhor` → dashboard: cards + CSS charts.
2. Courses → CS101 → Assignments → edit a mark live → Save.
3. Grades page → point at the subprocess call in the terminal log → values
   update; Ishita shows "Fail" at 39.25%.
4. Attendance → mark someone absent → eligibility summary updates; Kunal at
   exactly 75.0% stays "Eligible" (boundary).
5. Rankings → per-section ordering, medal for top 3.
6. Logout → login as `sharma` → she sees only CS104; open vibhor's student →
   view-only note, no edit/delete; try `/students/6/edit` → 403 page.

---

## 8. Questions to have one-line answers for

- "Why `http.server` and not sockets directly?" — it gives me parsed requests
  and response writing; I still own routing, cookies, and dispatch.
- "Why 303 for redirects?" — See Other: after POST, forces a GET on the
  target and won't replay the POST on refresh.
- "How would you deploy this?" — config is already env-driven; run behind a
  reverse proxy with HTTPS, move sessions to MySQL, add a process manager.
- "What's the first thing you'd add with more time?" — DB-backed sessions,
  then an automated smoke test of routes (I verified them with a scripted
  dispatch pass), then CSV export.
- "Where could this break under load?" — in-memory sessions don't scale
  horizontally; a connection pool would replace per-call connections;
  subprocess spawn per grades page is fine at demo scale, a long-lived engine
  process would be the next step.
