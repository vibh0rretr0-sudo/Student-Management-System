# Design.md
## Student Management System

**Status:** Draft — pages/roles to be confirmed with you.

---

## 1. Pages / Screens (confirmed: professor-only, single role)
| Page | Purpose |
|---|---|
| Login | Professor authenticates |
| Dashboard | Summary stats across the professor's courses (total students, avg grade, attendance alerts) |
| Course List | List/manage the professor's own courses |
| Student List | Search/filter/view students in a course |
| Add/Edit Student | Form to create or update a student record |
| Assignments | Create assignments, record submission/marks per student |
| Grades Entry | Enter raw marks; view computed grades/GPA (from C++ module) |
| Attendance | Mark present/absent; view computed attendance %/eligibility (from C++ module) |
| Rankings | View students sorted/ranked by performance (from C++ module) |

## 2. Navigation Flow
```
Login (Professor)
  → Dashboard
      → Courses → Students → Assignments / Grades / Attendance / Rankings
```

## 3. Database Schema (draft ERD — will refine once features are locked)

**Entities:**
- `professors` (id, username, password_hash, name)
- `batches` (id, batch_name) — e.g. "SN", with sections as a separate table
- `sections` (id, batch_id FK, section_name) — e.g. "SN1", "SN2"
- `students` (id, name, roll_number, date_of_birth, contact, enrollment_date, section_id FK)
- `courses` (id, course_name, course_code, professor_id FK, section_id FK, day_of_week, start_time, end_time) — a course/lab session is tied to one section and one time slot, so SN1 and SN2 can run different labs in the same slot without clashing
- `enrollments` (id, student_id FK, course_id FK, enrollment_date)
- `assignments` (id, course_id FK, title, description, max_marks, due_date)
- `submissions` (id, assignment_id FK, student_id FK, marks_obtained, submitted_on)
- `grades` (id, student_id FK, course_id FK, computed_grade, term) — populated from C++ module output
- `attendance` (id, student_id FK, course_id FK, date, status)

**Relationships:**
- One batch → many sections (SN → SN1, SN2)
- One section → many students
- One professor → many courses; each course belongs to one section and has its own schedule slot
- One course → many enrollments, assignments, grades, attendance records
- Students are a shared pool (not owned by a professor) — a professor sees the students enrolled in their own courses, which are naturally scoped by section

*(Full ERD diagram to be drawn once schema is finalized — can generate as an artifact/image later.)*

## 4. UI Style Guide (confirmed)
- **Color palette:** JECRC brand colors — red as the primary/accent color (headers, buttons, active nav links), white/light gray as the background, with a dark charcoal/gray for body text (pure red-on-white everywhere would be harsh, so red is used as an accent rather than a fill color).
  - Primary: `#B71C1C` (JECRC red) or close to it — verify exact hex against the official logo if you want a pixel-perfect match
  - Background: `#FFFFFF` / `#F5F5F5`
  - Text: `#212121`
- **Layout:** Simple sidebar + top navbar, content area with cards/tables.
- **Typography:** System fonts or a single Google Font for headings.
- **Components:** Tables for lists, a separate page (not a JS modal) for add/edit forms, badges for status (Present/Absent, Pass/Fail) styled with plain CSS classes.

## 5. Dashboard (confirmed)
- Includes basic charts (e.g. bar chart of grade distribution, attendance % by section) alongside summary numbers — built with **pure HTML/CSS, no JavaScript**, since the stack stays strictly HTML, CSS, Python, C++, SQL, DBMS/RDBMS.
- Approach: Python computes the values (e.g. count of students per grade band, attendance % per section), then generates simple `<div>` bars in the HTML with their `width`/`height` set inline via CSS based on those computed values (a classic CSS-only bar chart). No charting library, no client-side script — the "chart" is just styled HTML that Python fills in with numbers it already calculated.

## 6. Open Questions
- None blocking. Optional: confirm exact JECRC red hex if you want pixel-perfect brand matching (can grab it from the official logo file).
