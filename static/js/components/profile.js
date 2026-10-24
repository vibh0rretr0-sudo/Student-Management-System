import { api, upload } from "../core/api.js";
import {
  avatarEl, busyButton, el, errorPanel, formField, iconEl, loadingView,
  openModal, setFieldError, showFieldErrors, toast,
} from "../core/ui.js";
import { pageHeader, panel } from "./page.js";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/;
const PHONE_RE = /^[0-9+\-\s()]{7,18}$/;

export async function renderProfile(container) {
  container.append(loadingView());
  let profile;
  try {
    const response = await api("/api/common/me");
    profile = response.data.profile;
  } catch (error) {
    container.innerHTML = "";
    container.append(errorPanel(error.message, () => {
      container.innerHTML = "";
      renderProfile(container);
    }));
    return;
  }

  container.innerHTML = "";
  container.append(pageHeader({
    title: "Personal Details",
    subtitle: "Your official record, contact details and account security.",
  }));

  const identity = el("aside", { class: "panel identity-panel" });
  const avatarHolder = el("div", { class: "profile-avatar-holder" },
    avatarEl(profile.name, profile.photo_url, "avatar--xl"));
  avatarHolder.id = "profile-avatar-holder";

  const photoInput = el("input", {
    type: "file", accept: "image/png,image/jpeg,image/webp", hidden: true,
  });

  const uploadButton = el("button", { class: "btn btn--secondary btn--sm", type: "button" },
    iconEl("camera"), el("span", { class: "btn__label" }, "Change photo"));
  uploadButton.addEventListener("click", () => photoInput.click());

  photoInput.addEventListener("change", async () => {
    const file = photoInput.files && photoInput.files[0];
    photoInput.value = "";
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      toast("Choose a PNG, JPEG or WebP image.", "error");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast("Profile photos must be 5 MB or smaller.", "error");
      return;
    }
    const cropped = await openCropper(file);
    if (!cropped) return;
    const formData = new FormData();
    formData.append("photo", cropped, "profile.jpg");
    await busyButton(uploadButton, async () => {
      try {
        const response = await upload("/api/common/me/photo", formData);
        profile = response.data.profile;
        paintPhoto(profile);
        toast("Profile photo updated.", "success");
      } catch (error) {
        toast(error.message, "error");
      }
    });
  });

  const identityMeta = el("div", { class: "identity-card__meta" });
  const kv = el("dl", { class: "kv" });
  [
    ["Role", profile.role === "student" ? "Student" : "Professor"],
    profile.role === "student"
      ? ["Roll number", profile.roll_no]
      : ["Employee ID", profile.employee_id],
    profile.role === "student"
      ? ["Batch", `${profile.batch} · Sem ${profile.semester}`]
      : ["Department", profile.department],
    profile.role === "student"
      ? ["Branch", profile.branch]
      : ["Designation", profile.designation],
  ].forEach(([label, value]) => {
    kv.append(el("dt", {}, label), el("dd", {}, value || "—"));
  });
  identityMeta.append(kv);

  identity.append(el("div", { class: "identity-card" },
    avatarHolder,
    el("h3", { class: "identity-card__name" }, profile.name),
    el("p", { class: "identity-card__role" },
      profile.role === "student" ? "Student" : profile.designation),
    el("div", { class: "photo-actions" }, uploadButton, photoInput),
    identityMeta));

  const officialPanel = panel({
    title: "Official record",
    subtitle: "These fields are maintained by the academic office and cannot be edited here.",
    body: buildOfficial(profile),
  });

  const contactPanel = panel({
    title: "Contact information",
    subtitle: "Keep these up to date so faculty and the office can reach you.",
    body: buildContactForm(profile),
  });

  const securityPanel = panel({
    title: "Change password",
    subtitle: "Use at least 8 characters with a letter and a number.",
    body: buildPasswordForm(),
  });

  container.append(el("div", { class: "profile-grid" },
    identity,
    el("div", { class: "stack" }, officialPanel, contactPanel, securityPanel)));

  function paintPhoto(nextProfile) {
    const target = document.getElementById("profile-avatar-holder");
    if (target) {
      target.innerHTML = "";
      target.append(avatarEl(nextProfile.name, nextProfile.photo_url, "avatar--xl"));
    }
    ["topbar-avatar", "sidebar-avatar", "user-menu-avatar"].forEach((id) => {
      const current = document.getElementById(id);
      if (!current) return;
      const size = id === "user-menu-avatar" ? "" : "avatar--sm";
      const fresh = avatarEl(nextProfile.name, nextProfile.photo_url, size);
      fresh.id = id;
      current.replaceWith(fresh);
    });
  }
}

