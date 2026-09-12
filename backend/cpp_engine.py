"""Bridge to the C++ compute engine (sms_engine).

Python collects raw data from MySQL, feeds it to the compiled binary as
tab-separated text on stdin, and parses the engine's stdout (see
cpp_module/README.md for the exact wire format). All three confirmed
computations live in the C++ binary:
  - grades:     final % = 50% assignments + 50% exams, Pass >= 40
  - attendance: per-course %, eligible at >= 75%
  - rank:       rank students within a section by final %
"""
import subprocess
from pathlib import Path

from backend import config


class EngineError(RuntimeError):
    """Raised when the C++ engine is missing or fails."""


def _run(mode, lines):
    """Run the engine in `mode` with the given input lines; return stdout lines."""
    binary = Path(config.CPP_ENGINE_PATH)
    if not binary.exists():
        raise EngineError(
            "C++ engine not found. Build it first with: python scripts/build_cpp.py"
        )
    payload = ("\n".join(lines) + "\n") if lines else ""
    result = subprocess.run(
        [str(binary), mode],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise EngineError(f"Engine '{mode}' failed: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def _clean(text):
    """Names must not contain tabs or newlines (TSV-safe)."""
    return str(text).replace("\t", " ").replace("\n", " ").strip()


# ---------- grades ----------

def compute_grades(rows):
    """rows: [{student_id, name, roll_number, assign_sum, assign_n, exam_sum, exam_n}]
    Returns the same rows plus assign_pct, exam_pct, final_pct, result ('Pass'/'Fail')."""
    stdin_lines = [
        "\t".join(str(x) for x in (
            r["student_id"], _clean(r["name"]), _clean(r["roll_number"]),
            r["assign_sum"], r["assign_n"], r["exam_sum"], r["exam_n"],
        ))
        for r in rows
    ]
    by_id = {r["student_id"]: r for r in rows}
    for line in _run("grades", stdin_lines):
        sid, assign_pct, exam_pct, final_pct, outcome = line.split("\t")
        row = by_id[int(sid)]
        row["assign_pct"] = round(float(assign_pct), 2)
        row["exam_pct"] = round(float(exam_pct), 2)
        row["final_pct"] = round(float(final_pct), 2)
        row["result"] = "Pass" if outcome == "PASS" else "Fail"
    return rows


# ---------- attendance ----------

def compute_attendance(session_count, rows):
    """rows: [{student_id, name, roll_number, present}] for ONE course.
    Returns the rows plus pct and eligible (True/False)."""
    stdin_lines = [str(session_count)]
    stdin_lines += [
        "\t".join(str(x) for x in (
            r["student_id"], _clean(r["name"]), _clean(r["roll_number"]), r["present"] or 0,
        ))
        for r in rows
    ]
    by_id = {r["student_id"]: r for r in rows}
    for line in _run("attendance", stdin_lines):
        sid, present, sessions, pct, eligible = line.split("\t")
        row = by_id[int(sid)]
        row["present"] = int(present)
        row["sessions"] = int(sessions)
        row["pct"] = round(float(pct), 2)
        row["eligible"] = eligible == "ELIGIBLE"
    return rows


# ---------- rank ----------

def compute_rank(rows):
    """rows like compute_grades' input (section-wide overall marks).
    Returns rows sorted by rank with a 'rank' key added."""
    stdin_lines = [
        "\t".join(str(x) for x in (
            r["student_id"], _clean(r["name"]), _clean(r["roll_number"]),
            r["assign_sum"], r["assign_n"], r["exam_sum"], r["exam_n"],
        ))
        for r in rows
    ]
    by_id = {r["student_id"]: r for r in rows}
    for line in _run("rank", stdin_lines):
        rank, sid, final_pct = line.split("\t")
        row = by_id[int(sid)]
        row["rank"] = int(rank)
        row["final_pct"] = round(float(final_pct), 2)
    return sorted(by_id.values(), key=lambda r: r["rank"])
