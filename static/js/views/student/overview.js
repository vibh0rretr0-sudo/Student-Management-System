import { api } from "../../core/api.js";
import { doughnutChart, lineChart } from "../../core/charts.js";
import {
  callout, el, errorPanel, fmtClock, fmtDate, iconEl, loadingView, relativeTime,
  statusBadge, toast, goTo,
} from "../../core/ui.js";
import { getThreshold } from "../../runtime/session.js";
import { panel } from "../../components/page.js";
import { countdownChip, nextClass } from "../../components/schedule.js";

export const title = "Overview";

export async function render(container) {
  container.append(loadingView());
  let data;
  try {
    data = (await api("/api/student/overview")).data;
  } catch (error) {
    container.innerHTML = "";
    container.append(errorPanel(error.message, () => {
      container.innerHTML = "";
      render(container);
    }));
    return;
  }

  container.innerHTML = "";
  const threshold = getThreshold();
  const today = new Date();

  /* ---------------------------------------------------------- Greeting */
  const hour = today.getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const meta = el("div", { class: "greeting__meta" },
    el("span", { class: "chip" }, `Roll ${data.student.roll_no}`),
    el("span", { class: "chip" }, data.student.branch),
    el("span", { class: "chip" }, `Semester ${data.student.semester}`),
    el("span", { class: "chip" }, data.student.batch),
    el("span", { class: "badge badge--neutral" }, data.day_name));
  const greetingBlock = el("section", { class: "greeting is-entering" },
    el("span", { class: "greeting__eyebrow" }, iconEl("spark"),
      ` ${fmtDate(data.today, { weekday: true })} · Semester ${data.student.semester}`),
    el("h2", { class: "greeting__title" },
      `${greeting}, `, el("span", { class: "accent" }, data.student.name.split(" ")[0])),
    el("p", { class: "muted", style: { fontSize: "var(--text-base)", marginBottom: "12px" } },
      "Here's where your semester stands today."),
    meta);
  container.append(greetingBlock);

  const grid = el("div", { class: "dashboard-grid" });
  const mainCol = el("div", { class: "dash-main" });
  const sideCol = el("div", { class: "dash-side" });
  grid.append(mainCol, sideCol);
  container.append(grid);

  /* ---------------------------------------------------------- Attendance */
  const overall = data.attendance;
  const chartCanvas = el("canvas", { role: "img", "aria-label": `Overall attendance ${overall.percentage} percent` });
  const doughnut = el("div", { class: "doughnut-wrap" }, chartCanvas,
    el("div", { class: "doughnut-center" },
      el("span", { class: "doughnut-center__value" }, `${overall.percentage}%`),
      el("span", { class: "doughnut-center__label" }, "Overall"),
      el("span", { class: "doughnut-center__sub" },
        `${overall.attended} / ${overall.held} classes`)));

  const stats = el("div", { class: "att-stats" },
    el("div", { class: "att-stat att-stat--success" },
      el("div", { class: "att-stat__value" }, String(overall.attended)),
      el("div", { class: "att-stat__label" }, "Attended")),
    el("div", { class: "att-stat" },
      el("div", { class: "att-stat__value" }, String(overall.held)),
      el("div", { class: "att-stat__label" }, "Classes held")),
    el("div", { class: `att-stat ${overall.below_threshold ? "att-stat--danger" : "att-stat--success"}` },
      el("div", { class: "att-stat__value" },
        overall.below_threshold ? String(overall.need_attend) : String(overall.can_miss)),
      el("div", { class: "att-stat__label" },
        overall.below_threshold ? "Attend to reach 75%" : "Can still miss")));

  const warningText = overall.held === 0
    ? "No attendance has been recorded yet this semester."
    : overall.below_threshold
      ? `You are below ${threshold}%. Attend the next ${overall.need_attend} class${overall.need_attend === 1 ? "" : "es"} in a row to get back above the line.`
      : `You can miss ${overall.can_miss} more class${overall.can_miss === 1 ? "" : "es"} this semester and still stay at or above ${threshold}%.`;
  const warning = callout(warningText,
    overall.below_threshold ? "danger" : "success",
    overall.below_threshold ? "alert" : "shield");

  const subjectGrid = el("div", { class: "subject-grid" });
  data.subjects.forEach((subject) => {
    const pct = subject.percentage;
    const variant = pct < threshold ? "subject-tile--danger" : pct < threshold + 5 ? "subject-tile--warning" : "";
    const cell = el("div", { class: `subject-tile ${variant}` });
    const mini = el("div", { class: "subject-tile__chart" },
      el("canvas", { role: "img", "aria-label": `${subject.name} attendance ${pct} percent` }),
      el("span", { class: "subject-tile__pct" }, `${Math.round(pct)}%`));
    cell.append(mini, el("div", { class: "subject-tile__meta" },
      el("div", { class: "subject-tile__code" }, subject.code),
      el("div", { class: "subject-tile__name", title: subject.name }, subject.name),
      el("div", { class: "tiny muted" }, `${subject.attended}/${subject.held} attended`)));
    subjectGrid.append(cell);
    mini.dataset.value = String(pct);
  });

  const attendanceBody = el("div", { class: "stack" },
    el("div", { class: "attendance-hero" }, doughnut, el("div", { class: "stack" }, stats, warning)),
    el("div", {},
      el("div", { class: "section-head" },
        el("h3", {}, "Subject breakdown"),
        el("span", { class: "muted" }, "Tap Attendance for the full record")),
      subjectGrid));

  const attendancePanel = panel({
    title: "Attendance",
    subtitle: `${data.subjects.length} subjects this semester`,
    actions: [linkAction("Details", "/#/attendance", "arrowRight")],
    body: attendanceBody,
  });
  mainCol.append(attendancePanel);

  /* ---------------------------------------------------------- Trend */
  const trendCanvas = el("canvas", { role: "img", "aria-label": "Weekly attendance trend" });
  const trendPanel = panel({
    title: "Attendance trend",
    subtitle: "Your last six weeks, week by week",
    actions: [el("span", { class: "trend-badge" }, "Weekly")],
    body: el("div", {},
      el("div", { class: "chart-box" }, trendCanvas),
      el("div", { class: "chart-legend" },
        el("span", {}, el("span", { class: "legend-dot" }), "Attendance %"),
        el("span", {}, "Classes with no attendance show a gap"))),
  });
  mainCol.append(trendPanel);

  /* ---------------------------------------------------------- Schedule */
  const scheduleBody = data.schedule.length
    ? el("div", { class: "schedule-list" },
      ...data.schedule.map((item) => scheduleRow(item)))
    : el("div", { class: "schedule-empty" }, "No classes today. Check your weekly timetable for the next session.");
  const schedulePanel = panel({
    title: "Today's schedule",
    subtitle: `${data.day_name} · ${data.schedule.length} ${data.schedule.length === 1 ? "class" : "classes"}`,
    actions: [data.schedule.length ? countdownChip(data.schedule) : null,
      linkAction("Open", "/#/schedule", "arrowRight")].filter(Boolean),
    body: scheduleBody,
    footer: el("div", { class: "row-between" },
      el("span", { class: "muted" }, nextClass(data.schedule)
        ? `Next: ${nextClass(data.schedule).subject_code} · ${fmtClock(nextClass(data.schedule).start)}`
        : "All classes for today are done"),
      el("span", { class: "tiny muted" }, `${data.quick_stats.classes_today} classes scheduled`)),
  });
  mainCol.append(schedulePanel);

  /* ---------------------------------------------------------- Assignments */
  const pending = (data.assignments || []).filter((item) =>
    ["pending", "overdue"].includes(item.status)).slice(0, 4);
  const assignmentBody = pending.length
    ? el("div", { class: "schedule-list" }, ...pending.map(assignmentRow))
    : el("div", { class: "state", style: { minHeight: "150px" } },
      el("div", { class: "state__icon" }, iconEl("checkCircle")),
      el("p", { class: "state__title" }, "Nothing due right now"),
      el("p", { class: "state__text" }, "You're up to date on submissions. New work appears here."));
  mainCol.append(panel({
    title: "Assignments due soon",
    subtitle: `${data.pending_assignments} pending in total`,
    actions: [linkAction("All assignments", "/#/assignments", "arrowRight")],
    body: assignmentBody,
  }));

  /* ---------------------------------------------------------- Announcements */
  const noticesBody = el("div", { class: "notice-list" });
  const markAll = el("button", {
    class: "btn btn--ghost btn--sm", type: "button",
    onclick: async () => {
      markAll.disabled = true;
      try {
        await api("/api/student/announcements/read", { method: "POST", body: { all: true } });
        noticesBody.querySelectorAll(".notice__dot").forEach((dot) => {
          dot.classList.remove("notice__dot--unread");
          dot.classList.add("notice__dot--read");
        });
        const unreadLabel = document.querySelector("#announcement-count");
        if (unreadLabel) unreadLabel.textContent = "All read";
        toast("All announcements marked as read.", "success");
      } catch (error) {
        toast(error.message, "error");
      } finally {
        markAll.disabled = false;
      }
    },
  }, iconEl("check"), "Mark all read");

  if (data.announcements.length) {
    data.announcements.forEach((item) => {
      noticesBody.append(el("button", {
        class: "notice", type: "button",
        onclick: () => goTo("/#/announcements"),
      },
        el("div", { class: "notice__head" },
          el("span", { class: `notice__dot ${item.is_read ? "notice__dot--read" : "notice__dot--unread"}` }),
          el("span", { class: "notice__title" }, item.title),
          item.pinned ? el("span", { class: "badge badge--accent" }, "Pinned") : null),
        el("div", { class: "notice__meta" },
          statusBadge(item.priority),
          el("span", {}, item.professor),
          el("span", {}, relativeTime(item.publish_at))),
        el("p", { class: "notice__body" }, item.body)));
    });
  } else {
    noticesBody.append(el("div", { class: "state", style: { minHeight: "160px" } },
      el("div", { class: "state__icon" }, iconEl("megaphone")),
      el("p", { class: "state__title" }, "No announcements yet"),
      el("p", { class: "state__text" }, "Notices from your faculty will appear here.")));
  }

  sideCol.append(panel({
    title: "Announcements",
    subtitle: el("span", { id: "announcement-count" },
      `${data.unread_announcements} unread`) || "",
    actions: data.unread_announcements ? [markAll] : [el("span", { class: "badge badge--success" }, "All read")],
    body: noticesBody,
    footer: el("button", {
      class: "btn btn--ghost btn--sm w-full", type: "button",
      onclick: () => goTo("/#/announcements"),
    }, "View all announcements ", iconEl("arrowRight")),
  }));

  /* ---------------------------------------------------------- Quick stats */
  const quick = data.quick_stats;
  sideCol.append(panel({
    title: "At a glance",
    body: el("div", { class: "quick-grid" },
      quickStat(String(quick.subjects), "Subjects", true),
      quickStat(String(quick.pending_assignments), "Pending assignments"),
      quickStat(String(quick.classes_today), "Classes today"),
      quickStat(String(quick.unread_notifications), "Unread alerts")),
  }));

  const tips = panel({
    title: "Stay on track",
    body: el("div", { class: "stack-sm" },
      el("p", { class: "small muted" }, "Keep every subject above 75% to stay exam-eligible."),
      el("div", { class: "progress" },
        el("div", {
          class: `progress__bar ${overall.below_threshold ? "progress__bar--danger" : "progress__bar--success"}`,
          style: { width: `${Math.min(100, overall.percentage)}%` },
        })),
      el("div", { class: "row-between tiny muted" },
        el("span", {}, "Your attendance"),
        el("span", {}, `${overall.percentage}% / ${threshold}% required`)),
      el("button", {
        class: "btn btn--secondary btn--sm mt-2", type: "button",
        onclick: () => goTo("/#/assignments"),
      }, iconEl("clipboard"), "Check pending work")),
  });
  sideCol.append(tips);

  /* ---------------------------------------------------------- Charts */
  await Promise.all([
    doughnutChart(chartCanvas, { value: overall.percentage, threshold, cutout: "85%" }),
    lineChart(trendCanvas, {
      labels: data.trend.map((item) => item.label),
      values: data.trend.map((item) => item.percentage),
      label: "Attendance",
    }),
    ...[...subjectGrid.querySelectorAll(".subject-tile__chart")].map((wrap) =>
      doughnutChart(wrap.querySelector("canvas"), {
        value: Number(wrap.dataset.value),
        threshold,
        cutout: "72%",
      })),
  ]);
}

