import { api } from "../../core/api.js";
import {
  el, errorPanel, iconEl, loadingView, openDrawer, toast,
} from "../../core/ui.js";
import { dataTable } from "../../components/table.js";
import { pageHeader, panel } from "../../components/page.js";
import { goTo } from "../../core/ui.js";

export const title = "My Batches";

export async function render(container) {
  container.append(loadingView("table"));
  let data;
  try {
    data = (await api("/api/professor/batches")).data;
  } catch (error) {
    container.innerHTML = "";
    container.append(errorPanel(error.message, () => {
      container.innerHTML = "";
      render(container);
    }));
    return;
  }

  container.innerHTML = "";
  container.append(pageHeader({
    title: "My Batches",
    subtitle: "Everything you teach this semester, with live attendance health.",
  }));

  if (!data.batches.length) {
    container.append(el("section", { class: "panel" },
      el("div", { class: "state" },
        el("div", { class: "state__icon" }, iconEl("layers")),
        el("p", { class: "state__title" }, "No batches assigned"),
        el("p", { class: "state__text" }, "Contact the academic office if this looks wrong."))));
    return;
  }

  const grid = el("div", { class: "batch-grid" });
  data.batches.forEach((batch) => {
    const subjects = el("div", { class: "batch-card__subjects" },
      ...batch.subjects.map((subject) => el("span", { class: "chip" }, `${subject.code} · ${subject.name}`)));
    const card = el("article", { class: "batch-card" },
      el("div", { class: "batch-card__top" },
        el("div", {},
          el("div", { class: "batch-card__name" }, batch.name),
          el("div", { class: "batch-card__code" }, `${batch.code} · ${batch.branch}`)),
        el("span", { class: "badge badge--neutral" }, `Sem ${batch.semester}`)),
      el("div", { class: "batch-card__stats" },
        el("div", { class: "batch-card__stat" },
          el("b", {}, String(batch.students)), el("span", {}, "Students")),
        el("div", { class: "batch-card__stat" },
          el("b", {}, String(batch.subjects.length)), el("span", {}, "Subjects")),
        el("div", { class: "batch-card__stat" },
          el("b", { class: batch.low_attendance ? "text-danger" : "" },
            String(batch.low_attendance)),
          el("span", {}, "Below 75%"))),
      subjects,
      el("div", { class: "cluster", style: { marginTop: "14px" } },
        el("button", {
          class: "btn btn--secondary btn--sm", type: "button",
          onclick: () => openRoster(batch),
        }, iconEl("users"), "View roster"),
        batch.subjects[0] ? el("button", {
          class: "btn btn--primary btn--sm", type: "button",
          onclick: () => goTo(`/#/attendance?batch_id=${batch.id}&subject_id=${batch.subjects[0].id}`),
        }, iconEl("attendance"), "Mark attendance") : null));
    grid.append(card);
  });

  container.append(grid);

  function openRoster(batch) {
    const body = el("div", { class: "stack" });
    const loading = el("div", { class: "stack-sm" },
      el("div", { class: "skeleton skeleton--line" }),
      el("div", { class: "skeleton skeleton--line" }),
      el("div", { class: "skeleton skeleton--line" }));
    body.append(loading);

    const search = el("input", {
      class: "input", type: "search", placeholder: "Filter by name or roll number…",
      "aria-label": "Filter roster",
    });
    const lowOnly = el("input", { type: "checkbox" });
    let students = [];

    const drawer = openDrawer({
      title: batch.name,
      subtitle: `${batch.code} · ${batch.students} students`,
      body,
      footer: [{ label: "Close", variant: "secondary" }],
    });

    async function loadRoster() {
      try {
        const response = await api(`/api/professor/students?batch_id=${batch.id}`);
        students = response.data.items || [];
      } catch (error) {
        body.innerHTML = "";
        body.append(errorPanel(error.message, loadRoster));
        return;
      }
      paintRoster();
    }

    function paintRoster() {
      body.innerHTML = "";
      const filters = el("div", { class: "filters", style: { padding: "0 0 12px" } },
        el("div", { class: "search-field" }, iconEl("search"), search),
        el("label", { class: "check", style: { paddingTop: "8px" } },
          lowOnly, el("span", {}, "Below 75% only")));
      const host = el("div", {});

      const renderRows = () => {
        host.innerHTML = "";
        const query = search.value.trim().toLowerCase();
        const rows = students.filter((student) => {
          if (lowOnly.checked && student.percentage >= 75) return false;
          if (!query) return true;
          return `${student.name} ${student.roll_no}`.toLowerCase().includes(query);
        });
        if (!rows.length) {
          host.append(el("div", { class: "state" },
            el("div", { class: "state__icon" }, iconEl("users")),
            el("p", { class: "state__title" }, "No students match"),
            el("p", { class: "state__text" }, "Try clearing the filter.")));
          return;
        }
        host.append(dataTable({
          initialSort: { key: "roll_no", direction: "asc" },
          columns: [
            { key: "roll_no", label: "Roll", sortable: true, render: (row) => el("span", { class: "strong" }, row.roll_no) },
            { key: "name", label: "Student", sortable: true },
            { key: "held", label: "Classes", align: "right", sortable: true },
            { key: "attended", label: "Attended", align: "right", sortable: true },
            {
              key: "percentage", label: "Attendance", align: "right", sortable: true,
              render: (row) => el("span", {
                class: `badge badge--${row.percentage >= 75 ? "success" : row.percentage >= 65 ? "warning" : "danger"}`,
              }, `${row.percentage}%`),
            },
          ],
          rows,
          empty: "No students.",
        }));
      };
      search.addEventListener("input", renderRows);
      lowOnly.addEventListener("change", renderRows);
      body.append(filters, host);
      renderRows();
    }

    loadRoster();
    return drawer;
  }
}
