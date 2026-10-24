/* Shared UI primitives. All user data is inserted as text nodes. */
import { icon } from "./icons.js";

let idCounter = 0;
function uid(prefix = "ui") {
  idCounter += 1;
  return `${prefix}-${idCounter}`;
}

export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  Object.entries(props || {}).forEach(([key, value]) => {
    if (value === null || value === undefined || value === false) return;
    if (key === "class" || key === "className") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else if (key === "text") node.textContent = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key === "style" && typeof value === "object") Object.assign(node.style, value);
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === "value" || key === "checked" || key === "disabled") {
      node[key] = value;
    } else {
      node.setAttribute(key, value === true ? "" : String(value));
    }
  });
  appendChildren(node, children);
  return node;
}

export function appendChildren(node, children) {
  children.flat(Infinity).forEach((child) => {
    if (child === null || child === undefined || child === false) return;
    if (child instanceof Node) node.append(child);
    else node.append(document.createTextNode(String(child)));
  });
}

export function iconEl(name, className = "") {
  const template = document.createElement("template");
  template.innerHTML = icon(name, className);
  return template.content.firstElementChild;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

export function badge(text, variant = "neutral") {
  return el("span", { class: `badge badge--${variant}` }, text);
}

/* ------------------------------------------------------------------ Toasts */
export function toast(message, type = "info", { duration = 4200, actionLabel, onAction } = {}) {
  let host = document.getElementById("toasts");
  if (!host) {
    host = el("div", { class: "toasts", id: "toasts", "aria-live": "polite" });
    document.body.append(host);
  }
  const iconName = type === "success" ? "checkCircle"
    : type === "error" ? "alert"
    : type === "warning" ? "alert" : "info";
  const node = el("div", { class: `toast toast--${type}`, role: type === "error" ? "alert" : "status" });
  node.append(iconEl(iconName));
  const bodyNode = el("div", { class: "toast__body" },
    el("div", { class: "toast__message" }, message));
  if (actionLabel && typeof onAction === "function") {
    const actionWrap = el("div", { class: "toast__action" });
    const action = el("button", {
      class: "btn btn--link", type: "button", text: actionLabel,
      onclick: () => { dismiss(); onAction(); },
    });
    actionWrap.append(action);
    bodyNode.append(actionWrap);
  }
  node.append(bodyNode);
  const close = el("button", {
    class: "modal-close", type: "button", "aria-label": "Dismiss notification",
    onclick: () => dismiss(),
  }, iconEl("x"));
  node.append(close);
  host.append(node);

  let timer = null;
  const dismiss = () => {
    if (!node.isConnected) return;
    clearTimeout(timer);
    node.classList.add("is-leaving");
    window.setTimeout(() => node.remove(), 180);
  };
  if (duration > 0) timer = window.setTimeout(dismiss, duration);
  return { dismiss };
}

/* ------------------------------------------------------------------ Modals */
export function openModal({
  title, description, body, actions = [], size = "", dismissible = true,
  className = "", onClose = null, initialFocus = null,
}) {
  const dialog = el("dialog", {
    class: `modal ${size} ${className}`.trim(),
    "aria-labelledby": uid("modal-title"),
  });
  const panel = el("div", { class: "modal__panel" });
  const head = el("div", { class: "modal__head" });
  const headingWrap = el("div", {},
    el("h2", { class: "modal__title", id: dialog.getAttribute("aria-labelledby") }, title || ""));
  if (description) headingWrap.append(el("p", { class: "modal__desc" }, description));
  head.append(headingWrap);
  const closeButton = el("button", {
    type: "button", class: "modal-close", "aria-label": "Close dialog",
    onclick: () => close(),
  }, iconEl("x"));
  head.append(closeButton);

  const bodyNode = el("div", { class: "modal__body" });
  if (body instanceof Node) bodyNode.append(body);
  else if (body) bodyNode.append(el("p", {}, body));

  panel.append(head, bodyNode);
  if (actions.length) {
    const foot = el("div", { class: "modal__foot" });
    actions.forEach((action) => {
      const button = el("button", {
        class: `btn btn--${action.variant || "secondary"}`, type: "button",
        onclick: async () => {
          if (action.onClick) {
            button.classList.add("is-loading");
            button.disabled = true;
            try {
              const result = await action.onClick();
              if (result === false) return;
            } catch (error) {
              button.classList.remove("is-loading");
              button.disabled = false;
              return;
            }
          }
          if (action.closeOnClick !== false) close();
        },
      }, action.icon ? iconEl(action.icon) : null,
        el("span", { class: "btn__label" }, action.label));
      foot.append(button);
    });
    panel.append(foot);
  }
  dialog.append(panel);
  document.body.append(dialog);

  let closed = false;
  const close = (value) => {
    if (closed) return;
    closed = true;
    if (dialog.open) dialog.close();
    dialog.remove();
    if (typeof onClose === "function") onClose(value);
  };

  dialog.addEventListener("cancel", (event) => {
    if (!dismissible) event.preventDefault();
    else close();
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog && dismissible) close();
  });

  dialog.showModal();
  const focusTarget = initialFocus || dialog.querySelector(
    "input:not([type=hidden]), select, textarea, button.btn--primary"
  ) || closeButton;
  window.setTimeout(() => focusTarget.focus(), 30);
  return { dialog, close, body: bodyNode };
}

