// One-time Chart.js dark-theme defaults. Imported for side-effects from
// main.tsx so every chart in the admin analytics view inherits the look.

import { Chart } from "chart.js";

// Match the rest of the dark glassmorphic UI:
// zinc-400 text, zinc-700 (with alpha) grid lines, Inter font.
Chart.defaults.color = "#a1a1aa";
Chart.defaults.borderColor = "rgba(63, 63, 70, 0.5)";
Chart.defaults.font.family =
  '"Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
Chart.defaults.font.size = 12;

// Tooltip defaults — white text on a near-black panel.
Chart.defaults.plugins.tooltip.backgroundColor = "rgba(9, 9, 11, 0.92)";
Chart.defaults.plugins.tooltip.titleColor = "#fafafa";
Chart.defaults.plugins.tooltip.bodyColor = "#e4e4e7";
Chart.defaults.plugins.tooltip.borderColor = "rgba(99, 102, 241, 0.45)";
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 8;

// Legend defaults — small caps, zinc text.
Chart.defaults.plugins.legend.labels.color = "#d4d4d8";
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 8;
Chart.defaults.plugins.legend.labels.padding = 16;
