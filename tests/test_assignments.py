import io
from datetime import datetime, timedelta

from helpers import auth_headers, professor_login, student_login


def _create_assignment(app, db):
    professor_client = app.test_client()
    professor_login(professor_client, "rakesh.sharma")
    token = auth_headers(professor_client)["X-CSRF-Token"]
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")
    subject = db.query_one("SELECT id FROM subjects WHERE code = 'CS101'")
    due = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M")
    response = professor_client.post("/api/professor/assignments", json={
        "title": "Unit test: loops and arrays",
        "description": "Solve the five loop exercises and upload a single PDF.",
        "batch_id": batch["id"], "subject_id": subject["id"],
        "due_date": due, "max_marks": 20,
    }, headers={"X-CSRF-Token": token})
    assert response.status_code == 201, response.get_data(as_text=True)
    return professor_client, response.get_json()["data"]["id"], token


def test_create_assignment_validation(app, db):
    client = app.test_client()
    professor_login(client)
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")
    subject = db.query_one("SELECT id FROM subjects WHERE code = 'CS101'")
    response = client.post("/api/professor/assignments", json={
        "title": "x", "description": "short", "batch_id": batch["id"],
        "subject_id": subject["id"],
        "due_date": (datetime.now() - timedelta(days=2)).isoformat(),
        "max_marks": 500,
    }, headers=auth_headers(client))
    assert response.status_code == 422
    fields = response.get_json()["error"]["fields"]
    assert {"title", "description", "max_marks", "due_date"} <= set(fields)


def test_student_can_submit_and_resubmit(app, db):
    _, assignment_id, _ = _create_assignment(app, db)
    student = app.test_client()
    student_login(student)
    token = auth_headers(student)["X-CSRF-Token"]

    # Unsupported file type is rejected before anything is stored.
    response = student.post(
        f"/api/student/assignments/{assignment_id}/submit",
        data={"file": (io.BytesIO(b"not allowed"), "malware.exe")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "invalid_file"

    response = student.post(
        f"/api/student/assignments/{assignment_id}/submit",
        data={"file": (io.BytesIO(b"%PDF-1.4 first submission"), "solution.pdf")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    first_submission = response.get_json()["data"]["submission"]["id"]

    response = student.post(
        f"/api/student/assignments/{assignment_id}/submit",
        data={"file": (io.BytesIO(b"%PDF-1.4 improved"), "solution-v2.pdf")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    second_submission = response.get_json()["data"]["submission"]["id"]
    assert second_submission == first_submission  # replaced in place

    listing = student.get("/api/student/assignments").get_json()["data"]["items"]
    item = next(i for i in listing if i["id"] == assignment_id)
    assert item["status"] == "submitted"
    assert item["submission"]["file_name"] == "solution-v2.pdf"


def test_professor_grades_and_student_sees_marks(app, db):
    professor, assignment_id, professor_token = _create_assignment(app, db)
    student = app.test_client()
    student_login(student)
    student_token = auth_headers(student)["X-CSRF-Token"]
    student.post(
        f"/api/student/assignments/{assignment_id}/submit",
        data={"file": (io.BytesIO(b"%PDF-1.4 work"), "answer.pdf")},
        headers={"X-CSRF-Token": student_token},
        content_type="multipart/form-data",
    )

    sheet = professor.get(
        f"/api/professor/assignments/{assignment_id}/submissions"
    ).get_json()["data"]
    row = next(i for i in sheet["items"] if i["roll_no"] == "26CSAI001")
    assert row["status"] == "submitted"
    assert row["submission_id"]

    response = professor.post(
        f"/api/professor/submissions/{row['submission_id']}/grade",
        json={"marks": 18.5, "remarks": "Clean logic, good comments."},
        headers={"X-CSRF-Token": professor_token},
    )
    assert response.status_code == 200, response.get_data(as_text=True)

    listing = student.get("/api/student/assignments").get_json()["data"]["items"]
    graded = next(i for i in listing if i["id"] == assignment_id)
    assert graded["status"] == "graded"
    assert graded["submission"]["marks"] == 18.5
    assert "Clean logic" in graded["submission"]["remarks"]

    # Graded work is locked.
    again = student.post(
        f"/api/student/assignments/{assignment_id}/submit",
        data={"file": (io.BytesIO(b"%PDF-1.4 retry"), "retry.pdf")},
        headers={"X-CSRF-Token": student_token},
        content_type="multipart/form-data",
    )
    assert again.status_code == 409

    # Marks cannot exceed max marks.
    too_high = professor.post(
        f"/api/professor/submissions/{row['submission_id']}/grade",
        json={"marks": 25}, headers={"X-CSRF-Token": professor_token},
    )
    assert too_high.status_code == 422


def test_extend_remind_and_zip_download(app, db):
    professor, assignment_id, token = _create_assignment(app, db)
    student = app.test_client()
    student_login(student)
    student_token = auth_headers(student)["X-CSRF-Token"]
    student.post(
        f"/api/student/assignments/{assignment_id}/submit",
        data={"file": (io.BytesIO(b"%PDF-1.4 zipped"), "answer.pdf")},
        headers={"X-CSRF-Token": student_token},
        content_type="multipart/form-data",
    )

    new_due = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
    response = professor.post(
        f"/api/professor/assignments/{assignment_id}/extend",
        json={"due_date": new_due}, headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    assert response.get_json()["data"]["due_date"].startswith(new_due[:10])

    reminded = professor.post(
        f"/api/professor/assignments/{assignment_id}/remind",
        headers={"X-CSRF-Token": token})
    assert reminded.status_code == 200
    assert "Reminder sent" in reminded.get_json()["data"]["message"]

    archive = professor.get(f"/api/professor/assignments/{assignment_id}/download")
    assert archive.status_code == 200
    assert archive.mimetype == "application/zip"
    assert len(archive.data) > 100


def test_delete_and_restore_assignment(app, db):
    professor, assignment_id, token = _create_assignment(app, db)
    deleted = professor.delete(
        f"/api/professor/assignments/{assignment_id}",
        headers={"X-CSRF-Token": token})
    assert deleted.status_code == 200

    listed = professor.get("/api/professor/assignments").get_json()["data"]["items"]
    assert all(item["id"] != assignment_id for item in listed)

    student = app.test_client()
    student_login(student)
    student_items = student.get("/api/student/assignments").get_json()["data"]["items"]
    assert all(item["id"] != assignment_id for item in student_items)

    restored = professor.post(
        f"/api/professor/assignments/{assignment_id}/restore",
        headers={"X-CSRF-Token": token})
    assert restored.status_code == 200
    listed = professor.get("/api/professor/assignments").get_json()["data"]["items"]
    assert any(item["id"] == assignment_id for item in listed)


def test_assignment_attachment_download_requires_membership(app, db):
    _, assignment_id, _ = _create_assignment(app, db)
    student = app.test_client()
    student_login(student, "26csai001")
    ok = student.get(f"/api/common/files/assignment/{assignment_id}")
    assert ok.status_code == 404  # created without an attachment

    outsider = app.test_client()
    student_login(outsider, "26csc001")
    forbidden = outsider.get(f"/api/common/files/assignment/{assignment_id}")
    assert forbidden.status_code == 403
