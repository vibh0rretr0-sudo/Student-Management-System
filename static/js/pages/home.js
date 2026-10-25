import "../core/theme.js";
import { api, setCsrf } from "../core/api.js";
import { initDeviceGuard } from "../core/device.js";
import { icon } from "../core/icons.js";
import {
  el, iconEl, openModal, setFieldError, toast,
} from "../core/ui.js";

initDeviceGuard();

const csrfMeta = document.querySelector('meta[name="csrf-token"]');
if (csrfMeta) setCsrf(csrfMeta.getAttribute("content"));

/* =========================================================== Slideshow */
const slideshow = document.getElementById("slideshow");
const dotsHost = document.getElementById("slide-dots");
const caption = document.getElementById("slide-caption");
const captionName = document.getElementById("slide-caption-name");
let slides = [];
let images = [];
let currentSlide = 0;
let slideshowTimer = null;
let slideshowReady = false;

function scheduleSlideshow() {
  if (slideshowTimer) window.clearInterval(slideshowTimer);
  if (images.length < 2 || document.hidden) return;
  slideshowTimer = window.setInterval(() => {
    showSlide((currentSlide + 1) % images.length);
  }, 5000);
}

function preload(index) {
  if (!images[index]) return;
  const image = new Image();
  image.src = images[index].url;
}

function showSlide(index) {
  if (!slides.length || index === currentSlide) return;
  slides[currentSlide].classList.remove("is-active");
  currentSlide = index;
  slides[currentSlide].classList.add("is-active");
  dotsHost.querySelectorAll(".home__dot").forEach((dot, dotIndex) => {
    if (dotIndex === index) dot.setAttribute("aria-current", "true");
    else dot.removeAttribute("aria-current");
  });
  captionName.textContent = images[index].name;
  preload((index + 1) % images.length);
  scheduleSlideshow();
}

async function buildSlideshow() {
  try {
    // Using the actual jpeg files found in static/img/campus
    images = [
      { url: "/static/img/campus/1611837473phpHm8M7k.jpeg", name: "Campus View 1" },
      { url: "/static/img/campus/1611837489phpodvXL0.jpeg", name: "Campus View 2" },
      { url: "/static/img/campus/1611837617phpISGBKn.jpeg", name: "Campus View 3" },
      { url: "/static/img/campus/1742973665phpbybRrQ.jpeg", name: "Campus View 4" },
      { url: "/static/img/campus/1742973714phpshPA2z.jpeg", name: "Campus View 5" },
    ];
  } catch (error) {
    return;
  }
  if (!images.length) return;

  slideshow.innerHTML = "";
  dotsHost.innerHTML = "";
  slides = [];

  images.forEach((image, index) => {
    const slide = el("div", { class: `slide ${index === 0 ? "is-active" : ""}`.trim() });
    const img = el("img", {
      src: image.url,
      alt: image.name,
      loading: index === 0 ? "eager" : "lazy",
      decoding: "async",
      fetchpriority: index === 0 ? "high" : "auto",
    });
    slide.append(img);
    slideshow.append(slide);
    slides.push(slide);
    const dot = el("button", {
      class: "home__dot", type: "button",
      "aria-label": `Show ${image.name}`,
      "aria-current": index === 0 ? "true" : "false",
      onclick: () => showSlide(index),
    });
    dotsHost.append(dot);
  });

  caption.hidden = false;
  captionName.textContent = images[0].name;
  preload(1);
  slideshowReady = true;
  scheduleSlideshow();
}

document.addEventListener("visibilitychange", () => {
  if (!slideshowReady) return;
  if (document.hidden) {
    if (slideshowTimer) window.clearInterval(slideshowTimer);
    slideshowTimer = null;
  } else {
    scheduleSlideshow();
  }
});

buildSlideshow();

/* =========================================================== Login flow */
const ROLES = {
  student: {
    label: "Student",
    badgeClass: "badge--primary",
    heading: "Welcome back",
    subheading: "Sign in with your roll number to open your dashboard.",
    identifierLabel: "Roll number",
    placeholder: "e.g. 26CSAI001",
    submit: "Sign in as Student",
    switchCopy: "student",
    autocomplete: "username",
  },
  professor: {
    label: "Professor",
    badgeClass: "badge--accent",
    heading: "Faculty sign in",
    subheading: "Use your JECRC username to open your teaching dashboard.",
    identifierLabel: "Username",
    placeholder: "e.g. rakesh.sharma",
    submit: "Sign in as Professor",
    switchCopy: "professor",
    autocomplete: "username",
  },
};

