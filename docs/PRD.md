# Product Requirements Document (PRD)
## Student Management System (SMS)

**Author:** Vibhor Mathur
**Status:** Draft — v0.1 (pending your input, see open questions at bottom)
**Context:** First-semester B.Tech CSE (AI DevOps & Cloud Automation) portfolio project for GitHub/LinkedIn

---

## 1. Problem Statement
Schools and small colleges often manage student records (enrollment, grades, attendance, fees) using spreadsheets or paper registers, which are slow, error-prone, and hard to search. A Student Management System (SMS) centralizes this data in a proper database and gives staff/students a simple web interface to view and manage it.

## 2. Goals
- Build a working, end-to-end CRUD web application that demonstrates the full stack: HTML/CSS (frontend), Python (backend logic), SQL + a RDBMS (data layer), and C++ (a dedicated performance/logic module).
- Produce a project that is genuinely explainable in an interview — every feature should be something you built and understand, not boilerplate.
- Ship something demo-able (screenshots + a short video or live link) for GitHub and LinkedIn.

## 3. Non-Goals (v0.1 draft — confirm with you)
- Not aiming for production-grade security (OAuth, encryption at rest, etc.) — basic auth is enough for a student project.
- No mobile app.
- No payment/fee-processing gateway.
- No CI/CD pipeline or automated test suite (can be a "future work" bullet in the README instead).

## 4. Target Users (confirmed)
- **Professor** — the only role in the system. Multiple professors can log in, each managing their own courses, assignments, grades, and attendance for their students.
- No separate student login and no separate admin role in v1.

## 5. Core Features (confirmed)
1. Professor authentication (login/logout — multiple professor accounts)
2. Student records CRUD (add/edit/delete/view student profiles, per professor's course/class)
3. Course management (create courses)
4. Assignment tracking (create assignments, record submission/marks per student)
5. Grades module (enter/view grades, compute GPA/percentage — via C++ module)
6. Attendance tracking (mark present/absent, compute attendance % and eligibility — via C++ module)
7. Sorting/ranking students by performance (via C++ module)
8. Search & filter students (by name, course, roll number)
9. Dashboard with summary stats (total students, average grade, etc.)

## 6. Stretch Features (pick if time allows)
- Export student report as a downloadable file (PDF/CSV)
- Basic data visualization (charts for grade distribution)

## 7. Tech Stack Mapping (confirmed)
| Layer | Technology | Role |
|---|---|---|
| Frontend | HTML, CSS | Page structure & styling |
| Backend | Python (plain scripts, no framework) | Server logic, routing, request handling |
| Compute module | C++ | GPA/grade calc, attendance eligibility, student ranking — called via subprocess |
| Data | SQL | Queries |
| Database engine | MySQL | Persistent storage |

## 8. Success Criteria
- App runs locally end-to-end with no crashes on the core CRUD flows.
- Database is normalized (at least 3NF) with a clear ERD.
- README explains architecture, setup steps, and your specific contribution/learning.
- Code is on GitHub with clean commit history (see Rules.md).

## 9. Constraints
- Solo developer, first-semester skill level.
- No prior experience with Docker/CI-CD/testing frameworks — scope excludes these.
- Timeline: TBD (need your target date).

## 10. Open Questions (remaining)
- UI style/branding preferences (see Design.md section 4)

## 11. Confirmed Scope Notes
- Students belong to sections (e.g. SN1, SN2) under a batch (SN); a course is tied to one section and a specific day/time slot, so parallel sections can run different labs at the same time without conflict.
- Runs on localhost for the initial demo to professors; deployment is a planned follow-up, not a v1 requirement. Folder structure (Architecture.md §6) is kept clean and self-contained so it can be pushed to GitHub as-is.
- Timeline: 5+ weeks, flexible/no fixed deadline.