export function confirmDialog({
  title, message, confirmLabel = "Confirm", cancelLabel = "Cancel",
  danger = false, details = null,
}) {
  return new Promise((resolve) => {
    let answered = false;
    const body = el("div", {});
    body.append(el("p", { class: "muted" }, message));
    if (details) body.append(el("div", { class: "callout callout--info mt-3" },
      iconEl("info"), el("div", {}, details)));
    const ui = openModal({
      title, body, size: "modal--sm",
      actions: [
        { label: cancelLabel, variant: "secondary", onClick: () => { answered = true; resolve(false); } },
        { label: confirmLabel, variant: danger ? "danger" : "primary",
          onClick: () => { answered = true; resolve(true); } },
      ],
      onClose: () => { if (!answered) resolve(false); },
    });
    return ui;
  });
}

export function openDrawer({ title, subtitle, body, footer = [], onClose = null }) {
  const dialog = el("dialog", { class: "drawer", "aria-labelledby": uid("drawer-title") });
  const panel = el("div", { class: "drawer__panel" });
  const head = el("div", { class: "drawer__head" });
  const titleWrap = el("div", {},
    el("h2", { class: "modal__title", id: dialog.getAttribute("aria-labelledby") }, title || ""));
  if (subtitle) titleWrap.append(el("p", { class: "modal__desc" }, subtitle));
  head.append(titleWrap);
  head.append(el("button", {
    class: "modal-close", type: "button", "aria-label": "Close panel",
    onclick: () => close(),
  }, iconEl("x")));
  const bodyNode = el("div", { class: "drawer__body" },
    body instanceof Node ? body : el("p", {}, body || ""));
  const foot = el("div", { class: "drawer__foot" });
  footer.forEach((action) => {
    const button = el("button", {
      class: `btn btn--${action.variant || "secondary"}`, type: "button",
      onclick: async () => {
        if (action.onClick) {
          button.classList.add("is-loading");
          button.disabled = true;
          try {
            const result = await action.onClick();
            if (result === false) return;
          } catch (error) {
            button.classList.remove("is-loading");
            button.disabled = false;
            return;
          }
        }
        if (action.closeOnClick !== false) close();
      },
    }, action.icon ? iconEl(action.icon) : null, el("span", { class: "btn__label" }, action.label));
    foot.append(button);
  });
  if (footer.length) panel.append(head, bodyNode, foot);
  else panel.append(head, bodyNode);
  dialog.append(panel);
  document.body.append(dialog);
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    if (dialog.open) dialog.close();
    dialog.remove();
    if (typeof onClose === "function") onClose();
  };
  dialog.addEventListener("cancel", (event) => { event.preventDefault(); close(); });
  dialog.addEventListener("click", (event) => { if (event.target === dialog) close(); });
  dialog.showModal();
  return { dialog, close, body: bodyNode, footer: foot };
}

