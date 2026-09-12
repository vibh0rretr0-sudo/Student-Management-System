"""Student CRUD, search/filter, and edit-permission checks.

Permission model (confirmed): every professor can VIEW all students,
but can only EDIT/DELETE students enrolled in at least one of their own
courses.
"""
from backend.models import db

_BASE_SELECT = """
SELECT s.id, s.name, s.roll_number, s.date_of_birth, s.contact,
       s.enrollment_date, s.section_id, sec.section_name, b.batch_name
FROM students s
JOIN sections sec ON sec.id = s.section_id
JOIN batches b ON b.id = sec.batch_id
"""


def create(name, roll_number, section_id, enrollment_date, date_of_birth=None, contact=None):
    """Insert a student and return the new id."""
    return db.execute(
        """INSERT INTO students
           (name, roll_number, date_of_birth, contact, enrollment_date, section_id)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (name, roll_number, date_of_birth, contact, enrollment_date, section_id),
    )


def get(student_id):
    """Return one student with section/batch names, or None."""
    return db.fetch_one(_BASE_SELECT + "WHERE s.id = %s", (student_id,))


def update(student_id, name, roll_number, section_id, enrollment_date, date_of_birth=None, contact=None):
    """Update a student's editable fields."""
    db.execute(
        """UPDATE students
           SET name = %s, roll_number = %s, date_of_birth = %s, contact = %s,
               enrollment_date = %s, section_id = %s
           WHERE id = %s""",
        (name, roll_number, date_of_birth, contact, enrollment_date, section_id, student_id),
    )


def delete(student_id):
    """Delete a student (enrollments/marks/attendance cascade)."""
    db.execute("DELETE FROM students WHERE id = %s", (student_id,))


def roll_exists(section_id, roll_number, exclude_student_id=None):
    """True when another student in the section already uses this roll number."""
    row = db.fetch_one(
        """SELECT 1 AS ok FROM students
           WHERE section_id = %s AND roll_number = %s AND id != %s LIMIT 1""",
        (section_id, roll_number, exclude_student_id or 0),
    )
    return row is not None


def search(query=None, course_id=None, section_id=None):
    """List students with optional filters: name/roll substring, course, section."""
    sql = _BASE_SELECT
    params = []
    where = []

    if query:
        where.append("(s.name LIKE %s OR s.roll_number LIKE %s)")
        like = f"%{query.strip()}%"
        params += [like, like]
    if course_id:
        where.append(
            "s.id IN (SELECT student_id FROM enrollments WHERE course_id = %s)"
        )
        params.append(course_id)
    if section_id:
        where.append("s.section_id = %s")
        params.append(section_id)

    if where:
        sql += "WHERE " + " AND ".join(where)
    sql += " ORDER BY sec.section_name, s.roll_number"
    return db.fetch_all(sql, tuple(params))


def can_edit(student_id, professor_id):
    """Edit rights under the confirmed view-all/edit-own model.

    A professor may edit a student when either:
      - the student is enrolled in at least one of their courses, or
      - the student is 'unclaimed' (zero enrollments anywhere) — otherwise
        a freshly created student could never be edited or removed by
        anyone. Once the student joins any course, only that course's
        professor retains edit rights.
    """
    row = db.fetch_one(
        """SELECT
               EXISTS(SELECT 1
                      FROM enrollments e
                      JOIN courses c ON c.id = e.course_id
                      WHERE e.student_id = %s AND c.professor_id = %s) AS mine,
               (SELECT COUNT(*) FROM enrollments WHERE student_id = %s) AS total""",
        (student_id, professor_id, student_id),
    )
    return bool(row and (row["mine"] or row["total"] == 0))


def enrolled_courses(student_id):
    """Courses a student is enrolled in, with the professor's name."""
    return db.fetch_all(
        """SELECT c.id, c.course_name, c.course_code, c.term, p.name AS professor_name
           FROM enrollments e
           JOIN courses c ON c.id = e.course_id
           JOIN professors p ON p.id = c.professor_id
           WHERE e.student_id = %s
           ORDER BY c.course_name""",
        (student_id,),
    )
