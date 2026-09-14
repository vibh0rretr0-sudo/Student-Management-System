"""Assessments (assignments + exams), marks, and the aggregates fed to the
C++ engine.

Grading scheme (confirmed): final % = 50% assignment average + 50% exam
average; missing marks count as 0; Pass at >= 40%.

Two modeling decisions shape this module:

1. ONE table for both assessment kinds. Assignments and exams share the
   exact same shape (owning course, title, max marks, a date); only the
   label and the date's meaning differ. `assessments.kind` carries that
   distinction, so every constraint, index, and query exists once instead
   of twice. The kind-aware getters double as type checks: requesting an
   exam id through get_assignment() simply finds nothing.

2. Every mark is normalized to a PERCENTAGE (marks / max_marks * 100)
   the moment it's aggregated. An 18/20 assignment and a 70/100 exam
   become 90 and 70 — directly blendable at 50/50 no matter what each
   assessment's max was. The engine receives (sum of percentages, count)
   pairs and does the rest.
"""
from backend.models import db


# ---------- Assignments (kind = 'assignment') ----------

def list_assignments(course_id):
    """Assignments of one course, due-date order."""
    return db.fetch_all(
        """SELECT id, course_id, title, description, max_marks, assess_date AS due_date
           FROM assessments
           WHERE course_id = %s AND kind = 'assignment'
           ORDER BY assess_date, id""",
        (course_id,),
    )


def get_assignment(assignment_id):
    """One assignment by id, or None (an exam id returns None too)."""
    return db.fetch_one(
        """SELECT id, course_id, title, description, max_marks, assess_date AS due_date
           FROM assessments WHERE id = %s AND kind = 'assignment'""",
        (assignment_id,),
    )


def create_assignment(course_id, title, description, max_marks, due_date):
    """Insert an assignment; returns its new id."""
    return db.execute(
        """INSERT INTO assessments (kind, course_id, title, description, max_marks, assess_date)
           VALUES ('assignment', %s, %s, %s, %s, %s)""",
        (course_id, title, description, max_marks, due_date),
    )


def delete_assignment(assignment_id):
    """Delete an assignment (its marks cascade)."""
    db.execute("DELETE FROM assessments WHERE id = %s", (assignment_id,))


# ---------- Exams (kind = 'exam') ----------

def list_exams(course_id):
    """Exams of one course, date order."""
    return db.fetch_all(
        """SELECT id, course_id, title, max_marks, assess_date AS exam_date
           FROM assessments
           WHERE course_id = %s AND kind = 'exam'
           ORDER BY assess_date, id""",
        (course_id,),
    )


def get_exam(exam_id):
    """One exam by id, or None (an assignment id returns None too)."""
    return db.fetch_one(
        """SELECT id, course_id, title, max_marks, assess_date AS exam_date
           FROM assessments WHERE id = %s AND kind = 'exam'""",
        (exam_id,),
    )


def create_exam(course_id, title, max_marks, exam_date):
    """Insert an exam; returns its new id."""
    return db.execute(
        """INSERT INTO assessments (kind, course_id, title, description, max_marks, assess_date)
           VALUES ('exam', %s, %s, NULL, %s, %s)""",
        (course_id, title, max_marks, exam_date),
    )


def delete_exam(exam_id):
    """Delete an exam (its marks cascade)."""
    db.execute("DELETE FROM assessments WHERE id = %s", (exam_id,))


# ---------- Marks (upserts; marks-vs-max validated in the route layer) ----------
# MySQL 8.0.19+ `AS new` row-alias upserts — re-entering marks overwrites
# cleanly instead of erroring on UNIQUE(assessment, student).

def get_marks(assessment_id):
    """{student_id: {'marks': ..., 'submitted_on': ...}} for one assessment."""
    rows = db.fetch_all(
        "SELECT student_id, marks_obtained, submitted_on FROM marks WHERE assessment_id = %s",
        (assessment_id,),
    )
    return {r["student_id"]: {"marks": r["marks_obtained"], "submitted_on": r["submitted_on"]} for r in rows}


def set_mark(assessment_id, student_id, marks, submitted_on=None):
    """Upsert one student's marks (and submitted-on) for an assessment."""
    db.execute(
        """INSERT INTO marks (assessment_id, student_id, marks_obtained, submitted_on)
           VALUES (%s, %s, %s, %s)
           AS new
           ON DUPLICATE KEY UPDATE marks_obtained = new.marks_obtained,
                                   submitted_on = new.submitted_on""",
        (assessment_id, student_id, marks, submitted_on),
    )


# ---------- Computed grades (C++ engine output) ----------

