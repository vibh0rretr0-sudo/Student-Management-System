# Run Doc — Student Management System (HTML/CSS + plain Python + C++ + MySQL)

How to get this project serving locally for preview.

> NOTE: the live preview runs WITHOUT MySQL. Pages that only render
> templates (login, static files, 404/405 error pages) work; anything
> that queries the database needs the MySQL setup in `docs/MYSQL_SETUP.md`
> plus `python scripts/setup_db.py`.

## 1. Reproduce the artifacts

Everything needed is in the workspace. One-time setup (from the repo root):

```bash
pip install -r requirements.txt        # PyMySQL + cryptography (already done here)
python scripts/build_cpp.py            # compiles cpp_module/build/sms_engine.exe (already done here)
```

- **No `.env` file is required.** DB credentials live in `backend/config.py`
  (git-ignored; template in `backend/config.example.py`). It is committed
  here with a placeholder password because the DB is not set up yet.
- No virtualenv is used in this workspace; the system Python 3.14 has the
  requirements installed. To reproduce from scratch, prefer:
  `python -m venv venv && venv/Scripts/pip install -r requirements.txt`
  and run the server with `venv/Scripts/python.exe backend/server.py`.
- The C++ engine is optional for serving: pages that call it show a clear
  "build it first" note instead of crashing when the binary is missing.

## 2. Run the server

Default port 8000 (from `backend/config.py`, `HOST=127.0.0.1`, `PORT=8000`).
From the repo root:

```bash
python backend/server.py
```

Then open http://127.0.0.1:8000/login — demo account after DB seeding:
`vibhor` / `prof123`.

For the Freebuff preview specifically, the server is started detached via
PowerShell `Start-Process -PassThru` with stdout/stderr redirected to
DIFFERENT files under `.freebuff/` (PowerShell fails if both share a path):

```powershell
powershell -NoProfile -Command "(Start-Process -FilePath 'python.exe' -ArgumentList 'backend/server.py' -WorkingDirectory '<repo root>' -RedirectStandardOutput '<log>.out' -RedirectStandardError '<log>.err' -WindowStyle Hidden -PassThru).Id"
```

If port 8000 is busy, edit `PORT` in `backend/config.py` (nothing else
hardcodes it), or the URL passed to `register_preview` changes accordingly.
