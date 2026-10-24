import { api } from "../../core/api.js";
import {
  el, errorPanel, fmtClock, fmtDate, iconEl, loadingView, relativeTime,
  statusBadge, goTo,
} from "../../core/ui.js";
import { panel } from "../../components/page.js";
import { countdownChip } from "../../components/schedule.js";

export const title = "Overview";

export async function render(container) {
  container.append(loadingView());
  let data;
  try {
    data = (await api("/api/professor/overview")).data;
  } catch (error) {
    container.innerHTML = "";
    container.append(errorPanel(error.message, () => {
      container.innerHTML = "";
      render(container);
    }));
    return;
  }

  container.innerHTML = "";
  const now = new Date();
  const greeting = now.getHours() < 12 ? "Good morning"
    : now.getHours() < 17 ? "Good afternoon" : "Good evening";

  container.append(el("section", { class: "greeting is-entering" },
    el("span", { class: "greeting__eyebrow" }, iconEl("spark"),
      ` ${fmtDate(data.today, { weekday: true })} · ${data.professor.department}`),
    el("h2", { class: "greeting__title" },
      `${greeting}, `, el("span", { class: "accent" }, data.professor.name.replace(/^(Dr\.|Prof\.)\s*/, "").split(" ")[0])),
    el("p", { class: "muted", style: { fontSize: "var(--text-base)", marginBottom: "12px" } },
      "Your classes, submissions and notices at a glance."),
    el("div", { class: "greeting__meta" },
      el("span", { class: "chip" }, data.professor.designation),
      el("span", { class: "chip" }, data.professor.employee_id),
      el("span", { class: "chip" }, `${data.batches_count} batches · ${data.students_count} students`))));

  const grid = el("div", { class: "dashboard-grid" });
  const main = el("div", { class: "dash-main" });
  const side = el("div", { class: "dash-side" });
  grid.append(main, side);
  container.append(grid);

  /* ---------------------------------------------------------- Batch cards */
  const cards = el("div", { class: "batch-grid" });
  data.batch_cards.slice(0, 4).forEach((card) => {
    cards.append(el("article", { class: "batch-card" },
      el("div", { class: "batch-card__top" },
        el("div", {},
          el("div", { class: "batch-card__name" }, card.batch_name),
          el("div", { class: "batch-card__code" }, `${card.batch_code} · ${card.subject_code}`)),
        el("span", { class: `badge badge--${card.average_attendance >= 75 ? "success" : "warning"}` },
          `${card.average_attendance}% avg`)),
      el("div", { class: "batch-card__stats" },
        el("div", { class: "batch-card__stat" },
          el("b", {}, String(card.students)), el("span", {}, "Students")),
        el("div", { class: "batch-card__stat" },
          el("b", {}, card.subject_name.length > 22 ? `${card.subject_name.slice(0, 22)}…` : card.subject_name),
          el("span", {}, "Subject"))),
      el("div", { class: "cluster", style: { marginTop: "14px" } },
        el("button", {
          class: "btn btn--secondary btn--sm", type: "button",
          onclick: () => goTo(`/#/attendance?batch_id=${card.batch_id}&subject_id=${card.subject_id}`),
        }, iconEl("attendance"), "Mark attendance"),
        el("button", {
          class: "btn btn--ghost btn--sm", type: "button",
          onclick: () => goTo(`/#/assignments?batch_id=${card.batch_id}`),
        }, iconEl("clipboard"), "Assignments"))));
  });
  if (!data.batch_cards.length) {
    cards.append(el("div", { class: "state" },
      el("p", { class: "state__title" }, "No teaching load assigned yet")));
  }

  main.append(panel({
    title: "Your batches",
    subtitle: "Attendance averages update as you mark classes.",
    actions: [el("button", {
      class: "btn btn--ghost btn--sm", type: "button",
      onclick: () => goTo("/#/batches"),
    }, "View all ", iconEl("arrowRight"))],
    body: cards,
  }));

  /* ---------------------------------------------------------- Schedule */
  const scheduleBody = data.schedule.length
    ? el("div", { class: "schedule-list" }, ...data.schedule.map((item) =>
      el("div", { class: `schedule-item schedule-item--${item.status}` },
        el("div", { class: "schedule-item__time" },
          el("b", {}, fmtClock(item.start)), fmtClock(item.end)),
        el("div", {
          class: "schedule-item__rail",
          style: { background: item.status === "ongoing" ? "var(--success)" : item.status === "completed" ? "var(--border-strong)" : "var(--primary)" },
        }),
        el("div", { class: "schedule-item__body" },
          el("div", { class: "schedule-item__title" }, item.subject_name),
          el("div", { class: "schedule-item__meta" },
            `${item.subject_code} · ${item.batch_name} (${item.batch_code}) · ${item.room}`)),
        el("div", { class: "cluster gap-2" },
          statusBadge(item.status),
          el("button", {
            class: "btn btn--secondary btn--sm", type: "button",
            onclick: () => goTo(`/#/attendance?batch_id=${item.batch_id}&subject_id=${item.subject_id}`),
          }, "Mark")))))
    : el("div", { class: "schedule-empty" }, "No teaching slots today.");

  main.append(panel({
    title: "Today's teaching schedule",
    subtitle: `${data.day_name} · ${data.schedule.length} ${data.schedule.length === 1 ? "class" : "classes"}`,
    actions: [data.schedule.length ? countdownChip(data.schedule) : null,
      el("button", {
        class: "btn btn--ghost btn--sm", type: "button",
        onclick: () => goTo("/#/schedule"),
      }, "Timeline ", iconEl("arrowRight"))].filter(Boolean),
    body: scheduleBody,
  }));

  /* ---------------------------------------------------------- Awaiting review */
  const awaiting = (data.assignments || []).filter((item) => item.submitted > item.graded);
  const reviewBody = awaiting.length
    ? el("div", { class: "stack-sm" }, ...awaiting.slice(0, 4).map((item) =>
      el("div", { class: "course-row", style: { padding: "8px 0" } },
        el("div", { class: "course-row__main" },
          el("span", { class: "avatar avatar--sm" }, String(item.submitted - item.graded)),
          el("div", { style: { minWidth: "0" } },
            el("div", { class: "strong small truncate" }, item.title),
            el("div", { class: "tiny muted" },
              `${item.subject_code} · ${item.batch_code} · ${item.submitted - item.graded} to grade`))),
        el("button", {
          class: "btn btn--secondary btn--sm", type: "button",
          onclick: () => goTo("/#/assignments"),
        }, "Review"))))
    : el("div", { class: "state", style: { minHeight: "140px" } },
      el("div", { class: "state__icon" }, iconEl("checkCircle")),
      el("p", { class: "state__title" }, "Nothing waiting"),
      el("p", { class: "state__text" }, "All submitted work has been graded."));

  main.append(panel({
    title: "Awaiting review",
    subtitle: `${data.awaiting_review} submission${data.awaiting_review === 1 ? "" : "s"} across your assignments`,
    actions: [el("button", {
      class: "btn btn--ghost btn--sm", type: "button",
      onclick: () => goTo("/#/assignments"),
    }, "Open assignments ", iconEl("arrowRight"))],
    body: reviewBody,
  }));

  /* ---------------------------------------------------------- Recent submissions */
  if (data.recent_submissions.length) {
    const recent = el("div", { class: "stack-sm" }, ...data.recent_submissions.map((item) =>
      el("div", { class: "row-between", style: { padding: "4px 0" } },
        el("div", { style: { minWidth: "0" } },
          el("div", { class: "small strong truncate" }, item.student),
          el("div", { class: "tiny muted" }, `${item.assignment} · ${relativeTime(item.submitted_at)}`)),
        statusBadge(item.status))));
    main.append(panel({
      title: "Recent submissions",
      body: recent,
    }));
  }

  /* ---------------------------------------------------------- Announcements */
  const newNotice = el("button", { class: "btn btn--primary btn--sm", type: "button" },
    iconEl("plus"), "New");
  newNotice.addEventListener("click", () => goTo("/#/announcements?new=1"));

  const noticeList = el("div", { class: "notice-list" });
  if (data.announcements.length) {
    data.announcements.forEach((item) => {
      noticeList.append(el("button", {
        class: "notice", type: "button",
        onclick: () => goTo("/#/announcements"),
      },
        el("div", { class: "notice__head" },
          el("span", { class: `notice__dot ${item.status === "scheduled" ? "notice__dot--read" : "notice__dot--unread"}` }),
          el("span", { class: "notice__title" }, item.title),
          item.pinned ? el("span", { class: "badge badge--accent" }, "Pinned") : null),
        el("div", { class: "notice__meta" },
          statusBadge(item.priority),
          el("span", {}, item.status === "scheduled" ? "Scheduled" : `${item.read_count} read`),
          el("span", {}, relativeTime(item.publish_at))),
        el("p", { class: "notice__body" }, item.body)));
    });
  } else {
    noticeList.append(el("div", { class: "state", style: { minHeight: "150px" } },
      el("div", { class: "state__icon" }, iconEl("megaphone")),
      el("p", { class: "state__title" }, "No notices yet"),
      el("p", { class: "state__text" }, "Post a notice to reach one or all of your batches.")));
  }
  side.append(panel({
    title: "Your announcements",
    actions: [newNotice],
    body: noticeList,
    footer: el("button", {
      class: "btn btn--ghost btn--sm w-full", type: "button",
      onclick: () => goTo("/#/announcements"),
    }, "Manage announcements ", iconEl("arrowRight")),
  }));

  /* ---------------------------------------------------------- Low attendance */
  const lowBody = data.low_attendance.length
    ? el("div", { class: "stack-sm" }, ...data.low_attendance.map((item) =>
      el("div", { class: "row-between", style: { gap: "8px" } },
        el("div", { style: { minWidth: "0" } },
          el("div", { class: "small strong truncate" }, item.name),
          el("div", { class: "tiny muted" }, `${item.roll_no} · ${item.batch}`)),
        el("span", { class: "badge badge--danger" }, `${item.percentage}%`))))
    : el("div", { class: "callout callout--success" }, iconEl("shield"),
      el("span", {}, "Every student in your batches is above 75%."));
  side.append(panel({
    title: "Low attendance",
    subtitle: "Below the 75% eligibility line",
    actions: [el("button", {
      class: "btn btn--ghost btn--sm", type: "button",
      onclick: () => goTo("/#/batches"),
    }, "Batches")],
    body: lowBody,
  }));

  /* ---------------------------------------------------------- Quick stats */
  const quick = data.quick_stats;
  side.append(panel({
    title: "At a glance",
    body: el("div", { class: "quick-grid" },
      quickStat(String(quick.classes_today), "Classes today", true),
      quickStat(String(quick.students), "Students"),
      quickStat(String(quick.awaiting_review), "To review"),
      quickStat(String(quick.batches), "Batches")),
  }));
}

function quickStat(value, label, accent = false) {
  return el("div", { class: `quick-stat ${accent ? "quick-stat--accent" : ""}` },
    el("div", { class: "quick-stat__value" }, value),
    el("div", { class: "quick-stat__label" }, label));
}
