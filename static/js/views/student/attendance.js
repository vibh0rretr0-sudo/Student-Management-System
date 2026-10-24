import { api } from "../../core/api.js";
import { barChart, disposeCharts, lineChart } from "../../core/charts.js";
import {
  callout, el, errorPanel, fmtDate, formField, iconEl, loadingView, pager,
  setFieldError, statusBadge, toast,
} from "../../core/ui.js";
import { getThreshold } from "../../runtime/session.js";
import { dataTable } from "../../components/table.js";
import { pageHeader, panel } from "../../components/page.js";

export const title = "Attendance";

function isoDate(date) {
  return date.toISOString().slice(0, 10);
}

function stat(value, label, variant = "") {
  return el("div", { class: `att-stat ${variant ? `att-stat--${variant}` : ""}`.trim() },
    el("div", { class: "att-stat__value" }, value),
    el("div", { class: "att-stat__label" }, label));
}

export async function render(container, { params } = {}) {
  const today = new Date();
  const defaultFrom = new Date(today.getTime() - 90 * 86400000);
  let from = params?.get("from") || isoDate(defaultFrom);
  let to = params?.get("to") || isoDate(today);
  let page = 1;
  const threshold = getThreshold();

  async function load({ showSkeleton = true } = {}) {
    disposeCharts();
    container.innerHTML = "";
    if (showSkeleton) container.append(loadingView("table"));
    let response;
    try {
      const query = new URLSearchParams({ from, to, page: String(page), per_page: "15" });
      response = await api(`/api/student/attendance?${query}`);
    } catch (error) {
      container.innerHTML = "";
      container.append(errorPanel(error.message, () => load()));
      return;
    }
    if (!container.isConnected && !document.body.contains(container)) return;
    paint(response.data, response.meta);
  }

  function paint(data, meta) {
    container.innerHTML = "";
    const overall = data.overall;

    container.append(pageHeader({
      title: "Attendance",
      subtitle: "Every class, subject and percentage for the selected period.",
    }));

    /* Filters */
    const fromField = formField({
      label: "From", name: "from", type: "date", value: from,
    });
    const toField = formField({ label: "To", name: "to", type: "date", value: to });
    fromField.input.max = to;
    toField.input.max = isoDate(new Date());
    const apply = el("button", { class: "btn btn--primary btn--sm", type: "submit" },
      el("span", { class: "spinner", "aria-hidden": "true" }),
      el("span", { class: "btn__label" }, "Apply range"));
    const reset = el("button", { class: "btn btn--ghost btn--sm", type: "button" },
      iconEl("refresh"), "Last 90 days");
    const filterForm = el("form", { class: "filters", novalidate: true },
      fromField.wrapper, toField.wrapper,
      el("div", { class: "filters__actions" }, reset, apply));
    filterForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const nextFrom = fromField.input.value;
      const nextTo = toField.input.value;
      if (!nextFrom || !nextTo) {
        toast("Choose both a start and end date.", "warning");
        return;
      }
      if (nextFrom > nextTo) {
        setFieldError(toField.input, "The end date must be after the start date.");
        return;
      }
      setFieldError(toField.input, "");
      from = nextFrom;
      to = nextTo;
      page = 1;
      load();
    });
    reset.addEventListener("click", () => {
      from = isoDate(new Date(Date.now() - 90 * 86400000));
      to = isoDate(new Date());
      page = 1;
      load();
    });
    container.append(el("section", { class: "panel" }, filterForm));

    /* Summary */
    const warn = overall.below_threshold
      ? callout(
        `You're below the ${threshold}% requirement. Attend ${overall.need_attend} more class${overall.need_attend === 1 ? "" : "es"} in a row to recover.`,
        "danger", "alert")
      : callout(
        `You're above the ${threshold}% requirement and can still miss ${overall.can_miss} class${overall.can_miss === 1 ? "" : "es"} this period.`,
        "success", "shield");

    const summary = el("div", { class: "panel" },
      el("div", { class: "panel__body stack" },
        el("div", { class: "att-stats", style: { gridTemplateColumns: "repeat(4, 1fr)" } },
          stat(`${overall.percentage}%`, "Overall attendance", overall.below_threshold ? "danger" : "success"),
          stat(String(overall.attended), "Classes attended", "success"),
          stat(String(overall.held), "Classes held", ""),
          stat(String(overall.below_threshold ? overall.need_attend : overall.can_miss),
            overall.below_threshold ? "Classes to recover" : "Classes you can miss", "")),
        warn));
    container.append(summary);

    if (!data.subjects.length) {
      container.append(el("section", { class: "panel" },
        el("div", { class: "state" },
          el("div", { class: "state__icon" }, iconEl("chart")),
          el("p", { class: "state__title" }, "No attendance in this range"),
          el("p", { class: "state__text" },
            "Try widening the date range, or check back after your next class is marked."),
          el("div", { class: "state__actions" },
            el("button", {
              class: "btn btn--secondary btn--sm", type: "button",
              onclick: () => {
                from = isoDate(new Date(Date.now() - 90 * 86400000));
                to = isoDate(new Date());
                page = 1;
                load();
              },
            }, "Reset to last 90 days")))));
      return;
    }

    /* Charts */
    const barCanvas = el("canvas", { role: "img", "aria-label": "Attendance by subject" });
    const lineCanvas = el("canvas", { role: "img", "aria-label": "Monthly attendance trend" });
    container.append(el("div", { class: "two-col" },
      panel({
        title: "By subject",
        subtitle: `${threshold}% is the eligibility line`,
        body: el("div", { class: "chart-box" }, barCanvas),
        footer: el("div", { class: "chart-legend" },
          el("span", {}, el("span", { class: "legend-dot", style: { background: "var(--success)" } }), "Above 75%"),
          el("span", {}, el("span", { class: "legend-dot", style: { background: "var(--warning)" } }), "65–75%"),
          el("span", {}, el("span", { class: "legend-dot", style: { background: "var(--danger)" } }), "Below 65%")),
      }),
      panel({
        title: "Monthly trend",
        subtitle: "Percentage attended per month",
        body: el("div", { class: "chart-box" }, lineCanvas),
      })));

    /* Subject table */
    const subjectTable = dataTable({
      caption: "Subject-wise attendance summary",
      initialSort: { key: "percentage", direction: "desc" },
      columns: [
        { key: "code", label: "Code", sortable: true, render: (row) =>
          el("span", { class: "strong" }, row.code) },
        { key: "name", label: "Subject", sortable: true },
        { key: "professor", label: "Professor", sortable: true,
          render: (row) => row.professor || "—" },
        { key: "held", label: "Held", align: "right", sortable: true },
        { key: "attended", label: "Attended", align: "right", sortable: true },
        { key: "late", label: "Late", align: "right", sortable: true },
        { key: "absent", label: "Absent", align: "right", sortable: true },
        {
          key: "percentage", label: "Attendance", align: "right", sortable: true,
          render: (row) => el("div", { style: { minWidth: "130px" } },
            el("div", { class: "row-between", style: { marginBottom: "5px" } },
              el("span", { class: `badge badge--${row.percentage >= threshold ? "success" : row.percentage >= threshold - 10 ? "warning" : "danger"}` },
                `${row.percentage}%`),
              el("span", { class: "tiny muted" }, `${row.attended}/${row.held}`)),
            el("div", { class: "progress" },
              el("div", {
                class: `progress__bar ${row.percentage >= threshold ? "progress__bar--success" : row.percentage >= threshold - 10 ? "progress__bar--warning" : "progress__bar--danger"}`,
                style: { width: `${Math.min(100, row.percentage)}%` },
              }))),
        },
      ],
      rows: data.subjects,
      empty: "No subject attendance in this range.",
    });
    container.append(el("section", { class: "panel mt-4" },
      el("div", { class: "panel__head" },
        el("div", {},
          el("h3", { class: "panel__title" }, "Subject summary"),
          el("p", { class: "panel__sub" }, "Sort any column to compare.")
        )
      ),
      el("div", { class: "panel__body" }, subjectTable)));

    /* Records */
    const recordsPanel = el("section", { class: "panel mt-4" });
    const recordHead = el("div", { class: "panel__head" },
      el("div", {},
        el("h3", { class: "panel__title" }, "Class records"),
        el("p", { class: "panel__sub" }, "Newest first.")));
    recordsPanel.append(recordHead);
    const recordBody = el("div", { class: "panel__body" });
    recordsPanel.append(recordBody);

    if (data.records.length) {
      const recordsTable = dataTable({
        caption: "Attendance records for the selected range",
        columns: [
          { key: "date", label: "Date", sortable: true, render: (row) =>
            el("span", { class: "strong" }, fmtDate(row.date)) },
          { key: "subject", label: "Subject", sortable: true, render: (row) =>
            el("div", {},
              el("div", { class: "strong" }, row.subject_name),
              el("div", { class: "tiny muted" }, row.subject_code)) },
          { key: "professor", label: "Marked by", render: (row) => row.professor || "—" },
          { key: "status", label: "Status", align: "right", sortable: true,
            render: (row) => statusBadge(row.status) },
        ],
        rows: data.records,
        initialSort: null,
      });
      recordBody.append(recordsTable);
      recordBody.append(pager({
        page: meta.page, pages: meta.pages, total: meta.total, perPage: meta.per_page,
        onPage: (nextPage) => { page = nextPage; load({ showSkeleton: false }); },
      }));
    } else {
      recordBody.append(el("div", { class: "state" },
        el("div", { class: "state__icon" }, iconEl("calendar")),
        el("p", { class: "state__title" }, "No individual records"),
        el("p", { class: "state__text" }, "There are no attendance rows in this range.")));
    }
    container.append(recordsPanel);

    barChart(barCanvas, {
      labels: data.subjects.map((item) => item.code),
      values: data.subjects.map((item) => item.percentage),
      threshold,
    });
    lineChart(lineCanvas, {
      labels: data.monthly_trend.map((item) => item.label),
      values: data.monthly_trend.map((item) => item.percentage),
      label: "Monthly attendance",
    });
  }

  await load();
}
