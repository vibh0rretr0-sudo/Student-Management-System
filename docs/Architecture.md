# Architecture.md
## Student Management System

**Status:** Confirmed — strictly HTML, CSS, Python, C++, SQL, DBMS/RDBMS. No JavaScript, no frameworks, no external UI libraries.

---

## 1. High-Level Architecture (3-Tier)

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

## 2. Why This Shape
- **HTML/CSS** stays purely presentational — no logic in templates beyond simple loops/conditionals.
- **Python** owns all business logic: it receives requests, validates input, talks to the database, renders HTML by hand (string templates or `.html` files with simple placeholder substitution — no templating engine/library), and calls into the C++ module for the three confirmed computations.
- **C++** is deliberately scoped to THREE well-defined, related computations rather than spread across the app — you can explain exactly why C++ was needed there. Confirmed jobs for the C++ module:
  - GPA/grade calculation from raw assignment + exam marks
  - Attendance percentage + eligibility check (e.g. minimum 75% rule)
  - Sorting/ranking students by performance
  These can live as three functions in one compiled C++ program (or three small programs) — recommend one program with a "mode" argument (e.g. `./sms_engine grades`, `./sms_engine attendance`, `./sms_engine rank`) to keep the build simple.
- **SQL/RDBMS** is the single source of truth — Python never keeps its own copy of student data in memory beyond a request.

## 3. Backend Framework (confirmed: plain Python, no framework)
Since there's no framework, Python's built-in `http.server` (specifically `BaseHTTPRequestHandler` or `socketserver`) will handle HTTP requests directly. This means you'll write your own:
- Routing (matching URL paths to handler functions)
- Request parsing (reading form data / query strings manually)
- Response building (setting status codes, headers, writing HTML strings or reading template files)
This is more work than Flask but means every line of request-handling code is yours to explain — a good fit for the "genuinely explainable" goal.

## 4. Database Engine (confirmed: MySQL)
Python will connect via `mysql-connector-python` (or `PyMySQL`). Matches typical DBMS coursework and gives real client-server RDBMS experience (vs. file-based SQLite).

## 5. C++ Integration Method (confirmed: subprocess)
Python calls the compiled C++ executable via the `subprocess` module:
1. Python queries MySQL for the raw data needed (marks, attendance records, etc.)
2. Python passes that data to the C++ program (via command-line args or piped stdin, likely as simple delimited text or JSON)
3. C++ program computes the result and prints it to stdout
4. Python captures stdout, parses it, and either stores the result back in MySQL or renders it directly on the page

## 6. Folder Structure
```
student-management-system/
├── backend/
│   ├── server.py          # http.server entrypoint + routing
│   ├── routes/
│   ├── models/            # DB access functions (raw SQL via mysql-connector)
│   ├── db/
│   │   └── schema.sql
│   └── config.py          # DB host/user/password/port — kept out of version control (.gitignore)
├── cpp_module/
│   ├── src/
│   │   └── sms_engine.cpp # handles grades / attendance / ranking modes
│   └── build/
├── frontend/
│   ├── templates/
│   └── static/
│       └── css/
├── docs/
│   ├── PRD.md
│   ├── Architecture.md
│   ├── Design.md
│   ├── Phases.md
│   └── Rules.md
├── .gitignore
└── README.md
```

## 7. Data Flow Example (Add Student)
1. User submits "Add Student" form (HTML) → POST request.
2. Python route receives form data, validates it.
3. Python builds & runs an INSERT SQL query against the RDBMS.
4. Python redirects to the student list page, which re-queries the DB and renders updated HTML.

## 8. Deployment (confirmed)
- **v1:** runs on localhost (`localhost:PORT` via Python's built-in server) for demoing to professors.
- **Later:** deploy to a real host (e.g. a small VPS or PaaS) — not required for v1, but the folder structure below keeps config (DB credentials, port) out of code and in a separate config file/`.env`-style setup, so deployment later doesn't require restructuring.
- The whole project directory is self-contained and ready to push to GitHub as-is (see §6 folder structure).

## 9. Open Questions (remaining)
- None blocking — remaining detail is UI style/branding (see Design.md).
