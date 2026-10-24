import { api } from "../core/api.js";
import {
  avatarEl, confirmDialog, debounce, el, goTo, iconEl, openModal, relativeTime,
  clear, toast,
} from "../core/ui.js";

const SIDEBAR_KEY = "jecrc-sidebar-collapsed";

export function buildShell(boot, navItems) {
  const shellEl = document.getElementById("app-shell");
  const nav = document.getElementById("sidebar-nav");
  const collapseButton = document.getElementById("sidebar-collapse");
  const pageTitle = document.getElementById("page-title");
  const user = boot.user || {};

  /* ---------------------------------------------------------- Sidebar */
  function applyCollapsed(collapsed, persist = true) {
    shellEl.classList.toggle("is-collapsed", collapsed);
    collapseButton.setAttribute("aria-expanded", String(!collapsed));
    collapseButton.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
    collapseButton.setAttribute("title", collapsed ? "Expand sidebar (Ctrl+B)" : "Collapse sidebar (Ctrl+B)");
    navItems.forEach((item) => {
      const node = nav.querySelector(`[data-nav="${item.path}"]`);
      if (!node) return;
      if (collapsed) node.setAttribute("data-tooltip", item.label);
      else node.removeAttribute("data-tooltip");
    });
    if (persist) {
      try {
        localStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0");
      } catch (error) { /* ignore */ }
    }
  }

  navItems.forEach((item) => {
    const link = el("a", {
      class: "nav__item", href: `#${item.path}`, "data-nav": item.path,
      "aria-label": item.label,
    }, iconEl(item.icon), el("span", { class: "nav__label" }, item.label));
    nav.append(link);
  });

  let collapsed = false;
  try {
    collapsed = localStorage.getItem(SIDEBAR_KEY) === "1";
  } catch (error) { /* ignore */ }
  applyCollapsed(collapsed, false);
  collapseButton.addEventListener("click", () => {
    applyCollapsed(!shellEl.classList.contains("is-collapsed"));
  });

  /* ---------------------------------------------------------- Avatars */
  function paintAvatar(targetId, size) {
    const target = document.getElementById(targetId);
    if (!target) return;
    const fresh = avatarEl(user.display_name || user.name, user.photo_url || "", size);
    fresh.id = targetId;
    target.replaceWith(fresh);
  }
  paintAvatar("sidebar-avatar", "avatar--sm");
  paintAvatar("topbar-avatar", "avatar--sm");
  paintAvatar("user-menu-avatar", "");

  /* ---------------------------------------------------------- Clock */
  const clockTime = document.getElementById("clock-time");
  const clockDate = document.getElementById("clock-date");
  function updateClock() {
    const now = new Date();
    if (clockTime) {
      clockTime.textContent = now.toLocaleTimeString("en-IN", {
        hour: "2-digit", minute: "2-digit", hour12: true,
      });
    }
    if (clockDate) {
      clockDate.textContent = now.toLocaleDateString("en-GB", {
        weekday: "short", day: "2-digit", month: "short",
      });
    }
  }
  updateClock();
  window.setInterval(updateClock, 20000);

  /* ---------------------------------------------------------- Menus */
  const menus = [
    {
      button: document.getElementById("notification-button"),
      menu: document.getElementById("notification-menu"),
    },
    {
      button: document.getElementById("user-menu-button"),
      menu: document.getElementById("user-menu"),
    },
  ];

  function closeMenus(except = null) {
    menus.forEach(({ button, menu }) => {
      if (!menu || menu === except) return;
      menu.hidden = true;
      if (button) button.setAttribute("aria-expanded", "false");
    });
  }

  function toggleMenu(button, menu) {
    const willOpen = menu.hidden;
    closeMenus(menu);
    menu.hidden = !willOpen;
    button.setAttribute("aria-expanded", String(willOpen));
    if (willOpen && menu.id === "notification-menu") refreshNotifications();
  }

  menus.forEach(({ button, menu }) => {
    if (!button || !menu) return;
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleMenu(button, menu);
    });
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest(".menu-wrap, .notif-wrap")) return;
    closeMenus();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenus();
  });

  const sidebarUser = document.getElementById("sidebar-user");
  if (sidebarUser) {
    sidebarUser.addEventListener("click", () => {
      const menu = document.getElementById("user-menu");
      const button = document.getElementById("user-menu-button");
      if (menu && button) toggleMenu(button, menu);
    });
  }

  document.querySelectorAll("[data-route]").forEach((button) => {
    button.addEventListener("click", () => {
      goTo(button.getAttribute("data-route"));
      closeMenus();
    });
  });

  /* ---------------------------------------------------------- Notifications */
  const notifBadge = document.getElementById("notif-badge");
  const notifList = document.getElementById("notification-list");
  const readAllButton = document.getElementById("notifications-read-all");
  let notifications = [];

  function renderNotifications() {
    if (!notifList) return;
    clear(notifList);
    if (!notifications.length) {
      notifList.append(el("div", { class: "menu__empty" }, "You're all caught up."));
      return;
    }
    notifications.forEach((item) => {
      const button = el("button", {
        class: `menu__item notification-item ${item.is_read ? "" : "is-unread"}`,
        type: "button",
        onclick: async () => {
          closeMenus();
          if (!item.is_read) {
            try {
              await api(`/api/common/notifications/${item.id}/read`, { method: "POST" });
              item.is_read = true;
              updateBadge();
            } catch (error) { /* navigating is more important */ }
          }
          goTo(item.link || "/#/overview");
        },
      });
      const dot = el("span", {
        class: "dot",
        style: { visibility: item.is_read ? "hidden" : "visible", marginTop: "6px" },
      });
      const body = el("span", { style: { minWidth: "0" } },
        el("span", { class: "notification-item__title" }, item.title),
        el("span", { class: "notification-item__meta" },
          `${item.body || ""} · ${relativeTime(item.created_at)}`));
      button.append(dot, body);
      notifList.append(button);
    });
  }

  function updateBadge() {
    const unread = notifications.filter((item) => !item.is_read).length;
    if (!notifBadge) return;
    notifBadge.hidden = unread === 0;
    notifBadge.textContent = unread > 9 ? "9+" : String(unread);
    if (readAllButton) readAllButton.disabled = unread === 0;
  }

  async function refreshNotifications() {
    try {
      const response = await api("/api/common/notifications?per_page=15");
      notifications = response.data.items || [];
      renderNotifications();
      updateBadge();
    } catch (error) {
      if (notifList) {
        clear(notifList);
        notifList.append(el("div", { class: "menu__empty" },
          "Notifications couldn't be loaded."));
      }
    }
  }

  if (readAllButton) {
    readAllButton.addEventListener("click", async () => {
      try {
        await api("/api/common/notifications/read-all", { method: "POST" });
        notifications = notifications.map((item) => ({ ...item, is_read: true }));
        renderNotifications();
        updateBadge();
        toast("All notifications marked as read.", "success");
      } catch (error) {
        toast(error.message, "error");
      }
    });
  }

  refreshNotifications();
  window.setInterval(() => {
    if (document.visibilityState === "visible") refreshNotifications();
  }, 120000);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") refreshNotifications();
  });

  /* ---------------------------------------------------------- Logout */
  async function performLogout({ silent = false } = {}) {
    if (!silent) {
      const confirmed = await confirmDialog({
        title: "Sign out of the portal?",
        message: "Any unsaved changes on this page will be lost.",
        confirmLabel: "Sign out",
        danger: true,
      });
      if (!confirmed) return;
    }
    try {
      await api("/api/auth/logout", { method: "POST", authRedirect: false });
    } catch (error) {
      /* The cookie is cleared server-side even if the request raced expiry. */
    }
    document.body.style.transition = "opacity 260ms ease";
    document.body.style.opacity = "0";
    window.setTimeout(() => window.location.assign("/"), 240);
  }

  ["logout-button", "user-menu-logout"].forEach((id) => {
    const button = document.getElementById(id);
    if (button) button.addEventListener("click", () => performLogout());
  });

  /* ---------------------------------------------------------- Command palette */
  const palette = el("dialog", { class: "palette", "aria-label": "Search the portal" });
  const paletteInput = el("input", {
    class: "palette__input", type: "search", placeholder: "Search pages, subjects, assignments, notices…",
    "aria-label": "Search the portal", autocomplete: "off", spellcheck: "false",
  });
  const paletteResults = el("div", { class: "palette__results", role: "listbox", "aria-label": "Search results" });
  const palettePanel = el("div", { class: "palette__panel" });
  palettePanel.append(
    el("div", { class: "palette__search" }, iconEl("search"), paletteInput,
      el("kbd", {}, "Esc")),
    paletteResults,
    el("div", { class: "palette__foot" },
      el("span", {}, "↑ ↓ to move"), el("span", {}, "↵ to open"), el("span", {}, "Esc to close")),
  );
  palette.append(palettePanel);
  document.body.append(palette);

  let paletteResultsData = [];
  let paletteActive = 0;
  let searchController = null;

  const typeIcons = {
    Page: "overview", Subject: "book", Assignment: "clipboard", Announcement: "megaphone",
  };

  function renderPalette(items, { emptyMessage = "No matches. Try a subject code or a page name." } = {}) {
    clear(paletteResults);
    paletteResultsData = items;
    paletteActive = 0;
    if (!items.length) {
      paletteResults.append(el("div", { class: "palette__empty" }, emptyMessage));
      return;
    }
    let lastType = null;
    items.forEach((item, index) => {
      if (item.type !== lastType) {
        paletteResults.append(el("div", { class: "palette__group" }, item.type));
        lastType = item.type;
      }
      const button = el("button", {
        class: `palette__item ${index === 0 ? "is-active" : ""}`,
        type: "button", role: "option", "aria-selected": index === 0 ? "true" : "false",
        onclick: () => choosePaletteItem(index),
      }, iconEl(typeIcons[item.type] || "search"),
        el("span", {}, item.label),
        item.sub ? el("small", {}, item.sub) : null);
      button.dataset.index = String(index);
      paletteResults.append(button);
    });
  }

  function setPaletteActive(index) {
    const buttons = [...paletteResults.querySelectorAll(".palette__item")];
    if (!buttons.length) return;
    paletteActive = Math.max(0, Math.min(buttons.length - 1, index));
    buttons.forEach((button, buttonIndex) => {
      const active = buttonIndex === paletteActive;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
      if (active) button.scrollIntoView({ block: "nearest" });
    });
  }

  function choosePaletteItem(index) {
    const item = paletteResultsData[index];
    if (!item) return;
    palette.close();
    if (item.link) goTo(item.link);
  }

  function defaultPaletteItems() {
    return navItems.map((item) => ({
      type: "Page", label: item.label, sub: "Jump to", link: `/#${item.path}`,
    }));
  }

  function openPalette() {
    closeMenus();
    paletteInput.value = "";
    renderPalette(defaultPaletteItems());
    if (!palette.open) palette.showModal();
    window.setTimeout(() => paletteInput.focus(), 20);
  }

  const runSearch = debounce(async (query) => {
    if (searchController) searchController.abort();
    if (!query || query.length < 2) {
      renderPalette(defaultPaletteItems());
      return;
    }
    searchController = new AbortController();
    paletteResults.setAttribute("aria-busy", "true");
    try {
      const response = await api(`/api/common/search?q=${encodeURIComponent(query)}`, {
        signal: searchController.signal,
      });
      const items = response.data.results || [];
      const pageFallback = navItems
        .filter((item) => item.label.toLowerCase().includes(query.toLowerCase()))
        .map((item) => ({
          type: "Page", label: item.label, sub: "Jump to", link: `/#${item.path}`,
        }));
      const combined = [...pageFallback,
        ...items.filter((item) => item.type !== "Page")];
      renderPalette(combined);
    } catch (error) {
      if (error.name === "AbortError") return;
      renderPalette([], { emptyMessage: "Search is unavailable right now. Try one of the pages from the sidebar." });
    } finally {
      paletteResults.removeAttribute("aria-busy");
    }
  }, 220);

  paletteInput.addEventListener("input", () => runSearch(paletteInput.value.trim()));
  paletteInput.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setPaletteActive(paletteActive + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setPaletteActive(paletteActive - 1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      choosePaletteItem(paletteActive);
    }
  });
  palette.addEventListener("click", (event) => {
    if (event.target === palette) palette.close();
  });

  const searchTrigger = document.getElementById("search-trigger");
  if (searchTrigger) searchTrigger.addEventListener("click", openPalette);
  const paletteMenuButton = document.getElementById("open-palette");
  if (paletteMenuButton) paletteMenuButton.addEventListener("click", () => {
    closeMenus();
    openPalette();
  });

  document.addEventListener("keydown", (event) => {
    const meta = event.ctrlKey || event.metaKey;
    if (meta && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openPalette();
    }
    if (meta && event.key.toLowerCase() === "b") {
      event.preventDefault();
      applyCollapsed(!shellEl.classList.contains("is-collapsed"));
    }
  });

  /* ---------------------------------------------------------- Session timeout */
  const idleMinutes = Number(boot.idle_minutes) || 30;
  const warnMinutes = Math.min(Number(boot.warn_minutes) || 25, idleMinutes - 1);
  let lastActivity = Date.now();
  let warningOpen = false;
  let warningUi = null;

  const markActive = () => {
    if (!warningOpen) lastActivity = Date.now();
  };
  ["pointerdown", "keydown", "mousemove", "scroll", "touchstart"].forEach((eventName) => {
    document.addEventListener(eventName, markActive, { passive: true });
  });

  function showTimeoutWarning() {
    if (warningOpen) return;
    warningOpen = true;
    const shownAt = Date.now();
    const deadline = shownAt + (idleMinutes - warnMinutes) * 60 * 1000;
    const countdown = el("span", { class: "session-modal__time", "aria-live": "off" }, "05:00");
    const body = el("div", { class: "stack" },
      el("p", { class: "muted" },
        `You've been inactive for ${warnMinutes} minutes. For your security the portal will sign you out when the timer reaches zero.`),
      el("div", { class: "callout callout--warning" }, iconEl("clock"),
        el("div", {}, "Time remaining ", countdown)),
    );

    const timer = window.setInterval(() => {
      const left = Math.max(0, deadline - Date.now());
      const minutes = Math.floor(left / 60000);
      const seconds = Math.floor((left % 60000) / 1000);
      countdown.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
      if (left <= 0) {
        window.clearInterval(timer);
        if (warningUi) warningUi.close();
        window.location.assign("/?expired=1");
      }
    }, 1000);

    warningUi = openModal({
      title: "Still there?",
      description: "Your session is about to time out.",
      body, dismissible: false, size: "modal--sm",
      actions: [
        {
          label: "Sign out now", variant: "ghost",
          onClick: async () => { await performLogout({ silent: true }); return false; },
        },
        {
          label: "Stay signed in", variant: "primary",
          onClick: async () => {
            try {
              await api("/api/auth/heartbeat", { method: "POST", authRedirect: false });
              lastActivity = Date.now();
              warningOpen = false;
              window.clearInterval(timer);
              toast("Session extended for another 30 minutes.", "success");
            } catch (error) {
              toast("We couldn't extend your session. Please sign in again.", "error");
              return false;
            }
          },
        },
      ],
      onClose: () => {
        window.clearInterval(timer);
        warningOpen = false;
        warningUi = null;
      },
    });
  }

  window.setInterval(() => {
    if (document.visibilityState !== "visible" || warningOpen) return;
    const idleMs = Date.now() - lastActivity;
    if (idleMs >= idleMinutes * 60 * 1000) {
      window.location.assign("/?expired=1");
      return;
    }
    if (idleMs >= warnMinutes * 60 * 1000) showTimeoutWarning();
  }, 15000);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && warningOpen) return;
    if (document.visibilityState === "visible") {
      const idleMs = Date.now() - lastActivity;
      if (idleMs >= warnMinutes * 60 * 1000) showTimeoutWarning();
    }
  });

  /* ---------------------------------------------------------- Route updates */
  function setRoute(route, name) {
    if (pageTitle) pageTitle.textContent = route?.title || "Not found";
    navItems.forEach((item) => {
      const node = nav.querySelector(`[data-nav="${item.path}"]`);
      if (!node) return;
      if (item.path === `/${name}`) node.setAttribute("aria-current", "page");
      else node.removeAttribute("aria-current");
    });
    closeMenus();
  }

  return {
    setRoute,
    refreshNotifications,
    navigate: (path) => {
      window.location.hash = path.startsWith("#") ? path : `#${path}`;
    },
  };
}
