"""Canonical demo data for the JECRC portal.

Runs against either engine (see app/db.py).  Attendance covers ten weeks of
the real timetable derived from weekdays, so the dashboard always has
"today" classes.  Also emits schema/seed.sql for the MySQL deployment.
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

from .db import Database, db_from_config
from .security import hash_password

DEMO_PASSWORD = "Jecrc@2026"
RNG = random.Random(20261023)

PROFESSORS = [
    {
        "username": "anjali.verma",
        "employee_id": "JEC-CSE-014",
        "full_name": "Dr. Anjali Verma",
        "department": "Computer Science & Engineering",
        "designation": "Associate Professor",
        "qualifications": "M.Tech (CSE), Ph.D. (IIT Roorkee)",
        "email": "anjali.verma@jecrcu.edu.in",
        "phone": "+91 98290 45112",
        "address": "Flat 402, Malviya Nagar, Jaipur",
        "subjects": ["MA101", "HS101"],
    },
    {
        "username": "rakesh.sharma",
        "employee_id": "JEC-CSE-027",
        "full_name": "Prof. Rakesh Sharma",
        "department": "Computer Science & Engineering",
        "designation": "Assistant Professor",
        "qualifications": "M.Tech (Computer Science), Ph.D. pursuing (RTU Kota)",
        "email": "rakesh.sharma@jecrcu.edu.in",
        "phone": "+91 94140 77820",
        "address": "B-17, Vaishali Nagar, Jaipur",
        "subjects": ["CS101", "CS102"],
    },
    {
        "username": "meera.iyer",
        "employee_id": "JEC-AS-009",
        "full_name": "Dr. Meera Iyer",
        "department": "Applied Sciences",
        "designation": "Assistant Professor",
        "qualifications": "M.Sc. (Physics), Ph.D. (MNIT Jaipur)",
        "email": "meera.iyer@jecrcu.edu.in",
        "phone": "+91 99280 61234",
        "address": "C-9, Jawahar Nagar, Jaipur",
        "subjects": ["PH101", "EE101"],
    },
]

BATCHES = [
    {"code": "CSAI-A", "name": "CSE AI & DevOps — A",
     "branch": "Computer Science & Engineering (AI & DevOps)", "semester": 1, "year": 2026},
    {"code": "CSAI-B", "name": "CSE AI & DevOps — B",
     "branch": "Computer Science & Engineering (AI & DevOps)", "semester": 1, "year": 2026},
    {"code": "CSC-A", "name": "CSE Core — A",
     "branch": "Computer Science & Engineering", "semester": 1, "year": 2026},
]

SUBJECTS = [
    {"code": "MA101", "name": "Engineering Mathematics-I", "credits": 4},
    {"code": "CS101", "name": "Programming in C", "credits": 4},
    {"code": "PH101", "name": "Engineering Physics", "credits": 3},
    {"code": "EE101", "name": "Basic Electrical Engineering", "credits": 3},
    {"code": "HS101", "name": "Communication Skills", "credits": 2},
    {"code": "CS102", "name": "AI & DevOps Foundations", "credits": 3},
]

STUDENT_NAMES = [
    ("Aarav Mehta", "male"), ("Ananya Sharma", "female"), ("Rohan Gupta", "male"),
    ("Priya Nair", "female"), ("Kabir Singh", "male"), ("Ishita Agarwal", "female"),
    ("Aditya Verma", "male"), ("Sneha Joshi", "female"), ("Arjun Rathore", "male"),
    ("Diya Khandelwal", "female"), ("Vivaan Mathur", "male"),
    ("Krishna Yadav", "male"), ("Nandini Rao", "female"), ("Harsh Vardhan", "male"),
    ("Megha Purohit", "female"), ("Siddharth Jain", "male"), ("Tanvi Bhatnagar", "female"),
    ("Yash Chouhan", "male"), ("Riya Soni", "female"), ("Devansh Saxena", "male"),
    ("Aisha Khan", "female"),
    ("Om Prakash Gurjar", "male"), ("Kavya Shekhawat", "female"),
    ("Nitin Choudhary", "male"), ("Prerna Sharma", "female"), ("Saurabh Meena", "male"),
    ("Anjali Solanki", "female"), ("Manish Kumawat", "male"), ("Shreya Bansal", "female"),
    ("Abhinav Tiwari", "male"),
]

GUARDIANS = [
    "Rajesh", "Suman", "Vikram", "Anita", "Mahesh", "Kavita", "Dinesh", "Poonam",
    "Suresh", "Rekha", "Ashok", "Neelam", "Prakash", "Sharda", "Mukesh", "Usha",
]

SLOTS = [
    ("09:00", "09:55"),
    ("10:00", "10:55"),
    ("11:10", "12:05"),
    ("12:10", "13:05"),
]

ROOMS = ["A-201", "A-202", "B-104", "B-105", "C-301", "CS Lab-1", "Physics Lab"]


def _name_email(name: str) -> str:
    parts = name.lower().replace(".", "").split()
    return f"{parts[0]}.{parts[-1]}@jecrcu.edu.in"


def _roll_numbers() -> list[tuple[dict, list[str]]]:
    """Split the 30 students across three batches with realistic roll codes."""
    groups = [
        (BATCHES[0], [f"26CSAI{i:03d}" for i in range(1, 12)]),
        (BATCHES[1], [f"26CSAI{i:03d}" for i in range(101, 111)]),
        (BATCHES[2], [f"26CSC{i:03d}" for i in range(1, 10)]),
    ]
    return groups


def _ensure_demo_pdf(upload_dir: Path) -> str:
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / "seed-demo-submission.pdf"
    if not path.exists():
        body = b"BT /F1 16 Tf 72 780 Td (JECRC Portal demo submission) Tj ET"
        pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]"
            b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length " + str(len(body)).encode() + b">>stream\n" + body
            + b"\nendstream endobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF\n"
        )
        path.write_bytes(pdf)
    return path.name


def seed(db: Database, upload_dir: str | Path) -> dict:
    """Insert the full demo dataset. Returns a few ids for convenience."""
    upload_dir = Path(upload_dir)
    demo_pdf = _ensure_demo_pdf(upload_dir)
    now = datetime.now()
    today = now.date()
    password_hash = hash_password(DEMO_PASSWORD)

    # -- batches / subjects ------------------------------------------------
    batch_ids: dict[str, int] = {}
    for batch in BATCHES:
        batch_ids[batch["code"]] = db.insert("batches", {
            "code": batch["code"], "name": batch["name"], "branch": batch["branch"],
            "semester": batch["semester"], "year": batch["year"],
            "created_at": now,
        })

    subject_ids: dict[str, int] = {}
    for subject in SUBJECTS:
        subject_ids[subject["code"]] = db.insert("subjects", {
            "code": subject["code"], "name": subject["name"],
            "credits": subject["credits"], "semester": 1,
        })

    for batch_code in batch_ids:
        for code in subject_ids:
            db.insert("batch_subjects", {
                "batch_id": batch_ids[batch_code], "subject_id": subject_ids[code],
            })

    # -- professors --------------------------------------------------------
    professor_ids: dict[str, int] = {}
    professor_by_subject: dict[str, int] = {}
    for prof in PROFESSORS:
        user_id = db.insert("users", {
            "username": prof["username"], "password_hash": password_hash,
            "role": "professor", "is_active": 1,
            "created_at": now, "updated_at": now,
        })
        pid = db.insert("professors", {
            "user_id": user_id, "employee_id": prof["employee_id"],
            "full_name": prof["full_name"], "email": prof["email"],
            "phone": prof["phone"], "address": prof["address"],
            "department": prof["department"], "designation": prof["designation"],
            "qualifications": prof["qualifications"], "photo": None,
            "created_at": now,
        })
        professor_ids[prof["username"]] = pid
        for code in prof["subjects"]:
            professor_by_subject[code] = pid
            for batch_code in batch_ids:
                db.insert("professor_batch_subject", {
                    "professor_id": pid, "batch_id": batch_ids[batch_code],
                    "subject_id": subject_ids[code],
                })

    # -- students ----------------------------------------------------------
    groups = _roll_numbers()
    student_rows: list[dict] = []
    name_index = 0
    for batch, rolls in groups:
        for roll in rolls:
            full_name, gender = STUDENT_NAMES[name_index]
            name_index += 1
            guardian = GUARDIANS[name_index % len(GUARDIANS)] + " " + full_name.split()[-1]
            user_id = db.insert("users", {
                "username": roll.lower(), "password_hash": password_hash,
                "role": "student", "is_active": 1,
                "created_at": now, "updated_at": now,
            })
            student_id = db.insert("students", {
                "user_id": user_id, "roll_no": roll, "full_name": full_name,
                "email": f"{roll.lower()}@jecrcu.edu.in",
                "phone": f"+91 9{RNG.randint(100000000, 899999999)}",
                "address": f"{RNG.randint(1, 99)}, {RNG.choice(['Malviya Nagar', 'Vaishali Nagar', 'Mansarovar', 'Jagatpura', 'Shyam Nagar'])}, Jaipur",
                "branch": batch["branch"], "semester": batch["semester"],
                "batch_id": batch_ids[batch["code"]],
                "guardian_name": guardian,
                "guardian_phone": f"+91 9{RNG.randint(100000000, 899999999)}",
                "photo": None, "created_at": now,
            })
            student_rows.append({
                "id": student_id, "roll": roll, "batch_id": batch_ids[batch["code"]],
                "user_id": user_id, "name": full_name,
            })

    # -- timetable ---------------------------------------------------------
    subject_codes = [s["code"] for s in SUBJECTS]
    timetable_rows = []
    for b_idx, (batch_code, batch_id) in enumerate(batch_ids.items()):
        for day in range(1, 7):  # Monday..Saturday
            rotated = subject_codes[(day - 1 + b_idx) % len(subject_codes):] + \
                      subject_codes[:(day - 1 + b_idx) % len(subject_codes)]
            for slot_idx, (start, end) in enumerate(SLOTS):
                code = rotated[slot_idx % len(rotated)]
                room = ROOMS[(slot_idx + day + b_idx) % len(ROOMS)]
                tid = db.insert("timetable", {
                    "batch_id": batch_id, "day_of_week": day,
                    "start_time": start, "end_time": end, "room": room,
                    "subject_id": subject_ids[code],
                    "professor_id": professor_by_subject[code],
                })
                timetable_rows.append({
                    "id": tid, "batch_id": batch_id, "day": day,
                    "start": start, "end": end, "subject_id": subject_ids[code],
                    "code": code, "professor_id": professor_by_subject[code],
                })

    # -- attendance: ten weeks up to yesterday -----------------------------
    student_bias = {}
    for idx, student in enumerate(student_rows):
        # A deterministic spread from weak (below 75%) to strong attendance.
        student_bias[student["id"]] = 0.62 + ((idx * 7) % 34) / 100.0

    attendance_rows = []
    start_day = today - timedelta(days=70)
    day = start_day
    while day < today:
        if day.weekday() < 6:  # Mon..Sat
            dow = day.weekday() + 1
            for tt in [t for t in timetable_rows if t["day"] == dow]:
                students = [s for s in student_rows if s["batch_id"] == tt["batch_id"]]
                for student in students:
                    base = student_bias[student["id"]]
                    # subject-level wobble so one subject can drag a student down
                    wobble = ((sum(ord(c) for c in tt["code"]) % 11) - 5) / 100.0
                    chance = min(0.98, max(0.35, base + wobble))
                    roll = RNG.random()
                    if roll < chance:
                        status = "late" if RNG.random() < 0.06 else "present"
                    else:
                        status = "absent"
                    attendance_rows.append((
                        student["id"], tt["subject_id"], tt["batch_id"],
                        day.strftime("%Y-%m-%d"), status, tt["professor_id"], now,
                    ))
        day += timedelta(days=1)

    db.execute_many(
        """INSERT INTO attendance
           (student_id, subject_id, batch_id, date, status, marked_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        attendance_rows,
    )

    # -- assignments + submissions ----------------------------------------
    assignment_specs = [
        ("CS101", "C program: matrix operations",
         "Write a C program that performs addition, multiplication and transposition of two matrices. Submit the .c source and a short README with sample output.",
         -9, 20, "C Programming Lab"),
        ("MA101", "Matrices and eigenvalues — problem set",
         "Solve problems 4.1 to 4.12 from Unit 3 of the prescribed text. Show every intermediate step; scanned handwritten work is acceptable.",
         -3, 25, "Tutorial Sheet 3"),
        ("PH101", "Interference & diffraction lab record",
         "Complete the lab record for experiments 2 and 3, including observations, error analysis and conclusions. One PDF per student.",
         2, 15, "Lab Manual"),
        ("CS102", "Git & Docker workflow report",
         "Create a small project, commit it to Git with a sensible history, containerise it with Docker and submit a one-page report with screenshots plus your Dockerfile.",
         6, 20, "DevOps Lab"),
    ]
    assignment_rows = []
    for batch_code, batch_id in batch_ids.items():
        for code, title, description, due_offset, max_marks, attachment_name in assignment_specs:
            professor_id = professor_by_subject[code]
            due = datetime.combine(today + timedelta(days=due_offset), time(23, 59))
            aid = db.insert("assignments", {
                "title": title, "description": description,
                "subject_id": subject_ids[code], "batch_id": batch_id,
                "professor_id": professor_id, "due_date": due,
                "max_marks": max_marks,
                "attachment_path": demo_pdf, "attachment_name": f"{attachment_name}.pdf",
                "attachment_size": 512,
                "created_at": datetime.combine(today + timedelta(days=due_offset - 12), time(10, 0)),
                "updated_at": now, "deleted_at": None,
            })
            assignment_rows.append({
                "id": aid, "batch_id": batch_id, "subject_id": subject_ids[code],
                "code": code, "due": due, "max": max_marks, "professor_id": professor_id,
            })

    submission_rows = []
    for assignment in assignment_rows:
        students = [s for s in student_rows if s["batch_id"] == assignment["batch_id"]]
        due_passed = assignment["due"] < now
        for idx, student in enumerate(students):
            # Deterministic-ish spread: strong students submit more often.
            strong = student_bias[student["id"]] > 0.75
            roll = RNG.random()
            if due_passed:
                submit_chance = 0.86 if strong else 0.62
            else:
                submit_chance = 0.5 if strong else 0.25
            if roll > submit_chance:
                continue
            submitted_at = assignment["due"] - timedelta(
                days=RNG.randint(1, 5), hours=RNG.randint(0, 8)
            )
            graded = due_passed and assignment["due"].date() < today - timedelta(days=1) \
                and RNG.random() < 0.8
            marks = None
            remarks = None
            status = "submitted"
            graded_at = None
            if graded:
                marks = round(assignment["max"] * RNG.uniform(0.55, 0.98), 1)
                remarks = RNG.choice([
                    "Well structured solution. Watch the indentation.",
                    "Good work, but the conclusion needs more depth.",
                    "Accurate results; include error analysis next time.",
                    "Nicely presented. Revisit question 4.",
                ])
                status = "graded"
                graded_at = submitted_at + timedelta(days=2)
            submission_rows.append((
                assignment["id"], student["id"], demo_pdf,
                f"{student['roll']}_{assignment['code']}_submission.pdf", 512,
                submitted_at, marks, remarks, assignment["professor_id"],
                graded_at, status,
            ))
    db.execute_many(
        """INSERT INTO submissions
           (assignment_id, student_id, file_path, file_name, file_size, submitted_at,
            marks, remarks, graded_by, graded_at, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        submission_rows,
    )

    # -- announcements -----------------------------------------------------
    ann_specs = [
        ("Mid-semester examination schedule released", "important", 1, "all", [], -2,
         "The mid-semester examination schedule for Semester 1 is now available on the notice board and the student portal. Exams begin Monday, 9 November. Carry your college ID and arrive 15 minutes early.",
         "anjali.verma"),
        ("C lab manual — bring a printed copy", "normal", 0, "batches", ["CSAI-A", "CSAI-B"], -1,
         "For tomorrow's Programming in C lab, bring a printed copy of exercises 1–5. Students without the manual will not be allowed to attempt the lab assessment.",
         "rakesh.sharma"),
        ("Guest lecture: building CI/CD pipelines", "normal", 1, "all", [], -4,
         "A guest lecture by Mr. Nitin Bansal (DevOps Lead, Zomato) on building reliable CI/CD pipelines will be held in the Seminar Hall on Friday at 2:00 PM. Attendance is encouraged for all first-year students.",
         "rakesh.sharma"),
        ("Physics lab record submission — deadline extended", "important", 0, "batches", ["CSAI-A", "CSC-A"], -3,
         "The deadline for the Physics lab record has been extended to next Monday. Please ensure all observations are signed by the lab instructor before submission.",
         "meera.iyer"),
        ("Semester fee payment window is open", "urgent", 0, "all", [], -6,
         "The Semester 1 fee payment window closes on 31 October. Pay online through the ERP fee portal to avoid a late fee. Contact the accounts office for any discrepancy.",
         "anjali.verma"),
        ("Attendance below 75% — counselling session", "normal", 0, "batches", ["CSC-A"], -8,
         "Students with attendance below 75% in CSE Core A must attend a counselling session with the class coordinator on Saturday at 11:00 AM in room C-301.",
         "anjali.verma"),
        ("Library orientation for first-year students", "normal", 0, "batches", ["CSAI-B"], -5,
         "A library orientation session will be conducted on Thursday at 3:00 PM. Learn how to access IEEE, Springer and DELNET resources from the campus network.",
         "meera.iyer"),
        ("Hackathon registrations open next week", "important", 0, "all", [], 2,
         "Registrations for the 24-hour JECRC DevSprint hackathon open next week. Teams of 3–4 students; themes include campus automation, AI tooling and accessibility.",
         "rakesh.sharma"),
    ]
    announcement_rows = []
    for title, priority, pinned, audience, targets, offset, body, username in ann_specs:
        professor_id = professor_ids[username]
        publish_at = datetime.combine(today + timedelta(days=offset), time(9, 30))
        aid = db.insert("announcements", {
            "professor_id": professor_id, "title": title, "body": body,
            "priority": priority, "pinned": pinned, "audience": audience,
            "publish_at": publish_at,
            "created_at": publish_at - timedelta(hours=2),
            "updated_at": publish_at - timedelta(hours=2),
            "deleted_at": None,
        })
        batch_ids_for = list(batch_ids.values()) if audience == "all" else \
            [batch_ids[code] for code in targets]
        for batch_id in batch_ids_for:
            db.insert("announcement_targets", {
                "announcement_id": aid, "batch_id": batch_id,
            })
        announcement_rows.append({
            "id": aid, "targets": set(batch_ids_for), "publish_at": publish_at,
        })

    # reads for a subset of students on older announcements
    for ann in announcement_rows:
        if ann["publish_at"].date() >= today:
            continue
        for student in student_rows:
            if student["batch_id"] not in ann["targets"]:
                continue
            if RNG.random() < 0.45:
                db.insert("announcement_reads", {
                    "announcement_id": ann["id"], "user_id": student["user_id"],
                    "read_at": ann["publish_at"] + timedelta(hours=RNG.randint(1, 20)),
                })

    # -- notifications -----------------------------------------------------
    for student in student_rows:
        notify_at = now - timedelta(days=RNG.randint(0, 3))
        db.insert("notifications", {
            "user_id": student["user_id"],
            "title": "New announcement from Dr. Anjali Verma",
            "body": "Mid-semester examination schedule released. Check the announcements page.",
            "link": "/#/announcements", "kind": "announcement", "is_read": 0,
            "created_at": notify_at,
        })
        if student_bias[student["id"]] < 0.75:
            db.insert("notifications", {
                "user_id": student["user_id"],
                "title": "Attendance warning",
                "body": "Your overall attendance is below 75%. Attend the next classes to stay eligible.",
                "link": "/#/attendance", "kind": "warning", "is_read": 0,
                "created_at": now - timedelta(days=2),
            })
    for username, pid in professor_ids.items():
        user = db.query_one("SELECT user_id FROM professors WHERE id = ?", (pid,))
        db.insert("notifications", {
            "user_id": user["user_id"],
            "title": "Submissions awaiting review",
            "body": "New student submissions are waiting for grading.",
            "link": "/#/assignments", "kind": "assignment", "is_read": 0,
            "created_at": now - timedelta(hours=6),
        })

    db.insert("audit_log", {
        "user_id": None, "action": "seed", "entity": "database", "entity_id": None,
        "meta": "Demo dataset generated", "ip": "127.0.0.1", "created_at": now,
    })

    return {"batches": batch_ids, "subjects": subject_ids,
            "professors": professor_ids, "students": student_rows}


# --------------------------------------------------------------------------
# MySQL dump (schema/seed.sql)
# --------------------------------------------------------------------------
DUMP_TABLES = [
    "users", "batches", "subjects", "students", "professors", "batch_subjects",
    "professor_batch_subject", "timetable", "attendance", "assignments",
    "submissions", "announcements", "announcement_targets", "announcement_reads",
    "notifications",
]


def _sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        value = str(value)
    text = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{text}'"


def emit_mysql_seed(db: Database, path: str | Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "-- JECRC Student & Faculty Portal — demo seed data (MySQL 8)",
        "-- Generated by `python -m app.seed --emit-sql`.",
        f"-- Every demo account password: {DEMO_PASSWORD}",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]
    for table in DUMP_TABLES:
        rows = db.query(f"SELECT * FROM {table}")
        if not rows:
            continue
        columns = list(rows[0].keys())
        lines.append(f"-- {table} ({len(rows)} rows)")
        lines.append("DELETE FROM " + table + ";")
        col_sql = ", ".join(columns)
        for row in rows:
            values = ", ".join(_sql_literal(row[c]) for c in columns)
            lines.append(f"INSERT INTO {table} ({col_sql}) VALUES ({values});")
        lines.append("")
    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    import argparse

    from config import Config

    parser = argparse.ArgumentParser(description="Seed the JECRC portal database")
    parser.add_argument("--reset", action="store_true", help="drop and recreate schema first")
    parser.add_argument("--emit-sql", metavar="PATH", default=None,
                        help="write a MySQL seed dump to PATH")
    args = parser.parse_args()

    from .db import init_db

    class _App:
        root_path = str(Path(__file__).resolve().parent)
        config = {
            "DB_ENGINE": Config.DB_ENGINE,
            "SQLITE_PATH": Config.SQLITE_PATH,
            "MYSQL_HOST": Config.MYSQL_HOST,
            "MYSQL_PORT": Config.MYSQL_PORT,
            "MYSQL_USER": Config.MYSQL_USER,
            "MYSQL_PASSWORD": Config.MYSQL_PASSWORD,
            "MYSQL_DATABASE": Config.MYSQL_DATABASE,
        }

    app = _App()
    init_db(app, drop=args.reset)
    db = db_from_config(app.config)
    try:
        existing = db.scalar("SELECT COUNT(*) AS c FROM users", default=0) or 0
        if existing == 0:
            seed(db, Config.UPLOAD_DIR)
            print("Demo data loaded. Every account uses the demo password below.")
        else:
            print("Database already contains users; seed skipped "
                  "(use --reset to rebuild).")
        if args.emit_sql is not None:
            emit_mysql_seed(db, args.emit_sql)
            print(f"MySQL seed SQL written to {args.emit_sql}")
        print(f"  students: {db.scalar('SELECT COUNT(*) AS c FROM students')}")
        print(f"  attendance rows: {db.scalar('SELECT COUNT(*) AS c FROM attendance')}")
        print(f"  Demo password: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
