import { api } from "../../core/api.js";
import {
  busyButton, callout, confirmDialog, el, errorPanel, fmtDate, iconEl,
  loadingView, toast,
} from "../../core/ui.js";
import { pageHeader, panel } from "../../components/page.js";

export const title = "Attendance";

function isoDate(date) {
  return date.toISOString().slice(0, 10);
}

export async function render(container, { params } = {}) {
  container.append(loadingView("table"));

  const state = {
    batchId: Number(params?.get("batch_id")) || null,
    subjectId: Number(params?.get("subject_id")) || null,
    date: params?.get("date") || isoDate(new Date()),
    dirty: false,
  };

  async function fetchSheet() {
    const query = new URLSearchParams({ date: state.date });
    if (state.batchId) query.set("batch_id", String(state.batchId));
    if (state.subjectId) query.set("subject_id", String(state.subjectId));
    return api(`/api/professor/attendance?${query}`);
  }

  async function load() {
    let response;
    try {
      response = await fetchSheet();
    } catch (error) {
      container.innerHTML = "";
      container.append(errorPanel(error.message, () => {
        container.innerHTML = "";
        render(container, { params });
      }));
      return;
    }
    state.batchId = response.data.batch_id;
    state.subjectId = response.data.subject_id;
    state.date = response.data.date;
    paint(response.data);
  }

  function paint(data) {
    if (!data.pairs.length) {
      container.innerHTML = "";
      container.append(pageHeader({ title: "Attendance" }));
      container.append(el("section", { class: "panel" },
        el("div", { class: "state" },
          el("div", { class: "state__icon" }, iconEl("layers")),
          el("p", { class: "state__title" }, "No classes assigned"),
          el("p", { class: "state__text" }, "You need at least one batch-subject mapping to mark attendance."))));
      return;
    }

    let dirty = false;
    const wasUnmarked = data.summary.marked < data.roster.length;
    const roster = data.roster.map((student) => ({
      ...student,
      status: student.status || "present",
    }));

    container.innerHTML = "";

    const batches = [];
    data.pairs.forEach((pair) => {
      if (!batches.some((batch) => batch.id === pair.batch_id)) {
        batches.push({ id: pair.batch_id, name: `${pair.batch_name} (${pair.batch_code})` });
      }
    });

    const batchSelect = el("select", { class: "select", "aria-label": "Batch" },
      ...batches.map((batch) => el("option", { value: String(batch.id) }, batch.name)));
    batchSelect.value = String(state.batchId);

    const subjectSelect = el("select", { class: "select", "aria-label": "Subject" });
    function fillSubjects() {
      subjectSelect.innerHTML = "";
      data.pairs.filter((pair) => pair.batch_id === Number(batchSelect.value))
        .forEach((pair) => subjectSelect.append(
          el("option", { value: String(pair.subject_id) }, `${pair.subject_code} · ${pair.subject_name}`)));
      subjectSelect.value = String(state.subjectId);
    }
    fillSubjects();

    const dateInput = el("input", {
      class: "input", type: "date", value: state.date,
      max: isoDate(new Date()), "aria-label": "Attendance date",
    });

    const saveButton = el("button", { class: "btn btn--primary btn--sm", type: "button" },
      el("span", { class: "spinner", "aria-hidden": "true" }),
      iconEl("check"), el("span", { class: "btn__label" }, "Save attendance"));
    const presentAll = el("button", { class: "btn btn--ghost btn--sm", type: "button" },
      iconEl("checkCircle"), "All present");
    const absentAll = el("button", { class: "btn btn--ghost btn--sm", type: "button" },
      "All absent");

    const liveSummary = el("div", { class: "sheet-summary" });
    const dirtyBadge = el("span", { class: "badge badge--warning", hidden: true }, "Unsaved");

    function updateSummary() {
      const present = roster.filter((item) => item.status === "present").length;
      const late = roster.filter((item) => item.status === "late").length;
      const absent = roster.filter((item) => item.status === "absent").length;
      liveSummary.innerHTML = "";
      liveSummary.append(
        el("span", {}, "Present ", el("b", {}, String(present))),
        el("span", {}, "Late ", el("b", {}, String(late))),
        el("span", {}, "Absent ", el("b", {}, String(absent))),
        el("span", {}, "Total ", el("b", {}, String(roster.length))));
      dirtyBadge.hidden = !dirty;
    }

    const toolbar = el("div", { class: "sheet-toolbar" },
      el("div", { class: "field" }, el("label", { class: "field__label" }, "Batch"), batchSelect),
      el("div", { class: "field" }, el("label", { class: "field__label" }, "Subject"), subjectSelect),
      el("div", { class: "field" }, el("label", { class: "field__label" }, "Date"), dateInput),
      el("div", { class: "cluster", style: { marginLeft: "6px" } }, presentAll, absentAll),
      el("div", { style: { marginLeft: "auto", display: "flex", alignItems: "center", gap: "12px" } },
        dirtyBadge, saveButton));

    const rosterHost = el("div", {});
    roster.forEach((student) => {
      const row = el("div", { class: "roster-row", "data-student": String(student.student_id) });
      const group = el("div", { class: "status-group", role: "group", "aria-label": `Attendance for ${student.name}` });
      ["present", "absent", "late"].forEach((status) => {
        const button = el("button", {
          class: "status-btn", type: "button", "data-status": status,
          "aria-pressed": student.status === status ? "true" : "false",
        }, status[0].toUpperCase() + status.slice(1, 3));
        button.addEventListener("click", () => {
          student.status = status;
          dirty = true;
          group.querySelectorAll(".status-btn").forEach((btn) =>
            btn.setAttribute("aria-pressed", btn.dataset.status === status ? "true" : "false"));
          updateSummary();
        });
        group.append(button);
      });
      row.append(
        el("div", { class: "roster-row__roll" }, student.roll_no),
        el("div", {},
          el("div", { class: "roster-row__name" }, student.name),
          el("div", { class: "tiny muted" },
            student.edited_at ? `Last edited ${fmtDate(student.edited_at, { withYear: false })}` : "Not marked yet")),
        group);
      rosterHost.append(row);
    });

    presentAll.addEventListener("click", () => {
      roster.forEach((student) => { student.status = "present"; });
      rosterHost.querySelectorAll(".roster-row").forEach((rowNode) => {
        rowNode.querySelectorAll(".status-btn").forEach((button) =>
          button.setAttribute("aria-pressed", button.dataset.status === "present" ? "true" : "false"));
      });
      dirty = true;
      updateSummary();
    });
    absentAll.addEventListener("click", () => {
      roster.forEach((student) => { student.status = "absent"; });
      rosterHost.querySelectorAll(".roster-row").forEach((rowNode) => {
        rowNode.querySelectorAll(".status-btn").forEach((button) =>
          button.setAttribute("aria-pressed", button.dataset.status === "absent" ? "true" : "false"));
      });
      dirty = true;
      updateSummary();
    });

    const maybeDiscard = async () => {
      if (!dirty) return true;
      return confirmDialog({
        title: "Discard unsaved attendance?",
        message: "You have marks on this sheet that haven't been saved yet.",
        confirmLabel: "Discard changes",
        danger: true,
      });
    };

    async function changeSheet(nextBatch, nextSubject, nextDate) {
      if (!(await maybeDiscard())) {
        batchSelect.value = String(state.batchId);
        fillSubjects();
        dateInput.value = state.date;
        return;
      }
      state.batchId = nextBatch;
      state.subjectId = nextSubject;
      state.date = nextDate;
      await load();
    }

    batchSelect.addEventListener("change", async () => {
      const batchId = Number(batchSelect.value);
      const firstPair = data.pairs.find((pair) => pair.batch_id === batchId);
      if (!firstPair) return;
      subjectSelect.innerHTML = "";
      data.pairs.filter((pair) => pair.batch_id === batchId)
        .forEach((pair) => subjectSelect.append(
          el("option", { value: String(pair.subject_id) }, `${pair.subject_code} · ${pair.subject_name}`)));
      subjectSelect.value = String(firstPair.subject_id);
      await changeSheet(batchId, firstPair.subject_id, dateInput.value);
    });
    subjectSelect.addEventListener("change", async () => {
      await changeSheet(Number(batchSelect.value), Number(subjectSelect.value), dateInput.value);
    });
    dateInput.addEventListener("change", async () => {
      await changeSheet(Number(batchSelect.value), Number(subjectSelect.value), dateInput.value || state.date);
    });

    saveButton.addEventListener("click", async () => {
      await busyButton(saveButton, async () => {
        try {
          const response = await api("/api/professor/attendance", {
            method: "POST",
            body: {
              batch_id: state.batchId,
              subject_id: state.subjectId,
              date: state.date,
              records: roster.map((student) => ({
                student_id: student.student_id,
                status: student.status,
              })),
            },
          });
          toast(response.data.message || "Attendance saved.", "success");
          dirty = false;
          await load();
        } catch (error) {
          toast(error.message, "error");
        }
      });
    });

    container.append(pageHeader({
      title: "Attendance",
      subtitle: "Pick a class, adjust anyone who wasn't present, and save.",
      actions: [el("span", { class: "badge badge--neutral" }, fmtDate(state.date, { weekday: true }))],
    }));

    container.append(callout(
      wasUnmarked
        ? "Students without a mark default to present. Change anyone who was absent or late, then save."
        : "This sheet already has marks. Corrections overwrite the previous record and are audit-logged.",
      wasUnmarked ? "info" : "success", "info"));

    const sheetPanel = panel({
      title: `${data.pairs.find((pair) => pair.batch_id === data.batch_id && pair.subject_id === data.subject_id)?.subject_name || "Class"}`,
      subtitle: `${roster.length} students · ${fmtDate(state.date)}`,
      actions: [el("span", { class: "badge badge--primary" }, `${data.summary.marked}/${data.summary.total} marked`)],
      body: el("div", { class: "stack", style: { gap: "0" } }, rosterHost),
      footer: el("div", { class: "row-between" },
        liveSummary,
        el("span", { class: "tiny muted" }, "Saved sheet is visible to students immediately.")),
    });
    sheetPanel.insertBefore(toolbar, sheetPanel.querySelector(".panel__body"));

    container.append(el("div", { class: "mt-4" }, sheetPanel));
    updateSummary();
    if (wasUnmarked) {
      dirty = true;
      updateSummary();
    }
  }

  await load();
}
