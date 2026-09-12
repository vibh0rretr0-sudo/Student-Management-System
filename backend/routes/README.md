# backend/routes — HTTP route handlers

Each module registers its URL patterns on the shared dispatcher. Handlers receive the parsed request (`Request`) and return a `Response`; they are thin — validation lives in `validation.py`, data access in `backend/models/`.

- `helpers.py` — route table, Response/Request helpers shared by all modules
- `auth_routes.py` — login/logout
- `student_routes.py` — student CRUD + search
- `course_routes.py` — courses, enrollments
- `assessment_routes.py` — assignments, exams, marks entry
- `attendance_routes.py` — attendance marking
- `dashboard_routes.py` — dashboard with CSS-only charts
- `analytics_routes.py` — grades/attendance/rankings pages powered by the C++ engine
