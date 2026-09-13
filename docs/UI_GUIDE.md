# UI Guide — the design system

> **Note (scope trim):** the interface was re-skinned from glassmorphism to
> a flat, high-contrast JECRC red/white system. Sections below that describe
> glass surfaces, the aurora background, and chart animations refer to the
> earlier design and are kept for reference; the tokens, the pure-CSS theme
> toggle, and every selector/technique outside those effects still match
> the current stylesheet.

How the interface is built and *why*, in the language you can reuse in a viva
or interview. Everything below lives in **one stylesheet**
(`frontend/static/css/style.css`) and runs with **zero JavaScript** — the
project's framework-free rule turned into a design discipline. For a guided
path through the whole codebase (not just the UI), see the
[`CODE_TOUR.md`](CODE_TOUR.md).

---

## 1. Design goals

| Goal | How it's achieved |
|---|---|
| No JavaScript, no frameworks, no CDN | Pure CSS features only; system font stack; one local stylesheet |
| Functionality never moves for style | UI restyle verified byte-identical on routes/forms/links/permissions via a snapshot diff |
| Works offline | No web fonts — `"Segoe UI Variable Text", "Segoe UI", system-ui, ...` |
| Accessible | `prefers-reduced-motion` kills all motion; `:focus-visible` rings; real checkbox for the theme toggle |

---

## 2. Tokens — the whole theme is ~40 CSS variables

Everything visual derives from custom properties on `:root`:

```css
:root {
  --accent: #c81e3c;            /* modernized JECRC red */
  --grad-accent: linear-gradient(135deg, #b71c1c, #c81e3c, #e0334f);
  --glass: rgba(255,255,255,.60);   /* panel fill */
  --glass-border: rgba(255,255,255,.75);
  --blur: 18px;                     /* backdrop blur radius */
  --radius-lg: 22px;                /* "big & soft" shape language */
  --shadow-card: 0 10px 34px rgba(24,28,48,.10);
  --glow-accent: 0 4px 22px rgba(200,30,60,.35);
  color-scheme: light;              /* paints native widgets to match */
}
```

**Why tokens:** every component reads variables, never hard-coded colors, so
re-theming is a data change, not a code change. `color-scheme` is a detail
interviewers love: it tells the browser to paint scrollbars and form controls
in theme colors automatically.

---

## 3. Glassmorphism — how the "frosted glass" actually works

A glass panel is four ingredients:

1. **Translucent fill** — `background: var(--glass)` (white at 60% alpha).
2. **Backdrop blur** — `backdrop-filter: blur(18px) saturate(150%)` smears
   whatever is *behind* the panel; `saturate` keeps the aurora colors juicy.
   (`-webkit-` prefix included for Safari.)
3. **A light border** — 1px of near-white sells the "glass edge".
4. **A soft drop shadow** — lifts the panel off the background.

**Interview soundbite:** *glassmorphism = translucency + backdrop blur + edge
highlight + elevation shadow; the moving aurora behind the panels is what
makes the blur visible and the UI feel alive.*

---

## 4. The aurora — three blurred orbs, pure keyframes

`.aurora` is a fixed, `pointer-events: none` layer holding three `.orb`
divs: large radial gradients (red, crimson, violet) softened by
`filter: blur(90px)`, each on a slow `transform` loop (`28s/34s/40s` —
different durations avoid a visible "reset beat"):

```css
@keyframes orb-drift-1 {
  0%   { transform: translate(-8vw,-6vh) scale(1); }
  50%  { transform: translate(10vw,12vh) scale(1.25); }
  100% { transform: translate(-8vw,-6vh) scale(1); }
}
```

**Why transform only:** the browser can animate `transform` on the compositor
thread — it never re-runs layout or paint, so three huge blurred elements stay
cheap. Animating `top/left` would run layout every frame. `will-change:
transform` hints the promotion.

---

## 5. Light/dark with a checkbox — no JS theme switch

The topbar has a real `<input type="checkbox" id="theme-toggle">` (visually
hidden, wrapped in a styled label). The whole dark theme is a second variable
set:

```css
body:has(#theme-toggle:checked) {
  --bg: #0c0f1c;
  --glass: rgba(21,25,42,.62);
  --accent: #ef4467;
  /* ...~25 more overrides... */
  color-scheme: dark;
}
```

- `:has()` (the "parent selector") styles the `<body>` based on a checkbox
  nested inside it — the classic no-JS toggle pattern.
- The default state is **light**; the toggle **overrides**, regardless of OS
  setting (a product decision, confirmed with the project owner).
- The toggle's own visuals (sliding gradient thumb, glyph emphasis) are styled
  through the same selector, so the switch animates itself.

**Costs worth naming in an interview:** the choice lives in the checkbox only,
so it resets on reload — persisting it without JS would need a cookie or a
form round-trip (deliberately out of scope for a CSS-only build). Styling
through `:has()` also means the dark set cascades from `body`, keeping
specificity flat and predictable.

