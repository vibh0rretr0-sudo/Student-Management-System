from datetime import date, timedelta

import pytest

from app.utils import attendance_stats
from helpers import auth_headers, professor_login, student_login


def test_attendance_stats_threshold_math():
    safe = attendance_stats(80, 100)
    assert safe["percentage"] == 80.0
    assert safe["below_threshold"] is False
    assert safe["can_miss"] == 6  # 80/0.75 = 106.67 -> 6 more can be missed

    danger = attendance_stats(20, 40)
    assert danger["percentage"] == 50.0
    assert danger["below_threshold"] is True
    assert danger["need_attend"] == 40  # (20+y)/(40+y)=0.75 -> y=40

    exact = attendance_stats(30, 40)
    assert exact["percentage"] == 75.0
    assert exact["below_threshold"] is False
    assert exact["can_miss"] == 0

    assert attendance_stats(0, 0)["percentage"] == 0.0


def test_late_counts_as_attended():
    stats = attendance_stats(7, 10)
    assert stats["attended"] == 7
    assert stats["percentage"] == 70.0


def test_student_attendance_endpoint_matches_database(app, client, db):
    student_login(client)
    row = db.query_one(
        """SELECT COUNT(*) AS held,
                  SUM(CASE WHEN status IN ('present','late') THEN 1 ELSE 0 END) AS attended
           FROM attendance a JOIN students s ON s.id = a.student_id
           WHERE s.roll_no = '26CSAI001'"""
    )
    date_from = (date.today() - timedelta(days=300)).isoformat()
    date_to = date.today().isoformat()
    data = client.get(
        f"/api/student/attendance?from={date_from}&to={date_to}"
    ).get_json()["data"]
    assert data["overall"]["held"] == row["held"]
    assert data["overall"]["attended"] == row["attended"]
    expected = round(row["attended"] * 100.0 / row["held"], 1)
    assert data["overall"]["percentage"] == expected
    assert len(data["monthly_trend"]) == 6
    assert data["range"]["from"] == date_from
    for subject in data["subjects"]:
        assert subject["held"] >= subject["attended"] >= 0
        assert len(subject["name"]) > 0


def test_attendance_date_range_validation(client):
    student_login(client)
    response = client.get("/api/student/attendance?from=2026-05-01&to=2026-04-01")
    assert response.status_code == 422
    response = client.get("/api/student/attendance?from=not-a-date")
    assert response.status_code == 422


def test_timetable_has_full_week(client):
    student_login(client)
    data = client.get("/api/student/timetable").get_json()["data"]
    assert len(data["days"]) == 6
    for day in data["days"]:
        assert len(day["classes"]) == 4
        assert day["classes"][0]["room"]
    total = sum(len(day["classes"]) for day in data["days"])
    assert total == 24


def test_professor_marks_attendance_and_student_sees_it(app, db):
    professor_client = app.test_client()
    professor_login(professor_client, "rakesh.sharma")
    token = auth_headers(professor_client)["X-CSRF-Token"]
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")
    subject = db.query_one("SELECT id FROM subjects WHERE code = 'CS101'")
    today = date.today().isoformat()

    sheet = professor_client.get(
        f"/api/professor/attendance?batch_id={batch['id']}"
        f"&subject_id={subject['id']}&date={today}"
    ).get_json()["data"]
    assert len(sheet["roster"]) == 11
    records = [{"student_id": r["student_id"], "status": "present"}
               for r in sheet["roster"]]
    response = professor_client.post("/api/professor/attendance", json={
        "batch_id": batch["id"], "subject_id": subject["id"],
        "date": today, "records": records,
    }, headers={"X-CSRF-Token": token})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json()["data"]["marked"] == 11

    after = professor_client.get(
        f"/api/professor/attendance?batch_id={batch['id']}"
        f"&subject_id={subject['id']}&date={today}"
    ).get_json()["data"]
    assert all(r["status"] == "present" for r in after["roster"])

    # The same sheet can be corrected: one student marked absent.
    changed = [{"student_id": r["student_id"],
                "status": "absent" if r["roll_no"] == "26CSAI001" else "present"}
               for r in after["roster"]]
    response = professor_client.post("/api/professor/attendance", json={
        "batch_id": batch["id"], "subject_id": subject["id"],
        "date": today, "records": changed,
    }, headers={"X-CSRF-Token": token})
    assert response.status_code == 200

    student_client = app.test_client()
    student_login(student_client, "26csai001")
    date_from = (date.today() - timedelta(days=300)).isoformat()
    data = student_client.get(
        f"/api/student/attendance?from={date_from}&to={date.today().isoformat()}"
    ).get_json()["data"]
    assert any(r["date"] == today and r["status"] == "absent"
               for r in data["records"])


def test_cannot_mark_future_attendance(app, db):
    client = app.test_client()
    professor_login(client)
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")
    subject = db.query_one("SELECT id FROM subjects WHERE code = 'CS101'")
    future = (date.today() + timedelta(days=1)).isoformat()
    response = client.post("/api/professor/attendance", json={
        "batch_id": batch["id"], "subject_id": subject["id"],
        "date": future,
        "records": [{"student_id": 1, "status": "present"}],
    }, headers=auth_headers(client))
    assert response.status_code == 422


def test_attendance_rejects_foreign_student(app, db):
    client = app.test_client()
    professor_login(client)
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")
    subject = db.query_one("SELECT id FROM subjects WHERE code = 'CS101'")
    outsider = db.query_one(
        "SELECT id FROM students WHERE batch_id <> ? LIMIT 1", (batch["id"],))
    response = client.post("/api/professor/attendance", json={
        "batch_id": batch["id"], "subject_id": subject["id"],
        "date": date.today().isoformat(),
        "records": [{"student_id": outsider["id"], "status": "present"}],
    }, headers=auth_headers(client))
    assert response.status_code == 422
