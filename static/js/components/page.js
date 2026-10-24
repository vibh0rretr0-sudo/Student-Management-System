import { el } from "../core/ui.js";

export function pageHeader({ title, subtitle = "", actions = [], id = null }) {
  const head = el("header", { class: "view__head", id });
  const left = el("div", {},
    el("h2", {}, title),
    subtitle ? el("p", {}, subtitle) : null);
  head.append(left);
  if (actions.length) {
    const wrap = el("div", { class: "page-actions" });
    actions.forEach((action) => wrap.append(action));
    head.append(wrap);
  }
  return head;
}

export function panel({
  title = "", subtitle = "", actions = [], body, footer = null,
  className = "", id = null,
}) {
  const section = el("section", { class: `panel ${className}`.trim(), id });
  if (title || subtitle || actions.length) {
    const head = el("div", { class: "panel__head" });
    const text = el("div", {},
      title ? el("h3", { class: "panel__title" }, title) : null,
      subtitle ? el("p", { class: "panel__sub" }, subtitle) : null);
    head.append(text);
    if (actions.length) {
      const wrap = el("div", { class: "cluster" });
      actions.forEach((action) => wrap.append(action));
      head.append(wrap);
    }
    section.append(head);
  }
  const content = el("div", { class: "panel__body" });
  if (body instanceof Node) content.append(body);
  else if (body) content.append(body);
  section.append(content);
  if (footer) section.append(el("div", { class: "panel__foot" }, footer));
  return section;
}