function buildOfficial(profile) {
  const list = el("dl", { class: "kv" });
  const fields = profile.role === "student" ? [
    ["Full name", profile.name],
    ["Roll number", profile.roll_no],
    ["Branch", profile.branch],
    ["Semester", `Semester ${profile.semester}`],
    ["Batch", `${profile.batch} (${profile.batch_code})`],
    ["Guardian", profile.guardian_name || "—"],
    ["Guardian phone", profile.guardian_phone || "—"],
  ] : [
    ["Full name", profile.name],
    ["Employee ID", profile.employee_id],
    ["Department", profile.department],
    ["Designation", profile.designation],
    ["Qualifications", profile.qualifications || "—"],
    ["Subjects taught", [...new Set((profile.subjects || []).map((s) => s.subject_code))].join(", ") || "—"],
  ];
  fields.forEach(([label, value]) => {
    list.append(el("dt", {}, label), el("dd", {}, value));
  });
  return list;
}

function buildContactForm(profile) {
  const form = el("form", { class: "profile-form", novalidate: true });
  const email = formField({
    label: "Email address", name: "email", type: "email", value: profile.email || "",
    placeholder: "you@jecrcu.edu.in", autocomplete: "email",
  });
  const phone = formField({
    label: "Phone number", name: "phone", type: "tel", value: profile.phone || "",
    placeholder: "+91 98290 00000", autocomplete: "tel",
  });
  const address = formField({
    label: "Address", name: "address", type: "textarea", value: profile.address || "",
    placeholder: "House, street, locality, Jaipur", rows: 3,
  });
  address.input.maxLength = 255;

  const save = el("button", { class: "btn btn--primary", type: "submit" },
    el("span", { class: "spinner", "aria-hidden": "true" }),
    el("span", { class: "btn__label" }, "Save contact details"));

  form.append(email.wrapper, el("div", { class: "field-row" }, phone.wrapper),
    address.wrapper, el("div", { class: "form-actions" }, save));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showFieldErrors(form, {});
    const fields = {};
    const emailValue = email.input.value.trim();
    const phoneValue = phone.input.value.trim();
    if (emailValue && !EMAIL_RE.test(emailValue)) {
      fields.email = "Enter a valid email address.";
    }
    if (phoneValue && !PHONE_RE.test(phoneValue)) {
      fields.phone = "Enter a valid phone number (7–18 digits).";
    }
    if (Object.keys(fields).length) {
      showFieldErrors(form, fields);
      return;
    }
    await busyButton(save, async () => {
      try {
        const response = await api("/api/common/me/contact", {
          method: "PATCH",
          body: {
            email: emailValue,
            phone: phoneValue,
            address: address.input.value.trim(),
          },
        });
        toast(response.data.message || "Contact details updated.", "success");
      } catch (error) {
        if (error.fields && Object.keys(error.fields).length) {
          showFieldErrors(form, error.fields);
        } else {
          toast(error.message, "error");
        }
      }
    });
  });
  return form;
}

function buildPasswordForm() {
  const form = el("form", { class: "profile-form", novalidate: true });
  const current = formField({
    label: "Current password", name: "current_password", type: "password",
    autocomplete: "current-password",
  });
  const next = formField({
    label: "New password", name: "new_password", type: "password",
    autocomplete: "new-password",
    hint: "Minimum 8 characters, including a letter and a number.",
  });
  const confirm = formField({
    label: "Confirm new password", name: "confirm_password", type: "password",
    autocomplete: "new-password",
  });
  const save = el("button", { class: "btn btn--primary", type: "submit" },
    el("span", { class: "spinner", "aria-hidden": "true" }),
    el("span", { class: "btn__label" }, "Update password"));

  form.append(current.wrapper, el("div", { class: "field-row" }, next.wrapper, confirm.wrapper),
    el("div", { class: "form-actions" }, save));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = {};
    const value = next.input.value;
    if (!current.input.value) fields.current_password = "Enter your current password.";
    if (value.length < 8) fields.new_password = "Use at least 8 characters.";
    else if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) {
      fields.new_password = "Include at least one letter and one number.";
    }
    if (!confirm.input.value) fields.confirm_password = "Re-enter the new password.";
    else if (value !== confirm.input.value) fields.confirm_password = "Passwords do not match.";
    if (Object.keys(fields).length) {
      showFieldErrors(form, fields);
      return;
    }
    await busyButton(save, async () => {
      try {
        const response = await api("/api/common/me/password", {
          method: "POST",
          body: {
            current_password: current.input.value,
            new_password: next.input.value,
            confirm_password: confirm.input.value,
          },
        });
        toast(response.data.message || "Password changed.", "success");
        form.reset();
        [current, next, confirm].forEach((field) => setFieldError(field.input, ""));
      } catch (error) {
        if (error.fields && Object.keys(error.fields).length) {
          showFieldErrors(form, error.fields);
        } else {
          toast(error.message, "error");
        }
      }
    });
  });
  return form;
}

