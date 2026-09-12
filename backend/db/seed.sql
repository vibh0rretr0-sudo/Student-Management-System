-- ============================================================
-- Student Management System — seed.sql
-- Demo data for development/demos. Applied by scripts/setup_db.py
-- after schema.sql. Professor demo login: vibhor / prof123
--
-- Demo story baked into the data:
--  * Course 1 (CS101, SN1) has full data: 2 assignments + midterm marks
--    + 8 attendance sessions — enough to demo all three C++ modes.
--  * Student 4 (Ishita) sits at 25% attendance  -> Not Eligible.
--  * Student 5 (Kunal) sits at exactly 75%      -> Eligible (boundary).
--  * Professor 2 (sharma) owns Course 5 to demo per-professor scoping.
-- ============================================================

USE sms;

-- ---------- Batches & sections ----------
INSERT INTO batches (id, batch_name) VALUES (1, 'SN');
INSERT INTO sections (id, batch_id, section_name) VALUES
    (1, 1, 'SN1'),
    (2, 1, 'SN2');

-- ---------- Professors ----------
-- Password for both accounts: prof123  (PBKDF2-SHA256, 390000 iterations)
INSERT INTO professors (id, username, password_hash, name) VALUES
    (1, 'vibhor', 'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Vibhor Mathur'),
    (2, 'sharma', 'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Anita Sharma');

-- ---------- Students (shared pool, roll numbers unique per section) ----------
INSERT INTO students (id, name, roll_number, date_of_birth, contact, enrollment_date, section_id) VALUES
    (1, 'Aarav Sharma',  '01', '2007-08-14', '9876500011', '2026-07-01', 1),
    (2, 'Diya Patel',    '02', '2007-11-02', '9876500012', '2026-07-01', 1),
    (3, 'Rohan Gupta',   '03', '2008-01-27', '9876500013', '2026-07-01', 1),
    (4, 'Ishita Verma',  '04', '2007-05-19', '9876500014', '2026-07-01', 1),
    (5, 'Kunal Singh',   '05', '2007-09-30', '9876500015', '2026-07-01', 1),
    (6, 'Ananya Mehta',  '01', '2007-12-11', '9876500016', '2026-07-01', 2),
    (7, 'Vivaan Jain',   '02', '2008-03-08', '9876500017', '2026-07-01', 2),
    (8, 'Saanvi Kapoor', '03', '2007-07-23', '9876500018', '2026-07-01', 2);

-- ---------- Courses (term is set per course) ----------
INSERT INTO courses (id, course_name, course_code, professor_id, section_id, term, day_of_week, start_time, end_time) VALUES
    (1, 'Programming Fundamentals', 'CS101', 1, 1, 'Sem 1', 1, '09:00:00', '10:00:00'),
    (2, 'Data Structures',          'CS102', 1, 2, 'Sem 1', 3, '11:00:00', '12:00:00'),
    (3, 'Database Management',      'CS103', 1, 1, 'Sem 1', 4, '14:00:00', '15:00:00'),
    (4, 'Engineering Mathematics',  'MA101', 1, 2, 'Sem 1', 2, '08:00:00', '09:00:00'),
    (5, 'Web Technologies',         'CS104', 2, 1, 'Sem 1', 5, '10:00:00', '11:00:00');

-- ---------- Enrollments ----------
INSERT INTO enrollments (student_id, course_id, enrollment_date) VALUES
    (1, 1, '2026-07-01'), (2, 1, '2026-07-01'), (3, 1, '2026-07-01'), (4, 1, '2026-07-01'), (5, 1, '2026-07-01'),
    (6, 2, '2026-07-01'), (7, 2, '2026-07-01'), (8, 2, '2026-07-01'),
    (1, 3, '2026-07-01'), (2, 3, '2026-07-01'), (3, 3, '2026-07-01'), (4, 3, '2026-07-01'), (5, 3, '2026-07-01'),
    (6, 4, '2026-07-01'), (7, 4, '2026-07-01'), (8, 4, '2026-07-01'),
    (1, 5, '2026-07-01'), (2, 5, '2026-07-01'), (3, 5, '2026-07-01'), (4, 5, '2026-07-01'), (5, 5, '2026-07-01');

-- ---------- Assignments ----------
INSERT INTO assignments (id, course_id, title, description, max_marks, due_date) VALUES
    (1, 1, 'Assignment 1: C Basics',          'Variables, operators, simple I/O programs.', 20, '2026-08-10'),
    (2, 1, 'Assignment 2: Loops & Functions', 'Control flow and user-defined functions.',   20, '2026-09-05'),
    (3, 2, 'Assignment 1: Arrays & Strings',  'Array manipulation exercises.',              25, '2026-08-20'),
    (4, 3, 'Assignment 1: ER Modeling',       'Draw ER diagrams for given case studies.',   20, '2026-08-25'),
    (5, 4, 'Assignment 1: Set Theory',        'Problems on sets and relations.',            15, '2026-08-15');

