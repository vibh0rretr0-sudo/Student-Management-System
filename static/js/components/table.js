/* Sortable, sticky-header data table. */
import { clear, el, iconEl } from "../core/ui.js";

function sortValue(row, column) {
  if (typeof column.sortValue === "function") return column.sortValue(row);
  const raw = row[column.key];
  if (raw === null || raw === undefined) return "";
  return raw;
}

function compare(a, b, direction) {
  if (typeof a === "number" && typeof b === "number") {
    return (a - b) * direction;
  }
  const first = String(a).toLowerCase();
  const second = String(b).toLowerCase();
  if (!first && second) return 1;
  if (first && !second) return -1;
  return first.localeCompare(second, "en", { numeric: true }) * direction;
}

export function dataTable({
  columns, rows, initialSort = null, empty = null, sortable = true,
  tableClass = "", onRowClick = null, caption = null,
}) {
  const state = {
    key: initialSort ? initialSort.key : null,
    direction: initialSort ? initialSort.direction || "asc" : "asc",
  };
  const wrapper = el("div", { class: "table-wrap" });

  function render() {
    clear(wrapper);
    if (!rows.length) {
      if (empty instanceof Node) {
        wrapper.append(empty);
      } else {
        wrapper.append(el("div", { class: "state" },
          el("p", { class: "state__title" }, typeof empty === "string" ? empty : "Nothing here yet")));
      }
      return;
    }

    const table = el("table", { class: `table ${tableClass}`.trim() });
    if (caption) table.append(el("caption", { class: "sr-only" }, caption));
    const head = el("thead");
    const headRow = el("tr");
    columns.forEach((column) => {
      const cell = el("th", {
        class: column.align === "right" ? "num" : column.align === "center" ? "text-right" : "",
        scope: "col",
      });
      if (sortable && column.sortable !== false) {
        const isActive = state.key === column.key;
        const button = el("button", {
          class: "th-sort", type: "button",
          "aria-sort": isActive
            ? (state.direction === "asc" ? "ascending" : "descending")
            : "none",
          onclick: () => {
            if (state.key === column.key) {
              state.direction = state.direction === "asc" ? "desc" : "asc";
            } else {
              state.key = column.key;
              state.direction = "asc";
            }
            render();
          },
        }, column.label);
        cell.append(button);
      } else {
        cell.textContent = column.label;
      }
      if (column.width) cell.style.width = column.width;
      headRow.append(cell);
    });
    head.append(headRow);
    table.append(head);

    let displayRows = [...rows];
    if (state.key) {
      const column = columns.find((item) => item.key === state.key);
      if (column) {
        const direction = state.direction === "asc" ? 1 : -1;
        displayRows.sort((a, b) => compare(sortValue(a, column), sortValue(b, column), direction));
      }
    }

    const tbody = el("tbody");
    displayRows.forEach((row) => {
      const tr = el("tr");
      if (onRowClick) {
        tr.classList.add("is-clickable");
        tr.tabIndex = 0;
        tr.addEventListener("click", (event) => {
          if (event.target.closest("button, a, input, select, textarea, label")) return;
          onRowClick(row);
        });
        tr.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onRowClick(row);
          }
        });
      }
      columns.forEach((column) => {
        const cell = el("td", {
          class: column.align === "right" ? "num" : column.align === "center" ? "text-right" : "",
        });
        const content = typeof column.render === "function"
          ? column.render(row)
          : row[column.key];
        if (content instanceof Node) cell.append(content);
        else if (Array.isArray(content)) content.forEach((item) => {
          if (item instanceof Node) cell.append(item);
          else cell.append(document.createTextNode(String(item)));
        });
        else cell.textContent = content === null || content === undefined ? "—" : String(content);
        tr.append(cell);
      });
      tbody.append(tr);
    });
    table.append(tbody);
    wrapper.append(table);
  }

  render();
  return wrapper;
}