const stageRole = document.getElementById("stage-role");
const stageLogin = document.getElementById("stage-login");
const stages = document.getElementById("home-stages");
const loginForm = document.getElementById("login-form");
const identifierInput = document.getElementById("identifier");
const passwordInput = document.getElementById("password");
const identifierLabel = document.getElementById("identifier-label");
const identifierError = document.getElementById("identifier-error");
const passwordError = document.getElementById("password-error");
const roleBadge = document.getElementById("login-role-badge");
const loginHeading = document.getElementById("login-heading");
const loginSubheading = document.getElementById("login-subheading");
const submitButton = document.getElementById("login-submit");
const submitLabel = document.getElementById("login-submit-label");
const loginAlert = document.getElementById("login-alert");
const loginAlertText = document.getElementById("login-alert-text");
const capsWarning = document.getElementById("caps-warning");
const rememberRole = document.getElementById("remember-role");
const passwordToggle = document.getElementById("toggle-password");

let activeRole = "student";
let activeStage = "role";
let submitting = false;

function readStorage(key) {
  try { return localStorage.getItem(key); } catch (error) { return null; }
}
function writeStorage(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch (error) { /* storage can be blocked */ }
}

rememberRole.checked = readStorage("jecrc-remember-role") === "1";

function switchStage(next, direction = "forward") {
  if (next === stageRole && activeStage === "role") return;
  if (next === stageLogin && activeStage === "login") return;
  const current = activeStage === "role" ? stageRole : stageLogin;
  const startHeight = current.offsetHeight;
  stages.style.height = `${startHeight}px`;
  current.hidden = true;
  next.hidden = false;
  next.classList.remove("is-entering", "is-back");
  void next.offsetHeight;
  next.classList.add(direction === "back" ? "is-back" : "is-entering");
  const endHeight = next.offsetHeight;
  stages.classList.add("is-animating");
  window.requestAnimationFrame(() => {
    stages.style.height = `${endHeight}px`;
  });
  window.setTimeout(() => {
    stages.style.height = "auto";
    next.classList.remove("is-entering", "is-back");
    stages.classList.remove("is-animating");
  }, 400);
  activeStage = next === stageRole ? "role" : "login";
}

function hideAlert() {
  loginAlert.classList.remove("is-visible", "form-alert--warning");
  loginAlertText.textContent = "";
}

function showAlert(message, { warning = false } = {}) {
  loginAlert.classList.add("is-visible");
  loginAlert.classList.toggle("form-alert--warning", warning);
  loginAlertText.textContent = message;
}

function updateCaps(event) {
  if (typeof event.getModifierState !== "function") return;
  capsWarning.classList.toggle("is-visible",
    event.getModifierState("CapsLock") && activeStage === "login");
}

function configureRole(role) {
  activeRole = role;
  const config = ROLES[role];
  roleBadge.textContent = config.label;
  roleBadge.className = `badge ${config.badgeClass}`;
  loginHeading.textContent = config.heading;
  loginSubheading.textContent = config.subheading;
  identifierLabel.textContent = config.identifierLabel;
  identifierInput.placeholder = config.placeholder;
  identifierInput.setAttribute("aria-label", config.identifierLabel);
  identifierInput.setAttribute("autocomplete", config.autocomplete);
  submitLabel.textContent = config.submit;
  document.getElementById("switch-role-current").textContent = config.switchCopy;
  passwordToggle.setAttribute("aria-pressed", "false");
  passwordToggle.setAttribute("aria-label", "Show password");
  passwordInput.type = "password";
  passwordToggle.innerHTML = icon("eye");
  passwordInput.value = "";
  identifierInput.value = "";
  [identifierInput, passwordInput].forEach((input) => {
    input.removeAttribute("aria-invalid");
    const error = input === identifierInput ? identifierError : passwordError;
    error.textContent = "";
  });
  capsWarning.classList.remove("is-visible");
  hideAlert();
}

function showLogin(role, { instant = false, direction = "forward" } = {}) {
  configureRole(role);
  if (instant) {
    stageRole.hidden = true;
    stageLogin.hidden = false;
    stages.style.height = "auto";
    activeStage = "login";
  } else {
    switchStage(stageLogin, direction);
  }
  window.setTimeout(() => identifierInput.focus(), instant ? 60 : 240);
}

function showRoles() {
  hideAlert();
  configureRole(activeRole);
  switchStage(stageRole, "back");
  window.setTimeout(() => {
    const button = stageRole.querySelector(`[data-role="${activeRole}"]`);
    if (button) button.focus();
  }, 240);
}

document.querySelectorAll("[data-role]").forEach((button) => {
  button.addEventListener("click", () => {
    const role = button.getAttribute("data-role");
    writeStorage("jecrc-last-role", role);
    showLogin(role);
  });
});

document.getElementById("back-to-roles").addEventListener("click", showRoles);
document.getElementById("switch-role").addEventListener("click", () => {
  showLogin(activeRole === "student" ? "professor" : "student");
});

