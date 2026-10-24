import { el, iconEl, fmtClock, statusBadge, goTo } from "../core/ui.js";

export function nextClass(classes) {
  return classes.find((item) => item.status !== "completed") || null;
}

export function countdownText(next, now = new Date()) {
  if (!next) return null;
  const [hours, minutes] = String(next.start).split(":").map(Number);
  const start = new Date(now);
  start.setHours(hours, minutes, 0, 0);
  const diff = Math.round((start - now) / 60000);
  if (next.status === "ongoing") {
    const [endHours, endMinutes] = String(next.end).split(":").map(Number);
    const end = new Date(now);
    end.setHours(endHours, endMinutes, 0, 0);
    const left = Math.max(0, Math.round((end - now) / 60000));
    return left <= 1 ? "Ending now" : `${left} min left`;
  }
  if (diff <= 0) return "Starting now";
  if (diff < 60) return `in ${diff} min`;
  const h = Math.floor(diff / 60);
  const m = diff % 60;
  return `in ${h} h${m ? ` ${m} min` : ""}`;
}

export function countdownChip(classes) {
  const next = nextClass(classes);
  if (!next) return el("span", { class: "badge badge--neutral" }, "Day complete");
  const chip = el("span", { class: "countdown-chip" },
    el("span", { class: "dot-pulse", "aria-hidden": "true" }),
    el("span", {}, ""));
  const update = () => {
    const label = countdownText(next);
    chip.lastChild.textContent = next.status === "ongoing"
      ? `${label} · ${next.subject_code}`
      : `Next class ${label}`;
  };
  update();
  const timer = window.setInterval(update, 30000);
  window.addEventListener("view:unmount", () => window.clearInterval(timer), { once: true });
  return chip;
}

export function scheduleTimeline(classes, { role = "student", actionsFor = null } = {}) {
  if (!classes || !classes.length) {
    return el("div", { class: "state" },
      el("div", { class: "state__icon" }, iconEl("calendar")),
      el("p", { class: "state__title" }, "No classes today"),
      el("p", { class: "state__text" },
        role === "professor"
          ? "You have no teaching slots scheduled for today. Enjoy the breathing room."
          : "You have no classes scheduled today. Use the free time to get ahead on assignments."));
  }

  const timeline = el("div", { class: "timeline" });
  classes.forEach((item) => {
    const title = role === "professor"
      ? `${item.subject_name}`
      : `${item.subject_name}`;
    const metaParts = role === "professor"
      ? [`${item.batch_name} (${item.batch_code})`, item.room]
      : [item.professor, item.room];
    const card = el("div", { class: "timeline__card" });
    const top = el("div", { class: "row-between" },
      el("div", {},
        el("div", { class: "timeline__title" }, title),
        el("div", { class: "timeline__meta" },
          `${item.subject_code} · ${metaParts.filter(Boolean).join(" · ")}`)),
      statusBadge(item.status));
    card.append(top);
    if (role === "professor" && item.batch_id && item.subject_id) {
      const action = el("button", {
        class: "btn btn--secondary btn--sm mt-3", type: "button",
      }, iconEl("attendance"), "Mark attendance");
      action.addEventListener("click", () => {
        goTo(`/#/attendance?batch_id=${item.batch_id}&subject_id=${item.subject_id}`);
      });
      card.append(action);
    }
    const wrapper = el("div", {
      class: `timeline__item timeline__item--${item.status}`,
    });
    wrapper.append(el("div", { class: "timeline__dot", "aria-hidden": "true" }));
    wrapper.append(el("div", { class: "timeline__time" },
      `${fmtClock(item.start)} – ${fmtClock(item.end)}`));
    wrapper.append(card);
    timeline.append(wrapper);
  });
  return timeline;
}
