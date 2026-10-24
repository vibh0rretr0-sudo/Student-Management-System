import * as studentOverview from "../views/student/overview.js";
import * as studentAttendance from "../views/student/attendance.js";
import * as studentTimetable from "../views/student/timetable.js";
import * as studentAssignments from "../views/student/assignments.js";
import * as studentAnnouncements from "../views/student/announcements.js";
import * as professorOverview from "../views/professor/overview.js";
import * as professorBatches from "../views/professor/batches.js";
import * as professorAttendance from "../views/professor/attendance.js";
import * as professorAssignments from "../views/professor/assignments.js";
import * as professorAnnouncements from "../views/professor/announcements.js";
import { renderProfile } from "../components/profile.js";
import { renderSchedulePage } from "../components/schedule-page.js";

const STUDENT_NAV = [
  { path: "/overview", label: "Overview", icon: "overview" },
  { path: "/attendance", label: "Attendance", icon: "attendance" },
  { path: "/timetable", label: "Timetable", icon: "calendar" },
  { path: "/assignments", label: "Assignments", icon: "clipboard" },
  { path: "/announcements", label: "Announcements", icon: "megaphone" },
  { path: "/schedule", label: "Today's Schedule", icon: "clock" },
  { path: "/profile", label: "Personal Details", icon: "user" },
];

const PROFESSOR_NAV = [
  { path: "/overview", label: "Overview", icon: "overview" },
  { path: "/batches", label: "My Batches", icon: "layers" },
  { path: "/attendance", label: "Attendance", icon: "attendance" },
  { path: "/assignments", label: "Assignments", icon: "clipboard" },
  { path: "/announcements", label: "Announcements", icon: "megaphone" },
  { path: "/schedule", label: "Today's Schedule", icon: "clock" },
  { path: "/profile", label: "Personal Details", icon: "user" },
];

export function navItems(role) {
  return role === "professor" ? PROFESSOR_NAV : STUDENT_NAV;
}

export function buildRoutes(role) {
  const schedule = {
    title: "Today's Schedule",
    render: (container) => renderSchedulePage(container, role),
  };
  const profile = {
    title: "Personal Details",
    render: (container) => renderProfile(container),
  };

  if (role === "professor") {
    return {
      overview: { title: professorOverview.title, render: professorOverview.render },
      batches: { title: professorBatches.title, render: professorBatches.render },
      attendance: { title: professorAttendance.title, render: professorAttendance.render },
      assignments: { title: professorAssignments.title, render: professorAssignments.render },
      announcements: { title: professorAnnouncements.title, render: professorAnnouncements.render },
      schedule,
      profile,
    };
  }

  return {
    overview: { title: studentOverview.title, render: studentOverview.render },
    attendance: { title: studentAttendance.title, render: studentAttendance.render },
    timetable: { title: studentTimetable.title, render: studentTimetable.render },
    assignments: { title: studentAssignments.title, render: studentAssignments.render },
    announcements: { title: studentAnnouncements.title, render: studentAnnouncements.render },
    schedule,
    profile,
  };
}
