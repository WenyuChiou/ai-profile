"""Self-contained interactive dashboard renderer — the v0.8.0 Signal Console
(ADR-021 contract, ADR-031 presentation).

The dashboard is a pure function of the validated, privacy-safe ``VizStats``
contract. It never reads Git, SQLite, configuration, the clock, or the
network. All CSS, JavaScript, and aggregate data are embedded in one HTML
document so users may open it locally or publish it as a static page.

Presentation grammar (ADR-031): a compact status line carrying the
*snapshot* date, a four-cell core metric strip, a provider toolbar, the
primary commit map, and a provider/evidence sidebar that collapses under the
map on narrow screens; definitions live in a native ``<details>``
disclosure. One token system drives light, dark, and system themes; motion is
limited to short transform/opacity state changes and is fully disabled under
``prefers-reduced-motion``.
"""

from __future__ import annotations

import json

from ..viz import VizStats, to_json_dict
from .brand import BRAND

_PROVIDER_GLYPHS_JSON = json.dumps(
    {slug: spec.path for slug, spec in sorted(BRAND.items())},
    ensure_ascii=True,
    separators=(",", ":"),
    sort_keys=True,
)
_HTML_PREFIX = """<!doctype html>
<html lang="en" data-theme="auto">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline';
                 img-src data:; font-src 'none'; connect-src 'none'; object-src 'none';
                 base-uri 'none'; form-action 'none'">
  <title>AI Collaboration Record</title>
  <style>
    :root {
      color-scheme: light;
      --canvas: #f3f7fb;
      --surface: #fbfdff;
      --surface-raised: #ffffff;
      --surface-subtle: #edf4fb;
      --border: #c2d3e5;
      --border-strong: #7590aa;
      --text: #172033;
      --muted: #52647a;
      --accent: #005cc5;
      --accent-soft: #d9eaff;
      --evidence: #9a6700;
      --evidence-surface: #fff0bd;
      --grid-empty: #e5eef7;
      --calendar-active-border: #52647a;
      --focus: #005cc5;
      --display: "IBM Plex Sans Condensed", "Aptos Display", "Segoe UI",
        "DejaVu Sans Condensed", "Liberation Sans Narrow", sans-serif;
      --body: "IBM Plex Sans", "Aptos", "Segoe UI", "Noto Sans",
        "DejaVu Sans", sans-serif;
      --mono: "IBM Plex Mono", "Cascadia Mono", "SFMono-Regular",
        "DejaVu Sans Mono", Consolas, monospace;
      --text-1: 0.8125rem;
      --text-2: 0.9375rem;
      --text-3: 1.125rem;
      --text-4: 1.75rem;
      --text-5: 2.25rem;
      --space-1: 0.25rem;
      --space-2: 0.5rem;
      --space-3: 0.75rem;
      --space-4: 1rem;
      --space-5: 1.25rem;
      --space-6: 1.5rem;
      --space-8: 2rem;
      --radius-sm: 0.25rem;
      --radius-md: 0.375rem;
    }

    @media (prefers-color-scheme: dark) {
      :root:not([data-theme="light"]) {
        color-scheme: dark;
        --canvas: #0b1625;
        --surface: #111923;
        --surface-raised: #142b45;
        --surface-subtle: #122a43;
        --border: #34526f;
        --border-strong: #6683a0;
        --text: #eff6ff;
        --muted: #b5c7da;
        --accent: #8bc8ff;
        --accent-soft: #153756;
        --evidence: #eac54f;
        --evidence-surface: #3b331e;
        --grid-empty: #111923;
        --calendar-active-border: #b5ddff;
        --focus: #8bc8ff;
      }
    }

    :root[data-theme="dark"] {
      color-scheme: dark;
      --canvas: #0b1625;
      --surface: #111923;
      --surface-raised: #142b45;
      --surface-subtle: #122a43;
      --border: #34526f;
      --border-strong: #6683a0;
      --text: #eff6ff;
      --muted: #b5c7da;
      --accent: #8bc8ff;
      --accent-soft: #153756;
      --evidence: #eac54f;
      --evidence-surface: #3b331e;
      --grid-empty: #111923;
      --calendar-active-border: #b5ddff;
      --focus: #8bc8ff;
    }

    * {
      box-sizing: border-box;
    }

    html {
      min-width: 0;
      background: var(--canvas);
      font-family: var(--body);
      font-kerning: normal;
      font-variant-numeric: lining-nums tabular-nums;
      color: var(--text);
      text-rendering: optimizeLegibility;
    }

    body {
      min-height: 100vh;
      margin: 0;
      overflow-x: clip;
      background: var(--canvas);
      font-size: var(--text-2);
      line-height: 1.5;
    }

    button {
      font: inherit;
    }

    .theme-toggle,
    .filter,
    .provider-row {
      appearance: none;
      -webkit-appearance: none;
    }

    button:focus-visible,
    summary:focus-visible,
    [tabindex="0"]:focus-visible {
      outline: 0.1875rem solid var(--focus);
      outline-offset: 0.125rem;
    }

    .console {
      width: min(100% - 2rem, 76rem);
      min-width: 0;
      margin: 0 auto;
      padding: var(--space-4) 0 var(--space-8);
    }

    .console > *,
    .console-grid > *,
    .sidebar > *,
    .metrics > * {
      min-width: 0;
    }

    .statusbar {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      grid-template-areas: "title meta controls";
      gap: var(--space-2) var(--space-5);
      align-items: baseline;
      padding: var(--space-3) 0;
      border-bottom: 1px solid var(--border-strong);
    }

    .statusbar-title {
      grid-area: title;
      margin: 0;
      font-family: var(--display);
      font-size: var(--text-3);
      font-weight: 600;
      letter-spacing: -0.01em;
      line-height: 1.3;
    }

    .statusbar-meta {
      grid-area: meta;
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-1) var(--space-3);
      margin: 0;
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.5;
    }

    .status-item {
      display: inline-flex;
      gap: var(--space-1);
      align-items: baseline;
    }

    .status-item + .status-item::before {
      content: "·";
      margin-right: var(--space-1);
      color: var(--border-strong);
    }

    .status-value {
      color: var(--text);
      font-family: var(--mono);
      font-weight: 600;
    }

    .statusbar-controls {
      grid-area: controls;
      display: flex;
      gap: var(--space-2);
      align-items: center;
      justify-content: flex-end;
    }

    .theme-toggle {
      min-height: 2.25rem;
      padding: 0 var(--space-3);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      background: var(--surface);
      color: var(--text);
      cursor: pointer;
      font-size: var(--text-1);
      font-weight: 600;
    }

    .theme-toggle:hover {
      border-color: var(--border-strong);
    }

    .metrics {
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) repeat(3, minmax(0, 1fr));
      margin-top: var(--space-4);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      background: var(--surface);
    }

    .metric {
      padding: var(--space-4) var(--space-5);
      border-inline-start: 1px solid var(--border);
    }

    .metric:first-child {
      border-inline-start: 0;
    }

    .metric-value {
      margin: 0;
      font-family: var(--mono);
      font-size: var(--text-4);
      font-weight: 600;
      letter-spacing: -0.02em;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }

    .metric--primary .metric-value {
      color: var(--active-accent, var(--accent));
      font-size: var(--text-5);
    }

    .metric-label {
      margin: var(--space-2) 0 0;
      font-size: var(--text-2);
      font-weight: 600;
      line-height: 1.35;
    }

    .metric-detail {
      margin: var(--space-1) 0 0;
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.45;
    }

    .share-track {
      height: 0.375rem;
      margin-top: var(--space-3);
      overflow: hidden;
      border-radius: 0.125rem;
      background: var(--grid-empty);
    }

    .share-fill {
      width: 0;
      height: 100%;
      border-radius: inherit;
      background: var(--active-accent, var(--accent));
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2) var(--space-3);
      align-items: center;
      margin-top: var(--space-4);
    }

    .toolbar-label {
      color: var(--muted);
      font-size: var(--text-1);
      font-weight: 600;
    }

    .filters {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
    }

    .filter {
      display: inline-flex;
      gap: var(--space-2);
      align-items: center;
      min-height: 2.25rem;
      padding: 0 var(--space-3);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      background: var(--surface);
      color: var(--text);
      cursor: pointer;
      font-size: var(--text-1);
      font-weight: 600;
    }

    .filter:hover {
      border-color: var(--provider-accent, var(--accent));
    }

    .filter[aria-pressed="true"] {
      border-color: var(--provider-accent, var(--accent));
      background: color-mix(in srgb, var(--provider-accent, var(--accent)) 12%, var(--surface));
      box-shadow: inset 0 0 0 1px var(--provider-accent, var(--accent));
    }

    .provider-icon {
      display: inline-block;
      flex: 0 0 auto;
      width: 1rem;
      height: 1rem;
      color: var(--provider-accent, var(--accent));
      vertical-align: -0.14rem;
    }

    .provider-icon--row {
      width: 1.25rem;
      height: 1.25rem;
      padding: 0.18rem;
      border: 1px solid color-mix(in srgb, var(--provider-accent) 38%, var(--border));
      border-radius: var(--radius-sm);
      background: color-mix(in srgb, var(--provider-accent) 10%, var(--surface));
    }

    .console-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(18rem, 0.8fr);
      gap: var(--space-4);
      align-items: start;
      margin-top: var(--space-4);
    }

    .sidebar {
      display: grid;
      gap: var(--space-4);
    }

    .panel {
      padding: var(--space-5);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      background: var(--surface);
    }

    .panel-heading {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2) var(--space-4);
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: var(--space-4);
    }

    .panel-title {
      margin: 0;
      font-family: var(--display);
      font-size: var(--text-3);
      font-weight: 600;
      line-height: 1.3;
    }

    .panel-meta {
      margin: 0;
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.5;
    }

    .calendar-scroll {
      width: 100%;
      min-width: 0;
      max-width: 100%;
      overflow-x: auto;
      padding: var(--space-2) var(--space-1) var(--space-3);
      scrollbar-color: var(--border-strong) transparent;
    }

    .calendar {
      display: grid;
      grid-template-rows: repeat(7, 0.82rem);
      grid-auto-flow: column;
      grid-auto-columns: 0.82rem;
      gap: 0.28rem;
      width: max-content;
      min-width: 100%;
      align-content: start;
    }

    .day-cell,
    .day-spacer {
      width: 0.82rem;
      height: 0.82rem;
    }

    .day-cell {
      appearance: none;
      padding: 0;
      border: 1px solid color-mix(in srgb, var(--border) 62%, transparent);
      border-radius: 0.19rem;
      background: var(--grid-empty);
      cursor: help;
      transition: transform 120ms ease;
    }

    .day-cell[data-active="true"] {
      border-color: var(--calendar-active-border);
    }

    .day-cell:hover,
    .day-cell:focus-visible {
      z-index: 2;
      border-color: var(--text);
      transform: scale(1.42);
    }

    .calendar-empty {
      display: grid;
      min-height: 8rem;
      place-items: center;
      border: 1px dashed var(--border);
      border-radius: var(--radius-md);
      color: var(--muted);
      text-align: center;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3) var(--space-4);
      align-items: center;
      justify-content: space-between;
      margin-top: var(--space-3);
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.45;
    }

    .legend-scale {
      display: flex;
      gap: 0.24rem;
      align-items: center;
    }

    .legend-cell {
      width: 0.82rem;
      height: 0.82rem;
      border: 1px solid var(--border);
      border-radius: 0.18rem;
      background: var(--grid-empty);
    }

    .legend-cell[data-level] {
      border-color: var(--calendar-active-border);
    }

    .provider-list {
      display: grid;
      gap: var(--space-2);
    }

    .provider-row {
      display: grid;
      gap: var(--space-2);
      width: 100%;
      padding: var(--space-3);
      border: 1px solid transparent;
      border-radius: var(--radius-sm);
      background: transparent;
      color: inherit;
      cursor: pointer;
      text-align: left;
    }

    .provider-row[aria-current="true"] {
      border-color: var(--provider-accent);
      background: color-mix(in srgb, var(--provider-accent) 10%, var(--surface));
    }

    .provider-row:hover {
      background: color-mix(in srgb, var(--provider-accent) 6%, var(--surface));
    }

    .provider-row-head {
      display: flex;
      gap: var(--space-3);
      align-items: baseline;
      justify-content: space-between;
    }

    .provider-name {
      display: inline-flex;
      gap: var(--space-2);
      align-items: center;
      color: var(--text);
      font-size: var(--text-2);
      font-weight: 600;
    }

    .provider-count {
      font-family: var(--mono);
      font-size: var(--text-2);
      font-weight: 600;
    }

    .provider-track {
      height: 0.375rem;
      overflow: hidden;
      border-radius: 0.125rem;
      background: var(--grid-empty);
    }

    .provider-fill {
      height: 100%;
      border-radius: inherit;
      background: var(--provider-accent);
    }

    .provider-detail {
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.5;
    }

    .evidence-panel .panel-title::before {
      content: "";
      display: inline-block;
      width: 0.5rem;
      height: 0.5rem;
      margin-right: var(--space-2);
      border: 1px solid var(--evidence);
      border-radius: 0.125rem;
      background: var(--evidence-surface);
      vertical-align: 0.05em;
    }

    .evidence-track {
      display: flex;
      height: 0.625rem;
      margin: 0 0 var(--space-4);
      overflow: hidden;
      border-radius: 0.125rem;
      background: var(--grid-empty);
    }

    .evidence-segment {
      min-width: 0;
      height: 100%;
    }

    .evidence-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: var(--space-2) var(--space-4);
    }

    .evidence-item {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: var(--space-2);
      align-items: center;
      min-width: 0;
      color: var(--muted);
      font-size: var(--text-1);
    }

    .evidence-swatch {
      width: 0.55rem;
      height: 0.55rem;
      border-radius: 0.12rem;
      background: var(--evidence-color);
    }

    .evidence-count {
      color: var(--text);
      font-family: var(--mono);
      font-weight: 600;
    }

    .evidence-note {
      margin: var(--space-4) 0 0;
      padding-top: var(--space-3);
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.5;
    }

    .definitions {
      margin-top: var(--space-4);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      background: var(--surface);
    }

    .definitions-summary {
      display: flex;
      gap: var(--space-3);
      align-items: center;
      justify-content: space-between;
      padding: var(--space-3) var(--space-5);
      cursor: pointer;
      font-size: var(--text-2);
      font-weight: 600;
      list-style: none;
    }

    .definitions-summary::-webkit-details-marker {
      display: none;
    }

    .definitions-summary::after {
      content: "";
      flex: 0 0 auto;
      width: 0.5rem;
      height: 0.5rem;
      margin-right: var(--space-1);
      border-right: 2px solid var(--muted);
      border-bottom: 2px solid var(--muted);
      transform: rotate(45deg);
      transition: transform 120ms ease;
    }

    .definitions[open] .definitions-summary::after {
      transform: rotate(-135deg);
    }

    .definitions-body {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
      gap: var(--space-4) var(--space-6);
      padding: 0 var(--space-5) var(--space-5);
    }

    .note-title {
      margin: 0 0 var(--space-1);
      font-size: var(--text-2);
      font-weight: 600;
    }

    .note-copy {
      margin: 0;
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.6;
    }

    .console-foot {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2) var(--space-4);
      justify-content: space-between;
      margin-top: var(--space-4);
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.5;
    }

    .tooltip {
      position: fixed;
      z-index: 30;
      width: max-content;
      max-width: min(18rem, calc(100vw - 2rem));
      padding: var(--space-2) var(--space-3);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-sm);
      background: var(--surface-raised);
      color: var(--text);
      font-size: var(--text-1);
      line-height: 1.5;
      pointer-events: none;
      transform: translate(-50%, calc(-100% - 0.75rem));
    }

    .tooltip[hidden] {
      display: none;
    }

    .tooltip-date {
      display: block;
      margin-bottom: var(--space-1);
      font-family: var(--mono);
      font-weight: 600;
    }

    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }

    @media (max-width: 54rem) {
      .console-grid {
        grid-template-columns: minmax(0, 1fr);
      }

      .metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .metric:nth-child(odd) {
        border-inline-start: 0;
      }

      .metric:nth-child(n+3) {
        border-top: 1px solid var(--border);
      }
    }

    @media (max-width: 38rem) {
      .console {
        width: min(100% - 1rem, 76rem);
      }

      .statusbar {
        grid-template-columns: minmax(0, 1fr) auto;
        grid-template-areas:
          "title controls"
          "meta meta";
        align-items: center;
      }

      .metric {
        padding: var(--space-3) var(--space-4);
      }

      .panel {
        padding: var(--space-4);
      }

      .evidence-grid {
        grid-template-columns: minmax(0, 1fr);
      }
    }

    @media (max-width: 22rem) {
      .statusbar {
        grid-template-columns: minmax(0, 1fr);
        grid-template-areas:
          "title"
          "meta"
          "controls";
      }

      .statusbar-controls {
        justify-content: flex-start;
      }

      .metrics {
        grid-template-columns: minmax(0, 1fr);
      }

      .metric {
        border-inline-start: 0;
        border-top: 1px solid var(--border);
      }

      .metric:first-child {
        border-top: 0;
      }

      .filters {
        display: grid;
        grid-template-columns: minmax(0, 1fr);
      }

      .filter {
        width: 100%;
        justify-content: center;
      }

      .panel,
      .definitions-summary {
        padding: var(--space-4);
      }

      .definitions-body {
        padding: 0 var(--space-4) var(--space-4);
      }

      .panel-heading > *,
      .provider-row,
      .statusbar > * {
        min-width: 0;
        max-width: 100%;
      }

      .statusbar-title,
      .statusbar-meta,
      .panel-title,
      .panel-meta,
      .metric-label,
      .metric-detail,
      .provider-name,
      .provider-detail,
      .evidence-item,
      .console-foot {
        overflow-wrap: anywhere;
      }

      .provider-row-head,
      .legend-scale,
      .status-item {
        flex-wrap: wrap;
      }
    }

    @media (pointer: coarse) {
      .calendar {
        grid-template-rows: repeat(7, 1rem);
        grid-auto-columns: 1rem;
        gap: 0.5rem;
      }

      .day-cell,
      .day-spacer {
        width: 1rem;
        height: 1rem;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .day-cell,
      .definitions-summary::after {
        transition: none;
      }

      .day-cell:hover,
      .day-cell:focus-visible {
        transform: none;
      }
    }
  </style>
</head>
<body>
  <main class="console">
    <header class="statusbar">
      <h1 class="statusbar-title">AI Collaboration Record</h1>
      <p class="statusbar-meta">
        <span class="status-item"><span>Snapshot</span>
          <time class="status-value" id="snapshotDate"></time> <span>UTC</span></span>
        <span class="status-item" id="periodLabel"></span>
        <span class="status-item" id="schemaLabel"></span>
      </p>
      <div class="statusbar-controls">
        <button class="theme-toggle" id="themeToggle" type="button"
                aria-label="Theme: auto. Activate for light theme">Theme: auto</button>
      </div>
    </header>

    <p class="sr-only" id="selectionStatus" role="status" aria-live="polite"></p>

    <section class="metrics" aria-label="Core collaboration metrics">
      <div class="metric metric--primary" id="primaryMetric">
        <p class="metric-value" id="primaryValue">0</p>
        <p class="metric-label" id="primaryLabel">AI-attributed commits</p>
        <p class="metric-detail" id="primaryDetail"></p>
        <div class="share-track" aria-hidden="true">
          <div class="share-fill" id="shareFill"></div>
        </div>
      </div>
      <div class="metric">
        <p class="metric-value" id="presenceValue">0</p>
        <p class="metric-label" id="presenceLabel">AI actor presences</p>
        <p class="metric-detail">One per provider/tool in a commit.</p>
      </div>
      <div class="metric">
        <p class="metric-value" id="daysValue">0</p>
        <p class="metric-label">Active AI days</p>
        <p class="metric-detail">Commit author dates with AI evidence.</p>
      </div>
      <div class="metric">
        <p class="metric-value" id="unknownValue">0</p>
        <p class="metric-label">Unattributed commits</p>
        <p class="metric-detail">No explicit AI or human declaration recorded.</p>
      </div>
    </section>

    <section class="toolbar" aria-label="Provider view">
      <span class="toolbar-label" id="filterLabel">Provider view</span>
      <div class="filters" id="providerFilters" role="group"
           aria-label="Filter dashboard by AI provider"></div>
    </section>

    <div class="console-grid">
      <section class="panel activity-panel" aria-labelledby="activityTitle">
        <div class="panel-heading">
          <h2 class="panel-title" id="activityTitle">Commit map</h2>
          <p class="panel-meta" id="activityMeta"></p>
        </div>
        <div class="calendar-scroll">
          <div class="calendar" id="activityCalendar" role="group"
               aria-labelledby="activitySummary"></div>
        </div>
        <p class="sr-only" id="activitySummary"></p>
        <div class="legend">
          <span>
            Fixed bins: 1 / 2-4 / 5-7 / 8+ selected commits.
            Newest activity is shown; scroll for earlier days.
          </span>
          <span class="legend-scale"
                aria-label="Selected attributed-commit volume: none, 1, 2 to 4, 5 to 7, 8 or more">
            none
            <span class="legend-cell"></span>
            <span class="legend-cell" data-level="1"></span>
            <span class="legend-cell" data-level="2"></span>
            <span class="legend-cell" data-level="3"></span>
            <span class="legend-cell" data-level="4"></span>
            8+
          </span>
        </div>
      </section>

      <aside class="sidebar" aria-label="Provider ledger and evidence">
        <section class="panel providers-panel" aria-labelledby="providersTitle">
          <div class="panel-heading">
            <h2 class="panel-title" id="providersTitle">Providers</h2>
            <p class="panel-meta">Attributed commits, not mutually exclusive</p>
          </div>
          <div class="provider-list" id="providerList"></div>
        </section>

        <section class="panel evidence-panel" aria-labelledby="evidenceTitle">
          <div class="panel-heading">
            <h2 class="panel-title" id="evidenceTitle">Evidence</h2>
            <p class="panel-meta" id="evidenceTotal"></p>
          </div>
          <div class="evidence-track" id="evidenceTrack" aria-hidden="true"></div>
          <div class="evidence-grid" id="evidenceGrid"></div>
          <p class="evidence-note">All ACE records, every actor type. Unknown evidence is
            recorded as unknown; it is never recolored or inferred.</p>
        </section>
      </aside>
    </div>

    <details class="definitions" id="definitions">
      <summary class="definitions-summary">Definitions, attribution, and privacy boundary</summary>
      <div class="definitions-body">
        <div>
          <h2 class="note-title">Unique commits</h2>
          <p class="note-copy">
            The all-provider view counts a commit once when at least one explicit AI actor
            is present. Provider totals may overlap when several actors share one commit.
          </p>
        </div>
        <div>
          <h2 class="note-title">Unattributed is not human</h2>
          <p class="note-copy">
            Commits without an explicit AI or human declaration stay unattributed. They are
            never inferred from source-code style and never counted as human work.
          </p>
        </div>
        <div>
          <h2 class="note-title">Improve future attribution</h2>
          <p class="note-copy">
            Add an <code>AI-*</code> trailer to future commits. Historical commits without
            explicit evidence remain unattributed.
          </p>
        </div>
        <div>
          <h2 class="note-title">Privacy boundary</h2>
          <p class="note-copy" id="privacyCopy"></p>
        </div>
      </div>
    </details>

    <footer class="console-foot">
      <span>Static snapshot rendered locally by aiprofile from explicit Git provenance;
        numbers change only when the profile is regenerated.</span>
      <span id="footSnapshot"></span>
    </footer>
  </main>

  <div class="tooltip" id="tooltip" role="tooltip" hidden></div>
  <script type="application/json" id="profileData">"""

