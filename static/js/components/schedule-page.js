import { api } from "../core/api.js";
import {
  el, fmtDate, iconEl, loadingView, errorPanel, goTo,
} from "../core/ui.js";
import { pageHeader, panel } from "./page.js";
import { countdownChip, scheduleTimeline } from "./schedule.js";

export async function renderSchedulePage(container, role) {
  container.append(loadingView());
  let data;
  try {
    data = (await api(`/api/${role}/schedule/today`)).data;
  } catch (error) {
    container.innerHTML = "";
    container.append(errorPanel(error.message, () => {
      container.innerHTML = "";
      renderSchedulePage(container, role);
    }));
    return;
  }

  container.innerHTML = "";
  const action = el("button", { class: "btn btn--secondary btn--sm", type: "button" },
    iconEl(role === "student" ? "calendar" : "layers"),
    role === "student" ? "Full timetable" : "My batches");
  action.addEventListener("click", () => {
    goTo(role === "student" ? "/#/timetable" : "/#/batches");
  });

  container.append(pageHeader({
    title: "Today's Schedule",
    subtitle: `${data.day_name}, ${fmtDate(data.date)} · ${data.classes.length} ${data.classes.length === 1 ? "class" : "classes"}`,
    actions: [action],
  }));

  const heading = el("div", { class: "cluster" },
    el("span", { class: "chip" }, data.day_name),
    el("span", { class: "chip" }, `${data.classes.length} scheduled`));
  if (data.classes.length) heading.append(countdownChip(data.classes));

  container.append(panel({
    title: "Timeline",
    subtitle: "Ongoing and upcoming classes are highlighted as the day progresses.",
    actions: [heading],
    body: scheduleTimeline(data.classes, { role }),
  }));
}