---

## 6. Staggered entrances — one keyframe, server-side delays

One `rise-in` keyframe (fade + 14px slide + 0.985→1 scale) is reused by cards,
stat tiles, table rows, chart rows and nav links. The stagger comes from an
index the **server** renders into an inline custom property:

```html
<div class="stat-card" style="--i:3">
<tr style="--i:7">
```

```css
.card { animation: rise-in .5s cubic-bezier(.22,.9,.3,1) both;
        animation-delay: calc(min(var(--i,0),12) * 70ms); }
```

`min(var(--i),12)` caps the delay so a 50-row table can't wait 3.5s for its
last row; `both` fill mode applies the "from" state during the delay (no
flash of unanimated content). Python only learned to emit a counter — no
rendering logic changed.

---

## 7. Charts that grow — `--w` and a spring curve

Routes emit bar widths as a custom property instead of a literal `width`:

```html
<div class="bar-track threshold"><div class="bar-fill" style="--w:62%"></div></div>
```

```css
.bar-fill { width: var(--w, 0%);
            animation: bar-grow 1s cubic-bezier(.25,1.25,.4,1) both;
            animation-delay: calc(min(var(--i,0),12) * 60ms + 150ms); }
@keyframes bar-grow { from { width: 0; } }
```

The cubic-bezier has a control point **above 1** on the y-axis, which
overshoots slightly and settles — a spring feel without JS physics. The
attendance track adds a dashed 75% eligibility line (`::after` at `left:75%`)
and a warm `box-shadow` glow on bars below the cutoff — the threshold rule the
C++ engine enforces, made visible.

---

## 8. Count-up numbers — `@property` + CSS counters

Stat values that are always integers (students, courses) roll up from zero:

```css
@property --n { syntax: "<integer>"; inherits: false; initial-value: 0; }
.stat-value.count-up { counter-reset: stat var(--n); }
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

## 9. Login scene — the sanctioned exception

The login page drops the "refined chrome" restraint: `login-rise` keyframe
overshoots and settles (bounce), inputs get a red glow ring on focus, and the
button carries a slow sheen sweep:

```css
.login-card .btn::after {
  content: ""; position: absolute; width: 45%; inset-block: 0;
  background: linear-gradient(100deg, transparent, rgba(255,255,255,.5), transparent);
  animation: sheen-sweep 4.6s ease-in-out infinite;
}
```

The pseudo-element translates across and `overflow: hidden` clips it — a
highlight, not an image. `pointer-events: none` keeps it non-interactive.

---

## 10. Cross-fades, shimmer, scrollbar — the polish layer

- **Page transitions:** `@view-transition { navigation: auto; }` + old/new
  pseudo-elements fade pages on navigation in Chromium; other browsers ignore
  it and load instantly (graceful no-op). It is gated behind
  `prefers-reduced-motion: no-preference` because a cross-fade is motion —
  and because software-rendered/headless environments can stall on
  cross-document transitions (found by probing headless screenshots; the
  media gate plus feature detection makes the fallback instant everywhere).
- **Shimmering badges:** Pass/Fail pills are two stacked background images —
  the badge color plus a moving white `linear-gradient` sheen
  (`background-position` animation, `background-size: 220%`).
- **Selection/scrollbars:** `::selection`, `scrollbar-width/color`, and
  `-webkit-scrollbar` in accent gradients.
- **Focus:** `:focus-visible` outlines for keyboard users without punishing
  mouse clicks.

---

## 11. Reduced motion — a first-class fallback

```css
@media (prefers-reduced-motion: reduce) {
  .aurora .orb { animation: none; }
  .card, .stat-card, .bar-row, .data-table tbody tr { animation: none; opacity: 1; transform: none; }
  .bar-fill { animation: none; width: var(--w, 0%); }  /* final state immediately */
  * { transition-duration: .01ms !important; }
}
```

Motion is an enhancement; the static UI is identical informationally.

---

## 12. Viva one-liners

- "The theme system is **~25 overridden CSS variables**, not a second stylesheet."
- "Animations run on the **compositor** (`transform`, `opacity`, typed
  `@property`) so the aurora never triggers layout."
- "Stagger indexes are **rendered by Python**, so markup and motion stay in
  sync without JS."
- "Every dynamic number has a **static fallback**; progressive enhancement
  means the page degrades to a fully working 2015-era UI."
- "Marks saves are true **upserts** using MySQL 8.0.19+ row aliases
  (`INSERT ... AS new ON DUPLICATE KEY UPDATE ... = new.col`) — readable,
  and a version detail worth naming."
- "I proved the restyle didn't change behavior: a **snapshot diff of 18
  routes** — statuses, forms, inputs, links, permission probes — came back
  identical."
