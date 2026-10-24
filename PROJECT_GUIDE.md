# JECRC Student & Faculty Portal - Project Guide

## 🚀 Tech Stack
The project is a hybrid Web Application designed for academic management.

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | **Python / Flask** | Server-side logic, API endpoints, and session management. |
| **Frontend** | **Vanilla JS / Jinja2 / CSS** | Custom component-based UI with client-side routing. |
| **Database** | **SQLite / MySQL** | Relational storage for users, attendance, and academic data. |
| **Visualization**| **Chart.js** | Interactive dashboards for attendance and performance. |
| **Environment** | **.env / config.py** | Environment-driven configuration for DB and security. |

---

## 🏗️ Architecture & Routing

### Application Structure
The project follows the **Application Factory Pattern**. The `create_app()` function in `app/__init__.py` initializes the server, loads configurations, and registers modular components called **Blueprints**.

### Routing Logic
Routing is handled at two levels:
1. **Server-Side (Flask Blueprints):**
   - `auth`: Login, Logout, and Session validation.
   - `student`: Student dashboards, attendance tracking, and assignment submissions.
   - `professor`: Class management, marking attendance, and posting announcements.
   - `common`: Shared utility endpoints.
   - `pages`: General landing and static pages.
2. **Client-Side (Vanilla JS):**
   - Implements a custom router in `static/js/app/router.js` that swaps views dynamically without full page reloads (SPA behavior).

---

## 💾 Data Storage & Flow

### Database Engine
The project uses a custom wrapper in `app/db.py` that allows it to switch between **SQLite** (for local development) and **MySQL** (for production) simply by changing the `DB_ENGINE` variable in `.env`.

### Core Data Model
Data is structured across several key domains:
- **Identity**: `users` $\rightarrow$ `students` / `professors`.
- **Academic Structure**: `batches` $\rightarrow$ `subjects` $\rightarrow$ `timetable`.
- **Tracking**: `attendance` (per student/subject/date) and `submissions` (for assignments).
- **Communication**: `announcements` $\rightarrow$ `notifications`.
- **Audit**: `audit_log` and `login_attempts` for security tracking.

---

## ⚙️ Initialization Flow
When you start the project:
1. `run.py` $\rightarrow$ invokes `create_app()`.
2. `create_app()` $\rightarrow$ loads `config.py` $\rightarrow$ registers Blueprints.
3. **Database Init**: The `init-db` command creates tables based on `database/schema.sql`.
4. **Seeding**: The `seed-db` command (via `app/seed.py`) populates the DB with demo students, professors, and a 10-week attendance history.
5. **Server Start**: Flask starts serving on `http://127.0.0.1:5000`.
