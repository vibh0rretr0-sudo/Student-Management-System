-- JECRC Student & Faculty Portal — MySQL 8 schema
-- Load with: mysql -u jecrc -p jecrc_portal < schema/schema.sql

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS login_attempts;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS announcement_reads;
DROP TABLE IF EXISTS announcement_targets;
DROP TABLE IF EXISTS announcements;
DROP TABLE IF EXISTS submissions;
DROP TABLE IF EXISTS assignments;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS timetable;
DROP TABLE IF EXISTS professor_batch_subject;
DROP TABLE IF EXISTS batch_subjects;
DROP TABLE IF EXISTS professors;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS batches;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  username      VARCHAR(80)  NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('student','professor') NOT NULL,
  is_active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at    DATETIME NOT NULL,
  updated_at    DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  KEY idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE batches (
  id       INT UNSIGNED NOT NULL AUTO_INCREMENT,
  code     VARCHAR(30) NOT NULL,
  name     VARCHAR(120) NOT NULL,
  branch   VARCHAR(120) NOT NULL,
  semester TINYINT UNSIGNED NOT NULL,
  year     SMALLINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_batches_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE subjects (
  id       INT UNSIGNED NOT NULL AUTO_INCREMENT,
  code     VARCHAR(20) NOT NULL,
  name     VARCHAR(140) NOT NULL,
  credits  TINYINT UNSIGNED NOT NULL DEFAULT 3,
  semester TINYINT UNSIGNED NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY uq_subjects_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE students (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id       INT UNSIGNED NOT NULL,
  roll_no       VARCHAR(24) NOT NULL,
  full_name     VARCHAR(120) NOT NULL,
  email         VARCHAR(160) NULL,
  phone         VARCHAR(20) NULL,
  address       VARCHAR(255) NULL,
  branch        VARCHAR(120) NOT NULL,
  semester      TINYINT UNSIGNED NOT NULL,
  batch_id      INT UNSIGNED NOT NULL,
  guardian_name VARCHAR(120) NULL,
  guardian_phone VARCHAR(20) NULL,
  photo         VARCHAR(255) NULL,
  created_at    DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_students_roll (roll_no),
  UNIQUE KEY uq_students_user (user_id),
  KEY idx_students_batch (batch_id),
  CONSTRAINT fk_students_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_students_batch FOREIGN KEY (batch_id) REFERENCES batches (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE professors (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id        INT UNSIGNED NOT NULL,
  employee_id    VARCHAR(30) NOT NULL,
  full_name      VARCHAR(120) NOT NULL,
  email          VARCHAR(160) NULL,
  phone          VARCHAR(20) NULL,
  address        VARCHAR(255) NULL,
  department     VARCHAR(120) NOT NULL,
  designation    VARCHAR(120) NOT NULL,
  qualifications VARCHAR(255) NULL,
  photo          VARCHAR(255) NULL,
  created_at     DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_professors_employee (employee_id),
  UNIQUE KEY uq_professors_user (user_id),
  KEY idx_professors_department (department),
  CONSTRAINT fk_professors_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE batch_subjects (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  batch_id   INT UNSIGNED NOT NULL,
  subject_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_batch_subject (batch_id, subject_id),
  KEY idx_bs_subject (subject_id),
  CONSTRAINT fk_bs_batch FOREIGN KEY (batch_id) REFERENCES batches (id) ON DELETE CASCADE,
  CONSTRAINT fk_bs_subject FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE professor_batch_subject (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  professor_id INT UNSIGNED NOT NULL,
  batch_id     INT UNSIGNED NOT NULL,
  subject_id   INT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pbs (professor_id, batch_id, subject_id),
  KEY idx_pbs_batch (batch_id),
  KEY idx_pbs_subject (subject_id),
  KEY idx_pbs_professor (professor_id),
  CONSTRAINT fk_pbs_professor FOREIGN KEY (professor_id) REFERENCES professors (id) ON DELETE CASCADE,
  CONSTRAINT fk_pbs_batch FOREIGN KEY (batch_id) REFERENCES batches (id) ON DELETE CASCADE,
  CONSTRAINT fk_pbs_subject FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE timetable (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  batch_id    INT UNSIGNED NOT NULL,
  day_of_week TINYINT UNSIGNED NOT NULL,
  start_time  TIME NOT NULL,
  end_time    TIME NOT NULL,
  room        VARCHAR(40) NOT NULL,
  subject_id  INT UNSIGNED NOT NULL,
  professor_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  KEY idx_timetable_batch_day (batch_id, day_of_week),
  KEY idx_timetable_subject (subject_id),
  KEY idx_timetable_professor (professor_id),
  CONSTRAINT fk_tt_batch FOREIGN KEY (batch_id) REFERENCES batches (id) ON DELETE CASCADE,
  CONSTRAINT fk_tt_subject FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE,
  CONSTRAINT fk_tt_professor FOREIGN KEY (professor_id) REFERENCES professors (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE attendance (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  student_id INT UNSIGNED NOT NULL,
  subject_id INT UNSIGNED NOT NULL,
  batch_id   INT UNSIGNED NOT NULL,
  date       DATE NOT NULL,
  status     ENUM('present','absent','late') NOT NULL,
  marked_by  INT UNSIGNED NULL,
  edited_at  DATETIME NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_attendance (student_id, subject_id, date),
  KEY idx_attendance_student_subject_date (student_id, subject_id, date),
  KEY idx_attendance_batch_date (batch_id, date),
  KEY idx_attendance_subject_date (subject_id, date),
  KEY idx_attendance_marked_by (marked_by),
  CONSTRAINT fk_att_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
  CONSTRAINT fk_att_subject FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE,
  CONSTRAINT fk_att_batch FOREIGN KEY (batch_id) REFERENCES batches (id) ON DELETE CASCADE,
  CONSTRAINT fk_att_marked_by FOREIGN KEY (marked_by) REFERENCES professors (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE assignments (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title        VARCHAR(180) NOT NULL,
  description  TEXT NOT NULL,
  subject_id   INT UNSIGNED NOT NULL,
  batch_id     INT UNSIGNED NOT NULL,
  professor_id INT UNSIGNED NOT NULL,
  due_date     DATETIME NOT NULL,
  max_marks    SMALLINT UNSIGNED NOT NULL DEFAULT 20,
  attachment_path VARCHAR(255) NULL,
  attachment_name VARCHAR(180) NULL,
  attachment_size INT UNSIGNED NULL,
  created_at   DATETIME NOT NULL,
  updated_at   DATETIME NOT NULL,
  deleted_at   DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_assignments_batch (batch_id),
  KEY idx_assignments_subject (subject_id),
  KEY idx_assignments_professor (professor_id),
  KEY idx_assignments_due (due_date),
  CONSTRAINT fk_as_subject FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE,
  CONSTRAINT fk_as_batch FOREIGN KEY (batch_id) REFERENCES batches (id) ON DELETE CASCADE,
  CONSTRAINT fk_as_professor FOREIGN KEY (professor_id) REFERENCES professors (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE submissions (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  assignment_id INT UNSIGNED NOT NULL,
  student_id    INT UNSIGNED NOT NULL,
  file_path     VARCHAR(255) NULL,
  file_name     VARCHAR(180) NULL,
  file_size     INT UNSIGNED NULL,
  submitted_at  DATETIME NOT NULL,
  marks         DECIMAL(5,2) NULL,
  remarks       VARCHAR(500) NULL,
  graded_by     INT UNSIGNED NULL,
  graded_at     DATETIME NULL,
  status        ENUM('submitted','graded') NOT NULL DEFAULT 'submitted',
  PRIMARY KEY (id),
  UNIQUE KEY uq_submission (assignment_id, student_id),
  KEY idx_submissions_student (student_id),
  KEY idx_submissions_graded_by (graded_by),
  CONSTRAINT fk_sub_assignment FOREIGN KEY (assignment_id) REFERENCES assignments (id) ON DELETE CASCADE,
  CONSTRAINT fk_sub_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
  CONSTRAINT fk_sub_graded_by FOREIGN KEY (graded_by) REFERENCES professors (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE announcements (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  professor_id INT UNSIGNED NOT NULL,
  title        VARCHAR(180) NOT NULL,
  body         TEXT NOT NULL,
  priority     ENUM('normal','important','urgent') NOT NULL DEFAULT 'normal',
  pinned       TINYINT(1) NOT NULL DEFAULT 0,
  audience     ENUM('batches','all') NOT NULL DEFAULT 'batches',
  publish_at   DATETIME NOT NULL,
  created_at   DATETIME NOT NULL,
  updated_at   DATETIME NOT NULL,
  deleted_at   DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_announcements_professor (professor_id),
  KEY idx_announcements_publish (publish_at),
  CONSTRAINT fk_ann_professor FOREIGN KEY (professor_id) REFERENCES professors (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE announcement_targets (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  announcement_id INT UNSIGNED NOT NULL,
  batch_id        INT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_ann_target (announcement_id, batch_id),
  KEY idx_ant_batch (batch_id),
  CONSTRAINT fk_ant_ann FOREIGN KEY (announcement_id) REFERENCES announcements (id) ON DELETE CASCADE,
  CONSTRAINT fk_ant_batch FOREIGN KEY (batch_id) REFERENCES batches (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE announcement_reads (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  announcement_id INT UNSIGNED NOT NULL,
  user_id         INT UNSIGNED NOT NULL,
  read_at         DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_ann_read (announcement_id, user_id),
  KEY idx_ar_user (user_id),
  CONSTRAINT fk_ar_ann FOREIGN KEY (announcement_id) REFERENCES announcements (id) ON DELETE CASCADE,
  CONSTRAINT fk_ar_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE notifications (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    INT UNSIGNED NOT NULL,
  title      VARCHAR(180) NOT NULL,
  body       VARCHAR(500) NOT NULL,
  link       VARCHAR(255) NULL,
  kind       VARCHAR(30) NOT NULL DEFAULT 'info',
  is_read    TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  KEY idx_notifications_user (user_id, is_read),
  CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    INT UNSIGNED NULL,
  action     VARCHAR(80) NOT NULL,
  entity     VARCHAR(40) NULL,
  entity_id  VARCHAR(40) NULL,
  meta       TEXT NULL,
  ip         VARCHAR(45) NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  KEY idx_audit_user (user_id),
  KEY idx_audit_created (created_at),
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE sessions (
  token       VARCHAR(64) NOT NULL,
  user_id     INT UNSIGNED NULL,
  csrf_token  VARCHAR(64) NOT NULL,
  remember    TINYINT(1) NOT NULL DEFAULT 0,
  ip          VARCHAR(45) NULL,
  user_agent  VARCHAR(255) NULL,
  created_at  DATETIME NOT NULL,
  last_seen   DATETIME NOT NULL,
  expires_at  DATETIME NOT NULL,
  PRIMARY KEY (token),
  KEY idx_sessions_user (user_id),
  KEY idx_sessions_expires (expires_at),
  CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE login_attempts (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  identifier   VARCHAR(120) NOT NULL,
  ip           VARCHAR(45) NOT NULL,
  success      TINYINT(1) NOT NULL DEFAULT 0,
  attempted_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  KEY idx_attempts_identifier (identifier, attempted_at),
  KEY idx_attempts_ip (ip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
