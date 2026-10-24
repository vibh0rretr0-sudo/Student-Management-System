-- JECRC Student & Faculty Portal — SQLite schema
-- Identical structure to schema.sql, used when DB_ENGINE=sqlite (local dev).
PRAGMA foreign_keys = OFF;

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

PRAGMA foreign_keys = ON;

CREATE TABLE users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('student','professor')),
  is_active     INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE INDEX idx_users_role ON users(role);

CREATE TABLE batches (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  code       TEXT NOT NULL UNIQUE,
  name       TEXT NOT NULL,
  branch     TEXT NOT NULL,
  semester   INTEGER NOT NULL,
  year       INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE subjects (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  code     TEXT NOT NULL UNIQUE,
  name     TEXT NOT NULL,
  credits  INTEGER NOT NULL DEFAULT 3,
  semester INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE students (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id        INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  roll_no        TEXT NOT NULL UNIQUE,
  full_name      TEXT NOT NULL,
  email          TEXT,
  phone          TEXT,
  address        TEXT,
  branch         TEXT NOT NULL,
  semester       INTEGER NOT NULL,
  batch_id       INTEGER NOT NULL REFERENCES batches(id),
  guardian_name  TEXT,
  guardian_phone TEXT,
  photo          TEXT,
  created_at     TEXT NOT NULL
);
CREATE INDEX idx_students_batch ON students(batch_id);

CREATE TABLE professors (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id        INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  employee_id    TEXT NOT NULL UNIQUE,
  full_name      TEXT NOT NULL,
  email          TEXT,
  phone          TEXT,
  address        TEXT,
  department     TEXT NOT NULL,
  designation    TEXT NOT NULL,
  qualifications TEXT,
  photo          TEXT,
  created_at     TEXT NOT NULL
);
CREATE INDEX idx_professors_department ON professors(department);

CREATE TABLE batch_subjects (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id   INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
  subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  UNIQUE (batch_id, subject_id)
);
CREATE INDEX idx_bs_subject ON batch_subjects(subject_id);

CREATE TABLE professor_batch_subject (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  professor_id INTEGER NOT NULL REFERENCES professors(id) ON DELETE CASCADE,
  batch_id     INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
  subject_id   INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  UNIQUE (professor_id, batch_id, subject_id)
);
CREATE INDEX idx_pbs_batch ON professor_batch_subject(batch_id);
CREATE INDEX idx_pbs_subject ON professor_batch_subject(subject_id);

CREATE TABLE timetable (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id     INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
  day_of_week  INTEGER NOT NULL,
  start_time   TEXT NOT NULL,
  end_time     TEXT NOT NULL,
  room         TEXT NOT NULL,
  subject_id   INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  professor_id INTEGER NOT NULL REFERENCES professors(id) ON DELETE CASCADE
);
CREATE INDEX idx_timetable_batch_day ON timetable(batch_id, day_of_week);
CREATE INDEX idx_timetable_subject ON timetable(subject_id);
CREATE INDEX idx_timetable_professor ON timetable(professor_id);

CREATE TABLE attendance (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  batch_id   INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
  date       TEXT NOT NULL,
  status     TEXT NOT NULL CHECK (status IN ('present','absent','late')),
  marked_by  INTEGER REFERENCES professors(id) ON DELETE SET NULL,
  edited_at  TEXT,
  created_at TEXT NOT NULL,
  UNIQUE (student_id, subject_id, date)
);
CREATE INDEX idx_attendance_student_subject_date ON attendance(student_id, subject_id, date);
CREATE INDEX idx_attendance_batch_date ON attendance(batch_id, date);
CREATE INDEX idx_attendance_subject_date ON attendance(subject_id, date);
CREATE INDEX idx_attendance_marked_by ON attendance(marked_by);

CREATE TABLE assignments (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  title           TEXT NOT NULL,
  description     TEXT NOT NULL,
  subject_id      INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  batch_id        INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
  professor_id    INTEGER NOT NULL REFERENCES professors(id) ON DELETE CASCADE,
  due_date        TEXT NOT NULL,
  max_marks       INTEGER NOT NULL DEFAULT 20,
  attachment_path TEXT,
  attachment_name TEXT,
  attachment_size INTEGER,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  deleted_at      TEXT
);
CREATE INDEX idx_assignments_batch ON assignments(batch_id);
CREATE INDEX idx_assignments_subject ON assignments(subject_id);
CREATE INDEX idx_assignments_professor ON assignments(professor_id);
CREATE INDEX idx_assignments_due ON assignments(due_date);

CREATE TABLE submissions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  file_path     TEXT,
  file_name     TEXT,
  file_size     INTEGER,
  submitted_at  TEXT NOT NULL,
  marks         REAL,
  remarks       TEXT,
  graded_by     INTEGER REFERENCES professors(id) ON DELETE SET NULL,
  graded_at     TEXT,
  status        TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted','graded')),
  UNIQUE (assignment_id, student_id)
);
CREATE INDEX idx_submissions_student ON submissions(student_id);
CREATE INDEX idx_submissions_graded_by ON submissions(graded_by);

CREATE TABLE announcements (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  professor_id INTEGER NOT NULL REFERENCES professors(id) ON DELETE CASCADE,
  title        TEXT NOT NULL,
  body         TEXT NOT NULL,
  priority     TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('normal','important','urgent')),
  pinned       INTEGER NOT NULL DEFAULT 0,
  audience     TEXT NOT NULL DEFAULT 'batches' CHECK (audience IN ('batches','all')),
  publish_at   TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL,
  deleted_at   TEXT
);
CREATE INDEX idx_announcements_professor ON announcements(professor_id);
CREATE INDEX idx_announcements_publish ON announcements(publish_at);

CREATE TABLE announcement_targets (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
  batch_id        INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
  UNIQUE (announcement_id, batch_id)
);
CREATE INDEX idx_ant_batch ON announcement_targets(batch_id);

CREATE TABLE announcement_reads (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
  user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  read_at         TEXT NOT NULL,
  UNIQUE (announcement_id, user_id)
);
CREATE INDEX idx_ar_user ON announcement_reads(user_id);

CREATE TABLE notifications (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title      TEXT NOT NULL,
  body       TEXT NOT NULL,
  link       TEXT,
  kind       TEXT NOT NULL DEFAULT 'info',
  is_read    INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);

CREATE TABLE audit_log (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
  action     TEXT NOT NULL,
  entity     TEXT,
  entity_id  TEXT,
  meta       TEXT,
  ip         TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);

CREATE TABLE sessions (
  token      TEXT PRIMARY KEY,
  user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
  csrf_token TEXT NOT NULL,
  remember   INTEGER NOT NULL DEFAULT 0,
  ip         TEXT,
  user_agent TEXT,
  created_at TEXT NOT NULL,
  last_seen  TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

CREATE TABLE login_attempts (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  identifier   TEXT NOT NULL,
  ip           TEXT NOT NULL,
  success      INTEGER NOT NULL DEFAULT 0,
  attempted_at TEXT NOT NULL
);
CREATE INDEX idx_attempts_identifier ON login_attempts(identifier, attempted_at);
CREATE INDEX idx_attempts_ip ON login_attempts(ip);
