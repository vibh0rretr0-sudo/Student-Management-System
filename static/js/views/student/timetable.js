import { api } from "../../core/api.js";
import {
  el, errorPanel, fmtClock, fmtDate, iconEl, loadingView, toast,
} from "../../core/ui.js";
import { pageHeader, panel } from "../../components/page.js";

export const title = "Timetable";

export async function render(container) {
  container.append(loadingView());
  let data;
  try {
    data = (await api("/api/student/timetable")).data;
  } catch (error) {
    container.innerHTML = "";
    container.append(errorPanel(error.message, () => {
      container.innerHTML = "";
      render(container);
    }));
    return;
  }

  container.innerHTML = "";
  const printButton = el("button", { class: "btn btn--secondary btn--sm no-print", type: "button" },
    iconEl("printer"), "Print timetable");
  printButton.addEventListener("click", () => window.print());

  container.append(pageHeader({
    title: "Timetable",
    subtitle: `${data.batch} · Monday to Saturday, four periods a day`,
    actions: [printButton],
  }));

  container.append(el("div", { class: "print-header" },
    el("h1", {}, "JECRC Weekly Timetable"),
    el("p", {}, `${data.batch} · Semester 1 · Printed ${fmtDate(new Date().toISOString())}`)));

  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  const todayNumber = now.getDay() === 0 ? 7 : now.getDay();
  const grid = el("div", { class: "timetable" });
  const monday = new Date(now);
  monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));

  data.days.forEach((day) => {
    const dayDate = new Date(monday);
    dayDate.setDate(monday.getDate() + (day.day_number - 1));
    const isToday = day.day_number === todayNumber;
    const column = el("section", {
      class: `tt-day ${isToday ? "is-today" : ""}`.trim(),
      "aria-label": `${day.day} timetable`,
    });
    column.append(el("div", { class: "tt-day__head" },
      el("span", { class: "tt-day__name" }, isToday ? `${day.day} · Today` : day.day),
      el("span", { class: "tt-day__date" }, fmtDate(dayDate, { withYear: false }))));

    if (!day.classes.length) {
      column.append(el("div", { class: "tt-slot tt-slot--empty" }, "No classes"));
      grid.append(column);
      return;
    }

    day.classes.forEach((item) => {
      const [startHour, startMin] = item.start.split(":").map(Number);
      const [endHour, endMin] = item.end.split(":").map(Number);
      const start = startHour * 60 + startMin;
      const end = endHour * 60 + endMin;
      const isNow = isToday && nowMinutes >= start && nowMinutes < end;
      const slot = el("article", {
        class: `tt-slot ${isNow ? "is-now" : ""}`.trim(),
        "aria-label": `${item.subject_name}, ${fmtClock(item.start)} to ${fmtClock(item.end)}, room ${item.room}`,
      });
      if (isNow) slot.append(el("span", { class: "tt-slot__now" }, "Now"));
      slot.append(
        el("div", { class: "tt-slot__code" }, item.subject_code),
        el("div", { class: "tt-slot__subject" }, item.subject_name),
        el("div", { class: "tt-slot__meta" },
          `${fmtClock(item.start)} – ${fmtClock(item.end)}`),
        el("div", { class: "tt-slot__meta" }, `${item.room} · ${item.professor}`),
      );
      column.append(slot);
    });
    grid.append(column);
  });

  container.append(panel({
    title: "Weekly grid",
    subtitle: "Your current slot pulses green. Today's column is highlighted.",
    actions: [el("span", { class: "badge badge--primary" }, `${data.days.reduce((sum, day) => sum + day.classes.length, 0)} periods`)],
    body: el("div", { class: "tt-scroll" }, grid),
  }));

  const legend = el("div", { class: "chart-legend", style: { padding: "12px 0 0" } },
    el("span", {}, el("span", { class: "legend-dot", style: { background: "var(--success)" } }), "Happening now"),
    el("span", {}, el("span", { class: "legend-dot", style: { background: "var(--primary-soft)" } }), "Today"),
    el("span", {}, "Use Print for a clean paper copy or PDF."));
  container.append(legend);

  const refreshNotice = el("button", {
    class: "btn btn--ghost btn--sm mt-3 no-print", type: "button",
  }, iconEl("refresh"), "Looking at a stale view? Refresh");
  refreshNotice.addEventListener("click", () => {
    toast("Timetable refreshed.", "info");
    container.innerHTML = "";
    render(container);
  });
  container.append(refreshNotice);
}
