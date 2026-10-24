import { api } from "../../core/api.js";
import {
  busyButton, confirmDialog, el, errorPanel, fmtDateTime, formField,
  iconEl, loadingView, openDrawer, openModal, setFieldError, showFieldErrors,
  statusBadge, toast, goTo,
} from "../../core/ui.js";
import { pageHeader, panel } from "../../components/page.js";
import { dataTable } from "../../components/table.js";

export const title = "Assignments";
const VIEW_KEY = "jecrc-assignments-view";

let state = null;

export async function render(container, { params } = {}) {
  state = {
    items: [],
    pairs: [],
    counts: { all: 0, active: 0, past_due: 0, completed: 0 },
    batchFilter: params?.get("batch_id") || "",
    view: "board",
    container,
  };
  try {
    state.view = localStorage.getItem(VIEW_KEY) === "table" ? "table" : "board";
  } catch (error) { /* default */ }

  container.append(loadingView("table"));

  async function load() {
    const query = new URLSearchParams();
    if (state.batchFilter) query.set("batch_id", state.batchFilter);
    try {
      const response = await api(`/api/professor/assignments?${query}`);
      state.items = response.data.items;
      state.pairs = response.data.pairs;
      state.counts = response.data.counts;
      return true;
    } catch (error) {
      container.innerHTML = "";
      container.append(errorPanel(error.message, () => {
        container.innerHTML = "";
        render(container, { params });
      }));
      return false;
    }
  }

  if (!(await load())) return;

  container.innerHTML = "";
  const newButton = el("button", { class: "btn btn--primary", type: "button" },
    iconEl("plus"), "New assignment");
  newButton.addEventListener("click", () => openEditor(null));

  container.append(pageHeader({
    title: "Assignments",
    subtitle: "Create work, track submissions and release marks.",
    actions: [newButton],
  }));

  const batches = [];
  state.pairs.forEach((pair) => {
    if (!batches.some((batch) => batch.id === pair.batch_id)) {
      batches.push({ id: pair.batch_id, name: `${pair.batch_name} (${pair.batch_code})` });
    }
  });

  const batchSelect = el("select", { class: "select", "aria-label": "Filter by batch" },
    el("option", { value: "" }, "All my batches"),
    ...batches.map((batch) => el("option", { value: String(batch.id) }, batch.name)));
  batchSelect.value = state.batchFilter;
  batchSelect.addEventListener("change", async () => {
    state.batchFilter = batchSelect.value;
    host.style.opacity = "0.45";
    const ok = await load();
    host.style.opacity = "";
    if (ok) paint();
  });

  const boardButton = el("button", {
    type: "button", "aria-pressed": state.view === "board" ? "true" : "false",
  }, iconEl("overview"), "Board");
  const tableButton = el("button", {
    type: "button", "aria-pressed": state.view === "table" ? "true" : "false",
  }, iconEl("menu"), "Table");
  const setView = (view) => {
    state.view = view;
    boardButton.setAttribute("aria-pressed", String(view === "board"));
    tableButton.setAttribute("aria-pressed", String(view === "table"));
    try { localStorage.setItem(VIEW_KEY, view); } catch (error) { /* ignore */ }
    paint();
  };
  boardButton.addEventListener("click", () => setView("board"));
  tableButton.addEventListener("click", () => setView("table"));

  const viewToggle = el("div", { class: "segmented", "aria-label": "View style" },
    boardButton, tableButton);

  const filterBar = el("section", { class: "panel" },
    el("div", { class: "filters" },
      el("div", { class: "field", style: { flex: "1 1 240px" } },
        el("label", { class: "field__label" }, "Batch"), batchSelect),
      el("div", { style: { marginLeft: "auto" }, class: "cluster" }, viewToggle)));

  const host = el("div", { class: "mt-4" });
  container.append(filterBar, host);

  function paint() {
    host.innerHTML = "";
    const bucketCounts = {
      active: state.items.filter((item) => item.bucket === "active").length,
      past_due: state.items.filter((item) => item.bucket === "past_due").length,
      completed: state.items.filter((item) => item.bucket === "completed").length,
    };

    if (!state.items.length) {
      host.append(el("section", { class: "panel" },
        el("div", { class: "state" },
          el("div", { class: "state__icon" }, iconEl("clipboard")),
          el("p", { class: "state__title" }, "No assignments here"),
          el("p", { class: "state__text" },
            "Create an assignment for one of your classes to start collecting submissions."),
          el("div", { class: "state__actions" },
            el("button", {
              class: "btn btn--primary btn--sm", type: "button",
              onclick: () => openEditor(null),
            }, "Create the first assignment")))));
      return;
    }

    if (state.view === "board") {
      const board = el("div", { class: "board" });
      [
        ["active", "Active", "In progress, deadline ahead"],
        ["past_due", "Past due", "Deadline passed, grading incomplete"],
        ["completed", "Completed", "Every submission graded"],
      ].forEach(([bucket, label, hint]) => {
        const column = el("section", { class: `board__col board__col--${bucket}` });
        const head = el("div", { class: "board__col-head" },
          el("div", {},
            el("div", {}, label),
            el("div", { class: "tiny muted", style: { fontWeight: "500", marginTop: "2px" } }, hint)),
          el("span", { class: "board__count" }, String(bucketCounts[bucket])));
        column.append(head);
        const list = state.items.filter((item) => item.bucket === bucket);
        if (!list.length) {
          column.append(el("div", { class: "board-empty" }, "Nothing in this column."));
        } else {
          list.forEach((item) => column.append(boardCard(item)));
        }
        board.append(column);
      });
      host.append(board);
    } else {
      const table = dataTable({
        caption: "All assignments",
        initialSort: { key: "due_date", direction: "desc" },
        columns: [
          {
            key: "title", label: "Assignment", sortable: true,
            render: (row) => el("div", {},
              el("div", { class: "strong" }, row.title),
              el("div", { class: "tiny muted" }, `${row.subject_code} · ${row.batch_code}`)),
          },
          { key: "due_date", label: "Due", sortable: true, render: (row) => fmtDateTime(row.due_date) },
          { key: "submitted", label: "Submitted", align: "right", sortable: true,
            render: (row) => `${row.submitted}/${row.total_students}` },
          { key: "graded", label: "Graded", align: "right", sortable: true },
          { key: "bucket", label: "Status", sortable: true, render: (row) => statusBadge(row.bucket) },
          {
            key: "actions", label: "", align: "right", sortable: false,
            render: (row) => {
              const wrap = el("div", { class: "row-actions" });
              wrap.append(el("button", {
                class: "btn btn--secondary btn--sm", type: "button",
                onclick: () => openTracker(row),
              }, "Review"));
              wrap.append(el("button", {
                class: "btn btn--ghost btn--icon btn--sm", type: "button",
                "aria-label": `Edit ${row.title}`, title: "Edit", onclick: () => openEditor(row),
              }, iconEl("edit")));
              wrap.append(el("button", {
                class: "btn btn--danger-ghost btn--icon btn--sm", type: "button",
                "aria-label": `Delete ${row.title}`, title: "Delete", onclick: () => removeAssignment(row),
              }, iconEl("trash")));
              return wrap;
            },
          },
        ],
        rows: state.items,
        empty: "No assignments.",
      });
      host.append(el("section", { class: "panel" },
        el("div", { class: "panel__body" }, table)));
    }
  }

  function boardCard(item) {
    const card = el("article", {
      class: "a-card", tabindex: "0", role: "button",
      "aria-label": `Open ${item.title}`,
    });
    card.append(
      el("div", { class: "a-card__subject" }, `${item.subject_code} · ${item.batch_code}`),
      el("div", { class: "a-card__title" }, item.title),
      el("div", { class: "a-card__meta" },
        el("span", {}, `Due ${fmtDateTime(item.due_date)}`),
        el("span", {}, `${item.submitted}/${item.total_students}`)),
      el("div", { class: "a-card__progress" },
        el("div", { class: "progress" },
          el("div", {
            class: "progress__bar",
            style: { width: `${item.total_students ? Math.round(item.submitted * 100 / item.total_students) : 0}%` },
          })),
        el("span", {}, `${item.graded} graded`)),
      el("div", { class: "cluster", style: { marginTop: "8px" } },
        statusBadge(item.bucket),
        el("span", { class: "tiny muted" }, `${item.max_marks} marks`)));
    card.addEventListener("click", () => openTracker(item));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openTracker(item);
      }
    });
    return card;
  }

  /* ---------------------------------------------------------- Editor */
  function openEditor(existing) {
    const isEdit = Boolean(existing);
    const titleField = formField({
      label: "Title", name: "title", value: existing?.title || "",
      placeholder: "e.g. Lab record: arrays and pointers", required: true,
    });
    const descriptionField = formField({
      label: "Instructions", name: "description", type: "textarea",
      value: existing?.description || "",
      placeholder: "What should students submit, and how will it be assessed?",
      rows: 5, required: true,
    });
    const dueDefault = new Date(Date.now() + 7 * 86400000);
    dueDefault.setHours(23, 59, 0, 0);
    const dueValue = existing?.due_date ? existing.due_date.slice(0, 16) : localDateTime(dueDefault);
    const dueField = formField({
      label: "Due date and time", name: "due_date", type: "datetime-local",
      value: dueValue, required: true,
    });
    const marksField = formField({
      label: "Maximum marks", name: "max_marks", type: "number",
      value: existing?.max_marks || 20, min: 1, max: 100, required: true,
    });

    const form = el("form", { class: "stack", novalidate: true });
    let pairSelect = null;
    if (!isEdit) {
      pairSelect = formField({
        label: "Class", name: "pair", type: "select", required: true,
        options: state.pairs.map((pair) => ({
          value: `${pair.batch_id}:${pair.subject_id}`,
          label: `${pair.batch_name} (${pair.batch_code}) — ${pair.subject_code} ${pair.subject_name}`,
        })),
      });
      form.append(pairSelect.wrapper);
    } else {
      form.append(el("div", { class: "callout callout--info" }, iconEl("info"),
        el("span", {}, `${existing.subject_name} · ${existing.batch_name} (${existing.batch_code}) · ${existing.max_marks} marks`)));
    }
    form.append(titleField.wrapper, descriptionField.wrapper,
      el("div", { class: "field-row" }, dueField.wrapper, marksField.wrapper));

    const fileInput = el("input", {
      type: "file", class: "input", accept: ".pdf,.png,.jpg,.jpeg,.docx,.zip",
      "aria-label": "Assignment attachment",
    });
    form.append(el("div", { class: "field" },
      el("label", { class: "field__label" }, isEdit ? "Replace attachment (optional)" : "Attachment (optional)"),
      fileInput,
      el("span", { class: "field__hint" }, "PDF, PNG, JPG, DOCX or ZIP · max 10 MB")));

    if (isEdit && existing.attachment) {
      form.append(el("a", { href: existing.attachment.url, class: "btn btn--link" },
        iconEl("fileText"), ` Current attachment: ${existing.attachment.name}`));
    }

    const submit = el("button", { class: "btn btn--primary", type: "submit" },
      el("span", { class: "spinner", "aria-hidden": "true" }),
      el("span", { class: "btn__label" }, isEdit ? "Save changes" : "Publish assignment"));
    form.append(el("div", { class: "form-actions" }, submit));

    const ui = openModal({
      title: isEdit ? "Edit assignment" : "New assignment",
      description: isEdit
        ? "Changes are visible to students immediately."
        : "Students in the selected class will be notified.",
      body: form,
      size: "modal--lg",
      actions: [{ label: "Cancel", variant: "secondary" }],
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      showFieldErrors(form, {});
      const fields = {};
      const title = titleField.input.value.trim();
      const description = descriptionField.input.value.trim();
      const due = dueField.input.value;
      const marks = Number(marksField.input.value);
      if (title.length < 3) fields.title = "Give the assignment a clear title.";
      if (description.length < 10) fields.description = "Add instructions (10+ characters).";
      if (!due) fields.due_date = "Choose a due date and time.";
      else if (new Date(due) < new Date(Date.now() - 60000)) {
        fields.due_date = "The due date can't be in the past.";
      }
      if (!Number.isInteger(marks) || marks < 1 || marks > 100) {
        fields.max_marks = "Use a whole number from 1 to 100.";
      }
      if (Object.keys(fields).length) {
        showFieldErrors(form, fields);
        return;
      }

      const formData = new FormData();
      formData.append("title", title);
      formData.append("description", description);
      formData.append("due_date", due);
      formData.append("max_marks", String(marks));
      if (!isEdit && pairSelect) {
        const [batchId, subjectId] = pairSelect.input.value.split(":");
        formData.append("batch_id", batchId);
        formData.append("subject_id", subjectId);
      }
      if (fileInput.files && fileInput.files[0]) {
        formData.append("attachment", fileInput.files[0]);
      }

      await busyButton(submit, async () => {
        try {
          if (isEdit) {
            await api(`/api/professor/assignments/${existing.id}`, {
              method: "PATCH", form: formData,
            });
            toast("Assignment updated.", "success");
          } else {
            await api("/api/professor/assignments", { method: "POST", form: formData });
            toast("Assignment published and students notified.", "success");
          }
          ui.close();
          await reloadAll();
        } catch (error) {
          if (error.fields && Object.keys(error.fields).length) {
            const mapped = { ...error.fields };
            if (mapped.pair) mapped.pair = mapped.pair;
            showFieldErrors(form, mapped);
            if (error.fields.attachment) toast(error.fields.attachment, "error");
          } else {
            toast(error.message, "error");
          }
        }
      });
    });
  }

  /* ---------------------------------------------------------- Tracker */
  async function openTracker(assignment) {
    const body = el("div", { class: "stack" });
    body.append(el("div", { class: "skeleton skeleton--line" }),
      el("div", { class: "skeleton skeleton--line" }),
      el("div", { class: "skeleton skeleton--line" }));
    const drawer = openDrawer({
      title: assignment.title,
      subtitle: `${assignment.subject_code} · ${assignment.batch_name} · Due ${fmtDateTime(assignment.due_date)}`,
      body,
      footer: [{ label: "Close", variant: "secondary" }],
      onClose: () => reloadAll(),
    });

    let sheet;
    try {
      sheet = (await api(`/api/professor/assignments/${assignment.id}/submissions`)).data;
    } catch (error) {
      body.innerHTML = "";
      body.append(errorPanel(error.message, () => {
        drawer.close();
        openTracker(assignment);
      }));
      return;
    }
    renderTracker();

    function renderTracker() {
      body.innerHTML = "";
      const summary = sheet.summary;
      const bulk = el("div", { class: "cluster" });
      const extendButton = el("button", { class: "btn btn--secondary btn--sm", type: "button" },
        iconEl("clock"), "Extend deadline");
      const remindButton = el("button", { class: "btn btn--secondary btn--sm", type: "button" },
        iconEl("bell"), "Remind missing");
      const downloadLink = el("a", {
        class: "btn btn--secondary btn--sm",
        href: `/api/professor/assignments/${assignment.id}/download`,
      }, iconEl("download"), "Download ZIP");
      const editButton = el("button", { class: "btn btn--ghost btn--sm", type: "button" },
        iconEl("edit"), "Edit");
      const deleteButton = el("button", { class: "btn btn--danger-ghost btn--sm", type: "button" },
        iconEl("trash"), "Delete");
      bulk.append(extendButton, remindButton, downloadLink, editButton, deleteButton);

      body.append(
        el("div", { class: "cluster" },
          el("span", { class: "badge badge--primary" }, `${summary.submitted}/${summary.total} submitted`),
          el("span", { class: "badge badge--success" }, `${summary.graded} graded`),
          el("span", { class: "badge badge--warning" }, `${summary.missing} missing`)),
        el("p", { class: "small muted", style: { whiteSpace: "pre-line" } }, assignment.description),
        bulk);

      if (!sheet.items.length) {
        body.append(el("div", { class: "state" },
          el("p", { class: "state__title" }, "No students in this batch")));
        return;
      }

      const list = el("div", { class: "grading-list" });
      sheet.items.forEach((item) => {
        const row = el("div", { class: "grading-row" });
        const hasSubmission = Boolean(item.submission_id);
        const head = el("div", { class: "grading-row__head" },
          el("div", { style: { minWidth: "0" } },
            el("div", { class: "strong small" }, item.name),
            el("div", { class: "tiny muted" }, `${item.roll_no}${hasSubmission ? ` · submitted ${fmtDateTime(item.submitted_at)}` : ""}`)),
          el("div", { class: "cluster" },
            statusBadge(item.status),
            hasSubmission ? el("a", {
              href: item.download_url, class: "btn btn--link", title: item.file_name,
            }, iconEl("download"), " File") : null));
        row.append(head);

        if (hasSubmission) {
          const marksInput = el("input", {
            class: "input", type: "number", min: "0", max: String(sheet.assignment.max_marks),
            step: "0.5", value: item.marks !== null ? String(item.marks) : "",
            placeholder: "Marks", "aria-label": `Marks for ${item.name}`,
          });
          const remarksInput = el("input", {
            class: "input", type: "text", value: item.remarks || "",
            placeholder: "Remarks (visible to the student)", maxlength: "500",
            "aria-label": `Remarks for ${item.name}`,
          });
          const save = el("button", { class: "btn btn--primary btn--sm", type: "button" },
            el("span", { class: "spinner", "aria-hidden": "true" }),
            el("span", { class: "btn__label" }, item.marks !== null ? "Update" : "Save grade"));
          save.addEventListener("click", async () => {
            const marks = Number(marksInput.value);
            if (marksInput.value === "" || Number.isNaN(marks)) {
              toast("Enter the marks awarded.", "warning");
              marksInput.focus();
              return;
            }
            if (marks < 0 || marks > sheet.assignment.max_marks) {
              toast(`Marks must be between 0 and ${sheet.assignment.max_marks}.`, "error");
              marksInput.focus();
              return;
            }
            await busyButton(save, async () => {
              try {
                await api(`/api/professor/submissions/${item.submission_id}/grade`, {
                  method: "POST",
                  body: { marks, remarks: remarksInput.value.trim() },
                });
                item.marks = marks;
                item.remarks = remarksInput.value.trim();
                item.status = "graded";
                toast("Marks saved and student notified.", "success");
                sheet.summary.graded = sheet.items.filter((entry) => entry.marks !== null).length;
                renderTracker();
              } catch (error) {
                toast(error.message, "error");
              }
            });
          });
          row.append(el("div", { class: "grading-controls" },
            marksInput, remarksInput, save));
        } else {
          row.append(el("div", { class: "tiny muted", style: { marginTop: "6px" } },
            item.status === "overdue" ? "No submission before the deadline." : "No submission yet."));
        }
        list.append(row);
      });
      body.append(list);

      extendButton.addEventListener("click", () => openExtend(assignment));
      remindButton.addEventListener("click", async () => {
        try {
          const response = await api(`/api/professor/assignments/${assignment.id}/remind`, {
            method: "POST",
          });
          toast(response.data.message, "success");
        } catch (error) {
          toast(error.message, "error");
        }
      });
      editButton.addEventListener("click", () => {
        drawer.close();
        openEditor(assignment);
      });
      deleteButton.addEventListener("click", async () => {
        const removed = await removeAssignment(assignment, { skipReload: true });
        if (removed) drawer.close();
      });
    }
  }

  function openExtend(assignment) {
    const nextWeek = new Date(Date.now() + 7 * 86400000);
    nextWeek.setHours(23, 59, 0, 0);
    const field = formField({
      label: "New due date and time", name: "due_date", type: "datetime-local",
      value: localDateTime(nextWeek), required: true,
    });
    const form = el("form", { class: "stack", novalidate: true }, field.wrapper);
    const save = el("button", { class: "btn btn--primary", type: "submit" },
      el("span", { class: "spinner", "aria-hidden": "true" }),
      el("span", { class: "btn__label" }, "Extend deadline"));
    form.append(el("div", { class: "form-actions" }, save));
    const ui = openModal({
      title: "Extend deadline",
      description: "Students without a submission will be notified of the new deadline.",
      body: form,
      actions: [{ label: "Cancel", variant: "secondary" }],
      size: "modal--sm",
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!field.input.value) {
        setFieldError(field.input, "Choose a new deadline.");
        return;
      }
      await busyButton(save, async () => {
        try {
          const response = await api(`/api/professor/assignments/${assignment.id}/extend`, {
            method: "POST", body: { due_date: field.input.value },
          });
          toast(response.data.message, "success");
          ui.close();
          await reloadAll();
        } catch (error) {
          if (error.fields && error.fields.due_date) setFieldError(field.input, error.fields.due_date);
          else toast(error.message, "error");
        }
      });
    });
  }

  async function removeAssignment(assignment, { skipReload = false } = {}) {
    const confirmed = await confirmDialog({
      title: "Delete this assignment?",
      message: `“${assignment.title}” will disappear from the student portal. You can undo this from the toast for a few seconds.`,
      confirmLabel: "Delete assignment",
      danger: true,
    });
    if (!confirmed) return false;
    try {
      await api(`/api/professor/assignments/${assignment.id}`, { method: "DELETE" });
      toast(`“${assignment.title}” deleted.`, "success", {
        duration: 8000,
        actionLabel: "Undo",
        onAction: async () => {
          try {
            await api(`/api/professor/assignments/${assignment.id}/restore`, { method: "POST" });
            toast("Assignment restored.", "success");
            await reloadAll();
          } catch (error) {
            toast(error.message, "error");
          }
        },
      });
      if (!skipReload) await reloadAll();
      return true;
    } catch (error) {
      toast(error.message, "error");
      return false;
    }
  }

  async function reloadAll() {
    const ok = await load();
    if (ok) {
      batchSelect.value = state.batchFilter;
      paint();
    }
  }

  paint();
}

function localDateTime(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
