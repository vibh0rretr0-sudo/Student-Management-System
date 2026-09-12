-- ============================================================
-- Student Management System — schema.sql
-- Single source of truth for the database structure (Rules.md §5).
-- Re-apply with: python scripts/setup_db.py  (it offers drop & recreate)
--
-- Design notes:
--  * All tables InnoDB + utf8mb4, snake_case plural names.
--  * 3NF: no repeating groups, every non-key column depends on the key.
--  * `grades` intentionally stores C++-computed results (percentage,
--    Pass/Fail) — a materialized summary, not raw data; raw data stays
--    in submissions/exam_marks/attendance.
--  * Marks-vs-max validation (marks_obtained <= max_marks) is enforced
--    in the application layer; a CHECK cannot reference another table.
-- ============================================================

CREATE DATABASE IF NOT EXISTS sms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sms;

-- ---------- People ----------

CREATE TABLE professors (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,          -- format: pbkdf2_sha256$iter$salthex$hashhex
    name          VARCHAR(100) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

-- ---------- Batch / Section hierarchy (SN -> SN1, SN2) ----------

CREATE TABLE batches (
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    batch_name VARCHAR(50) NOT NULL UNIQUE      -- e.g. 'SN'
) ENGINE = InnoDB;

CREATE TABLE sections (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    batch_id     INT UNSIGNED NOT NULL,
    section_name VARCHAR(50) NOT NULL,           -- e.g. 'SN1'
    UNIQUE KEY uq_section (batch_id, section_name),
    FOREIGN KEY (batch_id) REFERENCES batches (id)
) ENGINE = InnoDB;

-- ---------- Students (shared pool) ----------

CREATE TABLE students (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    roll_number     VARCHAR(20)  NOT NULL,
    date_of_birth   DATE NULL,
    contact         VARCHAR(20)  NULL,
    enrollment_date DATE         NOT NULL,
    section_id      INT UNSIGNED NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Roll numbers are unique per section (confirmed decision)
    UNIQUE KEY uq_roll_section (section_id, roll_number),
    INDEX idx_students_name (name),
    FOREIGN KEY (section_id) REFERENCES sections (id)
) ENGINE = InnoDB;

-- ---------- Courses ----------
-- A course = one professor + one section + one weekly time slot,
-- so parallel sections can run different labs in the same slot.

CREATE TABLE courses (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    course_name  VARCHAR(100) NOT NULL,
    course_code  VARCHAR(20)  NOT NULL,
    professor_id INT UNSIGNED NOT NULL,
    section_id   INT UNSIGNED NOT NULL,
    term         VARCHAR(20)  NOT NULL DEFAULT 'Sem 1',  -- term is set per course (confirmed)
    day_of_week  TINYINT UNSIGNED NOT NULL,               -- 1 = Monday ... 7 = Sunday
    start_time   TIME NOT NULL,
    end_time     TIME NOT NULL,
    -- Same code may be reused across different sections (e.g. a lab per section)
    UNIQUE KEY uq_course_section_code (section_id, course_code),
    CONSTRAINT chk_day CHECK (day_of_week BETWEEN 1 AND 7),
    CONSTRAINT chk_times CHECK (end_time > start_time),
    FOREIGN KEY (professor_id) REFERENCES professors (id),
    FOREIGN KEY (section_id) REFERENCES sections (id)
) ENGINE = InnoDB;

CREATE TABLE enrollments (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id      INT UNSIGNED NOT NULL,
    course_id       INT UNSIGNED NOT NULL,
    enrollment_date DATE NOT NULL,
    UNIQUE KEY uq_enrollment (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES courses (id)  ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------- Assessment: assignments ----------

CREATE TABLE assignments (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    course_id   INT UNSIGNED NOT NULL,
    title       VARCHAR(100) NOT NULL,
    description TEXT NULL,
    max_marks   DECIMAL(5, 2) NOT NULL,
    due_date    DATE NULL,
    CONSTRAINT chk_assign_max CHECK (max_marks > 0),
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE submissions (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    assignment_id  INT UNSIGNED NOT NULL,
    student_id     INT UNSIGNED NOT NULL,
    marks_obtained DECIMAL(5, 2) NOT NULL,
    submitted_on   DATE NULL,
    UNIQUE KEY uq_submission (assignment_id, student_id),
    FOREIGN KEY (assignment_id) REFERENCES assignments (id) ON DELETE CASCADE,
    FOREIGN KEY (student_id)    REFERENCES students (id)    ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------- Assessment: exams ----------
-- Architecture.md requires exam marks for the C++ grade computation,
-- so exams are first-class entities (confirmed decision).

CREATE TABLE exams (
    id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    course_id INT UNSIGNED NOT NULL,
    title     VARCHAR(100) NOT NULL,              -- e.g. 'Midterm', 'Endterm'
    max_marks DECIMAL(5, 2) NOT NULL,
    exam_date DATE NULL,
    CONSTRAINT chk_exam_max CHECK (max_marks > 0),
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE exam_marks (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    exam_id        INT UNSIGNED NOT NULL,
    student_id     INT UNSIGNED NOT NULL,
    marks_obtained DECIMAL(5, 2) NOT NULL,
    UNIQUE KEY uq_exam_mark (exam_id, student_id),
    FOREIGN KEY (exam_id)    REFERENCES exams (id)    ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------- Computed grades (output of the C++ engine) ----------
-- Grading scheme (confirmed): final % = 50% assignment avg + 50% exam avg,
-- Pass/Fail with a 40% pass mark.

CREATE TABLE grades (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id     INT UNSIGNED NOT NULL,
    course_id      INT UNSIGNED NOT NULL,
    computed_grade VARCHAR(10)   NOT NULL,          -- 'Pass' / 'Fail'
    percentage     DECIMAL(5, 2) NOT NULL,          -- final percentage 0-100
    term           VARCHAR(20)   NOT NULL,          -- inherited from the course
    computed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_grade (student_id, course_id, term),
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES courses (id)  ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------- Attendance ----------
-- Eligibility (confirmed): per course, hard 75% cutoff, computed by the C++ engine.

CREATE TABLE attendance (
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id INT UNSIGNED NOT NULL,
    course_id  INT UNSIGNED NOT NULL,
    date       DATE NOT NULL,
    status     ENUM ('present', 'absent') NOT NULL,
    UNIQUE KEY uq_attendance (student_id, course_id, date),
    INDEX idx_attendance_course_date (course_id, date),
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES courses (id)  ON DELETE CASCADE
) ENGINE = InnoDB;
