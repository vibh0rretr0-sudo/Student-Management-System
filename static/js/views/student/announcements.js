import { api } from "../../core/api.js";
import {
  debounce, el, errorPanel, fmtDate, fmtDateTime, iconEl, loadingView, pager,
  relativeTime, statusBadge, toast,
} from "../../core/ui.js";
import { pageHeader } from "../../components/page.js";

export const title = "Announcements";

export async function render(container) {
  const state = { q: "", priority: "", unread: false, from: "", to: "", page: 1 };
  container.append(loadingView("table"));

  async function load() {
    const query = new URLSearchParams({ page: String(state.page), per_page: "10" });
    if (state.q) query.set("q", state.q);
    if (state.priority) query.set("priority", state.priority);
    if (state.unread) query.set("unread", "1");
    if (state.from) query.set("from", state.from);
    if (state.to) query.set("to", state.to);

    let response;
    try {
      response = await api(`/api/student/announcements?${query}`);
    } catch (error) {
      container.innerHTML = "";
      container.append(errorPanel(error.message, () => {
        container.innerHTML = "";
        render(container);
      }));
      return;
    }
    paint(response.data, response.meta);
  }

  function paint(data, meta) {
    container.innerHTML = "";
    const markAllButton = el("button", { class: "btn btn--secondary btn--sm", type: "button" },
      iconEl("check"), "Mark all read");
    markAllButton.addEventListener("click", async () => {
      try {
        const response = await api("/api/student/announcements/read", {
          method: "POST", body: { all: true },
        });
        toast(response.data.message || "All announcements marked as read.", "success");
        await load();
      } catch (error) {
        toast(error.message, "error");
      }
    });

    container.append(pageHeader({
      title: "Announcements",
      subtitle: "Notices from your professors, newest first.",
      actions: [markAllButton],
    }));

    /* Filters */
    const searchInput = el("input", {
      class: "input", type: "search", placeholder: "Search notices…",
      value: state.q, "aria-label": "Search announcements",
    });
    const prioritySelect = el("select", { class: "select", "aria-label": "Priority" },
      el("option", { value: "" }, "All priorities"),
      el("option", { value: "urgent" }, "Urgent"),
      el("option", { value: "important" }, "Important"),
      el("option", { value: "normal" }, "Normal"));
    prioritySelect.value = state.priority;
    const unreadToggle = el("input", { type: "checkbox", checked: state.unread });
    const fromInput = el("input", { class: "input", type: "date", value: state.from, "aria-label": "Published from" });
    const toInput = el("input", { class: "input", type: "date", value: state.to, "aria-label": "Published to" });
    const reset = el("button", { class: "btn btn--ghost btn--sm", type: "button" },
      iconEl("refresh"), "Reset");
    const filters = el("section", { class: "panel" },
      el("div", { class: "filters" },
        el("div", { class: "search-field", style: { flex: "2 1 240px" } }, iconEl("search"), searchInput),
        el("div", { class: "field" }, el("label", { class: "field__label" }, "Priority"), prioritySelect),
        el("div", { class: "field" }, el("label", { class: "field__label" }, "From"), fromInput),
        el("div", { class: "field" }, el("label", { class: "field__label" }, "To"), toInput),
        el("label", { class: "check", style: { alignSelf: "center", paddingTop: "16px" } },
          unreadToggle, el("span", {}, "Unread only")),
        el("div", { class: "filters__actions" }, reset)));

    const apply = () => { state.page = 1; load(); };
    searchInput.addEventListener("input", debounce(() => {
      state.q = searchInput.value.trim();
      apply();
    }, 250));
    prioritySelect.addEventListener("change", () => {
      state.priority = prioritySelect.value;
      apply();
    });
    unreadToggle.addEventListener("change", () => {
      state.unread = unreadToggle.checked;
      apply();
    });
    [fromInput, toInput].forEach((input) => input.addEventListener("change", () => {
      state.from = fromInput.value;
      state.to = toInput.value;
      apply();
    }));
    reset.addEventListener("click", () => {
      state.q = "";
      state.priority = "";
      state.unread = false;
      state.from = "";
      state.to = "";
      state.page = 1;
      load();
    });

    const list = el("div", { class: "mt-4" });
    container.append(filters, list);

    if (!data.items.length) {
      list.append(el("section", { class: "panel" },
        el("div", { class: "state" },
          el("div", { class: "state__icon" }, iconEl("megaphone")),
          el("p", { class: "state__title" },
            meta.total ? "No notices match these filters" : "No announcements yet"),
          el("p", { class: "state__text" },
            meta.total
              ? "Try clearing the search or widening the date range."
              : "When your faculty post notices, they'll show up here with their priority and batch tags."),
          meta.total ? el("div", { class: "state__actions" },
            el("button", { class: "btn btn--secondary btn--sm", type: "button", onclick: () => reset.click() },
              "Clear filters")) : null)));
      return;
    }

    data.items.forEach((item) => list.append(noticeCard(item)));

    const pagination = pager({
      page: meta.page, pages: meta.pages, total: meta.total, perPage: meta.per_page,
      onPage: (next) => { state.page = next; load(); },
    });
    list.append(pagination);

    function noticeCard(item) {
      const card = el("article", {
        class: `notice-card ${item.is_read ? "" : "notice-card--unread"} ${item.pinned ? "notice-card--pinned" : ""}`.trim(),
      });
      const unreadDot = el("span", {
        class: "dot",
        style: { visibility: item.is_read ? "hidden" : "visible", marginTop: "7px" },
        "aria-label": item.is_read ? "Read" : "Unread",
      });
      const header = el("div", { class: "notice-card__head" },
        el("div", { class: "row-between", style: { gap: "10px" } },
          unreadDot,
          el("h3", { class: "notice-card__title" }, item.title),
          item.pinned ? el("span", { class: "badge badge--accent" }, "Pinned") : null));
      const metaRow = el("div", { class: "notice-card__meta" },
        statusBadge(item.priority),
        el("span", {}, iconEl("user"), ` ${item.professor}`),
        el("span", {}, fmtDateTime(item.publish_at)),
        el("span", { class: "muted" }, relativeTime(item.publish_at)),
        ...(item.batches || []).map((batch) => el("span", { class: "chip" }, batch)));
      const body = el("p", { class: "notice-card__body is-clamped" }, item.body);
      let expanded = false;
      const toggle = el("button", {
        class: "btn btn--link", type: "button", "aria-expanded": "false",
      }, "Read more");
      toggle.addEventListener("click", async () => {
        expanded = !expanded;
        body.classList.toggle("is-clamped", !expanded);
        toggle.textContent = expanded ? "Show less" : "Read more";
        toggle.setAttribute("aria-expanded", String(expanded));
        if (expanded && !item.is_read) {
          item.is_read = true;
          unreadDot.style.visibility = "hidden";
          card.classList.remove("notice-card--unread");
          try {
            await api("/api/student/announcements/read", {
              method: "POST", body: { id: item.id },
            });
          } catch (error) { /* read state is non-critical */ }
        }
      });
      const foot = el("div", { class: "notice-card__foot" }, toggle);
      card.append(header, metaRow, body, foot);
      return card;
    }
  }

  await load();
}