/* Password visibility */
passwordToggle.addEventListener("click", () => {
  const showing = passwordInput.type === "text";
  passwordInput.type = showing ? "password" : "text";
  passwordToggle.setAttribute("aria-pressed", String(!showing));
  passwordToggle.setAttribute("aria-label", showing ? "Show password" : "Hide password");
  passwordToggle.innerHTML = icon(showing ? "eye" : "eyeOff");
  passwordInput.focus();
});

passwordInput.addEventListener("keydown", updateCaps);
passwordInput.addEventListener("keyup", updateCaps);
passwordInput.addEventListener("blur", () => capsWarning.classList.remove("is-visible"));

/* Remember-me role nudge */
rememberRole.addEventListener("change", () => {
  if (!rememberRole.checked) {
    writeStorage("jecrc-remember-role", null);
    writeStorage("jecrc-role", null);
  }
});

/* Forgot password */
document.getElementById("forgot-password").addEventListener("click", () => {
  const isStudent = activeRole === "student";
  const body = el("div", { class: "stack" },
    el("p", { class: "muted" },
      "Password resets are handled by the campus office so that student and staff accounts stay secure. There is no self-service reset in this portal."),
    el("div", { class: "callout callout--info" }, iconEl("mail"),
      el("div", {},
        el("strong", {}, "Email "),
        el("a", { href: "mailto:erp.support@jecrcu.edu.in" }, "erp.support@jecrcu.edu.in"),
        el("div", { class: "small muted", style: { marginTop: "4px" } },
          isStudent
            ? "Include your roll number, branch and batch in the email, then visit the academic office with your college ID for verification."
            : "Write from your JECRC email address and include your employee ID; the IT helpdesk will verify your identity."))),
    el("p", { class: "small muted" },
      isStudent
        ? "Academic office · Ground floor, Admin Block · Monday to Saturday, 9:00 AM – 5:00 PM."
        : "IT helpdesk · Room B-104 · Monday to Saturday, 9:30 AM – 5:30 PM."));
  openModal({
    title: isStudent ? "Student password help" : "Faculty password help",
    description: "We'll get you back in without compromising your account.",
    body,
    actions: [{ label: "Got it", variant: "primary" }],
    size: "modal--sm",
  });
});

/* Login submit */
loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (submitting) return;
  hideAlert();
  setFieldError(identifierInput, "");
  setFieldError(passwordInput, "");

  const identifier = identifierInput.value.trim();
  const password = passwordInput.value;
  let invalid = false;
  if (!identifier) {
    setFieldError(identifierInput, `Enter your ${ROLES[activeRole].identifierLabel.toLowerCase()}.`);
    invalid = true;
  }
  if (!password) {
    setFieldError(passwordInput, "Enter your password.");
    invalid = true;
  }
  if (invalid) {
    (identifier ? passwordInput : identifierInput).focus();
    return;
  }

  submitting = true;
  submitButton.classList.add("is-loading");
  submitButton.disabled = true;
  try {
    const response = await api("/api/auth/login", {
      method: "POST",
      body: {
        role: activeRole,
        identifier,
        password,
        remember: rememberRole.checked,
      },
    });
    setCsrf(response.data.csrf_token);
    writeStorage("jecrc-last-role", activeRole);
    if (rememberRole.checked) {
      writeStorage("jecrc-remember-role", "1");
      writeStorage("jecrc-role", activeRole);
    } else {
      writeStorage("jecrc-remember-role", null);
      writeStorage("jecrc-role", null);
    }

    const card = document.getElementById("home-card");
    card.classList.add("is-leaving");
    document.querySelector(".home").classList.add("is-leaving");
    window.setTimeout(() => window.location.assign("/app"), 460);
  } catch (error) {
    submitting = false;
    submitButton.classList.remove("is-loading");
    submitButton.disabled = false;
    if (error.fields) {
      if (error.fields.identifier) setFieldError(identifierInput, error.fields.identifier);
      if (error.fields.password) setFieldError(passwordInput, error.fields.password);
      if (error.fields.role) showAlert(error.fields.role);
    }
    if (error.status === 429) {
      showAlert(error.message, { warning: true });
    } else if (error.status === 401) {
      showAlert(error.message);
      passwordInput.select();
    } else if (!error.fields || !Object.keys(error.fields).length) {
      showAlert(error.message || "We couldn't sign you in. Please try again.");
    }
  }
});

/* Keyboard back from login */
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && activeStage === "login"
    && !document.querySelector("dialog[open]")) {
    showRoles();
  }
});

/* Expired-session notice */
const query = new URLSearchParams(window.location.search);
if (query.get("expired") === "1") {
  toast("Your session ended for security. Please sign in again.", "warning", { duration: 7000 });
  window.history.replaceState(null, "", window.location.pathname);
}

/* Returning visitors with a remembered role skip straight to the form. */
const rememberedRole = readStorage("jecrc-role");
if (readStorage("jecrc-remember-role") === "1"
  && (rememberedRole === "student" || rememberedRole === "professor")) {
  showLogin(rememberedRole, { instant: true });
}