_HTML_SUFFIX = """</script>
  <script>
    (() => {
      "use strict";

      const data = JSON.parse(document.getElementById("profileData").textContent);
      const providerGlyphs = __PROVIDER_GLYPHS__;
      // The SVG namespace URI for createElementNS - an identifier, never a
      // fetched network URL (the CSP forbids all connections anyway).
      const SVG_NS = "http:" + "//www.w3.org/2000/svg";
      const $ = (id) => document.getElementById(id);
      const number = new Intl.NumberFormat("en-US");
      const percent = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
      const providerColors = {
        anthropic: "#9a6700",
        openai: "#1a7f37",
        github_copilot: "#0969da",
        google: "#8250df",
        cursor: "#cf222e",
        sourcegraph: "#1f883d",
        moonshot: "#1f6feb",
        deepseek: "#1f6feb",
        alibaba: "#9a6700",
        mistral: "#bc4c00",
        xai: "#6e7681",
        zhipu: "#8250df",
        ollama: "#6e7681",
        meta: "#0969da",
        replit: "#bc4c00",
        amp: "#1a7f37",
        unrecognized: "#6e7781"
      };
      const fallbackColors = [
        "#0969da", "#1a7f37", "#9a6700", "#8250df", "#cf222e", "#1f6feb"
      ];
      const evidenceColors = {
        verified: "#1a7f37",
        declared: "#0969da",
        imported: "#8250df",
        inferred: "#bf8700",
        unknown: "#6e7781"
      };
      let selected = "all";
      let theme = "auto";
      let calendarFocusIndex = null;
      let tooltipOwner = null;
      let tooltipPinned = false;
      let tooltipSuppressed = null;
      let tooltipHoverPaused = false;

      function colorFor(slug) {
        if (providerColors[slug]) return providerColors[slug];
        let hash = 0;
        for (const char of slug) hash = ((hash << 5) - hash + char.charCodeAt(0)) | 0;
        return fallbackColors[Math.abs(hash) % fallbackColors.length];
      }

      function providerIcon(slug, label, variant) {
        const icon = document.createElementNS(SVG_NS, "svg");
        icon.classList.add("provider-icon", `provider-icon--${variant}`);
        icon.setAttribute("viewBox", "0 0 24 24");
        icon.setAttribute("aria-hidden", "true");
        icon.setAttribute("focusable", "false");
        const glyph = providerGlyphs[slug];
        if (glyph) {
          const path = document.createElementNS(SVG_NS, "path");
          path.setAttribute("d", glyph);
          path.setAttribute("fill", "currentColor");
          icon.append(path);
        } else if (slug === "all") {
          const path = document.createElementNS(SVG_NS, "path");
          path.setAttribute("d", "M6 6h4v4H6V6Zm8 0h4v4h-4V6ZM6 14h4v4H6v-4Zm8 0h4v4h-4v-4Z");
          path.setAttribute("fill", "currentColor");
          icon.append(path);
        } else {
          const text = document.createElementNS(SVG_NS, "text");
          text.setAttribute("x", "12");
          text.setAttribute("y", "17");
          text.setAttribute("fill", "currentColor");
          text.setAttribute("font-size", "14");
          text.setAttribute("font-weight", "700");
          text.setAttribute("text-anchor", "middle");
          text.textContent = label.slice(0, 1).toUpperCase();
          icon.append(text);
        }
        return icon;
      }

      function hexToRgb(hex) {
        const value = hex.replace("#", "");
        return [
          parseInt(value.slice(0, 2), 16),
          parseInt(value.slice(2, 4), 16),
          parseInt(value.slice(4, 6), 16)
        ];
      }

      function rgba(hex, alpha) {
        const [r, g, b] = hexToRgb(hex);
        return `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(3)})`;
      }

      function providerBySlug(slug) {
        return data.providers.find((row) => row.provider === slug);
      }

      function selectedRow() {
        return selected === "all" ? null : providerBySlug(selected);
      }

      function selectedName() {
        const row = selectedRow();
        return row ? row.display_name : "All AI";
      }

      function selectedAccent() {
        if (selected !== "all") return colorFor(selected);
        return getComputedStyle(document.documentElement)
          .getPropertyValue("--accent")
          .trim();
      }

      function selectedDayCount(day) {
        if (selected === "all") return day.ai_commits;
        const row = day.counts.find((count) => count.provider === selected);
        return row ? row.attributed_commits : 0;
      }

      function dateAtUtc(value) {
        const [year, month, day] = value.split("-").map(Number);
        return new Date(Date.UTC(year, month - 1, day));
      }

      function dateKey(value) {
        return value.toISOString().slice(0, 10);
      }

      function fillDailySeries() {
        if (!data.daily.length) return [];
        const byDate = new Map(data.daily.map((day) => [day.date, day]));
        const start = dateAtUtc(data.daily[0].date);
        const end = dateAtUtc(data.daily[data.daily.length - 1].date);
        const rows = [];
        for (
          let cursor = new Date(start);
          cursor <= end && rows.length < 365;
          cursor.setUTCDate(cursor.getUTCDate() + 1)
        ) {
          const key = dateKey(cursor);
          rows.push(byDate.get(key) || {
            date: key,
            total_commits: 0,
            ai_commits: 0,
            counts: []
          });
        }
        return rows;
      }

      function renderFilters() {
        const rows = [{ provider: "all", display_name: "All AI" }, ...data.providers];
        $("providerFilters").replaceChildren(...rows.map((row) => {
          const button = document.createElement("button");
          const accent = row.provider === "all" ? "#0969da" : colorFor(row.provider);
          button.type = "button";
          button.className = "filter";
          button.dataset.provider = row.provider;
          button.setAttribute("aria-pressed", String(selected === row.provider));
          button.style.setProperty("--provider-accent", accent);
          button.append(
            providerIcon(row.provider, row.display_name, "filter"),
            document.createTextNode(row.display_name)
          );
          button.addEventListener("click", () => {
            selected = row.provider;
            render();
          });
          return button;
        }));
      }

      function renderMetrics() {
        const row = selectedRow();
        const commitCount = row ? row.attributed_commits : data.totals.ai_attributed_commits;
        const presenceCount = row ? row.actor_presences : data.totals.ai_actor_presences;
        const dayCount = row ? row.active_days : data.totals.active_ai_days;
        const denominator = data.totals.commits_scanned;
        const share = denominator ? (commitCount / denominator) * 100 : 0;
        const accent = selectedAccent();

        $("primaryMetric").style.setProperty("--active-accent", accent);
        $("primaryLabel").textContent = row
          ? `${row.display_name}-attributed commits`
          : "Unique AI-attributed commits";
        $("primaryValue").textContent = number.format(commitCount);
        $("primaryDetail").textContent =
          `${percent.format(share)}% of ${number.format(denominator)} commits scanned` +
          (row ? " · may overlap other providers" : " · each commit counted once");
        $("shareFill").style.width = `${Math.min(100, share)}%`;
        $("presenceValue").textContent = number.format(presenceCount);
        $("presenceLabel").textContent = row
          ? `${row.display_name} actor presences`
          : "AI actor presences";
        $("daysValue").textContent = number.format(dayCount);
        $("unknownValue").textContent = number.format(data.totals.unknown_commits);
      }

      function renderCalendar() {
        const series = fillDailySeries();
        const calendar = $("activityCalendar");
        const scroller = document.querySelector(".calendar-scroll");
        const previousMaxScroll = Math.max(
          0,
          scroller.scrollWidth - scroller.clientWidth
        );
        const previousScrollLeft = scroller.scrollLeft;
        const followNewest =
          previousMaxScroll <= 1 || previousMaxScroll - previousScrollLeft <= 2;
        calendar.replaceChildren();
        if (!series.length) {
          calendarFocusIndex = null;
          const empty = document.createElement("div");
          empty.className = "calendar-empty";
          empty.textContent = "No publishable daily activity in this profile.";
          calendar.className = "calendar-empty";
          calendar.append(empty);
          $("activityMeta").textContent = "No daily series";
          $("activitySummary").textContent = "No publishable daily activity.";
          return;
        }
        calendar.className = "calendar";
        const accent = selectedAccent();
        const binOpacity = [0.42, 0.62, 0.81, 1];
        const rovingIndex = calendarFocusIndex === null
          ? series.length - 1
          : Math.max(0, Math.min(series.length - 1, calendarFocusIndex));
        if (calendarFocusIndex !== null) calendarFocusIndex = rovingIndex;
        const firstWeekday = dateAtUtc(series[0].date).getUTCDay();
        for (let index = 0; index < firstWeekday; index += 1) {
          const spacer = document.createElement("span");
          spacer.className = "day-spacer";
          spacer.setAttribute("aria-hidden", "true");
          calendar.append(spacer);
        }

        for (const [index, day] of series.entries()) {
          const selectedCount = selectedDayCount(day);
          const level = selectedCount === 0
            ? 0
            : selectedCount === 1
              ? 1
              : selectedCount <= 4
                ? 2
                : selectedCount <= 7
                  ? 3
                  : 4;
          const share = day.total_commits
            ? (selectedCount / day.total_commits) * 100
            : 0;
          const cell = document.createElement("button");
          cell.type = "button";
          cell.className = "day-cell";
          cell.tabIndex = index === rovingIndex ? 0 : -1;
          cell.dataset.index = String(index);
          cell.dataset.active = String(selectedCount > 0);
          cell.dataset.level = String(level);
          if (selectedCount) {
            cell.style.background = rgba(accent, binOpacity[level - 1]);
          }
          const label = `${day.date}: ${day.total_commits} total commits; ` +
            `${selectedCount} ${selectedName()} attributed commits; ` +
            `${percent.format(share)}% share`;
          cell.setAttribute("aria-label", label);
          cell.addEventListener("mouseenter", (event) => {
            if (!tooltipHoverPaused && tooltipSuppressed !== cell) {
              showTooltip(cell, day, selectedCount, event);
            }
          });
          cell.addEventListener("mousemove", (event) => {
            if (tooltipHoverPaused && (event.movementX || event.movementY)) {
              tooltipHoverPaused = false;
              tooltipSuppressed = null;
              showTooltip(cell, day, selectedCount, event);
              return;
            }
            if (tooltipOwner === cell && !tooltipPinned) moveTooltip(event);
          });
          cell.addEventListener("mouseleave", () => {
            if (tooltipSuppressed === cell) tooltipSuppressed = null;
            if (!tooltipPinned && document.activeElement !== cell) hideTooltip();
          });
          cell.addEventListener("focus", () => {
            calendarFocusIndex = index;
            tooltipHoverPaused = false;
            tooltipSuppressed = null;
            showTooltip(cell, day, selectedCount);
          });
          cell.addEventListener("blur", hideTooltip);
          cell.addEventListener("click", () => {
            if (tooltipOwner === cell && tooltipPinned) {
              tooltipHoverPaused = true;
              tooltipSuppressed = cell;
              hideTooltip();
            } else {
              tooltipHoverPaused = false;
              tooltipSuppressed = null;
              showTooltip(cell, day, selectedCount);
              tooltipPinned = true;
            }
          });
          cell.addEventListener("keydown", handleCalendarKeydown);
          calendar.append(cell);
        }

        $("activityMeta").textContent =
          `${series[0].date} → ${series[series.length - 1].date} · ` +
          "publishable activity only";
        $("activitySummary").textContent =
          `Daily ${selectedName()} attributed-commit counts from ` +
          `${series[0].date} through ${series[series.length - 1].date}; ` +
          "each cell uses the validated published daily aggregate.";
        const levels = document.querySelectorAll(".legend-cell[data-level]");
        levels.forEach((cell, index) => {
          cell.style.background = rgba(accent, binOpacity[index]);
        });
        requestAnimationFrame(() => {
          const nextMaxScroll = Math.max(
            0,
            scroller.scrollWidth - scroller.clientWidth
          );
          scroller.scrollLeft = followNewest
            ? nextMaxScroll
            : Math.min(previousScrollLeft, nextMaxScroll);
        });
      }

      function calendarCells() {
        return [...document.querySelectorAll(".day-cell")];
      }

      function focusCalendarCell(index) {
        const cells = calendarCells();
        const bounded = Math.max(0, Math.min(cells.length - 1, index));
        calendarFocusIndex = bounded;
        cells.forEach((cell, cellIndex) => {
          cell.tabIndex = cellIndex === bounded ? 0 : -1;
        });
        cells[bounded]?.focus();
      }

      function handleCalendarKeydown(event) {
        const index = Number(event.currentTarget.dataset.index);
        const offsets = {
          ArrowDown: 1,
          ArrowUp: -1,
          ArrowRight: 7,
          ArrowLeft: -7
        };
        if (event.key === "Escape") {
          tooltipHoverPaused = true;
          tooltipSuppressed = event.currentTarget;
          hideTooltip();
          return;
        }
        if (event.key === "Home" || event.key === "End" || offsets[event.key]) {
          event.preventDefault();
          const cells = calendarCells();
          const target = event.key === "Home"
            ? 0
            : event.key === "End"
              ? cells.length - 1
              : index + offsets[event.key];
          focusCalendarCell(target);
        }
      }

      function showTooltip(cell, day, selectedCount, event = null) {
        const tooltip = $("tooltip");
        const share = day.total_commits ? (selectedCount / day.total_commits) * 100 : 0;
        if (tooltipOwner !== cell) tooltipPinned = false;
        if (tooltipOwner && tooltipOwner !== cell) {
          tooltipOwner.removeAttribute("aria-describedby");
        }
        tooltipOwner = cell;
        cell.setAttribute("aria-describedby", "tooltip");
        tooltip.replaceChildren();
        const date = document.createElement("span");
        date.className = "tooltip-date";
        date.textContent = day.date;
        const detail = document.createElement("span");
        detail.textContent = `${selectedCount} ${selectedName()} · ` +
          `${day.total_commits} total · ${percent.format(share)}% share`;
        tooltip.append(date, detail);
        tooltip.hidden = false;
        if (event) {
          moveTooltip(event);
        } else {
          const bounds = cell.getBoundingClientRect();
          moveTooltip({
            clientX: bounds.left + bounds.width / 2,
            clientY: bounds.top
          });
        }
      }

      function moveTooltip(event) {
        const tooltip = $("tooltip");
        const margin = 16;
        const halfWidth = tooltip.getBoundingClientRect().width / 2;
        const minX = halfWidth + margin;
        const maxX = innerWidth - halfWidth - margin;
        tooltip.style.left = `${Math.max(minX, Math.min(maxX, event.clientX))}px`;
        tooltip.style.top = `${Math.max(90, event.clientY)}px`;
      }

      function hideTooltip() {
        $("tooltip").hidden = true;
        tooltipOwner?.removeAttribute("aria-describedby");
        tooltipOwner = null;
        tooltipPinned = false;
      }

      function renderProviders() {
        const max = Math.max(...data.providers.map((row) => row.attributed_commits), 1);
        $("providerList").replaceChildren(...data.providers.map((row) => {
          const accent = colorFor(row.provider);
          const button = document.createElement("button");
          button.type = "button";
          button.className = "provider-row";
          button.dataset.provider = row.provider;
          button.setAttribute("aria-current", String(selected === row.provider));
          button.setAttribute("aria-label", `Filter dashboard to ${row.display_name}`);
          button.style.setProperty("--provider-accent", accent);

          const head = document.createElement("span");
          head.className = "provider-row-head";
          const name = document.createElement("span");
          name.className = "provider-name";
          name.append(
            providerIcon(row.provider, row.display_name, "row"),
            document.createTextNode(row.display_name)
          );
          const count = document.createElement("span");
          count.className = "provider-count";
          count.textContent = number.format(row.attributed_commits);
          head.append(name, count);

          const track = document.createElement("span");
          track.className = "provider-track";
          const fill = document.createElement("span");
          fill.className = "provider-fill";
          fill.style.width = `${(row.attributed_commits / max) * 100}%`;
          track.append(fill);

          const detail = document.createElement("span");
          detail.className = "provider-detail";
          detail.textContent = `${number.format(row.actor_presences)} presences · ` +
            `${number.format(row.active_days)} active days`;
          button.append(head, track, detail);
          button.addEventListener("click", () => {
            selected = row.provider;
            render();
          });
          return button;
        }));
        if (!data.providers.length) {
          const empty = document.createElement("p");
          empty.className = "panel-meta";
          empty.textContent = "No AI provider recorded yet.";
          $("providerList").append(empty);
        }
      }

      function renderEvidence() {
        const entries = ["verified", "declared", "imported", "inferred", "unknown"]
          .map((key) => ({ key, value: data.evidence_records[key] }))
          .filter((entry) => entry.value > 0 || entry.key === "unknown");
        const total = data.evidence_records.total_records;
        $("evidenceTotal").textContent = `${number.format(total)} records`;
        $("evidenceTrack").replaceChildren(...entries.map((entry) => {
          const segment = document.createElement("span");
          segment.className = "evidence-segment";
          segment.style.width = `${total ? (entry.value / total) * 100 : 0}%`;
          segment.style.background = evidenceColors[entry.key];
          return segment;
        }));
        $("evidenceGrid").replaceChildren(...entries.map((entry) => {
          const item = document.createElement("div");
          item.className = "evidence-item";
          const swatch = document.createElement("span");
          swatch.className = "evidence-swatch";
          swatch.style.setProperty("--evidence-color", evidenceColors[entry.key]);
          swatch.setAttribute("aria-hidden", "true");
          const label = document.createElement("span");
          label.textContent = entry.key;
          const count = document.createElement("span");
          count.className = "evidence-count";
          count.textContent = number.format(entry.value);
          item.append(swatch, label, count);
          return item;
        }));
      }

      function renderPrivacy() {
        const privacy = data.privacy;
        if (
          privacy.anonymous_aggregate_commits > 0 &&
          privacy.explicitly_publishable_commits > 0
        ) {
          $("privacyCopy").textContent =
            "Headline aggregates combine publishable and aggregate-only activity; " +
            "the daily calendar uses publishable activity only. Repository identities " +
            "remain withheld.";
        } else if (privacy.anonymous_aggregate_commits > 0) {
          $("privacyCopy").textContent =
            "Headline aggregates contain aggregate-only activity. The daily calendar " +
            "is empty because no repository dates were selected for publication. " +
            "Repository identities remain withheld.";
        } else {
          $("privacyCopy").textContent =
            "This page contains only activity explicitly selected for publication. " +
            "Repository identities are not present in the dashboard data.";
        }
      }

      function render() {
        renderMetrics();
        renderCalendar();
        document.querySelectorAll(".filter").forEach((button) => {
          button.setAttribute("aria-pressed", String(button.dataset.provider === selected));
          if (button.dataset.provider === "all") {
            button.style.setProperty("--provider-accent", selectedAccent());
          }
        });
        document.querySelectorAll(".provider-row").forEach((button) => {
          button.setAttribute("aria-current", String(button.dataset.provider === selected));
        });
        $("selectionStatus").textContent = `Showing ${selectedName()} collaboration activity.`;
      }

      // CSS updates the surface tokens immediately when the OS preference
      // changes. The legacy branch keeps this working in older WebKit without
      // adding a dependency or a network path.
      const systemScheme = window.matchMedia
        ? window.matchMedia("(prefers-color-scheme: dark)") : null;
      const handleSystemSchemeChange = () => {
        if (theme === "auto") render();
      };
      if (systemScheme) {
        if (systemScheme.addEventListener) {
          systemScheme.addEventListener("change", handleSystemSchemeChange);
        } else if (systemScheme.addListener) {
          systemScheme.addListener(handleSystemSchemeChange);
        }
      }

      function setTheme(next) {
        theme = next;
        document.documentElement.dataset.theme = next;
        const nextTheme = next === "auto" ? "light" : next === "light" ? "dark" : "auto";
        $("themeToggle").textContent = `Theme: ${next}`;
        $("themeToggle").setAttribute(
          "aria-label",
          `Theme: ${next}. Activate for ${nextTheme} theme`
        );
      }

      $("themeToggle").addEventListener("click", () => {
        setTheme(theme === "auto" ? "light" : theme === "light" ? "dark" : "auto");
        render();
      });

      $("snapshotDate").textContent = data.generated_on;
      $("snapshotDate").setAttribute("datetime", data.generated_on);
      $("periodLabel").textContent = data.period.label;
      $("schemaLabel").textContent = `schema ${data.schema_version}`;
      $("footSnapshot").textContent =
        `Snapshot ${data.generated_on} UTC · ${data.period.label} · aiprofile`;
      renderEvidence();
      renderPrivacy();
      setTheme("auto");
      renderFilters();
      renderProviders();
      render();
    })();
  </script>
</body>
</html>
"""


def render_dashboard(stats: VizStats) -> str:
    """Return a deterministic, self-contained dashboard HTML document."""
    if type(stats) is not VizStats:
        raise TypeError("dashboard renderer requires an exact VizStats instance")
    payload = json.dumps(
        to_json_dict(stats),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    # Script-data escaping is defense in depth. VizStats already restricts
    # strings to a closed public vocabulary, but these replacements ensure
    # future additive fields cannot terminate the application/json element.
    payload = (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    return _HTML_PREFIX + payload + _HTML_SUFFIX.replace(
        "__PROVIDER_GLYPHS__", _PROVIDER_GLYPHS_JSON
    )
