import "../core/theme.js";
import { setCsrf } from "../core/api.js";
import { initDeviceGuard } from "../core/device.js";
import { errorPanel } from "../core/ui.js";
import { setBoot } from "./session.js";
import { buildShell } from "./shell.js";
import { createRouter } from "./router.js";
import { buildRoutes, navItems } from "./routes.js";

function fail(message) {
  const view = document.getElementById("view");
  if (view) {
    view.innerHTML = "";
    view.append(errorPanel(message, () => window.location.reload()));
  }
}

let boot;
try {
  const raw = document.getElementById("app-boot");
  boot = JSON.parse(raw.textContent);
} catch (error) {
  fail("We couldn't start the portal. Refresh the page to try again.");
  throw error;
}

if (!boot || !boot.user || !boot.user.role) {
  window.location.assign("/");
} else {
  setBoot(boot);
  setCsrf(boot.csrf_token);
  initDeviceGuard();

  const shell = buildShell(boot, navItems(boot.user.role));
  const router = createRouter({
    routes: buildRoutes(boot.user.role),
    container: document.getElementById("view"),
    onRouteChange: shell.setRoute,
  });
  router.start();
}
