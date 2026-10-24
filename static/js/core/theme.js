/* Theme controller: theme is applied before paint by the inline head script;
   this module keeps the toggle buttons, storage and system preference in sync. */
const STORAGE_KEY = "jecrc-theme";
const media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

export function currentTheme() {
  return document.documentElement.getAttribute("data-theme") === "dark"
    ? "dark"
    : "light";
}

function storedTheme() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "dark" || value === "light" ? value : null;
  } catch (error) {
    return null;
  }
}

function syncControls(theme) {
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    const next = theme === "dark" ? "light" : "dark";
    button.setAttribute("aria-pressed", String(theme === "dark"));
    button.setAttribute("aria-label", `Switch to ${next} theme`);
    button.setAttribute("title", `Switch to ${next} theme`);
  });
}

export function setTheme(theme, { persist = true } = {}) {
  const next = theme === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  syncControls(next);
  if (persist) {
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch (error) {
      /* ignore storage failures */
    }
  }
  window.dispatchEvent(new CustomEvent("themechange", { detail: { theme: next } }));
}

export function toggleTheme() {
  setTheme(currentTheme() === "dark" ? "light" : "dark");
}

let initialized = false;
export function initTheme() {
  if (initialized) {
    syncControls(currentTheme());
    return;
  }
  initialized = true;
  syncControls(currentTheme());

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-theme-toggle]");
    if (button) {
      event.preventDefault();
      toggleTheme();
    }
  });

  if (media) {
    const handleSystemChange = (event) => {
      if (!storedTheme()) {
        setTheme(event.matches ? "dark" : "light", { persist: false });
      }
    };
    if (media.addEventListener) {
      media.addEventListener("change", handleSystemChange);
    } else if (media.addListener) {
      media.addListener(handleSystemChange);
    }
  }
}

initTheme();
