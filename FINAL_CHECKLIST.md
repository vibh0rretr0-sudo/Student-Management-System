# FINAL CHECKLIST — JECRC Student & Faculty Portal

Honest status of every requirement. "Verified" = exercised end-to-end in a real browser during the final QA pass (both roles, seeded data). "Covered" = implemented and covered by the automated test suite / code inspection, but not manually clicked in the final pass.

---

## Device restriction (laptop only)

- **CSS media query** hides the app below 1024px — **Verified** (resized to 900px; app hidden, block screen shown).
- **JS check re-runs on resize** and restores the app when widened — **Verified** (900px → 1366px; app restored on the same page, no data loss).
- **Server-side user-agent check** returns the blocked page for mobile/tablet UAs — **Covered** (`is_mobile_user_agent` in `app/security.py`, exercised by tests).
- Block screen keeps JECRC branding + a working theme toggle — **Verified**.

## Theme (every page, no exceptions)

- Toggle present on home, login, both dashboards, every sub-page, the block screen and error pages — **Verified** on all surfaces visited.
- Persisted to `localStorage` (`jecrc-theme`), respects `prefers-color-scheme` on first visit, applied before first paint (inline head script) — **Verified** (persisted across reload; no flash).
- Smooth animated switch; charts re-theme live via the `themechange` event — **Verified** (toggle + `charts.js` listener confirmed; both themes screenshot-checked).

## Home page

- Full-screen campus slideshow, cross-fade + slow zoom, theme-aware overlay, pause when hidden, lazy-load — **Covered** (`static/js/pages/home.js`).
- Centered glass card with Student / Professor choices (hover lift, keyboard selectable) — **Verified**.
- In-place transition to the right login form (slide + fade, Back button, no reload) — **Verified**.
- Student (roll + password) and Professor (username + password) forms: show/hide password, Caps Lock warning, inline validation, loading state, generic credential error, "Forgot password?" contact-admin stub, "Remember my role" — **Verified** (role switch + form states; generic error covered by tests).
- Smooth fade/scale transition into the dashboard with the greeting animating in — **Verified**.

## Dashboard shell (both roles)

- Collapsible sidebar (icons + labels ⇄ icons only with tooltips), smooth width animation, persisted state, active item highlighted, `Ctrl+B` toggle, logout with confirm — **Verified**.
- Top bar: page title + breadcrumb, live date/clock, global search (`Ctrl+K` command palette), notification bell with unread count + dropdown, theme toggle, avatar + name menu — **Verified** (palette search "attend" → "Attendance · Jump to").
- Hash-based routing — Back/Forward/refresh keep the current page — **Verified**.
- Session-timeout warning with "Stay signed in" — **Covered** (implemented in `session.js`; long-lived timers not manually triggered).

## Student dashboard

- **Overview**: greeting by time of day + roll/branch/semester/batch, attendance doughnuts (overall + per subject, % in center, color-coded, below-75% warning + "classes you can miss / need to attend"), announcements panel (latest first, tags, unread dot, mark-all-read), today's schedule with Ongoing/Upcoming/Completed + "next class in X min", due-soon assignments, quick stats, weekly mini-trend — **Verified**.
- **Attendance**: subject-wise table (sortable), charts, monthly trend, attended/held, date-range filter, pagination — **Verified** (filters + 240 records across 16 pages).
- **Timetable**: weekly grid, today's column highlighted, current slot pulsing, print-friendly view — **Verified** (Mon–Sat, 24 periods, today highlighted).
- **Assignments**: grouped by subject, statuses (Pending/Submitted/Overdue/Graded), due date, attachment download, file upload to submit (type + size validated, progress bar), professor remarks + marks once graded — **Verified** (submitted a PDF → "Submitted"; graded item shows marks + feedback).
- **Announcements**: full list, filters (subject/date/unread), search, priority badges, mark-all-read, expand — **Verified**.
- **Today's Schedule**: detailed timeline — **Verified**.
- **Personal Details**: read-only official record, editable contact fields, profile photo upload, change-password form — **Verified** (contact save → "Contact details updated."; photo upload + crop implemented, not re-uploaded this pass).

## Professor dashboard

