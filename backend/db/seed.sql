-- ============================================================
-- Student Management System — seed.sql
-- Data seeded from the REAL JECRC University timetable:
--   B.Tech First Year, Semester-1 (2026-27), Section SN (DevOps),
--   w.e.f. 3 August 2026.
--
-- Structure (from the timetable):
--   * SN is one lecture section; SN1 / SN2 are LAB sub-batches.
--     Lectures run batch-wide - seeded once per sub-batch so every
--     student has an enrollment; labs and EM-1 tutorials split SN1/SN2.
--   * Subjects: CS=Communication Skills, CPLT=Computer Programming and
--     Logical Thinking, EM-1=Engineering Mathematics-1,
--     PS=Applied Physics, DDAL=Digital Data and AI Literacy (the
--     "Digital Literacy" labs).
--   * Teachers: AN=Dr. Anubhav, CH=Ms. Cheena, PS=Dr. Pranav Saxena,
--     AKS=Dr. Anil Kr. Sharma, PC=Dr. Priyanka Chholak,
--     MY=Ms. Monika Yadav, AN2=Dr. Abhishek Neemawat.
--   * Friday is free (no Friday courses in the timetable).
--
-- Two fixes where the printed timetable leaves a teacher double-booked:
--   * Thursday PS-Lab-2-SN2 is listed under PC, who already teaches
--     CPLT Lab-B 9:40-10:30 that morning -> moved to Dr. Abhishek
--     Neemawat (the TT lists him with no slots).
--   * The Tuesday EM-1 lecture (NYB-314 + AN) is likewise unclaimed
--     elsewhere -> given to Dr. Abhishek Neemawat.
--
-- Demo story kept for the viva:
--   * The login-page demo account is professor 8 (vibhor) - by design
--     he owns NO timetable course, so per-professor scoping (403s) is
--     easy to demo. Any timetable teacher's login shows real data.
--   * Attendance on Saturday's Physics Lab (SN1): student 04 sits at
--     exactly 75% -> Eligible (the C++ cutoff is inclusive); student
--     15 at 50% -> Not Eligible.
--   * Marks: CPLT lecture (SN1) and Monday's Physics lecture (SN1)
--     carry light demo marks so the dashboard charts and the C++
--     grades mode have data out of the box.
-- ============================================================

USE sms;

-- ---------- Sections (batch is an attribute, not a table) ----------
INSERT INTO sections (id, batch_name, section_name) VALUES
    (1, 'SN', 'SN1'),
    (2, 'SN', 'SN2');

