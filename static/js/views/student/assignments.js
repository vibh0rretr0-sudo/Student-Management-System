import { api, upload } from "../../core/api.js";
import {
  busyButton, callout, debounce, el, errorPanel, fmtClock, fmtDateTime,
  iconEl, loadingView, openModal, relativeTime, statusBadge, toast,
} from "../../core/ui.js";
import { pageHeader, panel } from "../../components/page.js";

export const title = "Assignments";
const ALLOWED = ["pdf", "png", "jpg", "jpeg", "docx", "zip"];
const MAX_BYTES = 10 * 1024 * 1024;

let assignments = [];
let filters = { status: "all", q: "" };

export async function render(container) {
  assignments = [];
  filters = { status: "all", q: "" };
  container.append(loadingView("table"));

  async function load() {
    try {
      const response = await api("/api/student/assignments");
      assignments = response.data.items || [];
    } catch (error) {
      container.innerHTML = "";
      container.append(errorPanel(error.message, () => {
        container.innerHTML = "";
        render(container);
      }));
      return false;
    }
    return true;
  }

  if (!(await load())) return;

  container.innerHTML = "";
  container.append(pageHeader({
    title: "Assignments",
    subtitle: "Submit your work, track deadlines and read faculty feedback.",
  }));

  /* Filters */
  const searchInput = el("input", {
    class: "input", type: "search", placeholder: "Search assignments…",
    "aria-label": "Search assignments",
  });
  const searchWrap = el("div", { class: "search-field" }, iconEl("search"), searchInput);

  const statusFilters = [
    ["all", "All"], ["pending", "Pending"], ["overdue", "Overdue"],
    ["submitted", "Submitted"], ["graded", "Graded"],
  ];
  const chipRow = el("div", { class: "cluster" });
  const chipButtons = {};
  statusFilters.forEach(([value, label]) => {
    const count = () => value === "all"
      ? assignments.length
      : assignments.filter((item) => item.status === value).length;
    const button = el("button", {
      class: "chip chip--button", type: "button",
      "aria-pressed": value === "all" ? "true" : "false",
      "data-value": value,
    }, label, el("span", { class: "badge badge--neutral", style: { marginLeft: "5px" } }, String(count())));
    button.addEventListener("click", () => {
      filters.status = value;
      Object.values(chipButtons).forEach((chip) =>
        chip.setAttribute("aria-pressed", chip === button ? "true" : "false"));
      renderList();
    });
    chipButtons[value] = button;
    chipRow.append(button);
  });

  searchInput.addEventListener("input", debounce(() => {
    filters.q = searchInput.value.trim().toLowerCase();
    renderList();
  }, 180));

  const toolbar = el("section", { class: "panel" },
    el("div", { class: "filters" },
      searchWrap, chipRow));

  const listHost = el("div", { class: "stack mt-4" });
  container.append(toolbar, listHost);

  function refreshCounts() {
    Object.entries(chipButtons).forEach(([value, button]) => {
      const badge = button.querySelector(".badge");
      if (!badge) return;
      badge.textContent = String(value === "all"
        ? assignments.length
        : assignments.filter((item) => item.status === value).length);
    });
  }

  function renderList() {
    listHost.innerHTML = "";
    refreshCounts();

    let visible = assignments;
    if (filters.status !== "all") {
      visible = visible.filter((item) => item.status === filters.status);
    }
    if (filters.q) {
      visible = visible.filter((item) =>
        `${item.title} ${item.subject_name} ${item.subject_code} ${item.professor}`
          .toLowerCase().includes(filters.q));
    }

    if (!visible.length) {
      listHost.append(el("section", { class: "panel" },
        el("div", { class: "state" },
          el("div", { class: "state__icon" }, iconEl("clipboard")),
          el("p", { class: "state__title" },
            assignments.length ? "No assignments match these filters" : "No assignments yet"),
          el("p", { class: "state__text" },
            assignments.length
              ? "Try a different status or clear the search."
              : "When your professors post work, it will appear here with its deadline."),
          assignments.length
            ? el("div", { class: "state__actions" },
              el("button", {
                class: "btn btn--secondary btn--sm", type: "button",
                onclick: () => {
                  filters = { status: "all", q: "" };
                  searchInput.value = "";
                  Object.values(chipButtons).forEach((chip) =>
                    chip.setAttribute("aria-pressed", chip.dataset.value === "all" ? "true" : "false"));
                  renderList();
                },
              }, "Clear filters"))
            : null)));
      return;
    }

    const groups = new Map();
    visible.forEach((item) => {
      const key = item.subject_code;
      if (!groups.has(key)) {
        groups.set(key, {
          name: item.subject_name,
          code: item.subject_code,
          professor: item.professor,
          items: [],
        });
      }
      groups.get(key).items.push(item);
    });

    [...groups.values()]
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach((group) => {
        const groupNode = el("section", { class: "subject-group" });
        groupNode.append(el("div", { class: "subject-group__head" },
          el("h3", {}, group.name),
          el("span", { class: "badge badge--primary" }, group.code),
          el("span", { class: "subject-group__count" },
            `${group.items.length} assignment${group.items.length === 1 ? "" : "s"}`),
          el("span", { class: "muted tiny", style: { marginLeft: "auto" } }, group.professor)));
        group.items
          .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
          .forEach((item) => groupNode.append(assignmentRow(item)));
        listHost.append(groupNode);
      });
  }

  function assignmentRow(item) {
    const row = el("article", { class: `a-row a-row--${item.status}` });
    const due = new Date(item.due_date);
    const dueSoon = item.status === "pending" && due - Date.now() < 48 * 3600000;
    const dueText = item.status === "graded"
      ? `Graded ${relativeTime(item.submission?.submitted_at)}`
      : item.status === "submitted"
        ? `Submitted ${relativeTime(item.submission?.submitted_at)}`
        : item.status === "overdue"
          ? `Was due ${relativeTime(item.due_date)}`
          : `Due ${relativeTime(item.due_date)}${dueSoon ? " · soon" : ""}`;

    const meta = el("div", { class: "a-row__meta" },
      statusBadge(item.status),
      el("span", {}, `Due ${fmtDateTime(item.due_date)}`),
      el("span", {}, `${item.max_marks} marks`),
      item.attachment
        ? el("a", {
          href: item.attachment.url, class: "btn--link",
          title: `Download ${item.attachment.name}`,
        }, iconEl("fileText"), ` ${item.attachment.name}`)
        : null,
      item.submission?.file_name
        ? el("a", {
          href: item.submission.download_url, class: "btn--link",
        }, iconEl("download"), ` ${item.submission.file_name}`)
        : null);

    const body = el("div", {},
      el("div", { class: "a-row__title" }, item.title),
      meta);

    const actions = el("div", { class: "a-row__actions" });
    if (item.status === "graded") {
      actions.append(el("div", { class: "a-row__marks text-right" },
        el("div", {}, `${item.submission.marks}`, el("span", {}, ` / ${item.max_marks}`))));
      actions.append(el("button", {
        class: "btn btn--secondary btn--sm", type: "button",
        onclick: () => openAssignment(item),
      }, "View feedback"));
    } else if (item.status === "submitted") {
      actions.append(el("button", {
        class: "btn btn--secondary btn--sm", type: "button",
        onclick: () => openAssignment(item),
      }, "View submission"));
      actions.append(el("button", {
        class: "btn btn--primary btn--sm", type: "button",
        onclick: () => openAssignment(item),
      }, "Replace"));
    } else {
      actions.append(el("button", {
        class: "btn btn--primary btn--sm", type: "button",
        onclick: () => openAssignment(item),
      }, item.status === "overdue" ? "Submit late" : "Submit work"));
    }

    row.append(el("div", { class: "a-row__rail", "aria-hidden": "true" }),
      body,
      actions);
    return row;
  }

  function openAssignment(item) {
    const graded = item.status === "graded";
    const body = el("div", { class: "stack" });
    body.append(el("p", { class: "muted-strong", style: { whiteSpace: "pre-line" } },
      item.description));
    body.append(el("dl", { class: "detail-grid" },
      el("div", {}, el("dt", {}, "Subject"), el("dd", {}, `${item.subject_name} (${item.subject_code})`)),
      el("div", {}, el("dt", {}, "Professor"), el("dd", {}, item.professor)),
      el("div", {}, el("dt", {}, "Due"), el("dd", {}, fmtDateTime(item.due_date))),
      el("div", {}, el("dt", {}, "Maximum marks"), el("dd", {}, String(item.max_marks)))));

    if (item.attachment) {
      body.append(el("a", {
        class: "btn btn--secondary btn--sm", href: item.attachment.url,
        style: { alignSelf: "flex-start" },
      }, iconEl("download"), ` ${item.attachment.name}`));
    }

    if (item.submission) {
      body.append(el("div", { class: "callout callout--info" }, iconEl("fileText"),
        el("div", {},
          el("div", { class: "strong" },
            graded ? "Graded submission" : "Submitted"),
          el("div", { class: "small muted", style: { marginTop: "2px" } },
            `${item.submission.file_name} · ${fmtDateTime(item.submission.submitted_at)}`),
          item.submission.download_url
            ? el("a", {
              href: item.submission.download_url, class: "btn btn--link", style: { marginTop: "4px" },
            }, "Download your file")
            : null)));
    }

    if (graded && item.submission) {
      const feedback = el("div", { class: "panel" },
        el("div", { class: "panel__body stack-sm" },
          el("div", { class: "row-between" },
            el("span", { class: "h3", style: { fontSize: "var(--text-lg)", fontWeight: "650" } }, "Faculty feedback"),
            el("span", { class: "a-row__marks" },
              `${item.submission.marks}`, el("span", {}, ` / ${item.max_marks}`))),
          el("p", { class: "small", style: { whiteSpace: "pre-line" } },
            item.submission.remarks || "No written remarks were added.")));
      body.append(feedback);
    }

    let close = null;
    if (!graded) {
      /* Upload form */
      let selectedFile = null;
      const fileInput = el("input", {
        type: "file", hidden: true,
        accept: ".pdf,.png,.jpg,.jpeg,.docx,.zip",
        "aria-label": "Choose your submission file",
      });
      const fileLabel = el("label", { class: "dropzone", tabindex: "0" },
        iconEl("upload"),
        el("span", {}, el("strong", {}, "Drop your file here"), " or click to browse"),
        el("span", { class: "tiny" }, "PDF, PNG, JPG, DOCX or ZIP · max 10 MB"),
        fileInput);
      const fileInfo = el("div", { class: "dropzone__file", hidden: true });
      const fileError = el("span", { class: "field__error", role: "alert" });
      const progressWrap = el("div", { class: "upload-progress", hidden: true },
        el("div", { class: "upload-progress__meta" },
          el("span", { id: "upload-label" }, "Uploading…"),
          el("span", { id: "upload-value" }, "0%")),
        el("div", { class: "progress" },
          el("div", { class: "progress__bar", style: { width: "0%" } })));

      const pick = (file) => {
        fileError.textContent = "";
        if (!file) return;
        const extension = file.name.split(".").pop().toLowerCase();
        if (!ALLOWED.includes(extension)) {
          fileError.textContent = "That file type isn't accepted. Use PDF, PNG, JPG, DOCX or ZIP.";
          return;
        }
        if (file.size > MAX_BYTES) {
          fileError.textContent = "File is larger than the 10 MB limit.";
          return;
        }
        selectedFile = file;
        fileInfo.hidden = false;
        fileInfo.innerHTML = "";
        fileInfo.append(iconEl("file"), el("span", {}, file.name),
          el("span", { class: "muted" }, ` · ${(file.size / 1024 / 1024).toFixed(1)} MB`));
      };

      fileInput.addEventListener("change", () => pick(fileInput.files[0]));
      fileLabel.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          fileInput.click();
        }
      });
      ["dragenter", "dragover"].forEach((name) => fileLabel.addEventListener(name, (event) => {
        event.preventDefault();
        fileLabel.classList.add("is-dragover");
      }));
      ["dragleave", "drop"].forEach((name) => fileLabel.addEventListener(name, (event) => {
        event.preventDefault();
        fileLabel.classList.remove("is-dragover");
      }));
      fileLabel.addEventListener("drop", (event) => {
        pick(event.dataTransfer.files && event.dataTransfer.files[0]);
      });

      const submitButton = el("button", {
        class: "btn btn--primary", type: "button",
      }, el("span", { class: "spinner", "aria-hidden": "true" }),
        iconEl("upload"), el("span", { class: "btn__label" },
          item.submission ? "Replace submission" : "Submit assignment"));

      submitButton.addEventListener("click", async () => {
        if (!selectedFile) {
          fileError.textContent = "Choose a file before submitting.";
          return;
        }
        const formData = new FormData();
        formData.append("file", selectedFile);
        await busyButton(submitButton, async () => {
          try {
            const response = await upload(
              `/api/student/assignments/${item.id}/submit`,
              formData,
              {
                onProgress: (value) => {
                  progressWrap.hidden = false;
                  progressWrap.querySelector(".progress__bar").style.width = `${value}%`;
                  progressWrap.querySelector("#upload-value").textContent = `${value}%`;
                  if (value === 100) {
                    progressWrap.querySelector("#upload-label").textContent = "Processing…";
                  }
                },
              }
            );
            toast(response.data.message || "Submission uploaded.", "success");
            if (close) close();
            await reload();
          } catch (error) {
            if (error.fields && error.fields.file) fileError.textContent = error.fields.file;
            toast(error.message, "error");
            progressWrap.hidden = true;
          }
        });
      });

      if (item.status === "overdue") {
        body.append(callout(
          "The deadline has passed. You can still submit, but your professor will see it as late.",
          "warning", "clock"));
      }
      body.append(el("div", { class: "divider" }));
      body.append(el("div", { class: "field" },
        el("span", { class: "field__label" }, item.submission ? "Upload a new file" : "Your submission"),
        fileLabel, fileInfo, fileError, progressWrap));
      body.append(el("div", { class: "row-between" }, submitButton));
    }

    const ui = openModal({
      title: item.title,
      description: `${item.subject_code} · ${item.professor}`,
      body,
      size: "modal--lg",
      actions: [{ label: "Close", variant: "secondary" }],
    });
    close = ui.close;
  }

  async function reload() {
    const ok = await load();
    if (ok) renderList();
  }

  container._reloadAssignments = reload;
  renderList();
}
