# UI Guide — the design system

How the interface is built and *why*, in the language you can reuse in a viva
or interview. Everything below lives in **one stylesheet**
(`frontend/static/css/style.css`) and runs with **zero JavaScript** — the
project's framework-free rule turned into a design discipline. For a guided
path through the whole codebase (not just the UI), see the
[`CODE_TOUR.md`](CODE_TOUR.md).

> **Design language:** flat, high-contrast surfaces in JECRC red/white.
> No backdrop blur, no translucent panels, no gradient fills — the charts are
> plain width-percentage bars. Motion is limited to entrance staggering and
> the CSS count-up, both driven by server-rendered custom properties.

---

## 1. Design goals

| Goal | How it's achieved |
|---|---|
| No JavaScript, no frameworks, no CDN | Pure CSS features only; system font stack; one local stylesheet |
| Functionality never moves for style | UI restyle verified byte-identical on routes/forms/links/permissions via a snapshot diff |
| Works offline | No web fonts — `"Segoe UI Variable Text", "Segoe UI", system-ui, ...` |
| Accessible | `prefers-reduced-motion` kills all motion; `:focus-visible` rings; real checkbox for the theme toggle |

---

## 2. Tokens — the whole theme is ~30 CSS variables

Everything visual derives from custom properties on `:root`:

```css
:root {
  --accent:      #b71c1c;   /* JECRC red */
  --accent-soft: #f7e2e2;   /* flat tint for hovers/rings */
  --bg:          #f5f5f5;
  --surface:     #ffffff;
  --surface-2:   #f0f1f4;
  --line:        #dcdfe6;
  --ok / --danger / --warn (+ a -soft tint of each)
  --radius-lg:   12px;      /* one shape language: 12 / 8 / 6 */
  --shadow-card: 0 1px 3px rgba(0, 0, 0, .08);
  color-scheme: light;
}
```

**Why tokens:** every component reads variables, never hard-coded colors, so
re-theming is a data change, not a code change. `color-scheme` is a detail
interviewers love: it tells the browser to paint scrollbars and form controls
in theme colors automatically.

---

## 3. The flat panel primitive

Seven surfaces — `.card`, `.stat-card`, `.login-card`, `.sidebar`, `.topbar`,
`.marks-block`, `.danger-zone` — share one rule: `background: var(--surface)`,
a 1px `--line` border, and a single soft shadow. Depth comes from **contrast
and borders**, not blur: a light-gray page (`--bg`), white panels, and a red
accent that marks exactly three things (headers, buttons, active nav).
Elevation is honest: one 1px–3px shadow, nothing floating on layered glows.

---

## 4. Light/dark with a checkbox — no JS theme switch

The topbar has a real `<input type="checkbox" id="theme-toggle">` (visually
hidden, wrapped in a styled label). The whole dark theme is a second variable
set:

```css
body:has(#theme-toggle:checked) {
  --bg: #14161d;  --surface: #1d2029;  --accent: #ef4467;
  /* ...the remaining overrides... */
  color-scheme: dark;
}
```

- `:has()` (the "parent selector") styles the `<body>` based on a checkbox
  nested inside it — the classic no-JS toggle pattern.
- The default state is **light**; the toggle **overrides**, regardless of OS
  setting (a product decision, confirmed with the project owner).
- The toggle is an iOS-style shifter: the solid thumb is a `::before` that
  slides under two glyphs. The math is fixed by construction — glyphs are
  16px wide with a 5px gap and 9px side padding, so the thumb is 16px at
  `left: 9px` and shifts exactly `16 + 5 = 21px` to land on the second glyph.

**Costs worth naming in an interview:** the choice lives in the checkbox only,
so it resets on reload — persisting it without JS would need a cookie or a
form round-trip (deliberately out of scope for a CSS-only build). Styling
through `:has()` also means the dark set cascades from `body`, keeping
specificity flat and predictable.

---

## 5. Staggered entrances — one keyframe, server-side delays

One `rise-in` keyframe (fade + 10px slide) is reused by cards, stat tiles,
table rows, chart rows and nav links. The stagger comes from an index the
**server** renders into an inline custom property:

```html
<div class="stat-card" style="--i:3">
<tr style="--i:7">
```

```css
.card { animation: rise-in .4s ease both;
        animation-delay: calc(min(var(--i, 0), 12) * 60ms); }
```

`min(var(--i), 12)` caps the delay so a 50-row table can't wait for its last
row (table rows use a slightly faster 28ms step with a cap of 24); `both` fill
mode applies the "from" state during the delay (no flash of unanimated
content). Python only learned to emit a counter — no rendering logic changed.

---

## 6. Count-up numbers — `@property` + CSS counters