/* -------------------------------------------------------------- Crop modal */
function openCropper(file) {
  return new Promise((resolve) => {
    const image = new Image();
    const objectUrl = URL.createObjectURL(file);
    const canvas = el("canvas", {
      width: 320, height: 320,
      style: { width: "100%", height: "auto", borderRadius: "14px", touchAction: "none", cursor: "grab", background: "var(--surface-sunken)" },
      "aria-label": "Photo preview. Drag to reposition.",
    });
    const zoom = el("input", {
      class: "input", type: "range", min: "1", max: "3", step: "0.01", value: "1",
      "aria-label": "Zoom photo",
    });
    let settled = false;
    let zoomValue = 1;
    let offsetX = 0;
    let offsetY = 0;
    let dragging = false;
    let lastX = 0;
    let lastY = 0;

    function dimensions() {
      const base = Math.max(320 / image.naturalWidth, 320 / image.naturalHeight);
      const scale = base * zoomValue;
      return { drawW: image.naturalWidth * scale, drawH: image.naturalHeight * scale };
    }

    function clamp() {
      const { drawW, drawH } = dimensions();
      const maxX = Math.max(0, (drawW - 320) / 2);
      const maxY = Math.max(0, (drawH - 320) / 2);
      offsetX = Math.max(-maxX, Math.min(maxX, offsetX));
      offsetY = Math.max(-maxY, Math.min(maxY, offsetY));
    }

    function draw() {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, 320, 320);
      const { drawW, drawH } = dimensions();
      ctx.drawImage(image, (320 - drawW) / 2 + offsetX, (320 - drawH) / 2 + offsetY, drawW, drawH);
      ctx.strokeStyle = "rgba(255,255,255,0.85)";
      ctx.lineWidth = 2;
      ctx.strokeRect(10, 10, 300, 300);
      ctx.strokeStyle = "rgba(255,255,255,0.4)";
      ctx.beginPath();
      ctx.moveTo(160, 10); ctx.lineTo(160, 310);
      ctx.moveTo(10, 160); ctx.lineTo(310, 160);
      ctx.stroke();
    }

    zoom.addEventListener("input", () => {
      zoomValue = Number(zoom.value);
      clamp();
      draw();
    });

    canvas.addEventListener("pointerdown", (event) => {
      dragging = true;
      lastX = event.clientX;
      lastY = event.clientY;
      canvas.setPointerCapture(event.pointerId);
      canvas.style.cursor = "grabbing";
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      const rect = canvas.getBoundingClientRect();
      const ratio = 320 / rect.width;
      offsetX += (event.clientX - lastX) * ratio;
      offsetY += (event.clientY - lastY) * ratio;
      lastX = event.clientX;
      lastY = event.clientY;
      clamp();
      draw();
    });
    const endDrag = () => {
      dragging = false;
      canvas.style.cursor = "grab";
    };
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);

    image.onload = () => {
      draw();
      openModal({
        title: "Crop your profile photo",
        description: "Drag to reposition and use the slider to zoom. The square is what others will see.",
        body: el("div", { class: "stack" }, canvas,
          el("div", { class: "field" },
            el("label", { class: "field__label", for: "crop-zoom" }, "Zoom"),
            zoom)),
        actions: [
          {
            label: "Cancel", variant: "secondary",
            onClick: () => { settled = true; resolve(null); },
          },
          {
            label: "Use this photo", variant: "primary",
            onClick: async () => {
              const output = document.createElement("canvas");
              output.width = 512;
              output.height = 512;
              const scale = 512 / 320;
              const { drawW, drawH } = dimensions();
              const ctx = output.getContext("2d");
              ctx.fillStyle = "#fff";
              ctx.fillRect(0, 0, 512, 512);
              ctx.drawImage(
                image,
                ((320 - drawW) / 2 + offsetX) * scale,
                ((320 - drawH) / 2 + offsetY) * scale,
                drawW * scale,
                drawH * scale
              );
              const blob = await new Promise((done) => output.toBlob(done, "image/jpeg", 0.9));
              if (!blob) {
                toast("That photo couldn't be processed. Try another one.", "error");
                return false;
              }
              settled = true;
              resolve(blob);
            },
          },
        ],
        onClose: () => {
          URL.revokeObjectURL(objectUrl);
          if (!settled) resolve(null);
        },
      });
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      toast("That image couldn't be opened. Try a different file.", "error");
      resolve(null);
    };
    image.src = objectUrl;
  });
}
