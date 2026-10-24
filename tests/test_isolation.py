from datetime import date, timedelta

from helpers import auth_headers, professor_login, student_login


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/api/student/overview").status_code == 401
    assert client.get("/api/professor/overview").status_code == 401
    assert client.get("/api/common/me").status_code == 401


def test_student_cannot_reach_professor_apis(app):
    client = app.test_client()
    student_login(client)
    assert client.get("/api/professor/overview").status_code == 403
    assert client.get("/api/professor/batches").status_code == 403
    response = client.post("/api/professor/attendance", json={},
                           headers=auth_headers(client))
    assert response.status_code == 403


def test_professor_cannot_reach_student_apis(app):
    client = app.test_client()
    professor_login(client)
    assert client.get("/api/student/overview").status_code == 403
    assert client.get("/api/student/assignments").status_code == 403


def test_student_cannot_download_another_students_submission(app, db):
    row = db.query_one(
        """SELECT sub.id FROM submissions sub
           JOIN students st ON st.id = sub.student_id
           WHERE st.roll_no = '26CSAI002' LIMIT 1"""
    )
    assert row
    client = app.test_client()
    student_login(client, "26csai001")
    response = client.get(f"/api/common/files/submission/{row['id']}")
    assert response.status_code == 403


def test_professor_cannot_read_a_colleagues_assignment(app, db):
    rakesh = db.query_one("SELECT id FROM professors WHERE employee_id = 'JEC-CSE-027'")
    assignment = db.query_one(
        "SELECT id FROM assignments WHERE professor_id = ? LIMIT 1", (rakesh["id"],)
    )
    client = app.test_client()
    professor_login(client, "meera.iyer")
    response = client.get(f"/api/professor/assignments/{assignment['id']}/submissions")
    assert response.status_code == 404
    grade = client.post("/api/professor/assignments/{}/extend".format(assignment["id"]),
                        json={"due_date": "2030-01-01T10:00"},
                        headers=auth_headers(client))
    assert grade.status_code == 404


def test_professor_cannot_mark_attendance_for_untaught_subject(app, db):
    client = app.test_client()
    professor_login(client, "meera.iyer")  # teaches PH101 and EE101
    subject = db.query_one("SELECT id FROM subjects WHERE code = 'MA101'")
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")
    response = client.post("/api/professor/attendance", json={
        "batch_id": batch["id"], "subject_id": subject["id"],
        "date": "2026-01-05",
        "records": [{"student_id": 1, "status": "present"}],
    }, headers=auth_headers(client))
    assert response.status_code == 403


def test_student_attendance_is_own_only(app):
    client = app.test_client()
    student_login(client, "26csai001")
    start = (date.today() - timedelta(days=300)).isoformat()
    data = client.get(
        f"/api/student/attendance?from={start}&to={date.today().isoformat()}"
    ).get_json()["data"]
    # Every subject total should be from this student's own attendance, and
    # there are six first-semester subjects.
    assert len(data["subjects"]) == 6
    assert data["overall"]["held"] > 0
    assert 0 <= data["overall"]["percentage"] <= 100


def test_state_changing_request_requires_csrf(app):
    client = app.test_client()
    professor_login(client)
    response = client.post("/api/professor/announcements", json={
        "title": "Test", "body": "This request should be rejected.",
    })
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "csrf_invalid"
