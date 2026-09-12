"""Assignments, exams, marks, and the aggregates fed to the C++ engine.

Grading scheme (confirmed): final % = 50% assignment average + 50% exam
average; missing marks count as 0; Pass at >= 40%.
"""
from backend.models import db


# ---------- Assignments ----------

def list_assignments(course_id):
    return db.fetch_all(
        """SELECT id, course_id, title, description, max_marks, due_date
           FROM assignments WHERE course_id = %s ORDER BY due_date, id""",
        (course_id,),
    )


def get_assignment(assignment_id):
    return db.fetch_one(
        "SELECT id, course_id, title, description, max_marks, due_date FROM assignments WHERE id = %s",
        (assignment_id,),
    )


def create_assignment(course_id, title, description, max_marks, due_date):
    return db.execute(
        """INSERT INTO assignments (course_id, title, description, max_marks, due_date)
           VALUES (%s, %s, %s, %s, %s)""",
        (course_id, title, description, max_marks, due_date),
    )


def update_assignment(assignment_id, title, description, max_marks, due_date):
    db.execute(
        """UPDATE assignments
           SET title = %s, description = %s, max_marks = %s, due_date = %s
           WHERE id = %s""",
        (title, description, max_marks, due_date, assignment_id),
    )


def delete_assignment(assignment_id):
    db.execute("DELETE FROM assignments WHERE id = %s", (assignment_id,))


# ---------- Exams ----------

def list_exams(course_id):
    return db.fetch_all(
        "SELECT id, course_id, title, max_marks, exam_date FROM exams WHERE course_id = %s ORDER BY exam_date, id",
        (course_id,),
    )


def get_exam(exam_id):
    return db.fetch_one(
        "SELECT id, course_id, title, max_marks, exam_date FROM exams WHERE id = %s",
        (exam_id,),
    )


def create_exam(course_id, title, max_marks, exam_date):
    return db.execute(
        "INSERT INTO exams (course_id, title, max_marks, exam_date) VALUES (%s, %s, %s, %s)",
        (course_id, title, max_marks, exam_date),
    )


def delete_exam(exam_id):
    db.execute("DELETE FROM exams WHERE id = %s", (exam_id,))


# ---------- Marks (upserts; marks-vs-max validated in the route layer) ----------

def get_submissions(assignment_id):
    """{student_id: {'marks': ..., 'submitted_on': ...}} for one assignment."""
    rows = db.fetch_all(
        "SELECT student_id, marks_obtained, submitted_on FROM submissions WHERE assignment_id = %s",
        (assignment_id,),
    )
    return {r["student_id"]: {"marks": r["marks_obtained"], "submitted_on": r["submitted_on"]} for r in rows}


def set_submission(assignment_id, student_id, marks, submitted_on):
    db.execute(
        """INSERT INTO submissions (assignment_id, student_id, marks_obtained, submitted_on)
           VALUES (%s, %s, %s, %s)
           AS new
           ON DUPLICATE KEY UPDATE marks_obtained = new.marks_obtained, submitted_on = new.submitted_on""",
        (assignment_id, student_id, marks, submitted_on),
    )


def get_exam_marks(exam_id):
    """{student_id: marks} for one exam."""
    rows = db.fetch_all(
        "SELECT student_id, marks_obtained FROM exam_marks WHERE exam_id = %s",
        (exam_id,),
    )
    return {r["student_id"]: r["marks_obtained"] for r in rows}


def set_exam_mark(exam_id, student_id, marks):
    db.execute(
        """INSERT INTO exam_marks (exam_id, student_id, marks_obtained)
           VALUES (%s, %s, %s)
           AS new
           ON DUPLICATE KEY UPDATE marks_obtained = new.marks_obtained""",
        (exam_id, student_id, marks),
    )


# ---------- Computed grades (C++ engine output) ----------

