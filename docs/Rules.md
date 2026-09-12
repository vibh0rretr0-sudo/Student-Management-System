# Rules.md
## Student Management System — Coding & Workflow Standards

---

## 1. General Principles
- Keep it simple: don't add a library, pattern, or abstraction you can't explain in an interview.
- Every feature should be something you understand end-to-end — no copy-pasted blocks you can't walk through.
- Prefer clarity over cleverness — readable code beats "smart" one-liners.

## 2. Python Conventions
- Follow PEP8 (snake_case for variables/functions, PascalCase for classes)
- One route/function does one job — keep route handlers short, push logic into helper functions
- Use docstrings for any non-trivial function
- Keep SQL queries parameterized (never string-format user input directly into a query — this also teaches you to avoid SQL injection)

## 3. C++ Conventions
- Keep the module small and single-purpose (matches its one defined job from Architecture.md)
- Comment the algorithm's logic (especially if it's a sort/search — explain time complexity)
- Compile with warnings enabled (`-Wall -Wextra`) and fix them

## 4. HTML/CSS Conventions
- Semantic HTML (use `<nav>`, `<table>`, `<form>` properly instead of divs for everything)
- One main stylesheet, organized by section (layout → components → utilities)
- Consistent naming for CSS classes (pick one convention, e.g. kebab-case, and stick to it)

## 5. SQL / Database Conventions
- Table names: plural, snake_case (`students`, `enrollments`)
- Column names: snake_case (`student_id`, `enrollment_date`)
- Every table has a primary key; foreign keys explicitly declared
- Schema changes go through `schema.sql` — no ad-hoc manual edits to the DB structure

## 6. Git / GitHub Workflow
- Commit early, commit often — small, descriptive commits (not one giant "final project" commit)
- Commit message format: `<type>: <short description>` e.g. `feat: add student CRUD routes`, `fix: correct grade calculation`, `docs: update README`
- Use a `.gitignore` (exclude venv, compiled binaries, `__pycache__`, DB files if using SQLite locally)
- Keep `main` branch always in a working state; use feature branches if comfortable, otherwise direct commits are fine for a solo first project

## 7. Documentation Rules
- Every folder with non-obvious code gets a short README or top-of-file comment explaining its purpose
- Final project README must include: what it does, tech stack, setup/run instructions, screenshots, and what you personally learned/built
- Keep this docs/ folder (PRD, Architecture, Design, Phases, Rules) updated as decisions change — treat it as the source of truth, not a one-time exercise

## 8. Scope Discipline
- If a feature isn't in PRD.md's Core Features list, it doesn't get built until Core Features are done
- Stretch features (PRD section 6) are attempted only after Phase 7 (Polish) confirms core stability