/* ------------------------------------------------------------------ States */
export function emptyState({ title, message, iconName = "inbox", actions = [] }) {
  const node = el("div", { class: "state" });
  node.append(el("div", { class: "state__icon" }, iconEl(iconName)));
  node.append(el("p", { class: "state__title" }, title));
  if (message) node.append(el("p", { class: "state__text" }, message));
  if (actions.length) {
    const wrap = el("div", { class: "state__actions" });
    actions.forEach((action) => wrap.append(el("button", {
      class: `btn btn--${action.variant || "secondary"} btn--sm`, type: "button",
      onclick: action.onClick,
    }, action.icon ? iconEl(action.icon) : null, action.label)));
    node.append(wrap);
  }
  return node;
}

export function errorPanel(message, onRetry) {
  const node = emptyState({
    title: "We couldn't load this",
    message: message || "Something went wrong while fetching your data.",
    iconName: "alert",
    actions: onRetry ? [{ label: "Try again", variant: "primary", icon: "refresh", onClick: onRetry }] : [],
  });
  node.classList.add("state--error");
  return node;
}

export function loadingView(kind = "dashboard") {
  const wrap = el("div", { class: "view-skeleton", "aria-hidden": "true" });
  const head = el("div", { class: "view-skeleton__head" },
    el("div", { style: { width: "min(420px, 60%)" } },
      el("div", { class: "skeleton skeleton--text", style: { width: "35%" } }),
      el("div", { class: "skeleton skeleton--text", style: { width: "78%", height: "32px" } }),
      el("div", { class: "skeleton skeleton--text", style: { width: "52%" } })),
    el("div", { class: "skeleton", style: { width: "130px", height: "40px" } }));
  wrap.append(head);
  if (kind === "table") {
    wrap.append(el("div", { class: "skeleton skeleton--line" }));
    wrap.append(el("div", { class: "skeleton skeleton--line" }));
    wrap.append(el("div", { class: "skeleton skeleton--line" }));
    wrap.append(el("div", { class: "skeleton skeleton--line" }));
  } else {
    wrap.append(el("div", { class: "view-skeleton__grid" },
      el("div", { class: "skeleton skeleton--chart" }),
      el("div", { class: "skeleton skeleton--chart" })));
    wrap.append(el("div", { class: "skeleton skeleton--line" }));
    wrap.append(el("div", { class: "skeleton skeleton--line" }));
  }
  return wrap;
}

/* ------------------------------------------------------------------ Fields */
export function formField({
  label, name, type = "text", value = "", placeholder = "", hint = "",
  required = false, options = null, rows = 4, autocomplete = null,
  min = null, max = null, step = null, iconName = null, disabled = false,
  inputMode = null,
}) {
  const id = uid(`field-${name || "input"}`);
  const wrapper = el("div", { class: "field" });
  if (label) {
    const labelNode = el("label", { class: "field__label", for: id }, label);
    if (required) labelNode.append(el("span", { "aria-hidden": "true", style: { color: "var(--danger)" } }, " *"));
    wrapper.append(labelNode);
  }

  let input;
  if (type === "select") {
    input = el("select", { class: "select", id, name });
    (options || []).forEach((option) => {
      const item = typeof option === "string" ? { value: option, label: option } : option;
      input.append(el("option", { value: item.value }, item.label));
    });
    if (value !== "" && value !== null) input.value = String(value);
  } else if (type === "textarea") {
    input = el("textarea", { class: "textarea", id, name, rows, placeholder });
    input.value = value;
  } else {
    const inputProps = {
      class: "input", id, name, type, placeholder, value,
      min, max, step, inputmode: inputMode, disabled,
      autocomplete: autocomplete || "off",
    };
    input = el("input", inputProps);
    if (required) input.setAttribute("required", "");
  }

  const describedBy = [];
  if (hint) {
    const hintNode = el("span", { class: "field__hint", id: `${id}-hint` }, hint);
    wrapper.append(hintNode);
    describedBy.push(`${id}-hint`);
  }
  if (iconName && type !== "textarea" && type !== "select") {
    const wrap = el("div", { class: "input-wrap" }, iconEl(iconName), input);
    wrapper.append(wrap);
  } else {
    wrapper.append(input);
  }
  const error = el("span", { class: "field__error", id: `${id}-error`, role: "alert" });
  wrapper.append(error);
  if (describedBy.length) input.setAttribute("aria-describedby", describedBy.join(" "));
  return { wrapper, input, error, id, name };
}