def upsert_grade(student_id, course_id, grade, percentage):
    """Store/refresh one computed grade row (materialized engine output).

    The uq_grade key is (student_id, course_id): one live grade per
    enrollment. The course's term lives on the course — recomputation
    after a term change just overwrites this row.
    """
    db.execute(
        """INSERT INTO grades (student_id, course_id, computed_grade, percentage)
           VALUES (%s, %s, %s, %s)
           AS new
           ON DUPLICATE KEY UPDATE computed_grade = new.computed_grade,
                percentage = new.percentage, computed_at = CURRENT_TIMESTAMP""",
        (student_id, course_id, grade, percentage),
    )


# ---------- Aggregates for the C++ engine ----------
# Per student: sum of per-assessment percentages (marks/max*100, missing = 0)
# and the number of assessments. The engine turns these into the final %.
#
# "Conducted" rule: an assessment enters the denominator only once at
# least ONE student has marks recorded for it course-wide (an unheld
# exam or unsubmitted assignment must not drag everyone's average
# down). A specific student's missing marks for a CONDUCTED assessment
# still count as 0 — that part is the confirmed "missing = 0" rule.

def course_grade_inputs(course_id):
    """Enrolled students of one course with assignment/exam percentage sums."""
    # The shape of this query (viva answer): the CROSS JOIN supplies the
    # COURSE-WIDE denominators (conducted counts — same for every
    # student), the LEFT JOIN supplies each student's SUM of percentages
    # (COALESCE to 0 when they have no marks). Splitting numerator-side
    # from denominator-side is what keeps 'missing = 0' and the
    # 'conducted' rule from entangling. One marks/assessments pass fills
    # both the assignment and exam columns — the CASE WHEN kind decides
    # which side each percentage lands in.
    return db.fetch_all(
        """
        SELECT s.id AS student_id, s.name, s.roll_number,
               COALESCE(g.assign_sum, 0) AS assign_sum,
               n.assign_n AS assign_n,
               COALESCE(g.exam_sum, 0) AS exam_sum,
               n.exam_n AS exam_n
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        CROSS JOIN (
            SELECT SUM(a.kind = 'assignment') AS assign_n,
                   SUM(a.kind = 'exam')       AS exam_n
            FROM assessments a
            WHERE a.course_id = %s
              AND EXISTS (SELECT 1 FROM marks m WHERE m.assessment_id = a.id)
        ) n
        LEFT JOIN (
            SELECT m.student_id AS sid,
                   SUM(CASE WHEN a.kind = 'assignment'
                            THEN m.marks_obtained / a.max_marks * 100 END) AS assign_sum,
                   SUM(CASE WHEN a.kind = 'exam'
                            THEN m.marks_obtained / a.max_marks * 100 END) AS exam_sum
            FROM marks m
            JOIN assessments a ON a.id = m.assessment_id
            WHERE a.course_id = %s
            GROUP BY m.student_id
        ) g ON g.sid = e.student_id
        WHERE e.course_id = %s
        ORDER BY s.roll_number
        """,
        (course_id, course_id, course_id),
    )


def section_overall_inputs(section_id):
    """Every student of a section with overall assignment/exam percentage sums
    across ALL their enrolled courses (used by the C++ rank mode)."""
    # Same numerator/denominator split as course_grade_inputs, but driven
    # from the section roster and filtered per kind with CASE (the rank
    # mode needs the two components kept separate for its 50/50 blend).
    return db.fetch_all(
        """
        SELECT s.id AS student_id, s.name, s.roll_number,
               COALESCE(g.assign_sum, 0) AS assign_sum,
               COALESCE(g.assign_n, 0)   AS assign_n,
               COALESCE(g.exam_sum, 0)   AS exam_sum,
               COALESCE(g.exam_n, 0)     AS exam_n
        FROM students s
        LEFT JOIN (
            SELECT e2.student_id AS sid,
                   SUM(CASE WHEN a.kind = 'assignment'
                            THEN COALESCE(m.marks_obtained / a.max_marks * 100, 0)
                            ELSE 0 END) AS assign_sum,
                   SUM(CASE WHEN a.kind = 'exam'
                            THEN COALESCE(m.marks_obtained / a.max_marks * 100, 0)
                            ELSE 0 END) AS exam_sum,
                   COUNT(DISTINCT CASE WHEN a.kind = 'assignment' AND con.n > 0
                                       THEN a.id END) AS assign_n,
                   COUNT(DISTINCT CASE WHEN a.kind = 'exam' AND con.n > 0
                                       THEN a.id END) AS exam_n
            FROM enrollments e2
            JOIN assessments a ON a.course_id = e2.course_id
            LEFT JOIN marks m ON m.assessment_id = a.id AND m.student_id = e2.student_id
            LEFT JOIN (SELECT assessment_id, COUNT(*) AS n
                       FROM marks GROUP BY assessment_id) con
                   ON con.assessment_id = a.id
            GROUP BY e2.student_id
        ) g ON g.sid = s.id
        WHERE s.section_id = %s
        ORDER BY s.roll_number
        """,
        (section_id,),
    )
