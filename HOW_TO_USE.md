# How to use this project — from the GitHub page to a running app

This guide assumes **zero prior setup**: if you have a computer with
internet, you can have the app running on your own machine in about
15 minutes. Every command you need is written out, and every prompt the
setup asks you is explained *before* it appears.

> The finished result: a login page at `http://127.0.0.1:8000` where two
> demo professors manage students, courses, marks, grades, attendance and
> announcements — entirely on your machine. Nothing is sent to any server.

---

## 0. What you need before starting

Install these three things first (all free):

| Need | Windows | macOS / Linux | Check it worked |
|---|---|---|---|
| **Python 3.10+** | [python.org/downloads](https://www.python.org/downloads/) — tick **"Add Python to PATH"** during install | `brew install python` / usually preinstalled | `python --version` |
| **A C++ compiler (g++)** | [MinGW-w64](https://www.mingw-w64.org/) or [MSYS2](https://www.msys2.org/) | `xcode-select --install` (mac) · `sudo apt install g++` (Ubuntu) | `g++ --version` |
| **MySQL 8** | Full walkthrough: [`docs/MYSQL_SETUP.md`](docs/MYSQL_SETUP.md) — installer + Workbench | [mysql.com downloads](https://dev.mysql.com/downloads/) or `brew install mysql` | `mysql --version` and the service running |

Write down the **root password you set during the MySQL install** — step 5
will ask for it exactly once.

---

## 1. Get the code

On the repo page, click the green **`< > Code`** button → copy the HTTPS link,
then in a terminal:

```bash
git clone https://github.com/vibh0rretr0-sudo/Student-Management-System.git
cd Student-Management-System
```

No git? Click **Download ZIP** instead, unzip it, and open a terminal
inside the unzipped folder — everything else is identical.

---

## 2. Install the Python dependencies

The project's *entire* third-party dependency list is two packages
(`PyMySQL` for MySQL, `cryptography` for the driver's auth). Everything
else is Python's standard library.

```bash
pip install -r requirements.txt
```

Optional but good practice — use a virtual environment so your global
Python stays clean:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Build the C++ engine

The grading / attendance math lives in a small C++ program
that Python starts and talks to. Compile it once:

```bash
python scripts/build_cpp.py
```

You should see a `Compiling: g++ ...` line and end with
**`Built cpp_module\build\sms_engine.exe`** (the `.exe` suffix is
Windows-only; on macOS/Linux it builds as `sms_engine` — see the note
in step 5).

---

## 4. Make sure MySQL is running

- **Windows:** MySQL usually installs as the `MySQL80` service and starts
  automatically. Check: *Workbench → Server → Startup/Shutdown*, or run
  `services.msc` and look for **MySQL80**.
- **macOS:** `brew services start mysql`
- **Linux:** `sudo systemctl start mysql`

---

## 5. Run the one-time database setup

```bash
python scripts/setup_db.py
```

This single command creates everything. Here is **exactly what it will
ask you**, in order:

1. **`MySQL root password:`** — type the root password from step 0.
   (It's read hidden and never stored anywhere.)
2. **`Choose a password for the new 'sms_app' DB user (press Enter to
   auto-generate):`** — press **Enter** and let it generate a secure one.
   This is *not* your root password; it's a separate, limited account the
   app itself uses (it can only touch this project's database).
3. *(only if you've run this before)* **`Database 'sms' already exists.
   Drop and recreate it? [y/N]:`** — press **Enter** (N) to keep your
   data, or `y` to wipe back to fresh demo data.

What it does for you afterwards:

- creates the `sms` database and the limited `sms_app` user,
- **writes `backend/config.py` for you** (the DB password lands there
  automatically — that file is git-ignored, so it never reaches GitHub),
- loads the 11-table schema and the demo data — the real JECRC SN-DevOps
  timetable (8 professors, 2 sections SN1/SN2, 30 students, 31 course
  slots, assignments, exams, marks, attendance, announcements).

It ends with: `Done. Demo professor login -> username: vibhor  password: prof123`

> **macOS / Linux only:** the build in step 3 names the engine
> `sms_engine` (no `.exe`), but `config.py` was copied from an example
> that points at `sms_engine.exe`. Open `backend/config.py` and change
> the one line to:
> `CPP_ENGINE_PATH = os.path.join(BASE_DIR, "cpp_module", "build", "sms_engine")`
> (Windows users: nothing to change.)

---

## 6. Start the app

```bash
python backend/server.py
```

You should see:

```
SMS running at http://127.0.0.1:8000  (Ctrl+C to stop)
```

Leave this terminal open — the app lives in it. Then open
**<http://127.0.0.1:8000>** in your browser.

---

## 7. Log in and explore

The seed data mirrors the real JECRC timetable (Section SN, DevOps,
Sem-1 2026-27). Every timetable teacher has a login (password `prof123`
for all): `anubhav`, `cheena`, `abhishek`, `pranav`, `anilsharma`,
`priyanka`, `monika` — plus the demo account:

| Username | Password | Owns |
|---|---|---|
| `cheena` | `prof123` | all CPLT lectures + Saturday lab — the full experience |
| `vibhor` | `prof123` | nothing — ideal for testing permissions (403s) |

A 2-minute tour:

1. Log in as **vibhor** → the **Dashboard** shows six stat cards and two
   bar charts (grade distribution, attendance per course).
2. **Courses → any course** → the action row opens Assignments, Exams,
   Attendance, and Grades. Enter some marks in a marks grid,
   save, then open **Grades** — the C++ engine computes the final %
   (50 % coursework + 50 % exams, pass at 40 %).
3. **Attendance** → pick present/absent for a date, save → the summary
   table shows the 75 % eligibility verdict per student.
4. **Announcements** (sidebar) → publish a notice (institute-wide or to
   one of your sections), attach a PDF or image, then download it back —
   the bytes round-trip exactly. Only the author sees a Delete button.
5. **Theme toggle** (top bar) → click it, visit three different tabs —
   the dark mode follows you. It's saved in a cookie by the server, so
   it survives restarts too.
6. Now the permission trick: log out, log in as **vibhor**, and browse
   around — he can *view* all students, open cheena's grades, and read
   institute-wide announcements, but the moment he opens a marks sheet,
   tries to edit something that isn't his, or deletes another
   professor's announcement, he gets a proper **403/404 page**. That
   check is enforced server-side, not just hidden in the buttons.

---

## 8. Stopping, restarting, resetting

- **Stop the app:** click the terminal and press **Ctrl+C**.
- **Start it again later:** repeat steps 4 (if MySQL isn't running) and 6.
  No rebuild, no setup — you're done in one command.
- **Wipe the data back to fresh demo state:** re-run
  `python scripts/setup_db.py` and answer `y` at the drop prompt.
- **Changed the C++ code?** Re-run `python scripts/build_cpp.py` and
  restart the server.
- Sessions live in the server's memory, so restarting logs you out —
  that's a documented design choice, not a bug (see
  [`docs/OVERVIEW.md`](docs/OVERVIEW.md)).

---

## Troubleshooting

| Symptom | What it means | Fix |
|---|---|---|
| `Cannot reach MySQL at 127.0.0.1:3306` (setup exits) | The MySQL service isn't running | Step 4 — start the service, re-run setup |
| `Access denied: the root password appears to be incorrect` | Wrong root password | Re-type it; forgot it? [`docs/MYSQL_SETUP.md`](docs/MYSQL_SETUP.md) covers the reset |
| `g++ not found on PATH` | Compiler missing or not on PATH | Reinstall from step 0's compiler column, **reopen the terminal**, retry |
| Grades/attendance pages say *"C++ engine not found"* | Engine wasn't built, or the path in `backend/config.py` doesn't match your OS | Run step 3; macOS/Linux users see the note in step 5 |
| `python` is not recognized (Windows) | Python wasn't added to PATH | Reinstall Python with "Add Python to PATH" ticked |
| `Address already in use` on startup | Port 8000 is taken (maybe another copy of this app) | Change `PORT` in `backend/config.py` to e.g. `8001` and use `http://127.0.0.1:8001` |
| Login says *Invalid username or password* | Typo, or the database was never seeded | Use `vibhor / prof123`; if the setup was interrupted, re-run step 5 |
| Page shows `400 Bad request` after a save | A form value failed server-side validation (e.g. marks above the max) | It's a feature: read the friendly message on the page and correct the field |

---

## Where to go next

- **[`Learning/`](Learning/)** — image-first explanations of how every
  part works, no programming knowledge needed (start with
  `01_HOW_IT_WORKS_flowchart.png`).
- **[`docs/CODE_TOUR.md`](docs/CODE_TOUR.md)** — a guided reading order
  through the actual source files.
- **[`docs/OVERVIEW.md`](docs/OVERVIEW.md)** — the architecture and the
  design decisions behind it.
- **[`docs/FLOWCHART.md`](docs/FLOWCHART.md)** — the full request
  lifecycle, from beginner story to technical wiring.

---

**One more time, the whole journey:**

```bash
git clone https://github.com/vibh0rretr0-sudo/Student-Management-System.git
cd Student-Management-System
pip install -r requirements.txt
python scripts/build_cpp.py      # once
python scripts/setup_db.py       # once — needs MySQL running + root password
python backend/server.py         # every time you want to use it
# -> http://127.0.0.1:8000  (vibhor / prof123)
```