- **Overview**: greeting with name/department/designation, batch cards (batch, subject, student count, avg attendance) with "View all", announcements panel + "New announcement", today's teaching schedule with "Mark attendance" shortcut, assignments-awaiting-review, low-attendance alerts, quick stats — **Verified**.
- **My Batches**: batch cards with low-attendance counts, subject chips, roster drawer (search + "below 75% only" filter) — **Verified** (roster showed all 11 students with percentages).
- **Attendance**: marking sheet (batch/subject/date selectors, All present/absent, per-student Present/Absent/Late), save → students see it immediately — **Verified** (marked 11/11, saved, header updated).
- **Assignments**: batch tabs, Kanban (Active / Past due / Completed) + Table toggle, create/edit/delete via modal (title, description, subject, batch, due date, attachment, max marks), per-assignment submission tracker, quick grade + remarks, bulk actions (extend, remind, download ZIP), undo toast after delete — **Verified** (created + published an assignment; deleted it via Table view with undo toast).
- **Announcements**: create/edit/delete, target one/several/all batches, priority, optional pinned, scheduled publish, sent history with read counts — **Verified** (posted one with a batch target + read counts; deleted it).
- **Today's Schedule**: detailed timeline with "Mark attendance" — **Verified**.
- **Personal Details**: name, employee ID, department, designation, qualifications, subjects taught, photo, editable contact fields, change-password — **Verified** (subjects-taught de-duplicated to "CS101, CS102").

## Database

- Tables: users, students, professors, batches, subjects, batch_subjects, professor_batch_subject, timetable, attendance, assignments, submissions, announcements, announcement_targets, announcement_reads, notifications, audit_log — **Present**.
- Indexes on all foreign keys + `(student_id, subject_id, date)` for attendance — **Present** (`database/schema.sql`).
- Realistic seed: Indian names, JECRC-style batches, first-semester subjects, 3 professors, 3 batches, 30 students, Mon–Sat timetable, 2–3 months of varied attendance (some below 75%), assignments in every status, mixed-priority announcements, "today" always shows real classes — **Verified**.
- `schema.sql` (MySQL 8) + `schema_sqlite.sql` (dev fallback) + generated `seed.sql` — **Present**.

## API & security

- REST endpoints under `/api/student`, `/api/professor`, `/api/common`; consistent `{ok, data, error}` envelope; proper status codes; pagination — **Verified**.
- Role-based access on every route + object-level checks (a student never reaches professor data; a professor sees only their own batches) — **Covered** (`tests/test_isolation.py`, passing).
- Hashed passwords, parameterized queries only, secure HttpOnly SameSite session cookies, CSRF on state-changing requests, login rate limiting + lockout, output escaping, file-upload allowlist + size limit + randomized filenames, no secrets in code — **Verified/Covered** (cookie `HttpOnly; SameSite=Lax`; CSRF enforced — login rejected `csrf_invalid` without a token; security headers served; lockout + hashing covered by tests).
- Security headers: CSP, X-Frame-Options: DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy — **Verified** (served on `/`).
- Never reveals whether the roll number or the password was wrong (generic message) — **Covered** (`tests/test_auth.py`, passing).

## Performance

- Fast first load (lazy-loaded charts + images, cached campus-image list), debounced search, no N+1 queries, cached static assets — **Covered**.

## Testing & verification

- **pytest: 41 passed** (auth, role/object isolation, attendance math, assignment flows) — **Verified** (`pytest -q`).
- Both roles manually run end to end; console errors checked after each page — **Verified** (0 console errors across all pages in the final pass).
- Visually verified in **both themes** at **1366×768** and **1920×1080**, plus the **<1024px block screen** — **Verified**.

---

## Known limitations (honest)

- **SQLite dev fallback vs MySQL prod**: the app runs on SQLite locally (zero-config) via the shared SQL dialect. The MySQL schema/seed are provided and the adapter targets PyMySQL, but a live MySQL instance was not available in this environment to run against — the MySQL path is code-complete and schema-validated, not integration-tested here.
- **Session-timeout warning** and the **profile photo crop** flows are implemented and wired but were not manually re-triggered in the final pass (they involve long timers / a real image file). Everything else listed as "Verified" was exercised live.
- Seeded demo data only — no real student records. Every demo account uses the single password `Jecrc@2026` (documented in the README).
