/* Inline, stroke-based icon set. Strings are trusted and only used for SVG. */
const PATHS = {
  overview:
    '<rect x="3" y="3" width="7" height="8" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="15" width="7" height="6" rx="1.5"/>',
  calendar:
    '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>',
  clock:
    '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
  chart:
    '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  attendance:
    '<path d="M4 4v16h16"/><path d="M7 14l3-4 3 2 4-5"/>',
  clipboard:
    '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4a3 3 0 0 1 6 0M9 10h6M9 14h6M9 18h4"/>',
  megaphone:
    '<path d="M3 11v3a1 1 0 0 0 1 1h3l7 4V6L7 10H4a1 1 0 0 0-1 1Z"/><path d="M17 8a5 5 0 0 1 0 8"/>',
  schedule:
    '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M8 2v4M16 2v4M3 9h18"/><path d="M9 14h2v2H9z"/>',
  user:
    '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>',
  users:
    '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c0-3.5 3.1-5.5 7-5.5s7 2 7 5.5"/><path d="M17 5a3 3 0 0 1 0 6M18 15c2.5.6 4 2.3 4 5"/>',
  layers:
    '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
  search:
    '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/>',
  bell:
    '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  logout:
    '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
  chevronLeft: '<path d="m15 18-6-6 6-6"/>',
  chevronRight: '<path d="m9 18 6-6-6-6"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5M12 15V3"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5M12 3v12"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/>',
  fileText:
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
  check: '<path d="m4 12 5 5L20 6"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  alert:
    '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  mapPin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
  book: '<path d="M4 19.5V6a2 2 0 0 1 2-2h13v16H6.5A2.5 2.5 0 0 0 4 22.5"/><path d="M8 8h7M8 12h5"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 15h10l1-15"/><path d="M10 11v6M14 11v6"/>',
  undo: '<path d="M3 7v6h6"/><path d="M3.5 13a9 9 0 1 0 2.1-8.4L3 7"/>',
  refresh: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  phone:
    '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z"/>',
  camera:
    '<path d="M4 7h3l2-3h6l2 3h3a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1Z"/><circle cx="12" cy="13" r="4"/>',
  printer:
    '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M6 17h12v5H6z"/>',
  filter: '<path d="M3 4h18l-7 8v7l-4-2v-5Z"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  arrowRight: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  arrowLeft: '<path d="M19 12H5M11 18l-6-6 6-6"/>',
  external: '<path d="M15 3h6v6M10 14 21 3"/><path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>',
  spark: '<path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/>',
  trendingUp: '<path d="m3 17 6-6 4 4 8-9"/><path d="M14 6h7v7"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  percent: '<path d="m5 19 14-14"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
  award: '<circle cx="12" cy="9" r="6"/><path d="m8.5 14-1.5 8 5-3 5 3-1.5-8"/>',
  eye: '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.5"/>',
  eyeOff:
    '<path d="M10.6 6.2A10.5 10.5 0 0 1 12 6c6.5 0 10 6 10 6a17 17 0 0 1-2.2 3M6.6 6.6A17 17 0 0 0 2 12s3.5 6 10 6a9.7 9.7 0 0 0 4.4-1"/><path d="M3 3l18 18"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  command: '<path d="M9 6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3Z"/>',
  inbox: '<path d="M4 4h16v16H4z"/><path d="M4 13h5l2 3h2l2-3h5"/>',
  dot: '<circle cx="12" cy="12" r="3"/>',
};

export function icon(name, className = "") {
  const path = PATHS[name] || PATHS.dot;
  return `<svg class="icon ${className}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${path}</svg>`;
}

export function hasIcon(name) {
  return Object.prototype.hasOwnProperty.call(PATHS, name);
}
