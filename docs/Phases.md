# Phases.md
## Student Management System — Development Roadmap

**Status:** Draft — durations are placeholders until you confirm your timeline.

---

## Phase 0 — Planning & Setup
- Finalize PRD, Architecture, Design, Rules (this round of documents)
- Set up GitHub repo, folder structure
- Set up local dev environment (Python venv, C++ compiler, chosen RDBMS)
- **Deliverable:** Repo skeleton pushed to GitHub with docs/ folder

## Phase 1 — Database Design
- Finalize ERD and schema
- Write `schema.sql` (CREATE TABLE statements, constraints, foreign keys)
- Seed sample/dummy data for testing
- **Deliverable:** Working local database with sample data

## Phase 2 — Backend Core (Python + SQL)
- Set up the plain Python backend (`http.server`/`BaseHTTPRequestHandler`, no framework) with manual routing
- Build DB connection layer (MySQL)
- Implement core CRUD routes for students (create, read, update, delete)
- **Deliverable:** Backend can add/view/edit/delete a student via a test route (no styling yet)

## Phase 3 — Frontend (HTML/CSS)
- Build page templates (login, dashboard, student list, student form)
- Style with CSS (layout, forms, tables)
- Wire templates to backend routes
- **Deliverable:** Clickable, styled app with working student CRUD end-to-end

## Phase 4 — Extended Features
- Courses, enrollments, grades, attendance modules
- Search/filter functionality
- Dashboard summary stats
- **Deliverable:** All core features from PRD section 5 working

## Phase 5 — C++ Module Integration
- Build & test the C++ program standalone
- Wire it into the Python backend (subprocess or chosen method)
- **Deliverable:** One feature in the app is visibly powered by the C++ module

## Phase 6 — Professor Auth
- Login/logout, session handling (multiple professor accounts)
- Each professor only accesses their own courses/students (pending your answer on shared vs. scoped student pool)
- **Deliverable:** Multiple professors can log in independently and see only their own data

## Phase 7 — Polish & Testing
- Manual test pass on all flows
- Fix bugs, handle edge cases (empty forms, duplicate entries)
- Basic input validation
- **Deliverable:** App is stable for a live demo

## Phase 8 — Documentation & Portfolio Packaging
- Write final README (setup instructions, screenshots, architecture summary)
- Record a short demo video or GIF
- Clean commit history / add LICENSE
- Write LinkedIn post draft
- **Deliverable:** Project is portfolio-ready on GitHub

## Open Questions
- Target completion date / how many weeks do you want to spend on this?
- How many hours/week can you realistically commit?
