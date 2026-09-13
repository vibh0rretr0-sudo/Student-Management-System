"""Attendance marking and summaries.

Eligibility (confirmed) is computed by the C++ engine: per course, hard
75% cutoff. This module stores/retrieves records and prepares counts.

The storage shape is worth stating: one row per (student, course, date)
— enforced by uq_attendance in the schema — holding 'present' or
'absent'. Absences are stored, not inferred, which is why per-session
percentages and the eligibility rule stay trivially computable.
"""
from backend.models import db


def get_day(course_id, date):
    """Enrolled students with their status on a date (None = not marked yet)."""
    return db.fetch_all(
        """SELECT s.id AS student_id, s.name, s.roll_number, a.status
           FROM enrollments e
           JOIN students s ON s.id = e.student_id
           LEFT JOIN attendance a
                  ON a.student_id = s.id AND a.course_id = e.course_id AND a.date = %s
           WHERE e.course_id = %s
           ORDER BY s.roll_number""",
        # LEFT JOIN is the point: unmarked students still get a row
        # (status NULL -> the form shows an empty radio), so the marking
        # page always lists the full roster.
        (date, course_id),
    )


def mark_day(course_id, date, statuses):
    """Upsert attendance for one day. `statuses` = {student_id: 'present'|'absent'}."""
    # One connection + one commit for the whole day (not one per student):
    # either every mark of the session lands, or none do — re-marking a
    # session is idempotent because the upsert updates in place.
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            for student_id, status in statuses.items():
                cur.execute(
                    """INSERT INTO attendance (student_id, course_id, date, status)
                       VALUES (%s, %s, %s, %s)
                       AS new
                       ON DUPLICATE KEY UPDATE status = new.status""",
                # MySQL 8.0.19+ row-alias syntax: `AS new` lets UPDATE
                # reference the would-be-inserted values by name instead
                # of repeating VALUES(...) — cleaner and one less place
                # for a copy-paste bug.
                    (student_id, course_id, date, status),
                )
        conn.commit()
    finally:
        conn.close()


def session_count(course_id):
    """Number of distinct recorded sessions for a course."""
    row = db.fetch_one(
        "SELECT COUNT(DISTINCT date) AS n FROM attendance WHERE course_id = %s",
        (course_id,),
    )
    return row["n"] if row else 0


def course_attendance_counts(course_id):
    """Per-student present counts + total sessions — input for the C++ engine."""
    rows = db.fetch_all(
        """SELECT s.id AS student_id, s.name, s.roll_number,
                  SUM(a.status = 'present') AS present
           FROM enrollments e
           JOIN students s ON s.id = e.student_id
           LEFT JOIN attendance a ON a.student_id = s.id AND a.course_id = e.course_id
           WHERE e.course_id = %s
           GROUP BY s.id
           ORDER BY s.roll_number""",
        # SUM(condition) is MySQL's boolean arithmetic: TRUE=1/FALSE=0,
        # so this counts 'present' rows directly. Combined with the
        # session_count from the engine input, the C++ side never
        # touches SQL — it just gets (present, sessions) per student.
        (course_id,),
    )
    return {"session_count": session_count(course_id), "students": rows}


def dates(course_id):
    """Distinct recorded session dates, newest first."""
    return db.fetch_all(
        "SELECT DISTINCT date FROM attendance WHERE course_id = %s ORDER BY date DESC",
        (course_id,),
    )
