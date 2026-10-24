import { api } from "../../core/api.js";
import {
  busyButton, confirmDialog, el, errorPanel, fmtDateTime, formField,
  iconEl, loadingView, openModal, setFieldError, showFieldErrors, statusBadge,
  toast,
} from "../../core/ui.js";
import { pageHeader } from "../../components/page.js";

export const title = "Announcements";

export async function render(container, { params } = {}) {
  container.append(loadingView("table"));
  let data;
  try {
    data = (await api("/api/professor/announcements")).data;
  } catch (error) {
    container.innerHTML = "";
    container.append(errorPanel(error.message, () => {
      container.innerHTML = "";
      render(container, { params });
    }));
    return;
  }

  const state = { status: "all", q: "", items: data.items, pairs: data.batches };
  container.innerHTML = "";

  const newButton = el("button", { class: "btn btn--primary", type: "button" },
    iconEl("plus"), "New announcement");
  newButton.addEventListener("click", () => openEditor(null));

  container.append(pageHeader({
    title: "Announcements",
    subtitle: "Post notices to one batch, several, or all of your classes.",
    actions: [newButton],
  }));

  /* Filters */
  const searchInput = el("input", {
    class: "input", type: "search", placeholder: "Search your notices…",
    "aria-label": "Search announcements",
  });
  const chips = el("div", { class: "cluster" });
  const statusButtons = {};
  [["all", "All"], ["published", "Published"], ["scheduled", "Scheduled"]].forEach(([value, label]) => {
    const button = el("button", {
      class: "chip chip--button", type: "button", "data-value": value,
      "aria-pressed": value === "all" ? "true" : "false",
    }, label);
    button.addEventListener("click", () => {
      state.status = value;
      Object.values(statusButtons).forEach((chip) =>
        chip.setAttribute("aria-pressed", chip === button ? "true" : "false"));
      paintList();
    });
    statusButtons[value] = button;
    chips.append(button);
  });

  container.append(el("section", { class: "panel" },
    el("div", { class: "filters" },
      el("div", { class: "search-field" }, iconEl("search"), searchInput),
      chips)));

  const list = el("div", { class: "mt-4" });
  container.append(list);

  searchInput.addEventListener("input", () => {
    state.q = searchInput.value.trim().toLowerCase();
    paintList();
  });

  function refreshCounts() {
    Object.entries(statusButtons).forEach(([value, button]) => {
      const count = value === "all" ? state.items.length
        : state.items.filter((item) => item.status === value).length;
      button.querySelector(".chip-count")?.remove();
      button.append(el("span", {
        class: "badge badge--neutral chip-count", style: { marginLeft: "5px" },
      }, String(count)));
    });
  }

  function paintList() {
    refreshCounts();
    list.innerHTML = "";
    let items = state.items;
    if (state.status !== "all") items = items.filter((item) => item.status === state.status);
    if (state.q) {
      items = items.filter((item) =>
        `${item.title} ${item.body}`.toLowerCase().includes(state.q));
    }

    if (!items.length) {
      list.append(el("section", { class: "panel" },
        el("div", { class: "state" },
          el("div", { class: "state__icon" }, iconEl("megaphone")),
          el("p", { class: "state__title" },
            state.items.length ? "No notices match" : "You haven't posted anything yet"),
          el("p", { class: "state__text" },
            state.items.length
              ? "Try another filter or clear the search."
              : "Announcements reach every student in the batches you target, with read tracking."),
          el("div", { class: "state__actions" },
            el("button", {
              class: "btn btn--primary btn--sm", type: "button",
              onclick: () => openEditor(null),
            }, "Write an announcement")))));
      return;
    }

    items.forEach((item) => {
      const readPct = item.audience_count
        ? Math.round(item.read_count * 100 / item.audience_count) : 0;
      const card = el("article", { class: "notice-card" });
      const editButton = el("button", {
        class: "btn btn--ghost btn--icon btn--sm", type: "button",
        "aria-label": `Edit ${item.title}`, title: "Edit",
        onclick: () => openEditor(item),
      }, iconEl("edit"));
      const deleteButton = el("button", {
        class: "btn btn--danger-ghost btn--icon btn--sm", type: "button",
        "aria-label": `Delete ${item.title}`, title: "Delete",
        onclick: () => remove(item),
      }, iconEl("trash"));

      card.append(el("div", { class: "notice-card__head" },
        el("div", {},
          el("h3", { class: "notice-card__title" }, item.title),
          el("div", { class: "notice-card__meta" },
            statusBadge(item.priority),
            statusBadge(item.status),
            item.pinned ? el("span", { class: "badge badge--accent" }, "Pinned") : null,
            el("span", {}, fmtDateTime(item.publish_at)),
            ...(item.batches || []).map((batch) => el("span", { class: "chip" }, batch.name)))),
        el("div", { class: "row-actions" }, editButton, deleteButton)),
        el("p", { class: "notice-card__body", style: { whiteSpace: "pre-line" } }, item.body),
        el("div", { class: "notice-card__foot" },
          el("div", { class: "notice-card__stats" },
            el("span", {}, `${item.read_count} of ${item.audience_count} read (${readPct}%)`),
            el("span", {}, `${item.batches.length} batch${item.batches.length === 1 ? "" : "es"}`)),
          el("div", { class: "progress", style: { maxWidth: "220px", marginLeft: "auto" } },
            el("div", {
              class: "progress__bar",
              style: { width: `${readPct}%` },
            }))));
      list.append(card);
    });
  }

  function openEditor(existing) {
    const isEdit = Boolean(existing);
    const titleField = formField({
      label: "Title", name: "title", value: existing?.title || "",
      placeholder: "e.g. Mid-semester exam schedule", required: true,
    });
    const bodyField = formField({
      label: "Message", name: "body", type: "textarea",
      value: existing?.body || "", rows: 6, required: true,
      placeholder: "Write the complete notice students will see…",
    });
    const priorityField = formField({
      label: "Priority", name: "priority", type: "select",
      options: [
        { value: "normal", label: "Normal" },
        { value: "important", label: "Important" },
        { value: "urgent", label: "Urgent" },
      ],
    });
    priorityField.input.value = existing?.priority || "normal";

    const pinnedField = el("input", { type: "checkbox", checked: Boolean(existing?.pinned) });
    const audienceField = formField({
      label: "Audience", name: "audience", type: "select",
      options: [
        { value: "all", label: "All my batches" },
        { value: "batches", label: "Choose specific batches" },
      ],
    });

    const uniqueBatches = [];
    state.pairs.forEach((pair) => {
      if (!uniqueBatches.some((batch) => batch.id === pair.batch_id)) {
        uniqueBatches.push({
          id: pair.batch_id,
          name: `${pair.batch_name} (${pair.batch_code})`,
        });
      }
    });
    const existingBatchIds = new Set((existing?.batches || []).map((batch) => batch.id));
    const batchChoices = el("div", { class: "stack-sm", style: { marginTop: "4px" } });
    const checks = uniqueBatches.map((batch) => {
      const input = el("input", {
        type: "checkbox",
        checked: existing ? existingBatchIds.has(batch.id) : true,
      });
      const label = el("label", { class: "check", style: { padding: "4px 0" } },
        input, el("span", {}, batch.name));
      batchChoices.append(label);
      return { input, batch };
    });
    const batchWrap = el("div", { class: "field" },
      el("span", { class: "field__label" }, "Batches"),
      batchChoices,
      el("span", { class: "field__error" }));

    function syncAudience() {
      const all = audienceField.input.value === "all";
      batchChoices.hidden = all;
      checks.forEach(({ input }) => { input.disabled = all; });
    }
    audienceField.input.addEventListener("change", syncAudience);

    const timingField = formField({
      label: "Publishing", name: "timing", type: "select",
      options: isEdit
        ? [
          { value: "keep", label: "Keep current publish time" },
          { value: "now", label: "Publish now" },
          { value: "schedule", label: "Schedule for later" },
        ]
        : [
          { value: "now", label: "Publish now" },
          { value: "schedule", label: "Schedule for later" },
        ],
    });
    const scheduleField = formField({
      label: "Publish date and time", name: "publish_at", type: "datetime-local",
      value: existing?.publish_at ? existing.publish_at.slice(0, 16) : "",
    });
    scheduleField.wrapper.hidden = true;
    timingField.input.addEventListener("change", () => {
      scheduleField.wrapper.hidden = timingField.input.value !== "schedule";
    });

    const form = el("form", { class: "stack", novalidate: true },
      titleField.wrapper, bodyField.wrapper,
      el("div", { class: "field-row" }, priorityField.wrapper, audienceField.wrapper),
      batchWrap,
      el("div", { class: "field-row" }, timingField.wrapper, scheduleField.wrapper),
      el("label", { class: "check" }, pinnedField, el("span", {}, "Pin this announcement to the top")));

    const submit = el("button", { class: "btn btn--primary", type: "submit" },
      el("span", { class: "spinner", "aria-hidden": "true" }),
      el("span", { class: "btn__label" }, isEdit ? "Save notice" : "Post announcement"));
    form.append(el("div", { class: "form-actions" }, submit));

    const ui = openModal({
      title: isEdit ? "Edit announcement" : "New announcement",
      description: isEdit ? "The audience sees changes the next time they open the portal."
        : "Target one batch, several, or all of your classes.",
      body: form,
      size: "modal--lg",
      actions: [{ label: "Cancel", variant: "secondary" }],
    });

    audienceField.input.value = existing?.audience === "all" ? "all" : "batches";
    syncAudience();
    if (existing?.status === "scheduled") {
      timingField.input.value = "keep";
      scheduleField.wrapper.hidden = true;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      showFieldErrors(form, {});
      const fields = {};
      const title = titleField.input.value.trim();
      const bodyText = bodyField.input.value.trim();
      const audience = audienceField.input.value;
      const selectedBatches = checks.filter(({ input }) => input.checked).map(({ batch }) => batch.id);
      if (title.length < 3) fields.title = "Give the notice a clear title.";
      if (bodyText.length < 10) fields.body = "Write at least a sentence (10+ characters).";
      if (audience === "batches" && !selectedBatches.length) {
        fields.batch_ids = "Choose at least one batch.";
      }
      if (timingField.input.value === "schedule" && !scheduleField.input.value) {
        fields.publish_at = "Choose when to publish.";
      }
      if (timingField.input.value === "schedule" && scheduleField.input.value
        && new Date(scheduleField.input.value) <= new Date()) {
        fields.publish_at = "Scheduled time must be in the future.";
      }
      if (Object.keys(fields).length) {
        showFieldErrors(form, fields);
        if (fields.batch_ids) {
          batchWrap.querySelector(".field__error").textContent = fields.batch_ids;
        }
        return;
      }

      const payload = {
        title, body: bodyText,
        priority: priorityField.input.value,
        pinned: pinnedField.checked,
        audience,
        batch_ids: audience === "batches" ? selectedBatches : uniqueBatches.map((batch) => batch.id),
      };
      if (timingField.input.value === "now") {
        payload.publish_at = new Date().toISOString().slice(0, 16);
      } else if (timingField.input.value === "schedule") {
        payload.publish_at = scheduleField.input.value;
        payload.audience = audience;
      }

      await busyButton(submit, async () => {
        try {
          if (isEdit) {
            await api(`/api/professor/announcements/${existing.id}`, {
              method: "PATCH", body: payload,
            });
            toast("Announcement updated.", "success");
          } else {
            await api("/api/professor/announcements", { method: "POST", body: payload });
            toast("Announcement posted.", "success");
          }
          ui.close();
          await reload();
        } catch (error) {
          if (error.fields && Object.keys(error.fields).length) {
            const mapped = { ...error.fields };
            if (mapped.batch_ids) {
              batchWrap.querySelector(".field__error").textContent = mapped.batch_ids;
              delete mapped.batch_ids;
            }
            showFieldErrors(form, mapped);
          } else {
            toast(error.message, "error");
          }
        }
      });
    });
  }

  async function remove(item) {
    const confirmed = await confirmDialog({
      title: "Delete this announcement?",
      message: `“${item.title}” will be removed from the student portal.`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    try {
      await api(`/api/professor/announcements/${item.id}`, { method: "DELETE" });
      toast("Announcement deleted.", "success");
      await reload();
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function reload() {
    try {
      const response = await api("/api/professor/announcements");
      state.items = response.data.items;
      state.pairs = response.data.batches;
      paintList();
    } catch (error) {
      toast(error.message, "error");
    }
  }

  paintList();
  if (params?.get("new") === "1") openEditor(null);
}