export function setFieldError(input, message) {
  const field = input.closest(".field");
  const error = field ? field.querySelector(".field__error") : null;
  if (message) {
    input.setAttribute("aria-invalid", "true");
    if (error) {
      error.textContent = message;
      if (error.id) input.setAttribute("aria-describedby", error.id);
    }
  } else {
    input.removeAttribute("aria-invalid");
    if (error) error.textContent = "";
  }
}

export function clearFormErrors(form) {
  form.querySelectorAll("[aria-invalid]").forEach((input) => setFieldError(input, ""));
}

export function showFieldErrors(form, fields) {
  clearFormErrors(form);
  Object.entries(fields || {}).forEach(([name, message]) => {
    const input = form.querySelector(`[name="${name}"]`);
    if (input) setFieldError(input, message);
  });
  const firstInvalid = form.querySelector("[aria-invalid='true']");
  if (firstInvalid) firstInvalid.focus();
}

export async function busyButton(button, task) {
  if (!button || button.classList.contains("is-loading")) return null;
  button.classList.add("is-loading");
  button.disabled = true;
  try {
    return await task();
  } finally {
    button.classList.remove("is-loading");
    button.disabled = false;
  }
}

/* ------------------------------------------------------------------ Format */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function toDate(value) {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const parsed = new Date(`${value}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function fmtDate(value, { withYear = true, weekday = false } = {}) {
  const day = toDate(value);
  if (!day) return "—";
  const base = `${day.getDate()} ${MONTHS[day.getMonth()]}`;
  return `${weekday ? `${WEEKDAYS[day.getDay()]}, ` : ""}${base}${withYear ? ` ${day.getFullYear()}` : ""}`;
}

export function fmtDateTime(value) {
  const day = toDate(value);
  if (!day) return "—";
  let hours = day.getHours();
  const minutes = String(day.getMinutes()).padStart(2, "0");
  const suffix = hours >= 12 ? "pm" : "am";
  hours = hours % 12 || 12;
  return `${day.getDate()} ${MONTHS[day.getMonth()]}, ${hours}:${minutes} ${suffix}`;
}

export function fmtClock(hhmm) {
  if (!hhmm) return "—";
  const [hourString, minute = "00"] = String(hhmm).split(":");
  let hour = Number.parseInt(hourString, 10);
  if (Number.isNaN(hour)) return String(hhmm);
  const suffix = hour >= 12 ? "pm" : "am";
  hour = hour % 12 || 12;
  return `${hour}:${minute.slice(0, 2)} ${suffix}`;
}

export function relativeTime(value) {
  const day = toDate(value);
  if (!day) return "";
  const diff = Date.now() - day.getTime();
  const future = diff < 0;
  const seconds = Math.abs(diff) / 1000;
  let text;
  if (seconds < 60) text = "just now";
  else if (seconds < 3600) text = `${Math.round(seconds / 60)}m`;
  else if (seconds < 86400) text = `${Math.round(seconds / 3600)}h`;
  else if (seconds < 86400 * 30) text = `${Math.round(seconds / 86400)}d`;
  else text = fmtDate(day, { withYear: false });
  if (text === "just now") return text;
  return future ? `in ${text}` : `${text} ago`;
}

export function initials(name) {
  return String(name || "?")
    .trim()
    .replace(/^(Dr|Prof)\.\s+/i, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function formatFileSize(bytes) {
  const size = Number(bytes) || 0;
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatPercent(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return `${Number(value).toFixed(digits)}%`;
}

export function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${Number(count) === 1 ? singular : plural}`;
}

export function debounce(fn, wait = 250) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), wait);
  };
}

