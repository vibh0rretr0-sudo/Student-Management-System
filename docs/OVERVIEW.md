# Overview — Student Management System

Consolidated reference for the project: what it is, how it is shaped, the
decisions behind it, and where it deliberately stops. (Merged from the
original PRD, Architecture, Design, Phases, and Rules documents.)

---

## Purpose

Schools and small colleges often manage student records — enrollment,
grades, attendance — with spreadsheets or paper registers: slow,
error-prone, and hard to search. This project centralizes that data in a
proper relational database and gives staff a simple web interface to
manage it: courses, enrollments, students, assignments, exams, marks,
grades, attendance, and rankings.

**Users:** professors only — one role, multiple accounts. Each professor
manages the courses, students, marks, and attendance of their own
courses. There is no student login and no admin role in v1.

**Goals**

- A working, end-to-end CRUD web app that demonstrates the full stack:
  HTML/CSS (frontend), Python (backend logic), SQL/MySQL (data), and C++
  (a dedicated compute module).
- A project that is genuinely explainable in an interview — every feature
  is something built and understood, not boilerplate.
- Demo-able locally: screenshots in the README, runs on first-semester
  hardware with no cloud dependencies.

**Core features**

1. Professor login/logout (multiple accounts)
2. Student records CRUD + search/filter (by name, roll number, course)
3. Course management (tied to professor, section, and weekly slot)
4. Assignment tracking with per-student marks
5. Grades — computed by the C++ engine from assignment + exam marks
6. Attendance — present/absent marking; C++ computes % and 75% eligibility
7. Ranking students by performance (C++)
8. Dashboard with summary stats and CSS-only charts

**Scope note:** students belong to sections (SN1, SN2) under a batch
(SN); a course is tied to one section and one weekly slot, so parallel
sections can run different labs in the same slot without conflict.

---

## Architecture

Strict stack: HTML, CSS, Python (stdlib only), C++, SQL on MySQL.
No JavaScript, no frameworks, no templating libraries.

```
┌─────────────────────────┐
│   Presentation Layer     │  HTML + CSS templates (rendered server-side
│   (Browser UI)           │  by Python as plain HTML strings/files — no JS)
└───────────┬──────────────┘
            │ HTTP requests
┌───────────▼──────────────┐
│   Application Layer       │  Python (routing, business logic,
│   (Backend)                │  auth, validation)
└───────────┬────────┬──────┘
            │        │ subprocess call
            │  ┌─────▼─────┐
            │  │ C++ Module │  grades / attendance / ranking
            │  └───────────┘
┌───────────▼──────────────┐
│   Data Layer               │  SQL queries → MySQL (RDBMS)
│   (Database)                │
└───────────────────────────┘
```

**Why this shape**

- **HTML/CSS** stays purely presentational — no logic in templates beyond
  simple loops/conditionals.
- **Python** owns all business logic: hand-written routing on
  `http.server`, form parsing, PBKDF2 password hashing, sessions,
  validation, and HTML rendered by hand (template files with
  `{{placeholder}}` substitution — no template engine).
- **C++** is deliberately scoped to three well-defined computations —
  grade calculation, attendance eligibility, ranking — invoked via
  subprocess over stdin/stdout with a TSV text protocol. One binary,
  three modes: `sms_engine grades|attendance|rank`.
- **MySQL** is the single source of truth; Python keeps no data in memory
  beyond a request.

**Data flow example (add student):** form POST → Python validates →
parameterized INSERT → redirect to the student list page, which re-queries
the DB and renders updated HTML.

---

## Key Decisions

| Decision | Why |
|---|---|
| No web framework (`http.server` + hand-rolled router) | Every line of request handling is yours to explain; the restraint is the point of the project |
| C++ for exactly three pure computations | A clean module boundary, a crisp answer to "why C++ here?", and a documented Python↔C++ text protocol |
| MySQL + PyMySQL, parameterized queries only | Real client-server RDBMS experience; placeholders make SQL injection structurally impossible |
| Least-privilege DB user (`sms_app`) | The app never connects as root; schema changes go through `schema.sql` only, never ad-hoc edits |
| PBKDF2 hashing + in-memory sessions | Stdlib-only auth that can still be defended line by line |
| 3NF schema, explicit foreign keys, cascade deletes | Per-section roll uniqueness, enrollment uniqueness, schedule-clash prevention at write time |
| UI: JECRC red `#B71C1C` as accent on white/light gray, charcoal text | Pure red-on-white everywhere would be harsh; red marks headers, buttons, active nav |
| Sidebar + topbar layout, tables/cards, separate form pages (no JS modals) | Semantic HTML, one stylesheet, kebab-case class names |
| CSS-only charts (div bars sized inline by Python) | No charting library, no client-side script — Python computes, HTML displays |
| Conventions: PEP8, plural snake_case tables, `<type>: <message>` commits | Keeps solo development reviewable and viva-friendly |

---

## Known Limitations

Deliberate non-goals for v1 — first-semester scope discipline, not
oversight:

- No production-grade security (OAuth, encryption at rest, CSRF tokens);
  sessions live in process memory and die on server restart.
- Runs on localhost only; deployment is a planned follow-up (config is
  already environment-driven, so no restructuring is needed later).
- No automated test suite, CI/CD pipeline, Docker, or mobile app.
- No payment/fee processing and no CSV/PDF report export (stretch idea,
  not started).
- Solo project at first-semester skill level — the code favors clarity
  over feature coverage.
