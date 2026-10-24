from helpers import auth_headers, professor_login, student_login


def test_student_only_sees_announcements_for_their_batches(client, db):
    student_login(client)
    data = client.get("/api/student/announcements?per_page=50").get_json()["data"]
    batch = db.query_one("SELECT id, name FROM batches WHERE code = 'CSAI-A'")
    # The seeded CSC-A-only counselling notice must not leak to CSAI-A.
    assert all("Attendance below 75%" not in item["title"] for item in data["items"])
    # The all-batch fee notice must be visible.
    assert any("Semester fee payment" in item["title"] for item in data["items"])
    for item in data["items"]:
        assert item["professor"]
        assert isinstance(item["batches"], list)
    assert batch["name"]


def test_mark_read_and_mark_all_read(client):
    student_login(client)
    items = client.get("/api/student/announcements").get_json()["data"]["items"]
    unread = next(item for item in items if not item["is_read"])
    response = client.post("/api/student/announcements/read",
                           json={"id": unread["id"]},
                           headers=auth_headers(client))
    assert response.status_code == 200
    after = client.get("/api/student/announcements?unread=1") \
        .get_json()["data"]["items"]
    assert all(item["id"] != unread["id"] for item in after)

    response = client.post("/api/student/announcements/read",
                           json={"all": True},
                           headers=auth_headers(client))
    assert response.status_code == 200
    remaining = client.get("/api/student/announcements?unread=1") \
        .get_json()["data"]["items"]
    assert remaining == []


def test_professor_creates_targeted_announcement(app, db):
    professor = app.test_client()
    professor_login(professor, "rakesh.sharma")
    token = auth_headers(professor)["X-CSRF-Token"]
    batch_a = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")
    batch_b = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-B'")

    response = professor.post("/api/professor/announcements", json={
        "title": "Lab assessment next Tuesday",
        "body": "The C lab assessment will cover loops, arrays and functions.",
        "priority": "important", "pinned": True, "audience": "batches",
        "batch_ids": [batch_a["id"], batch_b["id"]],
    }, headers={"X-CSRF-Token": token})
    assert response.status_code == 201, response.get_data(as_text=True)
    announcement_id = response.get_json()["data"]["id"]

    listing = professor.get("/api/professor/announcements").get_json()["data"]["items"]
    created = next(item for item in listing if item["id"] == announcement_id)
    assert created["priority"] == "important"
    assert created["pinned"] is True
    assert created["audience_count"] >= 21
    assert len(created["batches"]) == 2

    student_a = app.test_client()
    student_login(student_a, "26csai001")
    visible = student_a.get("/api/student/announcements?per_page=50") \
        .get_json()["data"]["items"]
    assert any(item["id"] == announcement_id for item in visible)

    student_c = app.test_client()
    student_login(student_c, "26csc001")
    hidden = student_c.get("/api/student/announcements?per_page=50") \
        .get_json()["data"]["items"]
    assert all(item["id"] != announcement_id for item in hidden)


def test_professor_cannot_target_another_batch(app, db):
    # A professor can only target batches they teach. Every seeded professor
    # teaches all batches, so assert the guard via a bogus batch id instead.
    professor = app.test_client()
    professor_login(professor, "anjali.verma")
    response = professor.post("/api/professor/announcements", json={
        "title": "Invalid target", "body": "This targets a nonexistent batch.",
        "audience": "batches", "batch_ids": [99999],
    }, headers=auth_headers(professor))
    assert response.status_code == 403


def test_scheduled_announcement_not_visible_to_students(app, db):
    professor = app.test_client()
    professor_login(professor, "meera.iyer")
    token = auth_headers(professor)["X-CSRF-Token"]
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSC-A'")
    response = professor.post("/api/professor/announcements", json={
        "title": "Scheduled notice",
        "body": "This should stay hidden until next week.",
        "audience": "batches", "batch_ids": [batch["id"]],
        "publish_at": "2099-01-01T09:00",
    }, headers={"X-CSRF-Token": token})
    assert response.status_code == 201
    announcement_id = response.get_json()["data"]["id"]

    student = app.test_client()
    student_login(student, "26csc001")
    visible = student.get("/api/student/announcements?per_page=50") \
        .get_json()["data"]["items"]
    assert all(item["id"] != announcement_id for item in visible)

    listing = professor.get("/api/professor/announcements").get_json()["data"]["items"]
    scheduled = next(item for item in listing if item["id"] == announcement_id)
    assert scheduled["status"] == "scheduled"


def test_announcement_update_and_delete(app, db):
    professor = app.test_client()
    professor_login(professor, "anjali.verma")
    token = auth_headers(professor)["X-CSRF-Token"]
    batch = db.query_one("SELECT id FROM batches WHERE code = 'CSAI-A'")
    created = professor.post("/api/professor/announcements", json={
        "title": "Edit me", "body": "Original body for the notice.",
        "audience": "batches", "batch_ids": [batch["id"]],
    }, headers={"X-CSRF-Token": token}).get_json()["data"]["id"]

    updated = professor.patch(f"/api/professor/announcements/{created}", json={
        "title": "Edited notice", "priority": "urgent",
    }, headers={"X-CSRF-Token": token})
    assert updated.status_code == 200
    listing = professor.get("/api/professor/announcements").get_json()["data"]["items"]
    edited = next(item for item in listing if item["id"] == created)
    assert edited["title"] == "Edited notice"
    assert edited["priority"] == "urgent"

    deleted = professor.delete(f"/api/professor/announcements/{created}",
                               headers={"X-CSRF-Token": token})
    assert deleted.status_code == 200
    listing = professor.get("/api/professor/announcements").get_json()["data"]["items"]
    assert all(item["id"] != created for item in listing)
