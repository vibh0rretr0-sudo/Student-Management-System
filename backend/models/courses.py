"""Courses, batches/sections, and enrollment management.

A course belongs to one professor, one section, and one weekly slot, so
parallel sections can run labs in the same slot (docs/OVERVIEW.md). Creating a
course is rejected when the same section already has a course overlapping
that slot.
"""
from backend.models import db


def list_sections():
    """All sections with their batch, for dropdowns."""
    return db.fetch_all(
        """SELECT sec.id, sec.section_name, b.batch_name
           FROM sections sec JOIN batches b ON b.id = sec.batch_id
           ORDER BY b.batch_name, sec.section_name"""
    )


def list_for_professor(professor_id):
    """The professor's courses with enrollment counts, soonest slot first."""
    return db.fetch_all(
        """SELECT c.id, c.course_name, c.course_code, c.term, c.day_of_week,
                  c.start_time, c.end_time, sec.section_name,
                  COUNT(e.id) AS student_count
           FROM courses c
           JOIN sections sec ON sec.id = c.section_id
           LEFT JOIN enrollments e ON e.course_id = c.id
           WHERE c.professor_id = %s
           GROUP BY c.id
           ORDER BY sec.section_name, c.course_code""",
        (professor_id,),
    )
    # Two SQL details worth remembering:
    #   LEFT JOIN  -> a course with zero enrollments still appears (COUNT 0)
    #   COUNT(e.id) -> counts matched rows only; COUNT(*) would count the
    #                  NULL-extended row and show 1 for empty courses


def get(course_id):
    """One course with section and professor names, or None."""
    return db.fetch_one(
        """SELECT c.*, sec.section_name, p.name AS professor_name
           FROM courses c
           JOIN sections sec ON sec.id = c.section_id
           JOIN professors p ON p.id = c.professor_id
           WHERE c.id = %s""",
        (course_id,),
    )


def create(course_name, course_code, professor_id, section_id, term, day_of_week, start_time, end_time):
    """Create a course; raises ValueError on a schedule clash in the section."""
    _ensure_no_clash(section_id, day_of_week, start_time, end_time)
    return db.execute(
        """INSERT INTO courses
           (course_name, course_code, professor_id, section_id, term,
            day_of_week, start_time, end_time)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (course_name, course_code, professor_id, section_id, term, day_of_week, start_time, end_time),
    )


def update(course_id, course_name, course_code, section_id, term, day_of_week, start_time, end_time):
    """Update a course; raises ValueError on a schedule clash in the section."""
    _ensure_no_clash(section_id, day_of_week, start_time, end_time, exclude_course_id=course_id)
    db.execute(
        """UPDATE courses
           SET course_name = %s, course_code = %s, section_id = %s, term = %s,
               day_of_week = %s, start_time = %s, end_time = %s
           WHERE id = %s""",
        (course_name, course_code, section_id, term, day_of_week, start_time, end_time, course_id),
    )


def delete(course_id):
    """Delete a course (enrollments/assignments/exams/attendance cascade)."""
    db.execute("DELETE FROM courses WHERE id = %s", (course_id,))


def is_owner(course_id, professor_id):
    """True when the course belongs to the professor.

    One query doing double duty: ownership check AND existence check —
    handlers call this before every edit, and non-owners can't even
    learn that the id exists (same 403 either way).
    """
    row = db.fetch_one(
        "SELECT 1 AS ok FROM courses WHERE id = %s AND professor_id = %s",
        (course_id, professor_id),
    )
    return row is not None


WEEKDAYS = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday",
            5: "Friday", 6: "Saturday", 7: "Sunday"}


def _ensure_no_clash(section_id, day_of_week, start_time, end_time, exclude_course_id=None):
    """Reject a slot that overlaps another course of the same section.

    Two [start, end) intervals overlap when a.start < b.end AND b.start < a.end.
    Mapping a=existing course, b=new slot gives the WHERE below — note the
    parameters arrive as (end_time, start_time) in that order. They LOOK
    swapped; they are not. (And touching an edge exactly — 10:00 ending
    where 10:00 begins — is allowed, hence strict <.)
    """
    clash = db.fetch_one(
        """SELECT course_name FROM courses
           WHERE section_id = %s AND day_of_week = %s
             AND start_time < %s AND %s < end_time
             AND id != %s
           LIMIT 1""",
        (section_id, day_of_week, end_time, start_time, exclude_course_id or 0),
    )
    if clash:
        # The error names the clashing course — the professor can fix the
        # slot without opening the timetable.
        raise ValueError(
            f"Schedule clash: section already has '{clash['course_name']}' overlapping this slot."
        )


# ---------- Enrollment ----------

def list_enrolled(course_id):
    """Students enrolled in the course."""
    return db.fetch_all(
        """SELECT s.id, s.name, s.roll_number, sec.section_name, e.enrollment_date
           FROM enrollments e
           JOIN students s ON s.id = e.student_id
           JOIN sections sec ON sec.id = s.section_id
           WHERE e.course_id = %s
           ORDER BY s.roll_number""",
        (course_id,),
    )


def is_enrolled(course_id, student_id):
    """True when the student is enrolled in the course."""
    row = db.fetch_one(
        "SELECT 1 AS ok FROM enrollments WHERE course_id = %s AND student_id = %s",
        (course_id, student_id),
    )
    return row is not None


def enroll(course_id, student_id, enrollment_date):
    """Enroll a student in a course (friendly 400 on a duplicate)."""
    # uq_enrollment is the last line of defense in the schema, but a raw
    # IntegrityError would surface as a 500 — the app should say it in
    # English first. (A double-click on the Enroll button hits exactly this.)
    if is_enrolled(course_id, student_id):
        raise ValueError("That student is already enrolled in this course.")
    db.execute(
        "INSERT INTO enrollments (student_id, course_id, enrollment_date) VALUES (%s, %s, %s)",
        (student_id, course_id, enrollment_date),
    )


def unenroll(course_id, student_id):
    """Remove a student from a course (their marks/attendance for it cascade)."""
    db.execute(
        "DELETE FROM enrollments WHERE course_id = %s AND student_id = %s",
        (course_id, student_id),
    )


def enrollable_students(course_id):
    """Students in the course's section who are not yet enrolled in it."""
    # Section-scoped on purpose (OVERVIEW): a course belongs to one section,
    # so its dropdown lists only that section's students — NOT IN keeps
    # already-enrolled ones out of the re-enroll list.
    course = get(course_id)
    if course is None:
        return []
    return db.fetch_all(
        """SELECT s.id, s.name, s.roll_number
           FROM students s
           WHERE s.section_id = %s
             AND s.id NOT IN (
                 SELECT student_id FROM enrollments WHERE course_id = %s)
           ORDER BY s.roll_number""",
        (course["section_id"], course_id),
    )