function scheduleRow(item) {
  const railColor = item.status === "ongoing" ? "var(--success)"
    : item.status === "completed" ? "var(--border-strong)" : "var(--primary)";
  return el("div", { class: `schedule-item schedule-item--${item.status}` },
    el("div", { class: "schedule-item__time" },
      el("b", {}, fmtClock(item.start)),
      fmtClock(item.end)),
    el("div", { class: "schedule-item__rail", style: { background: railColor } }),
    el("div", { class: "schedule-item__body" },
      el("div", { class: "schedule-item__title" }, item.subject_name),
      el("div", { class: "schedule-item__meta" },
        `${item.subject_code} · ${item.professor} · ${item.room}`)),
    el("div", { class: "schedule-item__status" },
      statusBadge(item.status),
      item.status === "ongoing" ? el("span", { class: "countdown-chip", style: { marginTop: "5px" } }, "Now") : null));
}

function assignmentRow(item) {
  const due = new Date(item.due_date);
  const diff = due.getTime() - Date.now();
  const urgency = item.status === "overdue" ? "danger"
    : diff < 24 * 3600 * 1000 ? "warning" : "info";
  const dueLabel = item.status === "overdue"
    ? `Was due ${relativeTime(item.due_date)}`
    : diff < 86400000 ? `Due today · ${fmtClock(item.due_date.slice(11, 16))}`
    : `Due ${relativeTime(item.due_date)}`;
  return el("div", { class: "schedule-item" },
    el("div", { class: "schedule-item__time" },
      el("b", {}, item.subject_code), el("span", {}, item.max_marks ? `${item.max_marks} marks` : "")),
    el("div", { class: "schedule-item__rail", style: { background: `var(--${urgency === "danger" ? "danger" : urgency === "warning" ? "warning" : "primary"})` } }),
    el("div", { class: "schedule-item__body" },
      el("div", { class: "schedule-item__title" }, item.title),
      el("div", { class: "schedule-item__meta" }, `${item.subject} · ${dueLabel}`)),
    el("div", { class: "schedule-item__status" },
      statusBadge(item.status),
      el("button", {
        class: "btn btn--ghost btn--sm", type: "button",
        onclick: () => goTo("/#/assignments"),
      }, item.status === "overdue" ? "Submit late" : "Open")));
}

function quickStat(value, label, accent = false) {
  return el("div", { class: `quick-stat ${accent ? "quick-stat--accent" : ""}` },
    el("div", { class: "quick-stat__value" }, value),
    el("div", { class: "quick-stat__label" }, label));
}

function linkAction(label, href, iconName) {
  const link = el("a", { class: "btn btn--ghost btn--sm", href },
    el("span", { class: "btn__label" }, label), iconEl(iconName));
  return link;
}