def upsert_grade(student_id, course_id, grade, percentage, term):
    """Store/refresh one computed grade row (materialized engine output)."""
    db.execute(
        """INSERT INTO grades (student_id, course_id, computed_grade, percentage, term)
           VALUES (%s, %s, %s, %s, %s)
           AS new
           ON DUPLICATE KEY UPDATE computed_grade = new.computed_grade,
                percentage = new.percentage, term = new.term, computed_at = CURRENT_TIMESTAMP""",
        (student_id, course_id, grade, percentage, term),
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
    return db.fetch_all(
        """
        SELECT s.id AS student_id, s.name, s.roll_number,
               COALESCE(ag.assign_sum, 0) AS assign_sum,
               an.assign_n AS assign_n,
               COALESCE(ex.exam_sum, 0) AS exam_sum,
               xn.exam_n AS exam_n
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        CROSS JOIN (SELECT COUNT(*) AS assign_n FROM assignments a
                    WHERE a.course_id = %s
                      AND EXISTS (SELECT 1 FROM submissions sub WHERE sub.assignment_id = a.id)) an
        CROSS JOIN (SELECT COUNT(*) AS exam_n FROM exams x
                    WHERE x.course_id = %s
                      AND EXISTS (SELECT 1 FROM exam_marks em WHERE em.exam_id = x.id)) xn
        LEFT JOIN (
            SELECT sub.student_id AS sid, a.course_id AS cid,
                   SUM(sub.marks_obtained / a.max_marks * 100) AS assign_sum
            FROM submissions sub
            JOIN assignments a ON a.id = sub.assignment_id
            GROUP BY sub.student_id, a.course_id
        ) ag ON ag.sid = e.student_id AND ag.cid = e.course_id
        LEFT JOIN (
            SELECT em.student_id AS sid, x.course_id AS cid,
                   SUM(em.marks_obtained / x.max_marks * 100) AS exam_sum
            FROM exam_marks em
            JOIN exams x ON x.id = em.exam_id
            GROUP BY em.student_id, x.course_id
        ) ex ON ex.sid = e.student_id AND ex.cid = e.course_id
        WHERE e.course_id = %s
        ORDER BY s.roll_number
        """,
        (course_id, course_id, course_id),
    )


def section_overall_inputs(section_id):
    """Every student of a section with overall assignment/exam percentage sums
    across ALL their enrolled courses (used by the C++ rank mode)."""
    return db.fetch_all(
        """
        SELECT s.id AS student_id, s.name, s.roll_number,
               COALESCE(ag.assign_sum, 0) AS assign_sum,
               COALESCE(ag.assign_n, 0)   AS assign_n,
               COALESCE(ex.exam_sum, 0)   AS exam_sum,
               COALESCE(ex.exam_n, 0)     AS exam_n
        FROM students s
        LEFT JOIN (
            SELECT e2.student_id AS sid,
                   SUM(CASE WHEN sub.student_id IS NOT NULL
                            THEN sub.marks_obtained / a.max_marks * 100 ELSE 0 END) AS assign_sum,
                   COUNT(DISTINCT CASE WHEN con.n > 0 THEN a.id END) AS assign_n
            FROM enrollments e2
            JOIN assignments a ON a.course_id = e2.course_id
            LEFT JOIN submissions sub ON sub.assignment_id = a.id AND sub.student_id = e2.student_id
            LEFT JOIN (SELECT assignment_id, COUNT(*) AS n FROM submissions GROUP BY assignment_id) con
                   ON con.assignment_id = a.id
            GROUP BY e2.student_id
        ) ag ON ag.sid = s.id
        LEFT JOIN (
            SELECT e3.student_id AS sid,
                   SUM(CASE WHEN em.student_id IS NOT NULL
                            THEN em.marks_obtained / x.max_marks * 100 ELSE 0 END) AS exam_sum,
                   COUNT(DISTINCT CASE WHEN conx.n > 0 THEN x.id END) AS exam_n
            FROM enrollments e3
            JOIN exams x ON x.course_id = e3.course_id
            LEFT JOIN exam_marks em ON em.exam_id = x.id AND em.student_id = e3.student_id
            LEFT JOIN (SELECT exam_id, COUNT(*) AS n FROM exam_marks GROUP BY exam_id) conx
                   ON conx.exam_id = x.id
            GROUP BY e3.student_id
        ) ex ON ex.sid = s.id
        WHERE s.section_id = %s
        ORDER BY s.roll_number
        """,
        (section_id,),
    )
