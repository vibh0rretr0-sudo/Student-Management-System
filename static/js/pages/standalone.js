import "../core/theme.js";

document.querySelectorAll("[data-retry]").forEach((button) => {
  button.addEventListener("click", () => window.location.reload());
});
