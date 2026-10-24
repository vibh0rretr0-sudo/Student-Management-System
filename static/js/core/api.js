/* Thin fetch wrapper for the JSON envelope {ok, data, error}. */
let csrfToken = null;

const csrfMeta = document.querySelector('meta[name="csrf-token"]');
if (csrfMeta) csrfToken = csrfMeta.getAttribute("content");

export function setCsrf(value) {
  if (value) csrfToken = value;
}

export function getCsrf() {
  return csrfToken;
}

export class ApiError extends Error {
  constructor(message, { status = 0, code = null, fields = null, payload = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields || {};
    this.payload = payload;
  }
}

function networkError() {
  return new ApiError(
    "We couldn't reach the portal. Check your connection and try again.",
    { status: 0, code: "network_error" }
  );
}

function handleUnauthorized(path) {
  const safe = path.startsWith("/api/auth/");
  if (!safe) {
    const next = encodeURIComponent(window.location.pathname + window.location.hash);
    window.location.assign(`/?expired=1&next=${next}`);
  }
}

export async function api(path, options = {}) {
  const {
    method = "GET",
    body = null,
    form = null,
    signal = null,
    authRedirect = true,
  } = options;

  const headers = { Accept: "application/json" };
  if (method !== "GET" && method !== "HEAD") {
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
  }

  let payload = null;
  if (form) {
    payload = form;
  } else if (body !== null) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: payload,
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error && error.name === "AbortError") throw error;
    throw networkError();
  }

  let json = null;
  try {
    json = await response.json();
  } catch (error) {
    if (response.status === 204) return null;
    throw new ApiError("The portal returned an unexpected response.", {
      status: response.status,
      code: "bad_response",
    });
  }

  if (!response.ok || !json || json.ok !== true) {
    if (response.status === 401 && authRedirect) {
      handleUnauthorized(path);
    }
    const error = json && json.error ? json.error : {};
    throw new ApiError(
      error.message || "Something went wrong. Please try again.",
      {
        status: response.status,
        code: error.code || null,
        fields: error.fields || null,
        payload: json,
      }
    );
  }

  return json;
}

/* Upload with progress via XHR (fetch has no upload progress events). */
export function upload(path, formData, { onProgress, method = "POST" } = {}) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open(method, path, true);
    request.withCredentials = true;
    request.setRequestHeader("Accept", "application/json");
    if (csrfToken) request.setRequestHeader("X-CSRF-Token", csrfToken);

    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && typeof onProgress === "function") {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    });

    request.addEventListener("load", () => {
      let json = null;
      try {
        json = JSON.parse(request.responseText);
      } catch (error) {
        reject(new ApiError("The portal returned an unexpected response.", {
          status: request.status,
        }));
        return;
      }
      if (request.status >= 200 && request.status < 300 && json.ok) {
        resolve(json);
        return;
      }
      if (request.status === 401) handleUnauthorized(path);
      const error = json.error || {};
      reject(new ApiError(error.message || "Upload failed. Please try again.", {
        status: request.status,
        code: error.code || null,
        fields: error.fields || null,
        payload: json,
      }));
    });

    request.addEventListener("error", () => reject(networkError()));
    request.addEventListener("abort", () => reject(
      new ApiError("Upload cancelled.", { status: 0, code: "aborted" })
    ));
    request.send(formData);
  });
}

export async function downloadBlob(path, filename) {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) {
    let message = "Download failed.";
    try {
      const json = await response.json();
      message = json.error?.message || message;
    } catch (error) { /* binary or empty */ }
    throw new ApiError(message, { status: response.status });
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename || "download";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}
