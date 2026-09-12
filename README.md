# Student Management System (SMS)

A Student Management System for professors: manage courses, students, assignments, exams, marks, grades, attendance, and rankings. Built to demonstrate a full three-tier stack with zero frameworks: **HTML/CSS frontend + plain-Python backend (`http.server`) + C++ compute engine (subprocess) + MySQL**. No JavaScript anywhere.

> Full documentation lives in [`docs/`](docs/): PRD, Architecture, Design, Phases, Rules.

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Frontend | HTML, CSS | Semantic templates, JECRC-red themed UI, CSS-only charts |
| Backend | Python (stdlib `http.server`) | Routing, form parsing, validation, sessions |
| Compute | C++ (`sms_engine`) | Grade %, attendance eligibility, ranking — via subprocess |
| Data | SQL on MySQL 8 | Single source of truth, normalized to 3NF |

## Status

🚧 Under active development — see `docs/Phases.md` for the roadmap.

## Running (placeholder)

```bash
# Coming in Phase 8: setup steps, screenshots, architecture summary
```

---

## Author

Vibhor Mathur — first-semester B.Tech CSE (AI DevOps & Cloud Automation)