-- ---------- Exam marks per assignment ----------
INSERT INTO submissions (id, assignment_id, student_id, marks_obtained, submitted_on) VALUES
    ( 1, 1, 1, 18, '2026-08-08'), ( 2, 1, 2, 15, '2026-08-09'),
    ( 3, 1, 3, 12, '2026-08-10'), ( 4, 1, 4,  8, '2026-08-10'),
    ( 5, 1, 5, 14, '2026-08-09'),
    ( 6, 2, 1, 17, '2026-09-03'), ( 7, 2, 2, 16, '2026-09-04'),
    ( 8, 2, 3, 13, '2026-09-05'), ( 9, 2, 4,  9, '2026-09-05'),
    (10, 2, 5, 15, '2026-09-04'),
    (11, 3, 6, 21, '2026-08-18'), (12, 3, 7, 17, '2026-08-20'),
    (13, 3, 8, 23, '2026-08-19'),
    (14, 4, 1, 16, '2026-08-24'), (15, 4, 2, 18, '2026-08-25'),
    (16, 5, 6, 12, '2026-08-14'), (17, 5, 7,  9, '2026-08-15');

-- ---------- Exams ----------
INSERT INTO exams (id, course_id, title, max_marks, exam_date) VALUES
    (1, 1, 'Midterm',  50, '2026-09-01'),
    (2, 1, 'Endterm',  50, '2026-11-20'),
    (3, 2, 'Midterm',  30, '2026-09-10'),
    (4, 3, 'Midterm',  50, '2026-09-12'),
    (5, 4, 'Midterm',  40, '2026-09-08');

-- ---------- Exam marks ----------
INSERT INTO exam_marks (exam_id, student_id, marks_obtained) VALUES
    (1, 1, 42), (1, 2, 35), (1, 3, 28), (1, 4, 18), (1, 5, 31),
    (3, 6, 24), (3, 7, 19), (3, 8, 26),
    (4, 1, 38), (4, 2, 41),
    (5, 6, 33), (5, 7, 21);

-- ---------- Attendance (Course 1: 8 Monday sessions) ----------
-- Demo story: student 4 = 25% (Not Eligible), student 5 = 75% (boundary Eligible).
INSERT INTO attendance (student_id, course_id, date, status) VALUES
    (1, 1, '2026-07-27', 'present'), (2, 1, '2026-07-27', 'present'), (3, 1, '2026-07-27', 'present'), (4, 1, '2026-07-27', 'present'), (5, 1, '2026-07-27', 'present'),
    (1, 1, '2026-08-03', 'present'), (2, 1, '2026-08-03', 'present'), (3, 1, '2026-08-03', 'present'), (4, 1, '2026-08-03', 'absent'),  (5, 1, '2026-08-03', 'present'),
    (1, 1, '2026-08-10', 'present'), (2, 1, '2026-08-10', 'present'), (3, 1, '2026-08-10', 'absent'),  (4, 1, '2026-08-10', 'absent'),  (5, 1, '2026-08-10', 'present'),
    (1, 1, '2026-08-17', 'present'), (2, 1, '2026-08-17', 'present'), (3, 1, '2026-08-17', 'present'), (4, 1, '2026-08-17', 'absent'),  (5, 1, '2026-08-17', 'present'),
    (1, 1, '2026-08-24', 'present'), (2, 1, '2026-08-24', 'present'), (3, 1, '2026-08-24', 'present'), (4, 1, '2026-08-24', 'present'), (5, 1, '2026-08-24', 'absent'),
    (1, 1, '2026-08-31', 'present'), (2, 1, '2026-08-31', 'present'), (3, 1, '2026-08-31', 'present'), (4, 1, '2026-08-31', 'absent'),  (5, 1, '2026-08-31', 'present'),
    (1, 1, '2026-09-07', 'present'), (2, 1, '2026-09-07', 'absent'),  (3, 1, '2026-09-07', 'present'), (4, 1, '2026-09-07', 'absent'),  (5, 1, '2026-09-07', 'present'),
    (1, 1, '2026-09-14', 'present'), (2, 1, '2026-09-14', 'present'), (3, 1, '2026-09-14', 'present'), (4, 1, '2026-09-14', 'absent'),  (5, 1, '2026-09-14', 'absent');

-- ---------- Attendance (Course 2: 3 sessions, SN2 students) ----------
INSERT INTO attendance (student_id, course_id, date, status) VALUES
    (6, 2, '2026-08-05', 'present'), (7, 2, '2026-08-05', 'present'), (8, 2, '2026-08-05', 'present'),
    (6, 2, '2026-08-12', 'present'), (7, 2, '2026-08-12', 'absent'),  (8, 2, '2026-08-12', 'present'),
    (6, 2, '2026-08-19', 'absent'),  (7, 2, '2026-08-19', 'present'), (8, 2, '2026-08-19', 'present');