-- ---------- Professors (the timetable's TEACHERS + your own login) ----------
-- Password for every account: prof123 (PBKDF2-SHA256, 390000 iterations)
INSERT INTO professors (id, username, password_hash, name) VALUES
    (1, 'anubhav',    'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Dr. Anubhav'),
    (2, 'cheena',     'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Ms. Cheena'),
    (3, 'abhishek',   'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Dr. Abhishek Neemawat'),
    (4, 'pranav',     'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Dr. Pranav Saxena'),
    (5, 'anilsharma', 'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Dr. Anil Kr. Sharma'),
    (6, 'priyanka',   'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Dr. Priyanka Chholak'),
    (7, 'monika',     'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Ms. Monika Yadav'),
    (8, 'vibhor',     'pbkdf2_sha256$390000$9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e$b8426d832dd25c26c6d1cfe8ce405a394db12c926d4e52993290250f38025d0d', 'Vibhor Mathur');

-- ---------- Students (15 per lab sub-batch, rolls 01..15) ----------
INSERT INTO students (id, name, roll_number, date_of_birth, contact, enrollment_date, section_id) VALUES
    ( 1, 'Aarav Sharma',       '01', '2007-08-14', '9876500011', '2026-08-03', 1),
    ( 2, 'Diya Patel',         '02', '2007-11-02', '9876500012', '2026-08-03', 1),
    ( 3, 'Rohan Gupta',        '03', '2008-01-27', '9876500013', '2026-08-03', 1),
    ( 4, 'Ishita Verma',       '04', '2007-05-19', '9876500014', '2026-08-03', 1),
    ( 5, 'Kunal Singh',        '05', '2007-09-30', '9876500015', '2026-08-03', 1),
    ( 6, 'Ananya Mehta',       '06', '2007-12-11', '9876500016', '2026-08-03', 1),
    ( 7, 'Vivaan Jain',        '07', '2008-03-08', '9876500017', '2026-08-03', 1),
    ( 8, 'Saanvi Kapoor',      '08', '2007-07-23', '9876500018', '2026-08-03', 1),
    ( 9, 'Arjun Nair',         '09', '2007-10-05', '9876500019', '2026-08-03', 1),
    (10, 'Myra Joshi',         '10', '2007-06-18', '9876500020', '2026-08-03', 1),
    (11, 'Reyansh Kulkarni',   '11', '2008-02-09', '9876500021', '2026-08-03', 1),
    (12, 'Aisha Qureshi',      '12', '2007-04-22', '9876500022', '2026-08-03', 1),
    (13, 'Kabir Chauhan',      '13', '2007-09-03', '9876500023', '2026-08-03', 1),
    (14, 'Navya Iyer',         '14', '2008-01-15', '9876500024', '2026-08-03', 1),
    (15, 'Dhruv Bhatnagar',    '15', '2007-11-28', '9876500025', '2026-08-03', 1),
    (16, 'Ananya Saxena',      '01', '2007-12-11', '9876500031', '2026-08-03', 2),
    (17, 'Vivaan Malhotra',    '02', '2008-03-08', '9876500032', '2026-08-03', 2),
    (18, 'Saanvi Rathore',     '03', '2007-07-23', '9876500033', '2026-08-03', 2),
    (19, 'Arjun Deshmukh',     '04', '2007-10-05', '9876500034', '2026-08-03', 2),
    (20, 'Myra Bansal',        '05', '2007-06-18', '9876500035', '2026-08-03', 2),
    (21, 'Reyansh Pillai',     '06', '2008-02-09', '9876500036', '2026-08-03', 2),
    (22, 'Aisha Trivedi',      '07', '2007-04-22', '9876500037', '2026-08-03', 2),
    (23, 'Kabir Sengupta',     '08', '2007-09-03', '9876500038', '2026-08-03', 2),
    (24, 'Navya Menon',        '09', '2008-01-15', '9876500039', '2026-08-03', 2),
    (25, 'Dhruv Chandrasekar', '10', '2007-11-28', '9876500040', '2026-08-03', 2),
    (26, 'Ira Pandey',         '11', '2007-08-30', '9876500041', '2026-08-03', 2),
    (27, 'Veer Pratap',        '12', '2007-05-07', '9876500042', '2026-08-03', 2),
    (28, 'Zara Sheikh',        '13', '2007-10-19', '9876500043', '2026-08-03', 2),
    (29, 'Advik Rana',         '14', '2008-02-26', '9876500044', '2026-08-03', 2),
    (30, 'Kiara Dixit',        '15', '2007-06-04', '9876500045', '2026-08-03', 2);

-- ---------- Courses: every timetable cell, w.e.f. 3 Aug 2026 ----------
-- day_of_week: 1=Mon ... 7=Sun. Times are the timetable's column spans.
-- Batch-wide lectures appear once per sub-batch (same teacher, same
-- slot) so each student of SN1/SN2 has an enrollment row.
-- ids in insertion order: 1-8 Mon, 9-14 Tue, 15-19 Wed, 20-25 Thu,
-- 26-31 Sat.

-- ===== Monday =====
INSERT INTO courses (id, course_name, course_code, professor_id, section_id, term, day_of_week, start_time, end_time) VALUES
    ( 1, 'Communication Skills (Lecture)',      'CS-L',           1, 1, '2026-27 S1', 1, '08:50', '09:40'),
    ( 2, 'Communication Skills (Lecture)',      'CS-L',           1, 2, '2026-27 S1', 1, '08:50', '09:40'),
    ( 3, 'Applied Physics (Lecture)',           'PS-L',           4, 1, '2026-27 S1', 1, '09:40', '10:30'),
    ( 4, 'Applied Physics (Lecture)',           'PS-L',           4, 2, '2026-27 S1', 1, '09:40', '10:30'),
    ( 5, 'Engineering Mathematics-1 (Lecture)', 'EM1-L',          1, 1, '2026-27 S1', 1, '10:30', '11:20'),
    ( 6, 'Engineering Mathematics-1 (Lecture)', 'EM1-L',          1, 2, '2026-27 S1', 1, '10:30', '11:20'),
    ( 7, 'Computer Programming Lab (SN1)',      'CPLT-LAB-SN1',   6, 1, '2026-27 S1', 1, '11:20', '12:50'),
    ( 8, 'Computer Programming Lab (SN2)',      'CPLT-LAB-SN2',   1, 2, '2026-27 S1', 1, '11:20', '12:50');

-- ===== Tuesday =====
INSERT INTO courses (id, course_name, course_code, professor_id, section_id, term, day_of_week, start_time, end_time) VALUES
    ( 9, 'Digital Literacy Lab (DDAL)',           'DDAL-LAB',   3, 1, '2026-27 S1', 2, '08:50', '10:30'),
    (10, 'Digital Literacy Lab (DDAL)',           'DDAL-LAB',   3, 2, '2026-27 S1', 2, '08:50', '10:30'),
    (11, 'Engineering Mathematics-1 (Lecture 2)', 'EM1-L2',     3, 1, '2026-27 S1', 2, '09:40', '10:30'),
    (12, 'Engineering Mathematics-1 (Lecture 2)', 'EM1-L2',     3, 2, '2026-27 S1', 2, '09:40', '10:30'),
    (13, 'Applied Physics (Lecture 2)',           'PS-L2',      4, 1, '2026-27 S1', 2, '11:20', '12:05'),
    (14, 'Applied Physics (Lecture 2)',           'PS-L2',      4, 2, '2026-27 S1', 2, '11:20', '12:05');

-- ===== Wednesday =====
INSERT INTO courses (id, course_name, course_code, professor_id, section_id, term, day_of_week, start_time, end_time) VALUES
    (15, 'Computer Programming and Logical Thinking (Lecture)', 'CPLT-L',      2, 1, '2026-27 S1', 3, '08:50', '10:30'),
    (16, 'Computer Programming and Logical Thinking (Lecture)', 'CPLT-L',      2, 2, '2026-27 S1', 3, '08:50', '10:30'),
    (17, 'Engineering Mathematics-1 Tutorial (SN1)',            'EM1-TUT-SN1', 7, 1, '2026-27 S1', 3, '09:40', '10:30'),
    (18, 'Digital Literacy Lab (DDAL) 2',                       'DDAL-LAB2',   3, 1, '2026-27 S1', 3, '11:20', '12:50'),
    (19, 'Digital Literacy Lab (DDAL) 2',                       'DDAL-LAB2',   3, 2, '2026-27 S1', 3, '11:20', '12:50');

-- ===== Thursday =====
INSERT INTO courses (id, course_name, course_code, professor_id, section_id, term, day_of_week, start_time, end_time) VALUES
    (20, 'Computer Programming and Logical Thinking (Lecture 2)', 'CPLT-L2',       2, 1, '2026-27 S1', 4, '08:50', '10:30'),
    (21, 'Computer Programming and Logical Thinking (Lecture 2)', 'CPLT-L2',       2, 2, '2026-27 S1', 4, '08:50', '10:30'),
    (22, 'Engineering Mathematics-1 Tutorial (SN2)',              'EM1-TUT-SN2',   7, 2, '2026-27 S1', 4, '08:50', '09:40'),
    (23, 'Computer Programming Lab (Batch)',                      'CPLT-LAB-B',    6, 1, '2026-27 S1', 4, '09:40', '10:30'),
    (24, 'Computer Programming Lab (Batch)',                      'CPLT-LAB-B',    6, 2, '2026-27 S1', 4, '09:40', '10:30'),
    (25, 'Applied Physics Lab-2 (SN2)',                           'PS-LAB-SN2',    3, 2, '2026-27 S1', 4, '09:40', '12:05');

-- ===== Saturday =====
INSERT INTO courses (id, course_name, course_code, professor_id, section_id, term, day_of_week, start_time, end_time) VALUES
    (26, 'Applied Physics Lab (SN1)',                             'PS-LAB-SN1',     5, 1, '2026-27 S1', 6, '08:50', '10:30'),
    (27, 'Computer Programming Lab (SN2 Saturday)',               'CPLT-LAB-SN2-S', 2, 2, '2026-27 S1', 6, '09:40', '10:30'),
    (28, 'Computer Programming and Logical Thinking (Lecture 3)', 'CPLT-L3',        2, 1, '2026-27 S1', 6, '10:30', '11:20'),
    (29, 'Computer Programming and Logical Thinking (Lecture 3)', 'CPLT-L3',        2, 2, '2026-27 S1', 6, '10:30', '11:20'),
    (30, 'Engineering Mathematics-1 (Lecture 3)',                 'EM1-L3',         1, 1, '2026-27 S1', 6, '10:30', '11:20'),
    (31, 'Engineering Mathematics-1 (Lecture 3)',                 'EM1-L3',         1, 2, '2026-27 S1', 6, '10:30', '11:20');

-- ---------- Enrollments ----------
-- Every student enrolls in all courses of their own sub-batch - one
-- INSERT..SELECT instead of hundreds of literal rows.
INSERT INTO enrollments (student_id, course_id, enrollment_date)
SELECT s.id, c.id, '2026-08-03'
FROM students s
JOIN courses c ON c.section_id = s.section_id;

-- ---------- Assessments + marks (light demo layer, SN1 courses) ----------
-- Course 15 (CPLT Lecture, SN1): two assignments + a midterm.
-- Course 3  (Physics Lecture, SN1): one assignment + a midterm.
INSERT INTO assessments (id, kind, course_id, title, description, max_marks, assess_date) VALUES
    (1, 'assignment', 15, 'Assignment 1: C Basics',           'Variables, operators, simple I/O programs.',  20, '2026-08-17'),
    (2, 'assignment', 15, 'Assignment 2: Loops & Functions',  'Control flow and user-defined functions.',    20, '2026-09-07'),
    (3, 'exam',       15, 'Midterm',                           NULL, 50, '2026-09-16'),
    (4, 'assignment',  3, 'Assignment 1: Units & Measurement', 'Numerical problems on units and dimensions.', 25, '2026-08-24'),
    (5, 'exam',        3, 'Midterm',                           NULL, 50, '2026-09-18');

INSERT INTO marks (assessment_id, student_id, marks_obtained, submitted_on) VALUES
    (1,  1, 18, '2026-08-15'), (1,  2, 16, '2026-08-15'), (1,  3, 14, '2026-08-16'),
    (1,  4,  9, '2026-08-16'), (1,  5, 15, '2026-08-15'), (1,  6, 17, '2026-08-16'),
    (1,  7, 12, '2026-08-17'), (1,  8, 19, '2026-08-15'), (1,  9, 13, '2026-08-17'),
    (1, 10, 18, '2026-08-16'), (1, 11, 11, '2026-08-18'), (1, 12, 20, '2026-08-15'),
    (1, 13, 14, '2026-08-17'), (1, 14, 16, '2026-08-16'), (1, 15,  8, '2026-08-18'),
    (2,  1, 17, '2026-09-05'), (2,  2, 15, '2026-09-05'), (2,  3, 13, '2026-09-06'),
    (2,  4,  8, '2026-09-06'), (2,  5, 14, '2026-09-05'), (2,  6, 16, '2026-09-06'),
    (2,  7, 11, '2026-09-07'), (2,  8, 18, '2026-09-05'), (2,  9, 12, '2026-09-07'),
    (2, 10, 17, '2026-09-06'), (2, 11, 10, '2026-09-08'), (2, 12, 19, '2026-09-05'),
    (2, 13, 13, '2026-09-07'), (2, 14, 15, '2026-09-06'), (2, 15,  7, '2026-09-08'),
    (3,  1, 42, NULL), (3,  2, 38, NULL), (3,  3, 33, NULL), (3,  4, 21, NULL),
    (3,  5, 35, NULL), (3,  6, 40, NULL), (3,  7, 29, NULL), (3,  8, 45, NULL),
    (3,  9, 31, NULL), (3, 10, 41, NULL), (3, 11, 26, NULL), (3, 12, 47, NULL),
    (3, 13, 34, NULL), (3, 14, 37, NULL), (3, 15, 19, NULL),
    (4,  1, 23, '2026-08-22'), (4,  2, 20, '2026-08-22'), (4,  3, 18, '2026-08-23'),
    (4,  4, 12, '2026-08-23'), (4,  5, 19, '2026-08-22'), (4,  6, 21, '2026-08-23'),
    (4,  7, 15, '2026-08-24'), (4,  8, 24, '2026-08-22'), (4,  9, 16, '2026-08-24'),
    (4, 10, 22, '2026-08-23'), (4, 11, 14, '2026-08-25'), (4, 12, 25, '2026-08-22'),
    (4, 13, 17, '2026-08-24'), (4, 14, 20, '2026-08-23'), (4, 15, 10, '2026-08-25'),
    (5,  1, 40, NULL), (5,  2, 36, NULL), (5,  3, 30, NULL), (5,  4, 18, NULL),
    (5,  5, 33, NULL), (5,  6, 38, NULL), (5,  7, 27, NULL), (5,  8, 43, NULL),
    (5,  9, 29, NULL), (5, 10, 39, NULL), (5, 11, 24, NULL), (5, 12, 45, NULL),
    (5, 13, 32, NULL), (5, 14, 35, NULL), (5, 15, 16, NULL);

-- ---------- Attendance (Course 26: Saturday Physics Lab, SN1) ----------
-- Four sessions. Story: student 4 = 3 of 4 present = exactly 75% ->
-- Eligible (inclusive cutoff, the viva boundary). Student 15 = 2 of 4
-- = 50% -> Not Eligible.
INSERT INTO attendance (student_id, course_id, date, status) VALUES
    ( 1, 26, '2026-08-08', 'present'), ( 2, 26, '2026-08-08', 'present'), ( 3, 26, '2026-08-08', 'present'),
    ( 4, 26, '2026-08-08', 'present'), ( 5, 26, '2026-08-08', 'present'), ( 6, 26, '2026-08-08', 'present'),
    ( 7, 26, '2026-08-08', 'present'), ( 8, 26, '2026-08-08', 'present'), ( 9, 26, '2026-08-08', 'present'),
    (10, 26, '2026-08-08', 'present'), (11, 26, '2026-08-08', 'present'), (12, 26, '2026-08-08', 'present'),
    (13, 26, '2026-08-08', 'present'), (14, 26, '2026-08-08', 'present'), (15, 26, '2026-08-08', 'present'),
    ( 1, 26, '2026-08-15', 'present'), ( 2, 26, '2026-08-15', 'present'), ( 3, 26, '2026-08-15', 'present'),
    ( 4, 26, '2026-08-15', 'present'), ( 5, 26, '2026-08-15', 'present'), ( 6, 26, '2026-08-15', 'present'),
    ( 7, 26, '2026-08-15', 'present'), ( 8, 26, '2026-08-15', 'present'), ( 9, 26, '2026-08-15', 'present'),
    (10, 26, '2026-08-15', 'present'), (11, 26, '2026-08-15', 'present'), (12, 26, '2026-08-15', 'present'),
    (13, 26, '2026-08-15', 'present'), (14, 26, '2026-08-15', 'absent'),  (15, 26, '2026-08-15', 'present'),
    ( 1, 26, '2026-08-22', 'present'), ( 2, 26, '2026-08-22', 'present'), ( 3, 26, '2026-08-22', 'present'),
    ( 4, 26, '2026-08-22', 'present'), ( 5, 26, '2026-08-22', 'present'), ( 6, 26, '2026-08-22', 'present'),
    ( 7, 26, '2026-08-22', 'present'), ( 8, 26, '2026-08-22', 'present'), ( 9, 26, '2026-08-22', 'present'),
    (10, 26, '2026-08-22', 'present'), (11, 26, '2026-08-22', 'present'), (12, 26, '2026-08-22', 'present'),
    (13, 26, '2026-08-22', 'present'), (14, 26, '2026-08-22', 'present'), (15, 26, '2026-08-22', 'absent'),
    ( 1, 26, '2026-08-29', 'present'), ( 2, 26, '2026-08-29', 'present'), ( 3, 26, '2026-08-29', 'present'),
    ( 4, 26, '2026-08-29', 'absent'),  ( 5, 26, '2026-08-29', 'present'), ( 6, 26, '2026-08-29', 'present'),
    ( 7, 26, '2026-08-29', 'present'), ( 8, 26, '2026-08-29', 'present'), ( 9, 26, '2026-08-29', 'present'),
    (10, 26, '2026-08-29', 'present'), (11, 26, '2026-08-29', 'present'), (12, 26, '2026-08-29', 'present'),
    (13, 26, '2026-08-29', 'present'), (14, 26, '2026-08-29', 'present'), (15, 26, '2026-08-29', 'absent');

-- ---------- Announcements (realistic notices) ----------
INSERT INTO announcements (id, professor_id, section_id, title, body, published_at) VALUES
    (1, 8, NULL, 'Timetable w.e.f. 3 August 2026',
     'The Semester-1 timetable for Section SN (DevOps) is final. Lectures run batch-wide for SN1 and SN2 - labs and EM-1 tutorials meet in sub-batches. Check the Courses tab for your exact rooms and slots. Friday is free.',
     '2026-08-01 10:00:00'),
    (2, 1, NULL, 'EM-1 tutorial groups',
     'EM-1 tutorials meet in sub-batches: SN1 on Wednesday 9:40 in VIB-218 with Ms. Monika Yadav, SN2 on Thursday 8:50 in NYB-402. Bring your tutorial sheet every week.',
     '2026-08-05 09:30:00'),
    (3, 7, NULL, 'Lab record notebooks',
     'Carry your lab record notebook to every lab session - CPLT labs on Monday (SN1) and Saturday (SN2), Physics labs on Thursday (SN2) and Saturday (SN1). Unsigned records will not be graded.',
     '2026-08-10 14:00:00');

-- Attachment for announcement 1: a plain-text timetable summary (bytes
-- inserted as a hex literal so the seed stays pure ASCII).
INSERT INTO announcement_attachments (announcement_id, filename, mime_type, file_bytes, size_bytes) VALUES
    (1, 'timetable-summary.txt', 'text/plain',
     0x4a4543524320556e6976657273697479202d20422e5465636820466972737420596561722c2053656d657374657220312028323032362d3237292c2053656374696f6e20534e20284465764f7073292e0a4c656374757265732072756e2062617463682d7769646520666f7220534e312b534e323b206c61627320616e64207475746f7269616c732073706c6974206279207375622d62617463682e0a46756c6c20736c6f74206c6973743a207365652074686520436f7572736573207461622028772e652e662e2033204175677573742032303236292e,
     216);
