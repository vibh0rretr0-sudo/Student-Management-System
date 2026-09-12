# MySQL Server + Workbench — Setup Guide

Follow these steps, then run `python scripts/setup_db.py` to create the
database. (No admin rights are needed for anything after the installer.)

## 1. Download

- MySQL Installer (Windows): <https://dev.mysql.com/downloads/installer/>
- Pick the **full** installer (`mysql-installer-community-*.msi`, ~300 MB).
  The "web" installer downloads pieces at install time and is slower.

## 2. Install — recommended choices

1. **Setup Type:** choose **Custom** (smaller than Developer Default) and add:
   - MySQL Server 8.x (x64)
   - MySQL Workbench
2. **Type and Networking:**
   - Config Type: *Development Computer*
   - Port: **3306** (the project's `backend/config.py` default)
3. **Authentication Method:** the default (*Use Strong Password Encryption*) is fine.
4. **Accounts and Roles:** set the **root** password — this is the password
   `setup_db.py` will prompt you for once. Remember it.
5. **Windows Service:** keep defaults — *MySQL80* service, start automatically.
6. Finish the configuration and complete the install.

## 3. Verify

Open MySQL Workbench → it should show a **Local instance 3306** connection.
Open it (enter the root password) and run a trivial query such as
`SELECT VERSION();` to confirm the server is up.

## 4. Initialize the project database

From the repo root:

```bash
python scripts/setup_db.py
```

The script will:

1. Prompt for the **root** password (never stored anywhere).
2. Ask you to choose a password for a new least-privilege **`sms_app`**
   user (or press Enter to auto-generate one).
3. Write that password into `backend/config.py` (git-ignored).
4. Create the `sms` database, apply `backend/db/schema.sql` (all 12
   tables) and `backend/db/seed.sql` (demo data).

## 5. Run the app

```bash
python backend/server.py
```

Open <http://127.0.0.1:8000/login> and log in with the seeded demo
professor: **`vibhor` / `prof123`**. The second seeded account
(`sharma` / `prof123`) exists to demo per-professor data scoping.

## 6. Reminder before you push to GitHub

Commit authorship is currently the placeholder
`vibhor@localhost`. Before pushing, set the email linked to your GitHub
account and optionally rewrite the author on the existing commits:

```bash
git config user.email "your-github-email@example.com"
git commit --amend --reset-author --no-edit   # fixes the latest commit
```