export function statusBadge(status) {
  const map = {
    pending: ["Pending", "warning"],
    submitted: ["Submitted", "info"],
    overdue: ["Overdue", "danger"],
    graded: ["Graded", "success"],
    present: ["Present", "success"],
    absent: ["Absent", "danger"],
    late: ["Late", "warning"],
    active: ["Active", "primary"],
    ongoing: ["Ongoing", "success"],
    upcoming: ["Upcoming", "info"],
    past_due: ["Past due", "warning"],
    completed: ["Completed", "success"],
    published: ["Published", "success"],
    scheduled: ["Scheduled", "info"],
    unread: ["Unread", "primary"],
    normal: ["Normal", "neutral"],
    important: ["Important", "warning"],
    urgent: ["Urgent", "danger"],
  };
  const [label, variant] = map[status] || [String(status || "—"), "neutral"];
  return badge(label, variant);
}

export function avatarEl(name, photoUrl, size = "") {
  const node = el("span", {
    class: `avatar ${size}`.trim(),
    title: name || "",
    "aria-hidden": "true",
  });
  if (photoUrl) {
    const image = el("img", { src: photoUrl, alt: "", loading: "lazy" });
    image.addEventListener("error", () => {
      image.remove();
      node.textContent = initials(name);
    });
    node.append(image);
  } else {
    node.textContent = initials(name);
  }
  return node;
}

export function pager({ page, pages, total, perPage, onPage }) {
  const wrap = el("div", { class: "pager" });
  const from = total === 0 ? 0 : (page - 1) * perPage + 1;
  const to = Math.min(total, page * perPage);
  wrap.append(el("span", { class: "pager__info" },
    `${from}–${to} of ${total}`));
  const controls = el("div", { class: "pager__controls" });
  controls.append(el("button", {
    class: "btn btn--secondary btn--sm", type: "button", "aria-label": "Previous page",
    disabled: page <= 1, onclick: () => onPage(page - 1),
  }, iconEl("chevronLeft")));

  const numbers = [];
  const push = (number) => { if (!numbers.includes(number)) numbers.push(number); };
  push(1);
  for (let index = Math.max(2, page - 1); index <= Math.min(pages - 1, page + 1); index += 1) push(index);
  if (pages > 1) push(pages);
  numbers.sort((a, b) => a - b);

  let previous = 0;
  numbers.forEach((number) => {
    if (previous && number - previous > 1) controls.append(el("span", { class: "muted" }, "…"));
    controls.append(el("button", {
      class: "pager__page", type: "button",
      "aria-current": number === page ? "page" : null,
      onclick: () => onPage(number),
    }, String(number)));
    previous = number;
  });

  controls.append(el("button", {
    class: "btn btn--secondary btn--sm", type: "button", "aria-label": "Next page",
    disabled: page >= pages, onclick: () => onPage(page + 1),
  }, iconEl("chevronRight")));
  wrap.append(controls);
  return wrap;
}

export function callout(text, variant = "info", iconName = "info") {
  return el("div", { class: `callout callout--${variant}` },
    iconEl(iconName), el("div", {}, text));
}

export function goTo(link) {
  if (!link) return;
  if (link.startsWith("#/")) {
    window.location.hash = link.slice(1);
    return;
  }
  if (link.startsWith("/#/")) {
    window.location.hash = link.slice(1);
    return;
  }
  if (link.startsWith("/")) {
    window.location.assign(link);
    return;
  }
  // Never follow an unexpected external URL from API-provided links.
}

export function routeFromLink(link) {
  if (!link) return null;
  const match = String(link).match(/#\/([a-z0-9-]+)/i);
  if (match) return `/${match[1]}`;
  return null;
}

export function currentHashRoute() {
  const raw = window.location.hash.replace(/^#\/?/, "");
  return raw.split("?")[0] || "overview";
}
