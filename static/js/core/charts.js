/* Chart helpers. Chart.js is injected on first use (never on the home page)
   and every chart re-colours when the theme changes. */
let libraryPromise = null;
const registry = new Map();

function prefersReducedMotion() {
  return window.matchMedia
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function cssVar(name, fallback = "") {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

function colors() {
  return {
    primary: cssVar("--primary", "#1b3a8f"),
    success: cssVar("--success", "#12724a"),
    warning: cssVar("--warning", "#a4550a"),
    danger: cssVar("--danger", "#b3261e"),
    muted: cssVar("--muted", "#58657c"),
    border: cssVar("--chart-grid", "rgba(17,26,44,.08)"),
    text: cssVar("--chart-text", "#58657c"),
    surface: cssVar("--surface", "#ffffff"),
    font: cssVar("--font-sans", "Inter, sans-serif"),
    accent: cssVar("--accent", "#d98324"),
  };
}

export function statusColor(value, threshold = 75) {
  if (value === null || value === undefined) return colors().muted;
  if (value >= threshold) return colors().success;
  if (value >= threshold - 10) return colors().warning;
  return colors().danger;
}

export function loadChartJs() {
  if (window.Chart) return Promise.resolve(window.Chart);
  if (libraryPromise) return libraryPromise;
  libraryPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "/static/vendor/chart.umd.js";
    script.async = true;
    script.onload = () => resolve(window.Chart);
    script.onerror = () => reject(new Error("Chart library failed to load."));
    document.head.append(script);
  });
  return libraryPromise;
}

function baseOptions(chartColors) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: prefersReducedMotion() ? false : { duration: 650, easing: "easeOutQuart" },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: colors().surface,
        titleColor: chartColors.text,
        bodyColor: chartColors.text,
        borderColor: chartColors.border,
        borderWidth: 1,
        padding: 10,
        displayColors: false,
        cornerRadius: 8,
        titleFont: { family: chartColors.font, size: 12, weight: "600" },
        bodyFont: { family: chartColors.font, size: 12 },
      },
    },
  };
}

function register(chart, themeFn) {
  registry.set(chart, themeFn);
  return chart;
}

window.addEventListener("themechange", () => {
  const palette = colors();
  registry.forEach((apply, chart) => {
    try {
      apply(chart, palette);
      chart.update("none");
    } catch (error) {
      /* a destroyed chart can be skipped */
    }
  });
});

export function disposeCharts() {
  registry.forEach((_apply, chart) => {
    try { chart.destroy(); } catch (error) { /* noop */ }
  });
  registry.clear();
}

function miniDoughnut(chart, palette) {
  const value = chart.$value;
  const color = statusColor(value, chart.$threshold);
  chart.data.datasets[0].backgroundColor = [color, palette.border];
  chart.data.datasets[0].borderColor = palette.surface;
}

export async function doughnutChart(canvas, { value, threshold = 75, cutout = "76%" }) {
  const Chart = await loadChartJs();
  const palette = colors();
  const safe = Math.max(0, Math.min(100, Number(value) || 0));
  const color = statusColor(safe, threshold);
  const chart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: ["Attended", "Missed"],
      datasets: [{
        data: [safe, Math.max(0, 100 - safe)],
        backgroundColor: [color, palette.border],
        borderColor: palette.surface,
        borderWidth: 3,
        hoverOffset: 2,
      }],
    },
    options: {
      ...baseOptions(palette),
      cutout,
      rotation: -90,
      circumference: 360,
      plugins: {
        ...baseOptions(palette).plugins,
        tooltip: {
          ...baseOptions(palette).plugins.tooltip,
          callbacks: {
            label: (context) => `${context.label}: ${context.raw}%`,
          },
        },
      },
    },
  });
  chart.$value = safe;
  chart.$threshold = threshold;
  return register(chart, miniDoughnut);
}

export async function lineChart(canvas, { labels, values, label = "Attendance", threshold = null }) {
  const Chart = await loadChartJs();
  const palette = colors();
  const context = canvas.getContext("2d");
  const gradient = context.createLinearGradient(0, 0, 0, canvas.height || 220);
  gradient.addColorStop(0, `${hexToRgba(palette.primary, 0.25)}`);
  gradient.addColorStop(1, `${hexToRgba(palette.primary, 0)}`);

  const chart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label,
        data: values,
        borderColor: palette.primary,
        backgroundColor: gradient,
        borderWidth: 2.5,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: palette.primary,
        pointBorderColor: palette.surface,
        pointBorderWidth: 2,
        tension: 0.35,
        spanGaps: true,
        fill: true,
      }],
    },
    options: {
      ...baseOptions(palette),
      scales: {
        x: {
          grid: { display: false, drawBorder: false },
          ticks: {
            color: palette.text, font: { family: palette.font, size: 10 },
            maxRotation: 0, autoSkip: true,
          },
          border: { display: false },
        },
        y: {
          min: 0,
          max: 100,
          grid: { color: palette.border, drawBorder: false },
          ticks: {
            color: palette.text, font: { family: palette.font, size: 10 },
            callback: (value) => `${value}%`, stepSize: 25,
          },
          border: { display: false },
        },
      },
      plugins: {
        ...baseOptions(palette).plugins,
        tooltip: {
          ...baseOptions(palette).plugins.tooltip,
          callbacks: {
            label: (context) => context.raw === null
              ? "No classes"
              : `${context.parsed.y}% attended`,
          },
        },
      },
    },
  });

  return register(chart, (instance, nextPalette) => {
    instance.data.datasets[0].borderColor = nextPalette.primary;
    instance.data.datasets[0].pointBackgroundColor = nextPalette.primary;
    instance.data.datasets[0].pointBorderColor = nextPalette.surface;
    const ctx = instance.ctx;
    const fill = ctx.createLinearGradient(0, 0, 0, canvas.height || 220);
    fill.addColorStop(0, hexToRgba(nextPalette.primary, 0.25));
    fill.addColorStop(1, hexToRgba(nextPalette.primary, 0));
    instance.data.datasets[0].backgroundColor = fill;
    themeScales(instance, nextPalette);
  });
}

