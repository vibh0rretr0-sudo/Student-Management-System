# backend/models — database access layer

One module per domain area. Every function opens a fresh PyMySQL connection via `db.get_connection()`, uses **parameterized queries only**, commits on writes, and closes the connection.

- `db.py` — connection factory
- `professors.py` — professor accounts, password verification
- `students.py` — student CRUD + search
- `courses.py` — courses, batches, sections, enrollments
- `assessments.py` — assignments, exams, submissions, exam marks
- `attendance.py` — attendance marking + retrieval
