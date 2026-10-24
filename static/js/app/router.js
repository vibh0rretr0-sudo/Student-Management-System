import { disposeCharts } from "../core/charts.js";
import { el, errorPanel, currentHashRoute } from "../core/ui.js";

export function createRouter({ routes, container, onRouteChange, defaultRoute = "overview" }) {
  let started = false;
  let renderToken = 0;

  function parse() {
    const raw = window.location.hash.replace(/^#\/?/, "");
    const [name, query = ""] = raw.split("?");
    return {
      name: name || defaultRoute,
      params: new URLSearchParams(query),
    };
  }

  async function render() {
    const { name, params } = parse();
    const route = routes[name];
    const token = ++renderToken;

    disposeCharts();
    window.dispatchEvent(new CustomEvent("view:unmount"));
    container.innerHTML = "";
    container.classList.add("is-switching");
    const status = document.getElementById("view-status");
    if (status) status.textContent = `Loading ${route ? route.title : "page"}…`;

    if (onRouteChange) onRouteChange(route || { title: "Not found" }, name);
    document.title = `${route ? route.title : "Not found"} · JECRC Portal`;

    try {
      if (!route) {
        container.append(errorPanel(
          "That page doesn't exist. Pick a destination from the sidebar to continue."
        ));
      } else {
        await route.render(container, { name, params, navigate });
      }
    } catch (error) {
      if (token !== renderToken) return;
      console.error("View failed to render:", error);
      container.append(errorPanel(
        error && error.message
          ? error.message
          : "Something went wrong while loading this page.",
        () => render()
      ));
    }

    if (token !== renderToken) return;
    container.classList.remove("is-switching");
    const heading = container.querySelector("h2");
    if (heading) heading.setAttribute("tabindex", "-1");
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
    if (status) status.textContent = "";
  }

  function navigate(path) {
    const target = path.startsWith("/") ? path : `/${path}`;
    if (currentHashRoute() === target.slice(1)) {
      render();
      return;
    }
    window.location.hash = `#${target}`;
  }

  function start() {
    if (started) return;
    started = true;
    if (!window.location.hash) {
      window.history.replaceState(null, "", `#/${defaultRoute}`);
    }
    window.addEventListener("hashchange", render);
    render();
  }

  return { start, render, navigate, current: parse };
}