Stat values that are always integers (students, courses) roll up from zero:

```css
@property --n { syntax: "<integer>"; inherits: false; initial-value: 0; }
.stat-value.count-up { counter-reset: stat var(--n); animation: count-up 1s ease-out both; }
.stat-value.count-up::after { content: counter(stat); }
@keyframes count-up { from { --n: 0; } }
```

- Normally custom properties are opaque strings CSS can't interpolate;
  `@property` gives `--n` a **type**, so the browser animates it as an integer.
- The element renders an *empty span*; the digits you see are a CSS `counter`
  drawn by `::after`. The Python template only substitutes the final value
  into `style="--n:{{value}}"`.
- Percentages and "—" placeholders keep a static `.stat-value` (fallback text),
  so **unsupported browsers show the real number** — progressive enhancement,
  never a regression.

---

## 7. Charts that ARE the data — plain width bars

Routes emit bar widths as a custom property; the stylesheet renders it
directly — no grow animation, because the number is the visual:

```html
<div class="bar-row" style="--i:2">
  <span class="bar-label">Aarav Sharma</span>
  <div class="bar-track threshold"><div class="bar-fill warn" style="--w:62.5%"></div></div>
  <span class="bar-value">62.5</span>
</div>
```

The row is a CSS grid (`label | track | value`), the fill is `width:
var(--w)`. The attendance track adds a dashed 75%-eligibility line — drawn
**under** the fill (`z-index`), inset 2px so it never pokes past the rounded
corners, and rendered **only when the bar is actually below the cutoff** (on
at-or-above bars the line would just peek past the tip). Below-cutoff bars
also get the warm `--warn` fill. Both signals are server-decided: Python
compares the rate to 75 and emits the classes — CSS never makes a data
decision.

---

## 8. The theme toggle — a form button, saved server-side

Dark mode is a real `<form method="post">` whose submit button *looks*
like a switch (`.toggle-ui`'s sliding pill is pure CSS). Clicking it POSTs
`/prefs/theme`; the server flips a one-year `theme` cookie and the next
render puts `class="dark"` on `<html>` — so the choice survives every tab
switch and even a server restart. The dark palette keys off `html.dark`
rather than the old checkbox `:has()` state: same tokens, now server-owned.

---

## 9. Cross-fades, scrollbars, focus — the polish layer

- **Page transitions:** `@view-transition { navigation: auto; }` + old/new
  pseudo-elements fade pages on navigation in Chromium; other browsers ignore
  it and load instantly (graceful no-op). It is gated behind
  `prefers-reduced-motion: no-preference` because a cross-fade is motion —
  and because software-rendered/headless environments can stall on
  cross-document transitions (found by probing headless screenshots; the
  media gate plus feature detection makes the fallback instant everywhere).
- **Scrollbars/selection:** `::selection` in the accent tint,
  `scrollbar-width/color`, and `-webkit-scrollbar` thumbs in the accent.
- **Focus:** `:focus-visible` outlines for keyboard users without punishing
  mouse clicks.

---

## 10. Reduced motion + small screens — the safety nets

```css
@media (prefers-reduced-motion: reduce) {
  .card, .stat-card, .marks-block, .data-table tbody tr, .bar-row,
  .sidebar-nav a, .login-card { animation: none; opacity: 1; transform: none; }
  .stat-value.count-up { animation: none; }
  * { transition-duration: .01ms !important; }
}
```

Motion is an enhancement; the static UI is identical informationally.
Below 860px the sidebar stacks into a header, and — the classic mobile
data-table pattern — wide tables turn into `display: block; overflow-x: auto`
boxes that scroll **inside their panel** instead of stretching the page
sideways (verified at 320px on every table-heavy page); marks/date inputs
shrink to match.

---

## 11. Viva one-liners

- "The theme system is **a second set of ~30 CSS variables**, not a second
  stylesheet — `:has()` makes a checkbox a theme switch."
- "The thumb shift is **fixed by construction**: 16px glyph + 5px gap = a
  21px `translateX`, no measuring."
- "Stagger indexes are **rendered by Python**, and `min(--i, 12)` caps the
  wait — markup and motion stay in sync without JS."
- "Every dynamic number has a **static fallback**; progressive enhancement
  means the page degrades to a fully working 2015-era UI."
- "The charts are **data, not decoration** — a server-computed `<div>` width
  and a threshold line the server decided to draw."
- "Marks saves are true **upserts** using MySQL 8.0.19+ row aliases
  (`INSERT ... AS new ON DUPLICATE KEY UPDATE ... = new.col`) — readable,
  and a version detail worth naming."
- "I proved the restyle didn't change behavior: a **snapshot diff of the
  routes** — statuses, forms, inputs, links, permission probes — came back
  identical."