function themeScales(chart, palette) {
  if (chart.options.scales) {
    Object.values(chart.options.scales).forEach((scale) => {
      if (scale.ticks) scale.ticks.color = palette.text;
      if (scale.grid && scale.grid.color) scale.grid.color = palette.border;
    });
  }
  if (chart.options.plugins?.tooltip) {
    Object.assign(chart.options.plugins.tooltip, {
      backgroundColor: palette.surface,
      titleColor: palette.text,
      bodyColor: palette.text,
      borderColor: palette.border,
    });
  }
}

export async function barChart(canvas, { labels, values, threshold = 75 }) {
  const Chart = await loadChartJs();
  const palette = colors();
  const chartColors = values.map((value) => statusColor(value, threshold));
  const chart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: chartColors,
        borderRadius: 6,
        borderSkipped: false,
        maxBarThickness: 42,
      }],
    },
    options: {
      ...baseOptions(palette),
      scales: {
        x: {
          grid: { display: false, drawBorder: false },
          ticks: { color: palette.text, font: { family: palette.font, size: 10 } },
          border: { display: false },
        },
        y: {
          min: 0, max: 100,
          grid: { color: palette.border, drawBorder: false },
          ticks: {
            color: palette.text, font: { family: palette.font, size: 10 },
            callback: (value) => `${value}%`, stepSize: 25,
          },
          border: { display: false },
        },
      },
      plugins: {
        ...baseOptions(palette).plugins,
        tooltip: {
          ...baseOptions(palette).plugins.tooltip,
          callbacks: { label: (context) => `${context.parsed.y}% attended` },
        },
      },
    },
  });
  return register(chart, (instance, nextPalette) => {
    instance.data.datasets[0].backgroundColor = instance.data.datasets[0].data
      .map((value) => statusColor(value, threshold));
    themeScales(instance, nextPalette);
  });
}

export async function stackedBarChart(canvas, { labels, present, late, absent }) {
  const Chart = await loadChartJs();
  const palette = colors();
  const chart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "Present", data: present, backgroundColor: palette.success, borderRadius: 4, stack: "a" },
        { label: "Late", data: late, backgroundColor: palette.warning, borderRadius: 4, stack: "a" },
        { label: "Absent", data: absent, backgroundColor: palette.danger, borderRadius: 4, stack: "a" },
      ],
    },
    options: {
      ...baseOptions(palette),
      scales: {
        x: {
          stacked: true, grid: { display: false, drawBorder: false },
          ticks: { color: palette.text, font: { family: palette.font, size: 10 } },
          border: { display: false },
        },
        y: {
          stacked: true, beginAtZero: true,
          grid: { color: palette.border, drawBorder: false },
          ticks: { color: palette.text, font: { family: palette.font, size: 10 }, precision: 0 },
          border: { display: false },
        },
      },
      plugins: {
        ...baseOptions(palette).plugins,
        legend: {
          display: true,
          position: "bottom",
          labels: {
            color: palette.text, boxWidth: 8, boxHeight: 8, usePointStyle: true,
            font: { family: palette.font, size: 11 },
          },
        },
      },
    },
  });
  return register(chart, (instance, nextPalette) => {
    instance.data.datasets[0].backgroundColor = nextPalette.success;
    instance.data.datasets[1].backgroundColor = nextPalette.warning;
    instance.data.datasets[2].backgroundColor = nextPalette.danger;
    themeScales(instance, nextPalette);
    if (instance.options.plugins.legend?.labels) {
      instance.options.plugins.legend.labels.color = nextPalette.text;
    }
  });
}

function hexToRgba(color, alpha) {
  if (!color) return `rgba(27, 58, 143, ${alpha})`;
  const hex = color.replace("#", "");
  if (hex.length === 3) {
    const [r, g, b] = hex.split("").map((part) => Number.parseInt(part + part, 16));
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  if (hex.length >= 6) {
    const r = Number.parseInt(hex.slice(0, 2), 16);
    const g = Number.parseInt(hex.slice(2, 4), 16);
    const b = Number.parseInt(hex.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return `rgba(27, 58, 143, ${alpha})`;
}
