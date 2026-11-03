import io

from helpers import auth_headers, login, professor_login


def test_professor_can_create_student_account(app, db):
    professor = app.test_client()
    professor_login(professor)
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")

    response = professor.post("/api/professor/students/add", json={
        "batch_id": batch["id"],
        "roll_no": "26CSAI999",
        "full_name": "New Demo Student",
    }, headers=auth_headers(professor))

    assert response.status_code == 201, response.get_data(as_text=True)
    data = response.get_json()["data"]
    assert data["username"] == "26csai999"
    assert data["temporary_password"]
    student = db.query_one(
        "SELECT s.user_id, u.username, u.role FROM students s "
        "JOIN users u ON u.id = s.user_id WHERE s.roll_no = ?",
        ("26CSAI999",),
    )
    assert student["user_id"]
    assert student["username"] == "26csai999"
    assert student["role"] == "student"

    new_client = app.test_client()
    logged_in = login(
        new_client,
        "26CSAI999",
        password=data["temporary_password"],
    )
    assert logged_in.status_code == 200, logged_in.get_data(as_text=True)


def test_student_import_is_atomic_and_creates_accounts(app, db):
    professor = app.test_client()
    professor_login(professor)
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")
    headers = auth_headers(professor)

    invalid = professor.post(
        "/api/professor/students/import",
        data={
            "batch_id": str(batch["id"]),
            "file": (io.BytesIO(b"roll_no,full_name\n26CSAI998,Partial\n26CSAI997,\n"),
                     "students.csv"),
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    assert invalid.status_code == 422
    assert db.query_one("SELECT id FROM students WHERE roll_no = '26CSAI998'") is None

    valid = professor.post(
        "/api/professor/students/import",
        data={
            "batch_id": str(batch["id"]),
            "file": (io.BytesIO(
                "roll_no,full_name\n26CSAI998,Imported One\n26CSAI997,Imported Two\n"
                .encode("utf-8")), "students.csv"),
        },
        headers=headers,
        content_type="multipart/form-data",
    )

    assert valid.status_code == 200, valid.get_data(as_text=True)
    assert valid.get_json()["data"]["created"] == 2
    assert db.scalar("SELECT COUNT(*) AS c FROM students WHERE roll_no IN (?, ?)",
                     ("26CSAI998", "26CSAI997")) == 2
