# JECRC Student & Faculty Portal

A laptop-only ERP web portal for JECRC, Jaipur — attendance, timetable, assignments and announcements for students, with batch/attendance/assignment/announcement management for faculty. Built with **Flask + MySQL** on the backend and **vanilla ES6 modules + CSS custom properties** on the frontend (no SPA framework, no CDN dependencies).

> Seeded demo data only — no real student records. Every demo account shares one password (see below).

---

## 1. Features at a glance

**Students** — Overview (greeting, attendance doughnuts, today's schedule, due-soon widgets), subject-wise attendance with trends, weekly timetable, assignments (submit/replace/grade), announcements, today's timeline, and a personal-details page with editable contact fields, photo upload and password change.

**Professors** — Overview (greeting, batch cards, teaching schedule, review/alert widgets), batch rosters with low-attendance filters, attendance marking sheet, assignment board (create/track/grade/extend/remind/ZIP), announcements (one batch, several or all, priority + pinned + scheduled), today's timeline, and personal details.

**Everywhere** — dark/light theme (persisted, applied before first paint, live chart re-theming), laptop-only enforcement in three layers (CSS + JS resize + server-side UA), collapsible sidebar with `Ctrl+B`, hash routing (Back/Forward/refresh-safe), `Ctrl+K` command palette, notifications, toasts, loading skeletons, empty states and error states with Retry, keyboard accessibility.

---

## 2. Quick start

```bash
# one command — creates the venv, installs deps, seeds the DB, starts the server
./start.sh            # macOS / Linux
start.bat             # Windows
```

The portal is then available at **http://127.0.0.1:5000** (override with `PORT`).

<details>
<summary>Manual setup (equivalent to <code>start.sh</code>)</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edit as needed
python -m app.seed                 # create + seed the demo database
python run.py                      # start the dev server
```
</details>

### Configuration

All settings come from environment variables / `.env` (see [`.env.example`](.env.example)):

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | dev fallback | Flask session signing key — **set a strong value in production** |
| `DATABASE_URL` | `sqlite:///jecrc.sqlite3` | SQLAlchemy URL. MySQL: `mysql+pymysql://user:pass@host/jecrc?charset=utf8mb4` |
| `PORT` | `5000` | HTTP port |
| `FLASK_ENV` | `production` | `development` enables the reloader/debug |

The backend uses a single SQL dialect that runs on both **MySQL 8** (production) and **SQLite** (zero-config local dev). Point `DATABASE_URL` at MySQL and run the schema in [`database/schema.sql`](database/schema.sql); the default SQLite file is created and seeded automatically by `python -m app.seed`.

---

## 3. Demo logins

Every account uses the password **`Jecrc@2026`**.

**Students** (sign in with the roll number):

| Roll number | Batch |
| --- | --- |
| `26CSAI001` … `26CSAI011` | CSE AI & DevOps — A |
| `26CSAI101` … `26CSAI110` | CSE AI & DevOps — B |
| `26CSC001` … `26CSC009` | CSE Core — A |

**Professors** (sign in with the username):

| Username | Name | Department |
| --- | --- | --- |
| `anjali.verma` | Dr. Anjali Verma | CSE |
| `rakesh.sharma` | Prof. Rakesh Sharma | CSE |
| `meera.iyer` | Dr. Meera Iyer | Physics / Electrical |

Re-seed at any time with `python -m app.seed` (add `--emit-sql` to regenerate `database/seed.sql` for MySQL).

---

## 4. Adding real campus photos

The home-page slideshow reads every image in [`static/img/campus/`](static/img/campus/) via the `/api/campus-images` endpoint (the list is cached). Four tasteful SVG placeholders ship by default.

To use real JECRC photography:

1. Drop your images (`.jpg`, `.jpeg`, `.png`, `.webp` or `.svg`) into `static/img/campus/`.
2. Name them with a human-readable title — the file stem becomes the slide caption (e.g. `Main Building.jpg` → “Main Building”).
3. Recommended: **1920×1080** (or larger), landscape, compressed. The slideshow cross-fades and slowly zooms, so wide, high-resolution shots look best.
4. Restart the server (or wait for the image-list cache to refresh) and reload the home page.

No other changes are needed — new files are picked up automatically.

---

## 5. Project layout

```
app/
  __init__.py        app factory, blueprints, security headers, error pages
  db.py              MySQL (PyMySQL) + SQLite adapter over one SQL dialect
  security.py        server-side sessions, CSRF, role guards, login lockout, uploads
  utils.py           JSON envelope, pagination, validation, audit, notifications
  seed.py            canonical demo data; also emits database/seed.sql
  blueprints/
    auth.py          login / logout / csrf / session / heartbeat
    common.py        profile, notifications, search, campus images, file downloads
    student.py       /api/student/*
    professor.py     /api/professor/*
    pages.py         home, dashboard shell, blocked screen, error pages
database/
  schema.sql         MySQL 8 schema (indexes on all FKs + (student_id, subject_id, date))
  schema_sqlite.sql  identical schema for the SQLite dev fallback
  seed.sql           MySQL seed dump (python -m app.seed --emit-sql)
static/
  css/               tokens · base · components · home · app
  js/
    core/            icons, theme, api client, ui primitives, charts, device guard
    components/      table, page/panel, schedule, profile, schedule-page
    pages/           home, standalone
    app/             session, router, routes, shell, main
    views/student/   overview, attendance, timetable, assignments, announcements
    views/professor/ overview, batches, attendance, assignments, announcements
  img/campus/        4 swappable campus illustrations
  vendor/            Chart.js 4.4.3 (vendored, no CDN)
templates/           home.html, app.html, blocked.html, error.html, partials/
tests/               pytest: auth, role/object isolation, attendance math, assignment flows
```

---

## 6. Testing

```bash
pytest -q
```

Covers authentication and lockout, student/professor role isolation, object-level access (a student sees only their own records), attendance percentage math, and the assignment submission/grading flows. All tests run against the SQLite dev database.

---

## 7. Deployment

1. **Set a strong `SECRET_KEY`** and `FLASK_ENV=production`.
2. **Use MySQL** for production: create the database, load `database/schema.sql`, then seed with `python -m app.seed --emit-sql` + `mysql < database/seed.sql` (or run `python -m app.seed` against the configured `DATABASE_URL`).
3. **Serve with a production WSGI server** instead of the built-in dev server, e.g. Gunicorn (Linux):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 127.0.0.1:8000 "app:create_app()"
   ```
   Put nginx or a similar reverse proxy in front for TLS, static-file serving and gzip.
4. The app already sets security headers (CSP, X-Frame-Options, etc.), HttpOnly + SameSite session cookies and CSRF protection — keep it behind HTTPS in production.

A container is not required; the app is a standard Flask WSGI application (`app:create_app()`).

---

## 8. Browser support

Modern evergreen browsers on a laptop/desktop (viewport ≥ 1024px). Below that width — or on a mobile/tablet user-agent — the portal is replaced by a full-screen “laptop only” notice (with branding and the theme toggle still available).
