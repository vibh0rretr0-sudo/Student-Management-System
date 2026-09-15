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
--
-- Note: assignments and exams live in ONE `assessments` table (kind
-- column); ids 1-5 are assignments, 6-10 are exams. Their marks share
-- the single `marks` table.
-- ============================================================

USE sms;

-- ---------- Sections (batch is an attribute, not a table) ----------
INSERT INTO sections (id, batch_name, section_name) VALUES
    (1, 'SN', 'SN1'),
    (2, 'SN', 'SN2');

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

-- ---------- Assessments (ids 1-5 assignments, 6-10 exams) ----------
INSERT INTO assessments (id, kind, course_id, title, description, max_marks, assess_date) VALUES
    (1, 'assignment', 1, 'Assignment 1: C Basics',          'Variables, operators, simple I/O programs.', 20, '2026-08-10'),
    (2, 'assignment', 1, 'Assignment 2: Loops & Functions', 'Control flow and user-defined functions.',   20, '2026-09-05'),
    (3, 'assignment', 2, 'Assignment 1: Arrays & Strings',  'Array manipulation exercises.',              25, '2026-08-20'),
    (4, 'assignment', 3, 'Assignment 1: ER Modeling',       'Draw ER diagrams for given case studies.',   20, '2026-08-25'),
    (5, 'assignment', 4, 'Assignment 1: Set Theory',        'Problems on sets and relations.',            15, '2026-08-15'),
    (6, 'exam',       1, 'Midterm',  NULL, 50, '2026-09-01'),
    (7, 'exam',       1, 'Endterm',  NULL, 50, '2026-11-20'),
    (8, 'exam',       2, 'Midterm',  NULL, 30, '2026-09-10'),
    (9, 'exam',       3, 'Midterm',  NULL, 50, '2026-09-12'),
    (10, 'exam',      4, 'Midterm',  NULL, 40, '2026-09-08');

-- ---------- Marks (one table for both kinds) ----------
INSERT INTO marks (id, assessment_id, student_id, marks_obtained, submitted_on) VALUES
    ( 1, 1, 1, 18, '2026-08-08'), ( 2, 1, 2, 15, '2026-08-09'),
    ( 3, 1, 3, 12, '2026-08-10'), ( 4, 1, 4,  8, '2026-08-10'),
    ( 5, 1, 5, 14, '2026-08-09'),
    ( 6, 2, 1, 17, '2026-09-03'), ( 7, 2, 2, 16, '2026-09-04'),
    ( 8, 2, 3, 13, '2026-09-05'), ( 9, 2, 4,  9, '2026-09-05'),
    (10, 2, 5, 15, '2026-09-04'),
    (11, 3, 6, 21, '2026-08-18'), (12, 3, 7, 17, '2026-08-20'),
    (13, 3, 8, 23, '2026-08-19'),
    (14, 4, 1, 16, '2026-08-24'), (15, 4, 2, 18, '2026-08-25'),
    (16, 5, 6, 12, '2026-08-14'), (17, 5, 7,  9, '2026-08-15'),
    (18, 6, 1, 42, NULL), (19, 6, 2, 35, NULL), (20, 6, 3, 28, NULL),
    (21, 6, 4, 18, NULL), (22, 6, 5, 31, NULL),
    (23, 8, 6, 24, NULL), (24, 8, 7, 19, NULL), (25, 8, 8, 26, NULL),
    (26, 9, 1, 38, NULL), (27, 9, 2, 41, NULL),
    (28, 10, 6, 33, NULL), (29, 10, 7, 21, NULL);

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

-- ---------- Announcements (demo content for the Announcements tab) ----------
-- One institute-wide notice from each professor; the seeded attachments
-- are tiny hand-built files so the download link works out of the box.

INSERT INTO announcements (id, professor_id, section_id, title, body, published_at) VALUES
    (1, 1, NULL, 'Welcome to Semester 1',
     'Classes for all SN sections begin Monday. Timetables are final — check your Courses tab for rooms and slots. Attendance eligibility (75%) applies from the first session.',
     '2026-09-01 09:00:00'),
    (2, 2, NULL, 'Library hours extended',
     'The central library stays open until 20:00 throughout the exam month. Carry your student ID.',
     '2026-09-05 12:30:00');

-- Attachment for announcement 1: a tiny timetable text file (the bytes
-- below are the literal file content, inserted as a hex literal so the
-- seed stays pure ASCII and newline-agnostic across editors/OSes).
INSERT INTO announcement_attachments (announcement_id, filename, mime_type, file_bytes, size_bytes) VALUES
    (1, 'week1-timetable.txt', 'text/plain',
     0x5765656B2031202D20534E2073656D6573746572203120696E737469747574652074696D657461626C652E0A436865636B20796F757220436F75727365732074616220666F72207065722073656374696F6E20736C6F74732E,
     89);
