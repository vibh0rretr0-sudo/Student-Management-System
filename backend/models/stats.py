"""Aggregated numbers for the dashboard (summary cards + CSS-only charts)."""
from backend.models import db


def dashboard_stats(professor_id):
    """All numbers shown on the dashboard, in one place."""
    return {
        "cards": _cards(professor_id),
        "grade_bands": _grade_distribution(professor_id),
        "attendance_by_course": _attendance_by_course(professor_id),
    }


def _cards(professor_id):
    total_students = db.fetch_one("SELECT COUNT(*) AS n FROM students")["n"]
    my_courses = db.fetch_one(
        "SELECT COUNT(*) AS n FROM courses WHERE professor_id = %s", (professor_id,)
    )["n"]
    my_students = db.fetch_one(
        """SELECT COUNT(DISTINCT e.student_id) AS n
           FROM enrollments e JOIN courses c ON c.id = e.course_id
           WHERE c.professor_id = %s""",
        (professor_id,),
    )["n"]
    attendance = db.fetch_one(
        """SELECT AVG(a.status = 'present') AS rate
           FROM attendance a JOIN courses c ON c.id = a.course_id
           WHERE c.professor_id = %s""",
        (professor_id,),
    )["rate"]
    grades = db.fetch_one(
        """SELECT AVG(g.percentage) AS avg_pct,
                  SUM(g.computed_grade = 'Pass') / NULLIF(COUNT(*), 0) AS pass_rate
           FROM grades g JOIN courses c ON c.id = g.course_id
           WHERE c.professor_id = %s""",
        (professor_id,),
    )
    return {
        "total_students": total_students,
        "my_courses": my_courses,
        "my_students": my_students,
        "avg_attendance": round(float(attendance) * 100, 1) if attendance is not None else None,
        "avg_grade": round(float(grades["avg_pct"]), 1) if grades["avg_pct"] is not None else None,
        "pass_rate": round(float(grades["pass_rate"]) * 100, 1) if grades["pass_rate"] is not None else None,
    }


def _grade_distribution(professor_id):
    """Count of stored (C++-computed) grades in each percentage band."""
    bands = [
        ("90-100% (O)", 90, 100),
        ("75-89% (A)", 75, 89.99),
        ("60-74% (B)", 60, 74.99),
        ("40-59% (C)", 40, 59.99),
        ("Below 40% (F)", 0, 39.99),
    ]
    out = []
    for label, low, high in bands:
        n = db.fetch_one(
            """SELECT COUNT(*) AS n
               FROM grades g JOIN courses c ON c.id = g.course_id
               WHERE c.professor_id = %s AND g.percentage BETWEEN %s AND %s""",
            (professor_id, low, high),
        )["n"]
        out.append({"label": label, "count": n})
    return out


def _attendance_by_course(professor_id):
    """Attendance rate for each of the professor's courses (for the bar chart)."""
    rows = db.fetch_all(
        """SELECT c.id, c.course_code, c.course_name,
                  AVG(a.status = 'present') AS rate
           FROM courses c
           LEFT JOIN attendance a ON a.course_id = c.id
           WHERE c.professor_id = %s
           GROUP BY c.id
           ORDER BY c.course_code""",
        (professor_id,),
    )
    return [
        {
            "label": f"{r['course_code']} — {r['course_name']}",
            "rate": round(float(r["rate"]) * 100, 1) if r["rate"] is not None else None,
        }
        for r in rows
    ]
