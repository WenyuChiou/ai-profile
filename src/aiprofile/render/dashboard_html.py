"""Self-contained interactive dashboard renderer — v0.9.0 Voxel Collaboration World
(ADR-033 contract; presentation supersedes ADR-031 and ADR-032).

The dashboard is a pure function of the validated, privacy-safe ``VizStats``
contract. It never reads Git, SQLite, configuration, the clock, or the
network. All CSS, JavaScript, and aggregate data are embedded in one HTML
document so users may open it locally or publish it as a static page.

Presentation grammar (ADR-033 approved revision):
1. Status/snapshot line carrying snapshot date and period; schema is in definitions.
2. Four-cell core metric strip (unique AI commits, presences, active days, unattributed).
3. Provider toolbar and date range controls (presets 28d/84d/365d/All/Custom, zoom, anim toggle).
4. Voxel Collaboration World: continuous chronological terraces (responsive 28/14/7 days per row),
   shared zero-based linear scale ceiling from peak daily total in active range.
   Scaffolding on outer platform with animated original miner and friendly small zombie.
5. Selected-date detail panel (date, total, AI, Other, precise %, daily provider breakdown).
6. Mining Workstations: integrated provider workbench & mineral troughs (common denominator:
   total AI commits, explicit count + %, persistent overlap notice).
7. Archive Rock Stratum: 3D geological evidence layers, quantitative lengths, neutral unknown.
8. Collapsible sortable daily activity table synchronized with active date range.
9. Definitions, attribution & privacy boundary; footer snapshot.
"""

from __future__ import annotations

import json

from ..viz import VizStats, to_json_dict
from .brand import BRAND
from .voxel_art import actor_body

_ACTOR_BODIES_JSON = json.dumps(
    {kind: actor_body(kind) for kind in ("miner", "zombie")},
    ensure_ascii=True, separators=(",", ":"), sort_keys=True,
).replace("<", "\\u003c").replace(">", "\\u003e")

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
      --voxel-grass-top: #5b8c32;
      --voxel-grass-fringe: #6fa83e;
      --voxel-dirt-front: #866043;
      --voxel-dirt-side: #5a402d;
      --voxel-ai-front: #0ea5e9;
      --voxel-ai-top: #7dd3fc;
      --voxel-ai-side: #0284c7;
      --voxel-other-front: #94a3b8;
      --voxel-other-top: #cbd5e1;
      --voxel-other-side: #64748b;
      --voxel-slot-border: #c2d3e5;
      --voxel-slot-bg: #e2e8f0;
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
      --radius-sm: 0;
      --radius-md: 0;
      --voxel-bevel-light: #ffffff;
      --voxel-bevel-dark: #c2d3e5;
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
        --voxel-grass-top: #3a6920;
        --voxel-grass-fringe: #4d822d;
        --voxel-dirt-front: #4d3726;
        --voxel-dirt-side: #332419;
        --voxel-ai-front: #38bdf8;
        --voxel-ai-top: #bae6fd;
        --voxel-ai-side: #0284c7;
        --voxel-other-front: #64748b;
        --voxel-other-top: #94a3b8;
        --voxel-other-side: #475569;
        --voxel-slot-border: #34526f;
        --voxel-slot-bg: #1e293b;
        --voxel-bevel-light: #22374e;
        --voxel-bevel-dark: #070d18;
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
      --voxel-grass-top: #3a6920;
      --voxel-grass-fringe: #4d822d;
      --voxel-dirt-front: #4d3726;
      --voxel-dirt-side: #332419;
      --voxel-ai-front: #38bdf8;
      --voxel-ai-top: #bae6fd;
      --voxel-ai-side: #0284c7;
      --voxel-other-front: #64748b;
      --voxel-other-top: #94a3b8;
      --voxel-other-side: #475569;
      --voxel-slot-border: #34526f;
      --voxel-slot-bg: #1e293b;
      --voxel-bevel-light: #22374e;
      --voxel-bevel-dark: #070d18;
    }

    * {
      box-sizing: border-box;
    }

    html {
      min-width: 0;
      font-family: var(--body);
      font-size: 16px;
      line-height: 1.5;
      background: var(--canvas);
      color: var(--text);
      -webkit-text-size-adjust: 100%;
    }

    body {
      margin: 0;
      padding: 0;
      background: var(--canvas);
      color: var(--text);
      font-variant-numeric: lining-nums tabular-nums;
    }

    .console {
      width: min(100% - 2rem, 76rem);
      margin: 0 auto;
      padding: var(--space-4) 0 var(--space-8);
    }

    .statusbar {
      display: grid;
      grid-template-columns: auto 1fr auto;
      grid-template-areas: "title meta controls";
      gap: var(--space-4);
      align-items: baseline;
      padding-bottom: var(--space-3);
      border-bottom: 2px solid var(--border-strong);
    }

    .statusbar-title {
      grid-area: title;
      margin: 0;
      font-family: var(--display);
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.01em;
      white-space: nowrap;
    }

    .statusbar-meta {
      grid-area: meta;
      margin: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2) var(--space-4);
      color: var(--muted);
      font-size: var(--text-1);
    }

    .status-item {
      display: inline-flex;
      gap: var(--space-1);
    }

    .status-value {
      font-family: var(--mono);
      font-weight: 600;
      color: var(--text);
    }

    .statusbar-controls {
      grid-area: controls;
      display: flex;
      gap: var(--space-2);
      align-items: center;
      justify-content: flex-end;
    }

    .theme-toggle {
      min-height: 2rem;
      padding: 0 var(--space-3);
      border: 1px solid var(--border-strong);
      border-radius: 0;
      background: var(--surface);
      color: var(--text);
      cursor: pointer;
      font-family: var(--body);
      font-size: var(--text-1);
      font-weight: 600;
      box-shadow:
        inset 1px 1px 0 var(--voxel-bevel-light),
        inset -1px -1px 0 var(--voxel-bevel-dark);
    }

    .theme-toggle:hover {
      border-color: var(--accent);
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-top: var(--space-4);
      border: 1px solid var(--border-strong);
      border-radius: 0;
      background: var(--surface);
      box-shadow:
        inset 1px 1px 0 var(--voxel-bevel-light),
        inset -1px -1px 0 var(--voxel-bevel-dark);
    }

    .metric {
      padding: var(--space-4);
      border-inline-start: 1px solid var(--border);
    }

    .metric:first-child {
      border-inline-start: 0;
    }

    .metric--primary {
      background: var(--surface-subtle);
    }

    .metric-value {
      margin: 0;
      font-family: var(--mono);
      font-size: var(--text-5);
      font-weight: 700;
      line-height: 1.1;
      letter-spacing: -0.02em;
      color: var(--text);
    }

    .metric--primary .metric-value {
      color: var(--active-accent, var(--accent));
    }

    .metric-label {
      margin: var(--space-1) 0 0;
      font-size: var(--text-2);
      font-weight: 600;
      color: var(--text);
    }

    .metric-detail {
      margin: var(--space-1) 0 0;
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.4;
    }

    .share-track {
      height: 0.375rem;
      margin-top: var(--space-2);
      overflow: hidden;
      background: var(--grid-empty);
      border: 1px solid var(--voxel-slot-border);
    }

    .share-fill {
      height: 100%;
      background: var(--active-accent, var(--accent));
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2) var(--space-4);
      align-items: center;
      margin-top: var(--space-4);
      padding: var(--space-2) 0;
      border: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
    }

    .toolbar-label {
      color: var(--muted);
      font-size: var(--text-1);
      font-weight: 600;
    }

    .filters {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(4.5rem, 1fr));
      width: 100%;
      gap: var(--space-2);
      align-items: center;
    }

    .filter {
      display: inline-flex;
      flex-direction: column;
      gap: var(--space-1);
      align-items: center;
      justify-content: center;
      min-height: 4.5rem;
      padding: var(--space-2);
      border: 1px solid var(--border);
      border-radius: 0;
      background: var(--surface);
      color: var(--text);
      cursor: pointer;
      font-size: var(--text-1);
      font-weight: 600;
      box-shadow:
        inset 1px 1px 0 var(--voxel-bevel-light),
        inset -1px -1px 0 var(--voxel-bevel-dark);
      transition: transform 120ms ease;
    }

    .filter:hover {
      border-color: var(--provider-accent, var(--accent));
      background: color-mix(in srgb, var(--provider-accent, var(--accent)) 8%, var(--surface));
    }

    .filter[aria-pressed="true"] {
      border-color: var(--provider-accent, var(--accent));
      background: color-mix(in srgb, var(--provider-accent, var(--accent)) 15%, var(--surface));
      color: var(--provider-accent, var(--accent));
      box-shadow: inset 0 0 0 1px var(--provider-accent, var(--accent));
    }

    .provider-icon {
      width: 1rem;
      height: 1rem;
      flex-shrink: 0;
    }

    .provider-icon--filter {
      width: 2rem;
      height: 2rem;
      color: var(--provider-accent, currentColor);
    }

    .provider-icon--row {
      width: 2.5rem;
      height: 2.5rem;
      color: var(--provider-accent, currentColor);
      background: var(--surface);
      padding: var(--space-1);
    }

    .console-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 22rem;
      gap: var(--space-4);
      margin-top: var(--space-4);
      align-items: start;
    }

    .panel {
      padding: var(--space-4);
      border: 1px solid var(--border);
      border-radius: 0;
      background: var(--surface);
      box-shadow:
        inset 1px 1px 0 var(--voxel-bevel-light),
        inset -1px -1px 0 var(--voxel-bevel-dark);
    }

    .panel-heading {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2) var(--space-4);
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: var(--space-3);
    }

    .panel-title {
      margin: 0;
      font-family: var(--display);
      font-size: var(--text-3);
      font-weight: 700;
      letter-spacing: -0.01em;
    }

    .panel-meta {
      margin: 0;
      color: var(--muted);
      font-size: var(--text-1);
    }

    .voxel-controls {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--space-3);
    }

    .date-controls {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
      align-items: center;
    }

    .preset-group {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-1);
    }

    .range-btn {
      min-height: 2rem;
      padding: 0 var(--space-3);
      border: 1px solid var(--border-strong);
      border-radius: 0;
      background: var(--surface-subtle);
      color: var(--text);
      cursor: pointer;
      font-size: var(--text-1);
      font-weight: 600;
      box-shadow:
        inset 1px 1px 0 var(--voxel-bevel-light),
        inset -1px -1px 0 var(--voxel-bevel-dark);
      transition: transform 120ms ease;
    }

    .range-btn:hover {
      border-color: var(--accent);
      background: var(--surface-raised);
    }

    .range-btn[aria-pressed="true"] {
      border-color: var(--accent);
      background: color-mix(in srgb, var(--accent) 15%, var(--surface));
      color: var(--accent);
      box-shadow: inset 0 0 0 1px var(--accent);
    }

    .custom-range-form {
      display: inline-flex;
      flex-wrap: wrap;
      gap: var(--space-1) var(--space-2);
      align-items: center;
      font-size: var(--text-1);
      color: var(--muted);
      max-width: 100%;
    }

    .date-input {
      min-height: 2rem;
      padding: 0 var(--space-2);
      border: 1px solid var(--border);
      border-radius: 0;
      background: var(--surface);
      color: var(--text);
      font-family: var(--mono);
      font-size: var(--text-1);
      box-shadow: inset 1px 1px 0 var(--voxel-bevel-dark);
      max-width: 100%;
      min-width: 0;
    }

    .voxel-action-controls {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
      align-items: center;
    }

    .date-range-error {
      color: #dc2626;
      font-size: var(--text-1);
      font-weight: 600;
      margin-inline-start: var(--space-2);
    }

    .anim-toggle-btn {
      min-height: 2rem;
      padding: 0 var(--space-3);
      border: 1px solid var(--border-strong);
      border-radius: 0;
      background: var(--surface-subtle);
      color: var(--text);
      cursor: pointer;
      font-size: var(--text-1);
      font-weight: 600;
      box-shadow:
        inset 1px 1px 0 var(--voxel-bevel-light),
        inset -1px -1px 0 var(--voxel-bevel-dark);
    }

    .anim-toggle-btn:hover {
      border-color: var(--accent);
      background: var(--surface-raised);
    }

    .calendar-scroll {
      width: 100%;
      min-width: 0;
      max-width: 100%;
      overflow-x: auto;
      padding: var(--space-1) 0 var(--space-3);
      scrollbar-color: var(--border-strong) transparent;
    }

    .calendar {
      display: flex;
      flex-direction: column;
      gap: var(--space-3);
      width: 100%;
    }

    .voxel-terraces {
      display: flex;
      flex-direction: column;
      gap: var(--space-3);
      width: 100%;
    }

    .voxel-terrace-row {
      display: flex;
      flex-direction: column;
      padding: var(--space-1) 0;
      border: none;
      background: transparent;
      box-shadow: none;
    }

    .voxel-terrace-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 4px 12px;
      margin-bottom: 2px;
      font-family: var(--mono);
      font-size: var(--text-1);
      color: var(--muted);
      font-weight: 600;
    }

    .voxel-terrace-svg {
      display: block;
      width: 100%;
      height: auto;
      overflow: visible;
    }

    g.day-cell {
      cursor: pointer;
      outline: none;
    }

    :focus-visible {
      outline: 0.1875rem solid var(--focus);
      outline-offset: 3px;
    }

    g.day-cell .day-label {
      font-family: var(--mono);
      font-size: 14px;
      font-weight: 600;
      fill: var(--muted);
      user-select: none;
    }

    g.day-cell[data-selected-day="true"] .day-ground-marker {
      fill: var(--focus);
    }

    g.day-cell[data-selected-day="true"] .day-label {
      fill: var(--text);
      font-weight: 700;
    }

    g.day-cell[data-highlighted="true"] .day-ground-marker {
      fill: var(--provider-accent, var(--accent));
    }

    g.day-cell:hover .day-label {
      fill: var(--text);
    }

    g.day-cell:hover .day-ground-marker {
      fill: var(--text);
    }

    g.day-cell:focus-visible .day-hit {
      stroke: var(--focus);
      stroke-width: 1.5;
      stroke-dasharray: 3 2;
    }

    g.day-cell:focus-visible .day-ground-marker {
      fill: var(--focus);
    }

    .calendar-empty {
      display: grid;
      min-height: 8rem;
      place-items: center;
      border: 1px dashed var(--border);
      border-radius: 0;
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

    .legend-swatches {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
      align-items: center;
    }

    .legend-item {
      display: inline-flex;
      gap: var(--space-1);
      align-items: center;
    }

    .legend-swatch {
      width: 0.65rem;
      height: 0.65rem;
      border-radius: 0.12rem;
    }

    .legend-swatch--ai {
      background: var(--voxel-ai-front);
    }

    .legend-swatch--other {
      background: var(--voxel-other-front);
    }

    .legend-swatch--base {
      background: var(--voxel-grass-top);
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

    .detail-panel {
      margin-top: var(--space-4);
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
      gap: var(--space-3);
      margin-bottom: var(--space-4);
    }

    .detail-card {
      display: flex;
      flex-direction: column;
      padding: var(--space-3);
      border: 1px solid var(--border);
      border-radius: 0;
      background: var(--surface-subtle);
      box-shadow:
        inset 1px 1px 0 var(--voxel-bevel-light),
        inset -1px -1px 0 var(--voxel-bevel-dark);
    }

    .detail-card--ai {
      border-color: color-mix(in srgb, var(--voxel-ai-front) 40%, var(--border));
      background: color-mix(in srgb, var(--voxel-ai-front) 8%, var(--surface));
    }

    .detail-card--other {
      border-color: color-mix(in srgb, var(--voxel-other-front) 40%, var(--border));
      background: color-mix(in srgb, var(--voxel-other-front) 8%, var(--surface));
    }

    .detail-label {
      color: var(--muted);
      font-size: var(--text-1);
      font-weight: 600;
    }

    .detail-val {
      margin-top: var(--space-1);
      font-size: var(--text-3);
      font-weight: 700;
      color: var(--text);
    }

    .detail-sub {
      margin-top: var(--space-1);
      font-size: var(--text-1);
      color: var(--muted);
    }

    .detail-providers {
      border-top: 1px solid var(--border);
      padding-top: var(--space-3);
    }

    .detail-subtitle {
      margin: 0 0 var(--space-2);
      font-size: var(--text-1);
      font-weight: 600;
      color: var(--muted);
      letter-spacing: 0.04em;
    }

    .detail-provider-list {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
    }

    .detail-chip {
      display: inline-flex;
      gap: var(--space-2);
      align-items: center;
      padding: 0.25rem 0.5rem;
      border: 1px solid var(--border);
      border-radius: 0;
      background: var(--surface);
      font-size: var(--text-1);
    }

    .table-panel {
      margin-top: var(--space-4);
    }

    .table-scroll {
      width: 100%;
      overflow-x: auto;
      max-height: 22rem;
      scrollbar-color: var(--border-strong) transparent;
    }

    .daily-table {
      width: 100%;
      border-collapse: collapse;
      font-size: var(--text-1);
      text-align: left;
    }

    .daily-table th,
    .daily-table td {
      padding: var(--space-2) var(--space-3);
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }

    .daily-table th {
      position: sticky;
      top: 0;
      background: var(--surface);
      color: var(--muted);
      font-weight: 600;
      z-index: 1;
    }

    .sort-btn {
      background: none;
      border: none;
      padding: 0;
      font: inherit;
      color: var(--muted);
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
    }

    .sort-btn:hover {
      color: var(--text);
    }

    .sort-icon {
      font-size: var(--text-1);
    }

    .daily-row {
      cursor: pointer;
    }

    .daily-row:hover {
      background: var(--surface-subtle);
    }

    .date-select {
      border: 0;
      background: transparent;
      color: inherit;
      font: inherit;
      min-height: 2.75rem;
      cursor: pointer;
    }

    .daily-row[data-selected="true"] {
      background: color-mix(in srgb, var(--accent) 12%, var(--surface));
      font-weight: 600;
    }

    .workstations-panel .panel-heading {
      margin-bottom: var(--space-3);
    }

    .provider-list {
      display: grid;
      gap: var(--space-2);
      padding: var(--space-2);
      position: relative;
    }

    .provider-row {
      display: grid;
      gap: var(--space-1);
      width: 100%;
      padding: var(--space-2);
      border: none;
      border-bottom: 1px solid var(--border);
      border-radius: 0;
      background: transparent;
      color: inherit;
      cursor: pointer;
      text-align: left;
      box-shadow: none;
      transition: transform 120ms ease;
      position: relative;
    }

    .provider-row::before {
      content: "";
      position: absolute;
      left: calc(-1 * var(--space-2) - 3px);
      top: 0;
      bottom: 0;
      width: 4px;
      background: #78350f;
    }

    .provider-row::after {
      content: "";
      position: absolute;
      left: calc(-1 * var(--space-2) - 5px);
      bottom: 0;
      width: 8px;
      height: 4px;
      background: var(--voxel-stone-front, #6e7681);
    }

    .provider-row:last-child {
      border-bottom: none;
    }

    .provider-row[aria-current="true"] {
      border-color: var(--provider-accent);
      background: color-mix(in srgb, var(--provider-accent) 10%, var(--surface));
      outline: 2px solid var(--provider-accent);
      outline-offset: -2px;
    }

    .provider-row:hover {
      background: color-mix(in srgb, var(--provider-accent) 8%, var(--surface));
    }

    .provider-row-head {
      display: flex;
      gap: var(--space-3);
      align-items: center;
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

    .workbench-tool {
      display: inline-block;
      width: 0.75rem;
      height: 0.75rem;
      margin-left: 2px;
      opacity: 0.75;
      vertical-align: -0.1em;
    }

    .provider-count {
      font-family: var(--mono);
      font-size: var(--text-2);
      font-weight: 600;
    }

    .provider-track {
      display: block;
      width: 100%;
      height: 0.75rem;
      overflow: hidden;
      border: 1px solid var(--voxel-slot-border);
      border-radius: 0;
      background: var(--voxel-slot-bg);
      box-shadow: inset 1px 1px 0 var(--voxel-bevel-dark), 0 1px 0 var(--voxel-bevel-light);
      position: relative;
    }

    .provider-fill {
      display: block;
      height: 100%;
      background: var(--provider-accent, var(--accent));
      box-shadow: inset 0 2px 0 rgba(255, 255, 255, 0.35), inset 0 -1px 0 rgba(0, 0, 0, 0.25);
    }

    .provider-detail {
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.4;
    }

    .custom-range > summary,
    .ledger-disclosure > summary {
      cursor: pointer;
      color: var(--text);
      font-weight: 600;
      padding: var(--space-2) 0;
    }

    .custom-range[open] {
      flex-basis: 100%;
    }

    .ledger-disclosure {
      min-width: 0;
    }

    .day-composition {
      display: flex;
      height: 1.5rem;
      background: var(--grid-empty);
      margin-bottom: var(--space-3);
    }

    .day-composition span {
      display: block;
      height: 100%;
    }

    .day-composition-ai { background: var(--voxel-ai-front); }
    .day-composition-other { background: var(--voxel-other-front); }

    .provider-facts {
      padding-left: var(--space-4);
      color: var(--muted);
    }

    .workstations-overlap-note {
      margin: var(--space-3) 0 0;
      padding-top: var(--space-2);
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: var(--text-1);
      line-height: 1.45;
    }

    .rock-stratum-container {
      margin-bottom: var(--space-3);
    }

    .rock-stratum-svg {
      display: block;
      width: 100%;
      height: 32px;
      overflow: visible;
    }

    .evidence-panel .panel-title::before {
      content: "";
      display: inline-block;
      width: 0.625rem;
      height: 0.625rem;
      margin-right: var(--space-2);
      border: 1px solid #d97706;
      border-radius: 0.125rem;
      background: #f59e0b;
      box-shadow: inset 1px 1px 0 #fef08a, 0 0 0 1px #78350f;
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
      border-radius: 0;
      background: var(--surface);
      box-shadow:
        inset 1px 1px 0 var(--voxel-bevel-light),
        inset -1px -1px 0 var(--voxel-bevel-dark);
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
      border-radius: 0;
      background: var(--surface-raised);
      color: var(--text);
      font-size: var(--text-1);
      line-height: 1.5;
      pointer-events: none;
      transform: translate(-50%, calc(-100% - 0.75rem));
      box-shadow: 2px 2px 0 var(--voxel-bevel-dark);
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

    .mono {
      font-family: var(--mono);
    }

    @keyframes minerMine18s {
      0% { transform: translate(0px, 0px); }
      12% { transform: translate(6px, 0px); }
      22% { transform: translate(12px, -6px); }
      32% { transform: translate(18px, -6px); }
      40% { transform: translate(18px, -6px); }
      60% { transform: translate(18px, -6px); }
      70% { transform: translate(12px, -6px); }
      80% { transform: translate(6px, 0px); }
      90% { transform: translate(0px, 0px); }
      100% { transform: translate(0px, 0px); }
    }

    @keyframes pickaxeSwing18s {
      0%, 36% { transform: rotate(0deg); transform-origin: 23px 23px; }
      40% { transform: rotate(-30deg); transform-origin: 23px 23px; }
      44% { transform: rotate(38deg); transform-origin: 23px 23px; }
      48% { transform: rotate(-25deg); transform-origin: 23px 23px; }
      52% { transform: rotate(38deg); transform-origin: 23px 23px; }
      56% { transform: rotate(-25deg); transform-origin: 23px 23px; }
      60% { transform: rotate(38deg); transform-origin: 23px 23px; }
      64%, 100% { transform: rotate(0deg); transform-origin: 23px 23px; }
    }

    @keyframes zombiePatrol18s {
      0%, 100% { transform: translate(0px, 0px); }
      15% { transform: translate(-8px, 0px); }
      35% { transform: translate(-8px, 20px); }
      55% { transform: translate(-8px, 20px); }
      75% { transform: translate(-8px, 0px); }
      90% { transform: translate(0px, 0px); }
    }

    @keyframes actorLegWalk {
      0%, 100% { transform: translateY(0px); }
      25%, 75% { transform: translateY(-2px); }
      50% { transform: translateY(1px); }
    }

    .miner-actor {
      animation: minerMine18s 18s ease-in-out infinite;
    }

    .pickaxe-arm {
      animation: pickaxeSwing18s 18s ease-in-out infinite;
    }

    .zombie-actor {
      animation: zombiePatrol18s 18s ease-in-out infinite;
    }

    .miner-leg-l,
    .zombie-leg-l {
      animation: actorLegWalk 0.8s ease-in-out infinite;
    }

    .actors-paused .miner-actor,
    .actors-paused .pickaxe-arm,
    .actors-paused .zombie-actor,
    .actors-paused .miner-leg-l,
    .actors-paused .zombie-leg-l {
      animation-play-state: paused !important;
    }

    @media (max-width: 54rem) {
      .console-grid {
        grid-template-columns: minmax(0, 1fr);
      }

      .activity-panel {
        grid-column: 1;
        grid-row: 1;
      }

      #selectedDatePanel {
        grid-column: 1;
        grid-row: 2;
      }

      .sidebar {
        grid-column: 1;
        grid-row: 3;
      }

      .table-panel {
        grid-column: 1;
        grid-row: 4;
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
        padding: 0.5rem 0 1.5rem;
      }

      .statusbar {
        grid-template-columns: minmax(0, 1fr) auto;
        grid-template-areas:
          "title controls"
          "meta meta";
        align-items: center;
        padding-bottom: 0.25rem;
        gap: 0.25rem 0.5rem;
      }

      .statusbar-title {
        font-size: 1.25rem;
      }

      .statusbar-meta {
        font-size: var(--text-1);
        gap: 0.25rem 0.5rem;
      }

      .theme-toggle {
        min-height: 1.75rem;
        padding: 0 0.5rem;
        font-size: var(--text-1);
      }

      .metrics {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin-top: 0.35rem;
        padding: 0.35rem;
        gap: 0.25rem;
      }

      .metric {
        padding: 0.25rem 0.35rem;
        border-inline-start: 1px solid var(--border);
        border-top: 0;
      }

      .metric:first-child {
        border-inline-start: 0;
      }

      .metric-value {
        font-size: 1.125rem;
      }

      .metric--primary .metric-value {
        font-size: 1.125rem;
      }

      .metric-label {
        margin: 0.15rem 0 0;
        font-size: var(--text-1);
        letter-spacing: 0.02em;
      }

      .metric-detail,
      .share-track {
        display: none;
      }

      .toolbar {
        margin-top: 0.35rem;
        gap: 0.25rem;
        overflow-x: auto;
        flex-wrap: wrap;
        padding-bottom: 8px;
      }

      .toolbar-label {
        font-size: var(--text-1);
        white-space: nowrap;
      }

      .filters {
        flex-wrap: wrap;
        gap: 0.25rem;
      }

      .filter {
        min-height: 4.5rem;
        padding: var(--space-2);
        font-size: var(--text-1);
        white-space: nowrap;
      }

      .console-grid {
        margin-top: 0.35rem;
        gap: var(--space-3);
      }

      .panel {
        padding: 0.5rem 0.65rem;
      }

      .panel-heading {
        margin-bottom: 0.35rem;
      }

      .panel-title {
        font-size: 1rem;
      }

      .panel-meta {
        font-size: var(--text-1);
      }

      .voxel-controls {
        margin-bottom: 0.35rem;
        gap: 0.25rem;
      }

      .range-btn {
        min-height: 1.75rem;
        padding: 0 0.5rem;
        font-size: var(--text-1);
      }

      .anim-toggle-btn {
        min-height: 1.75rem;
        padding: 0 0.5rem;
        font-size: var(--text-1);
      }

      .legend {
        margin-top: 0.35rem;
        font-size: var(--text-1);
        gap: 0.25rem 0.5rem;
      }

      .evidence-grid {
        grid-template-columns: minmax(0, 1fr);
      }
    }

    @media (max-width: 22rem) {
      .console {
        width: 100%;
        padding-left: var(--space-2);
        padding-right: var(--space-2);
      }

      .statusbar-title {
        white-space: normal;
      }

      .preset-group {
        width: 100%;
      }

      .range-btn,
      .anim-toggle-btn {
        padding: 0 var(--space-2);
        font-size: var(--text-1);
      }

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

      .metric:nth-child(n+2) {
        border-top: 1px solid var(--border);
      }

      .metric {
        border-inline-start: 0;
      }

      .filters {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(4rem, 1fr));
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
        padding: 0 var(--space-3) var(--space-3);
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
      .legend-scale,
      .console-foot {
        overflow-wrap: anywhere;
      }

      .provider-row-head,
      .status-item {
        flex-wrap: wrap;
      }
    }

    @media (pointer: coarse) {
      .filter,
      .range-btn,
      .anim-toggle-btn {
        min-height: 2.25rem;
      }
    }

    @media (prefers-reduced-motion: reduce), print {
      .day-cell,
      .definitions-summary::after,
      .filter,
      .daily-row,
      .miner-actor,
      .pickaxe-arm,
      .zombie-actor {
        animation: none !important;
        transition: none !important;
      }

      .day-cell:hover,
      .day-cell:focus-visible,
      .filter:hover {
        transform: none !important;
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
        <p class="metric-detail sr-only" id="primaryDetail"></p>
        <div class="share-track" aria-hidden="true">
          <div class="share-fill" id="shareFill"></div>
        </div>
      </div>
      <div class="metric">
        <p class="metric-value" id="presenceValue">0</p>
        <p class="metric-label" id="presenceLabel">AI actor presences</p>
        <p class="metric-detail sr-only">One per provider/tool in a commit.</p>
      </div>
      <div class="metric">
        <p class="metric-value" id="daysValue">0</p>
        <p class="metric-label">Active AI days</p>
        <p class="metric-detail sr-only">Commit author dates with AI evidence.</p>
      </div>
      <div class="metric">
        <p class="metric-value" id="unknownValue">0</p>
        <p class="metric-label">Unattributed commits</p>
        <p class="metric-detail sr-only">No explicit AI or human declaration recorded.</p>
      </div>
    </section>

    <section class="toolbar" aria-label="Provider view">
      <span class="toolbar-label sr-only" id="filterLabel">Provider view</span>
      <div class="filters" id="providerFilters" role="group"
           aria-label="Filter dashboard by AI provider"></div>
    </section>

    <div class="console-grid">
      <section class="panel activity-panel" aria-labelledby="activityTitle">
        <div class="panel-heading">
          <h2 class="panel-title" id="activityTitle">Collaboration mine</h2>
          <p class="panel-meta" id="activityMeta"></p>
        </div>

        <div class="voxel-controls">
          <div class="date-controls" id="dateControls" aria-label="Date range selection">
            <div class="preset-group" role="group" aria-label="Date range presets">
              <button type="button" class="range-btn" id="preset28" data-preset="28d">28d</button>
              <button type="button" class="range-btn" id="preset84"
                      data-preset="84d" aria-pressed="true">84d</button>
              <button type="button" class="range-btn" id="preset365"
                      data-preset="365d">365d</button>
              <button type="button" class="range-btn" id="presetAll" data-preset="all">All</button>
            </div>
            <details class="custom-range" id="customRangeDisclosure">
              <summary>Custom dates</summary>
              <div class="custom-range-form" id="customRangeForm">
              <label for="customStartDate">From</label>
              <input type="date" class="date-input" id="customStartDate">
              <label for="customEndDate">To</label>
              <input type="date" class="date-input" id="customEndDate">
              <button type="button" class="range-btn" id="applyCustomRangeBtn">Apply</button>
              <span class="date-range-error" id="dateRangeError" role="alert"></span>
              </div>
            </details>
          </div>
          <div class="voxel-action-controls">
            <button type="button" class="range-btn" id="zoomToggleBtn"
                    aria-label="Toggle zoom density">Zoom: Standard</button>
            <button type="button" class="anim-toggle-btn" id="animToggleBtn"
                    aria-label="Pause character animation">⏸ Pause</button>
          </div>
        </div>

        <div class="panel-meta" id="scaleMeta"
             style="margin-bottom: var(--space-2);">Scale: 0–100 commits/day</div>

        <div class="legend">
          <div class="legend-swatches">
            <span class="legend-item">
              <span class="legend-swatch legend-swatch--ai"></span>
              <span>AI-attributed</span>
            </span>
            <span class="legend-item">
              <span class="legend-swatch legend-swatch--other"></span>
              <span>Other (total − AI)</span>
            </span>
            <span class="legend-item">
              <span class="legend-swatch legend-swatch--base"></span>
              <span>Published dates</span>
            </span>
          </div>
          <div class="sr-only" id="legendScaleMeta"></div>
        </div>
        <div class="calendar-scroll">
          <div class="calendar" id="activityCalendar" role="group"
               aria-labelledby="activitySummary"></div>
        </div>
        <p class="sr-only" id="activitySummary"></p>
      </section>

      <section class="panel detail-panel" id="selectedDatePanel" aria-labelledby="detailTitle">
        <div class="panel-heading">
          <h2 class="panel-title" id="detailTitle">Day breakdown</h2>
          <p class="panel-meta sr-only" id="selectedDateMeta">
            Select a day in the landscape or ledger</p>
        </div>
        <div class="day-composition" id="dayComposition" role="img"
             aria-label="Select a day for its AI and Other composition"></div>
        <div class="detail-grid" id="detailGrid">
          <div class="detail-card">
            <span class="detail-label">Date</span>
            <span class="detail-val mono" id="detailDate">—</span>
          </div>
          <div class="detail-card">
            <span class="detail-label">Total Commits</span>
            <span class="detail-val mono" id="detailTotal">—</span>
          </div>
          <div class="detail-card detail-card--ai">
            <span class="detail-label">AI-Attributed</span>
            <span class="detail-val mono" id="detailAi">—</span>
          </div>
          <div class="detail-card detail-card--other">
            <span class="detail-label">Other Records</span>
            <span class="detail-val mono" id="detailOther">—</span>
            <span class="detail-sub">Total − AI (not human)</span>
          </div>
          <div class="detail-card">
            <span class="detail-label">AI Share</span>
            <span class="detail-val mono" id="detailShare">—</span>
          </div>
        </div>
        <div class="detail-providers" id="detailProviders">
          <h3 class="detail-subtitle">Attributed Providers</h3>
          <div class="detail-provider-list" id="detailProviderList"></div>
        </div>
      </section>

      <aside class="sidebar" aria-label="Provider workstations and evidence">
        <section
          class="panel workstations-panel"
          id="workstationsSection"
          aria-labelledby="workstationsTitle"
        >
          <div class="panel-heading">
            <h2 class="panel-title" id="workstationsTitle">Mining Workstations</h2>
            <p class="panel-meta" id="workstationsDenominator"></p>
          </div>
          <div class="provider-list" id="providerList"></div>
          <p class="workstations-overlap-note">
            Provider counts overlap — do not add them together.
          </p>
        </section>

        <section class="panel evidence-panel" id="evidenceSection" aria-labelledby="evidenceTitle">
          <div class="panel-heading">
            <h2 class="panel-title" id="evidenceTitle">Archive Rock Stratum</h2>
            <p class="panel-meta" id="evidenceTotal"></p>
          </div>
          <div class="rock-stratum-container" id="rockStratumContainer" aria-hidden="true"></div>
          <div class="evidence-track" id="evidenceTrack" aria-hidden="true"
               style="display: none;"></div>
          <div class="evidence-grid" id="evidenceGrid"></div>
          <p class="evidence-note">All-time evidence · unknown ≠ human.</p>
        </section>
      </aside>

      <section class="panel table-panel" id="dailyTableSection" aria-labelledby="tableTitle">
        <details class="ledger-disclosure" id="dailyLedger">
        <summary>Daily table</summary>
        <div class="panel-heading">
          <h2 class="panel-title" id="tableTitle">Daily Activity Ledger</h2>
          <p class="panel-meta" id="tableRangeMeta">Showing selected range</p>
        </div>
        <div class="table-scroll">
          <table class="daily-table" id="dailyTable" aria-label="Daily activity table">
            <thead>
              <tr>
                <th scope="col" aria-sort="descending">
                  <button type="button" class="sort-btn" data-sort="date">
                    Date <span class="sort-icon" id="sortIcon-date">▼</span>
                  </button>
                </th>
                <th scope="col">
                  <button type="button" class="sort-btn" data-sort="total">
                    Total <span class="sort-icon" id="sortIcon-total"></span>
                  </button>
                </th>
                <th scope="col">
                  <button type="button" class="sort-btn" data-sort="ai">
                    AI <span class="sort-icon" id="sortIcon-ai"></span>
                  </button>
                </th>
                <th scope="col">
                  <button type="button" class="sort-btn" data-sort="other">
                    Other <span class="sort-icon" id="sortIcon-other"></span>
                  </button>
                </th>
                <th scope="col">
                  <button type="button" class="sort-btn" data-sort="share">
                    AI % <span class="sort-icon" id="sortIcon-share"></span>
                  </button>
                </th>
                <th scope="col">Providers</th>
              </tr>
            </thead>
            <tbody id="dailyTableBody"></tbody>
          </table>
        </div>
        </details>
      </section>
    </div>

    <details class="definitions" id="definitions">
      <summary class="definitions-summary">How to read this profile</summary>
      <div class="definitions-body">
        <div>
          <h2 class="note-title">Symbols and scope</h2>
          <p class="note-copy">Blue crystal = AI-attributed commits; stone = Other records
            (total minus AI), not human. Heights share one linear scale. Provider symbols
            highlight participation without changing the columns. Provider identity does not
            identify a specific editor or tool.</p>
          <p class="note-copy">All top metrics cover the full profile period. Active-day counts
            use commit author dates. AI actor presences count one per provider/tool in a commit.</p>
        </div>
        <div>
          <h2 class="note-title">Provider details</h2>
          <ul class="provider-facts" id="providerFacts"></ul>
        </div>
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
            Human-Only means an explicit human-only declaration. All ACE records, every
            actor type, contribute to the all-time evidence archive; no daily evidence
            grade is inferred.
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
          <p class="note-copy" id="schemaLabel"></p>
        </div>
      </div>
    </details>

    <footer class="console-foot">
      <span>Git provenance · static snapshot</span>
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
      const actorBodies = __VOXEL_ACTORS__;
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
        verified: "#10b981",
        declared: "#0284c7",
        imported: "#8b5cf6",
        inferred: "#d97706",
        unknown: "#64748b"
      };
      const evidence3D = {
        verified: { front: "#10b981", top: "#34d399", side: "#059669" },
        declared: { front: "#0284c7", top: "#38bdf8", side: "#0369a1" },
        imported: { front: "#8b5cf6", top: "#a78bfa", side: "#7c3aed" },
        inferred: { front: "#d97706", top: "#fbbf24", side: "#b45309" },
        unknown:  { front: "#64748b", top: "#94a3b8", side: "#475569" }
      };

      let selected = "all";
      let theme = "auto";
      let calendarFocusIndex = null;
      let selectedDate = null;
      let sortCol = "date";
      let sortDir = "desc";
      let isZoomed = false;
      let animRunning = true;

      let tooltipOwner = null;
      let tooltipPinned = false;
      let tooltipSuppressed = null;
      let tooltipHoverPaused = false;

      // Publishable date extent
      const dailyData = data.daily || [];
      const byDate = new Map(dailyData.map((d) => [d.date, d]));
      const minPublishableDate = dailyData.length ? dailyData[0].date : null;
      const maxPublishableDate = dailyData.length ? dailyData[dailyData.length - 1].date : null;

      let activePreset = "84d";
      let currentStartDate = null;
      let currentEndDate = null;
      let lastValidStartDate = null;
      let lastValidEndDate = null;

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
        if (!day) return 0;
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

      function niceCeiling(peak) {
        if (peak <= 1) return 1;
        const s = String(peak);
        const power = 10 ** (s.length - 1);
        const leading = Math.ceil(peak / power);
        return leading * power;
      }

      function computePresetRange(preset) {
        if (!maxPublishableDate) return { start: null, end: null };
        const end = dateAtUtc(maxPublishableDate);
        let daysBack = 84;
        if (preset === "28d") daysBack = 28;
        else if (preset === "84d") daysBack = 84;
        else if (preset === "365d") daysBack = 365;
        else if (preset === "all") {
          return { start: minPublishableDate, end: maxPublishableDate };
        }
        const start = new Date(end);
        start.setUTCDate(start.getUTCDate() - (daysBack - 1));
        return {
          start: dateKey(start),
          end: maxPublishableDate
        };
      }

      function initDates() {
        if (!dailyData.length) {
          $("preset28").disabled = true;
          $("preset84").disabled = true;
          $("preset365").disabled = true;
          $("presetAll").disabled = true;
          $("customStartDate").disabled = true;
          $("customEndDate").disabled = true;
          $("applyCustomRangeBtn").disabled = true;
          return;
        }
        const range = computePresetRange("84d");
        currentStartDate = range.start;
        currentEndDate = range.end;
        lastValidStartDate = currentStartDate;
        lastValidEndDate = currentEndDate;
        $("customStartDate").value = currentStartDate;
        $("customEndDate").value = currentEndDate;
        $("customStartDate").min = minPublishableDate;
        $("customStartDate").max = maxPublishableDate;
        $("customEndDate").min = minPublishableDate;
        $("customEndDate").max = maxPublishableDate;
      }

      function getActiveSeries() {
        if (!currentStartDate || !currentEndDate) return [];
        const start = dateAtUtc(currentStartDate);
        const end = dateAtUtc(currentEndDate);
        const series = [];
        const curr = new Date(start);
        while (curr <= end) {
          const key = dateKey(curr);
          const cell = byDate.get(key) || {
            date: key,
            total_commits: 0,
            ai_commits: 0,
            counts: []
          };
          series.push(cell);
          curr.setUTCDate(curr.getUTCDate() + 1);
        }
        return series;
      }

      function pctLabel(num, den) {
        if (den <= 0 || num === 0) return "0%";
        if (num === den) return "100%";
        const p = Math.round((100 * num) / den);
        if (p === 0) return "<1%";
        if (p === 100) return ">99%";
        return `${p}%`;
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
          button.setAttribute("aria-label", `Highlight ${row.display_name}`);
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
        const commitCount = data.totals.ai_attributed_commits;
        const presenceCount = data.totals.ai_actor_presences;
        const dayCount = data.totals.active_ai_days;
        const denominator = data.totals.commits_scanned;
        const share = denominator ? (commitCount / denominator) * 100 : 0;
        const accent = selectedAccent();

        $("primaryMetric").style.setProperty("--active-accent", accent);
        $("primaryLabel").textContent = "AI-attributed commits";
        $("primaryValue").textContent = number.format(commitCount);
        $("primaryDetail").textContent =
          `${percent.format(share)}% of ${number.format(denominator)} commits scanned · ` +
          "each commit counted once";
        $("shareFill").style.width = `${Math.min(100, share)}%`;
        $("presenceValue").textContent = number.format(presenceCount);
        $("presenceLabel").textContent = "AI actor presences";
        $("daysValue").textContent = number.format(dayCount);
        $("unknownValue").textContent = number.format(data.totals.unknown_commits);
      }

      function getPalette() {
        const isDark = document.documentElement.dataset.theme === "dark" ||
          (document.documentElement.dataset.theme === "auto" &&
           window.matchMedia("(prefers-color-scheme: dark)").matches);
        return isDark ? {
          grassTop: "#3a6920",
          grassFringe: "#4d822d",
          dirtFront: "#4d3726",
          dirtSide: "#332419",
          stoneFront: "#3d444d",
          stoneSide: "#282d33",
          aiFront: "#38bdf8",
          aiTop: "#bae6fd",
          aiSide: "#0284c7",
          otherFront: "#64748b",
          otherTop: "#94a3b8",
          otherSide: "#475569",
          slotBorder: "#34526f",
          slotBg: "#1e293b"
        } : {
          grassTop: "#5b8c32",
          grassFringe: "#6fa83e",
          dirtFront: "#866043",
          dirtSide: "#5a402d",
          stoneFront: "#6e7681",
          stoneSide: "#57606a",
          aiFront: "#0ea5e9",
          aiTop: "#7dd3fc",
          aiSide: "#0284c7",
          otherFront: "#94a3b8",
          otherTop: "#cbd5e1",
          otherSide: "#64748b",
          slotBorder: "#c2d3e5",
          slotBg: "#e2e8f0"
        };
      }

      function renderTerraceSvg(
        terraceIdx, rowDays, ceiling, globalStartIndex, rovingIndex, hasActors, hasActivity,
        rowCapacity, compact
      ) {
        const dayPitch = 25;
        // One pixel scale for every row, including an incomplete final row.
        const baseW = 12 + rowCapacity * dayPitch;
        const totalW = baseW + (compact ? 22 : 92);
        const totalH = compact && hasActors ? 258 : 146;
        const baselineY = 80;
        const maxH = 46.0;
        const voxelDx = 3;
        const voxelDy = 2.5;
        const pal = getPalette();

        const svg = document.createElementNS(SVG_NS, "svg");
        svg.setAttribute("viewBox", `0 0 ${totalW} ${totalH}`);
        svg.setAttribute("class", "voxel-terrace-svg");
        svg.setAttribute("role", "group");
        svg.setAttribute("aria-label", `Terrace ${terraceIdx + 1} activity landscape`);

        const baseX = 6;

        // Broad orthographic slab. Only pillar fronts carry quantities.
        function decor(tag, attrs) {
          const el = document.createElementNS(SVG_NS, tag);
          for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, String(value));
          svg.append(el);
          return el;
        }
        decor("path", {class: "terrain-top", fill: pal.grassTop,
          d: "M " + baseX + " " + baselineY + " l 18 -12 h " + baseW + " l -18 12 Z"});
        for (let i = 0; i <= rowCapacity; i++) {
          decor("path", {d: "M " + (baseX + i * dayPitch) + " " + baselineY + " l 18 -12",
            stroke: pal.grassFringe, "stroke-width": 1});
        }
        decor("rect", {x: baseX, y: baselineY, width: baseW, height: 14, fill: pal.dirtFront});
        decor("rect", {x: baseX, y: baselineY + 14, width: baseW, height: 22,
          fill: pal.stoneFront});
        decor("path", {d: "M " + (baseX + baseW) + " " + baselineY +
          " l 18 -12 v 14 l -18 12 Z", fill: pal.dirtSide});
        decor("path", {d: "M " + (baseX + baseW) + " " + (baselineY + 14) +
          " l 18 -12 v 22 l -18 12 Z", fill: pal.stoneSide});
        for (let course = 0; course < 2; course++) {
          for (let i = 0; i <= rowCapacity; i++) {
            const bx = baseX + i * dayPitch + (course ? 12 : 0);
            const bw = Math.min(24, baseX + baseW - bx);
            if (bw <= 0) continue;
            const by = baselineY + 15 + course * 10;
            decor("rect", {x: bx, y: by, width: bw, height: 9,
              fill: (i + course + terraceIdx) % 5 === 0 ? pal.stoneSide : pal.stoneFront});
            decor("path", {d: "M " + bx + " " + (by + 9) + " h " + bw,
              stroke: pal.stoneSide, "stroke-width": 1});
          }
        }
        for (let i = 0; i < rowCapacity; i += 2) {
          const gx = baseX + i * dayPitch;
          decor("rect", {x: gx, y: baselineY, width: 24, height: 3, fill: pal.grassFringe});
          decor("rect", {x: gx + 8, y: baselineY + 3, width: 5, height: 3, fill: pal.grassTop});
        }
        for (const ratio of [0.2, 0.65]) {
          const ox = baseX + Math.floor(baseW * ratio);
          decor("rect", {x: ox, y: baselineY + 23, width: 5, height: 4, fill: pal.aiSide});
          decor("rect", {x: ox + 5, y: baselineY + 20, width: 3, height: 3, fill: pal.aiTop});
        }

        // Days in this row
        for (let d = 0; d < rowDays.length; d++) {
          const day = rowDays[d];
          const index = globalStartIndex + d;
          const selectedCount = selectedDayCount(day);
          const share = day.total_commits
            ? (selectedCount / day.total_commits) * 100
            : 0;
          const label = `${day.date}: ${day.total_commits} total commits; ` +
            `${selectedCount} ${selectedName()} attributed commits; ` +
            `${percent.format(share)}% share`;

          const dayX = baseX + 4 + d * dayPitch;
          const cell = document.createElementNS(SVG_NS, "g");
          cell.setAttribute("class", "day-cell");
          cell.setAttribute("role", "button");
          cell.tabIndex = index === rovingIndex ? 0 : -1;
          cell.dataset.index = String(index);
          cell.dataset.date = day.date;
          cell.dataset.active = String(selectedCount > 0);
          if (selectedCount) {
            cell.dataset.hasSelected = "true";
          }
          cell.setAttribute("aria-label", label);

          if (day.date === selectedDate) {
            cell.setAttribute("data-selected-day", "true");
          }

          const hasProviderParticipation = selected === "all" ||
            (day.counts && day.counts.some(c => c.provider === selected));
          if (selected !== "all" && hasProviderParticipation) {
            cell.setAttribute("data-highlighted", "true");
          }

          // Ground marker
          const groundMarker = document.createElementNS(SVG_NS, "rect");
          groundMarker.setAttribute("class", "day-ground-marker");
          groundMarker.setAttribute("x", String(dayX - 1));
          groundMarker.setAttribute("y", String(baselineY - 2));
          groundMarker.setAttribute("width", "19");
          groundMarker.setAttribute("height", "3");
          groundMarker.setAttribute("rx", "1");
          groundMarker.setAttribute("fill", "transparent");
          cell.append(groundMarker);

          // Day label
          const dayNum = day.date.slice(8);
          const textLabel = document.createElementNS(SVG_NS, "text");
          textLabel.setAttribute("class", "day-label");
          textLabel.setAttribute("x", String(dayX + 8.5));
          textLabel.setAttribute("y", String(baselineY + 57));
          textLabel.setAttribute("text-anchor", "middle");
          textLabel.setAttribute("font-size", "14");
          if (compact) textLabel.style.fontSize = "18px";
          textLabel.setAttribute("font-family", "var(--mono)");
          textLabel.setAttribute("fill", "var(--muted)");
          textLabel.textContent = dayNum;
          cell.append(textLabel);

          // Pillars or Zero slot
          if (day.total_commits === 0 && day.ai_commits === 0) {
            const slot = document.createElementNS(SVG_NS, "rect");
            slot.setAttribute("x", String(dayX));
            slot.setAttribute("y", String(baselineY - 1));
            slot.setAttribute("width", "17");
            slot.setAttribute("height", "1");
            slot.setAttribute("fill", pal.slotBorder);
            cell.append(slot);
          } else {
            const cAi = day.ai_commits;
            const cOther = Math.max(0, day.total_commits - day.ai_commits);

            if (cAi > 0) {
              const hAi = (maxH * cAi) / ceiling;
              const aiX = dayX;

              const rect = document.createElementNS(SVG_NS, "rect");
              rect.setAttribute("x", String(aiX));
              rect.setAttribute("y", String(baselineY - hAi));
              rect.setAttribute("width", "8");
              rect.setAttribute("height", String(hAi));
              rect.setAttribute("fill", pal.aiFront);
              cell.append(rect);

              const top = document.createElementNS(SVG_NS, "path");
              top.setAttribute(
                "d",
                `M ${aiX} ${baselineY - hAi} ` +
                `L ${aiX + voxelDx} ${baselineY - hAi - voxelDy} ` +
                `L ${aiX + 8 + voxelDx} ${baselineY - hAi - voxelDy} ` +
                `L ${aiX + 8} ${baselineY - hAi} Z`
              );
              top.setAttribute("fill", pal.aiTop);
              cell.append(top);

              const side = document.createElementNS(SVG_NS, "path");
              side.setAttribute(
                "d",
                `M ${aiX + 8} ${baselineY} L ${aiX + 8} ${baselineY - hAi} ` +
                `L ${aiX + 8 + voxelDx} ${baselineY - hAi - voxelDy} ` +
                `L ${aiX + 8 + voxelDx} ${baselineY - voxelDy} Z`
              );
              side.setAttribute("fill", pal.aiSide);
              cell.append(side);
            }

            if (cOther > 0) {
              const hOther = (maxH * cOther) / ceiling;
              const otherX = dayX + 9;

              const rect = document.createElementNS(SVG_NS, "rect");
              rect.setAttribute("x", String(otherX));
              rect.setAttribute("y", String(baselineY - hOther));
              rect.setAttribute("width", "8");
              rect.setAttribute("height", String(hOther));
              rect.setAttribute("fill", pal.otherFront);
              cell.append(rect);

              const top = document.createElementNS(SVG_NS, "path");
              top.setAttribute(
                "d",
                `M ${otherX} ${baselineY - hOther} ` +
                `L ${otherX + voxelDx} ${baselineY - hOther - voxelDy} ` +
                `L ${otherX + 8 + voxelDx} ${baselineY - hOther - voxelDy} ` +
                `L ${otherX + 8} ${baselineY - hOther} Z`
              );
              top.setAttribute("fill", pal.otherTop);
              cell.append(top);

              const side = document.createElementNS(SVG_NS, "path");
              side.setAttribute(
                "d",
                `M ${otherX + 8} ${baselineY} L ${otherX + 8} ${baselineY - hOther} ` +
                `L ${otherX + 8 + voxelDx} ${baselineY - hOther - voxelDy} ` +
                `L ${otherX + 8 + voxelDx} ${baselineY - voxelDy} Z`
              );
              side.setAttribute("fill", pal.otherSide);
              cell.append(side);
            }
          }

          // Full-height hit area
          const hit = document.createElementNS(SVG_NS, "rect");
          hit.setAttribute("class", "day-hit");
          hit.setAttribute("x", String(dayX - 2));
          hit.setAttribute("y", "4");
          hit.setAttribute("width", "21");
          hit.setAttribute("height", "137");
          hit.setAttribute("fill", "transparent");
          hit.setAttribute("cursor", "pointer");
          cell.append(hit);

          // Listeners
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
            updateDetailPanel(day);
          });
          cell.addEventListener("blur", hideTooltip);
          cell.addEventListener("click", () => {
            updateDetailPanel(day);
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

          svg.append(cell);
        }

        // Characters stay outside all date hit areas, including at 195px.
        if (hasActors) {
          const sx = compact ? Math.max(16, baseW - 82) : baseW + 26;
          const sy = compact ? baselineY + 142 : baselineY;
          for (const px of [sx, sx + 58]) {
            decor("rect", {x: px, y: sy - 66, width: 3, height: 96, fill: "#765036"});
            decor("rect", {x: px + 3, y: sy - 66, width: 2, height: 96, fill: "#a47d4d"});
          }
          for (const py of [sy - 36, sy]) {
            decor("path", {d: "M " + sx + " " + py + " l 5 -4 h 58 l -5 4 Z", fill: "#c09b61"});
            decor("rect", {x: sx, y: py, width: 58, height: 4, fill: "#765036"});
          }
          for (const lx of [sx + 3, sx + 14]) {
            decor("rect", {x: lx, y: sy - 58, width: 2, height: 80, fill: "#c09b61"});
          }
          for (let ly = sy - 54; ly < sy + 20; ly += 8) {
            decor("rect", {x: sx + 3, y: ly, width: 13, height: 2, fill: "#a47d4d"});
          }
          const ox = sx + 39, oy = sy - 19;
          decor("rect", {x: ox, y: oy, width: 17, height: 19, fill: pal.stoneFront});
          decor("path", {d: "M " + ox + " " + oy + " l 4 -3 h 17 l -4 3 Z", fill: pal.otherTop});
          decor("path", {d: "M " + (ox + 17) + " " + oy + " l 4 -3 v 19 l -4 3 Z",
            fill: pal.stoneSide});
          decor("rect", {x: ox + 3, y: oy + 5, width: 5, height: 5, fill: pal.aiFront});
          decor("rect", {x: ox + 10, y: oy + 11, width: 4, height: 4, fill: pal.aiTop});
          for (const [kind, ax, ay] of [
            ["zombie", sx + 20, sy - 78], ["miner", sx + 1, sy - 42]
          ]) {
            const wrap = decor("g", {transform: "translate(" + ax + ", " + ay + ")"});
            const actor = document.createElementNS(SVG_NS, "g");
            actor.setAttribute("class", kind + "-actor");
            actor.innerHTML = actorBodies[kind];
            if (!hasActivity) {
              actor.style.animation = "none";
              actor.querySelectorAll("[class]").forEach(part => {part.style.animation = "none";});
            }
            wrap.append(actor);
          }
        }

        return svg;
      }

      function updateDetailPanel(day) {
        if (!day) return;
        selectedDate = day.date;
        $("detailDate").textContent = day.date;
        $("detailTotal").textContent = number.format(day.total_commits);
        $("detailAi").textContent = number.format(day.ai_commits);
        const other = Math.max(0, day.total_commits - day.ai_commits);
        $("detailOther").textContent = number.format(other);
        const share = day.total_commits ? (day.ai_commits / day.total_commits) * 100 : 0;
        $("detailShare").textContent = `${percent.format(share)}%`;
        $("selectedDateMeta").textContent = `${day.date} collaboration breakdown`;
        const composition = $("dayComposition");
        composition.replaceChildren();
        composition.setAttribute("aria-label", `${day.date}: ${day.ai_commits} AI-attributed, ` +
          `${other} Other records, ${day.total_commits} total commits`);
        for (const [kind, value] of [["ai", day.ai_commits], ["other", other]]) {
          const segment = document.createElement("span");
          segment.className = `day-composition-${kind}`;
          segment.style.width = `${day.total_commits ? value / day.total_commits * 100 : 0}%`;
          composition.append(segment);
        }

        const list = $("detailProviderList");
        list.replaceChildren();
        if (day.counts && day.counts.length) {
          for (const count of day.counts) {
            const row = providerBySlug(count.provider);
            const name = row ? row.display_name : count.provider;
            const chip = document.createElement("span");
            chip.className = "detail-chip";
            chip.append(
              providerIcon(count.provider, name, "filter"),
              document.createTextNode(`${name}: ${count.attributed_commits}`)
            );
            list.append(chip);
          }
        } else {
          const empty = document.createElement("span");
          empty.className = "panel-meta";
          empty.textContent = day.ai_commits === 0
            ? "No AI provider activity recorded."
            : "AI attribution recorded.";
          list.append(empty);
        }

        document.querySelectorAll("g.day-cell").forEach((btn) => {
          btn.setAttribute("data-selected-day", String(btn.dataset.date === day.date));
        });
        document.querySelectorAll(".daily-row").forEach((tr) => {
          tr.dataset.selected = String(tr.dataset.date === day.date);
          const dateButton = tr.querySelector(".date-select");
          if (dateButton) dateButton.setAttribute("aria-pressed", tr.dataset.selected);
        });
      }

      function renderCalendar() {
        const series = getActiveSeries();
        const calendar = $("activityCalendar");
        const scroller = document.querySelector(".calendar-scroll");
        const previousMaxScroll = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
        const previousScrollLeft = scroller.scrollLeft;
        const followNewest = previousMaxScroll <= 1 || previousMaxScroll - previousScrollLeft <= 2;
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
        const rovingIndex = calendarFocusIndex === null
          ? series.length - 1
          : Math.max(0, Math.min(series.length - 1, calendarFocusIndex));
        if (calendarFocusIndex !== null) calendarFocusIndex = rovingIndex;

        let peakTotal = 0;
        let peakDate = series[series.length - 1].date;
        for (const day of series) {
          if (day.total_commits > peakTotal) {
            peakTotal = day.total_commits;
            peakDate = day.date;
          }
        }
        const ceiling = niceCeiling(peakTotal);
        const mid = Math.round(ceiling / 2);
        $("scaleMeta").textContent =
          `Scale: 0–${ceiling} commits/day · Peak: ${peakTotal} (${peakDate}) · ` +
          `${series.length} days`;
        const legendScale = $("legendScaleMeta");
        if (legendScale) {
          legendScale.textContent = `Linear scale: 0 · ${mid} · ${ceiling} commits/day`;
        }

        // Determine days per row based on container width & zoom
        const containerWidth = calendar.clientWidth || window.innerWidth;
        let daysPerRow = 28;
        if (containerWidth < 480) {
          daysPerRow = 7;
        } else if (containerWidth < 800) {
          daysPerRow = 14;
        }
        if (isZoomed) {
          daysPerRow = Math.max(7, Math.floor(daysPerRow / 2));
        }
        calendar.dataset.daysPerRow = String(daysPerRow);

        const terracesContainer = document.createElement("div");
        terracesContainer.className = "voxel-terraces";

        const numTerraces = Math.ceil(series.length / daysPerRow);
        for (let t = 0; t < numTerraces; t++) {
          const rowStart = t * daysPerRow;
          const rowEnd = Math.min(series.length, (t + 1) * daysPerRow);
          const rowDays = series.slice(rowStart, rowEnd);
          const hasActors = (t === 0);

          const terraceRow = document.createElement("div");
          terraceRow.className = "voxel-terrace-row";

          const header = document.createElement("div");
          header.className = "voxel-terrace-header";
          const firstDate = rowDays[0].date;
          const lastDate = rowDays[rowDays.length - 1].date;
          header.textContent = `${firstDate} → ${lastDate}`;
          terraceRow.append(header);

          const terraceSvg = renderTerraceSvg(
            t, rowDays, ceiling, rowStart, rovingIndex, hasActors, peakTotal > 0,
            daysPerRow, containerWidth < 240
          );
          terraceRow.append(terraceSvg);
          terracesContainer.append(terraceRow);
        }

        calendar.append(terracesContainer);

        $("activityMeta").textContent =
          `${series[0].date} → ${series[series.length - 1].date}`;
        $("activitySummary").textContent =
          `Daily ${selectedName()} attributed-commit counts from ` +
          `${series[0].date} through ${series[series.length - 1].date}; ` +
          "each cell uses the validated published daily aggregate.";

        // Selected date retention or fall back to last date
        if (selectedDate && series.some(d => d.date === selectedDate)) {
          const currentDay = series.find(d => d.date === selectedDate);
          updateDetailPanel(currentDay);
        } else if (series.length) {
          updateDetailPanel(series[series.length - 1]);
        }

        requestAnimationFrame(() => {
          const nextMaxScroll = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
          scroller.scrollLeft = followNewest
            ? nextMaxScroll
            : Math.min(previousScrollLeft, nextMaxScroll);
        });
      }

      function calendarCells() {
        return [...document.querySelectorAll("g.day-cell")];
      }

      function focusCalendarCell(index) {
        const series = getActiveSeries();
        const maxIdx = Math.max(0, series.length - 1);
        const bounded = Math.max(0, Math.min(maxIdx, index));
        const cells = calendarCells();
        calendarFocusIndex = bounded;
        cells.forEach((cell) => {
          const cIdx = Number(cell.dataset.index);
          cell.tabIndex = cIdx === bounded ? 0 : -1;
        });
        const targetCell = cells.find(c => Number(c.dataset.index) === bounded);
        if (targetCell) {
          targetCell.focus();
        }
      }

      function handleCalendarKeydown(event) {
        const index = Number(event.currentTarget.dataset.index);
        const rowStep = Number($("activityCalendar").dataset.daysPerRow) || 7;
        const series = getActiveSeries();
        const maxIdx = Math.max(0, series.length - 1);
        let target = null;
        if (event.key === "Escape") {
          tooltipHoverPaused = true;
          tooltipSuppressed = event.currentTarget;
          hideTooltip();
          return;
        }
        if (event.key === "ArrowRight") {
          target = index + 1;
        } else if (event.key === "ArrowLeft") {
          target = index - 1;
        } else if (event.key === "ArrowDown") {
          target = index + rowStep;
        } else if (event.key === "ArrowUp") {
          target = index - rowStep;
        } else if (event.key === "Home") {
          target = 0;
        } else if (event.key === "End") {
          target = maxIdx;
        } else if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          if (series[index]) updateDetailPanel(series[index]);
          return;
        }
        if (target !== null) {
          event.preventDefault();
          const bounded = Math.max(0, Math.min(maxIdx, target));
          focusCalendarCell(bounded);
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

      function renderDailyTable() {
        const tbody = $("dailyTableBody");
        tbody.replaceChildren();
        document.querySelectorAll(".sort-btn").forEach((button) => {
          const header = button.closest("th");
          if (button.dataset.sort === sortCol) {
            header.setAttribute("aria-sort", sortDir === "asc" ? "ascending" : "descending");
          } else {
            header.removeAttribute("aria-sort");
          }
        });
        let rows = [...getActiveSeries()];
        if (!rows.length) {
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 6;
          td.style.textAlign = "center";
          td.textContent = "No daily records to display.";
          tr.append(td);
          tbody.append(tr);
          return;
        }

        rows.sort((a, b) => {
          let vA, vB;
          if (sortCol === "date") {
            vA = a.date; vB = b.date;
          } else if (sortCol === "total") {
            vA = a.total_commits; vB = b.total_commits;
          } else if (sortCol === "ai") {
            vA = a.ai_commits; vB = b.ai_commits;
          } else if (sortCol === "other") {
            vA = a.total_commits - a.ai_commits; vB = b.total_commits - b.ai_commits;
          } else if (sortCol === "share") {
            vA = a.total_commits ? a.ai_commits / a.total_commits : 0;
            vB = b.total_commits ? b.ai_commits / b.total_commits : 0;
          }
          if (vA < vB) return sortDir === "asc" ? -1 : 1;
          if (vA > vB) return sortDir === "asc" ? 1 : -1;
          return 0;
        });

        for (const day of rows) {
          const tr = document.createElement("tr");
          tr.className = "daily-row";
          tr.dataset.date = day.date;
          tr.dataset.selected = String(day.date === selectedDate);

          const other = Math.max(0, day.total_commits - day.ai_commits);
          const share = day.total_commits ? (day.ai_commits / day.total_commits) * 100 : 0;

          const provText = (day.counts && day.counts.length)
            ? day.counts.map(c => {
                const r = providerBySlug(c.provider);
                return `${r ? r.display_name : c.provider} (${c.attributed_commits})`;
              }).join(", ")
            : "—";

          tr.innerHTML = `
            <td class="mono"><button type="button" class="date-select"
              aria-label="Select ${day.date}" aria-pressed="${day.date === selectedDate}"
              >${day.date}</button></td>
            <td class="mono">${day.total_commits}</td>
            <td class="mono" style="color: var(--voxel-ai-front);">${day.ai_commits}</td>
            <td class="mono" style="color: var(--voxel-other-front);">${other}</td>
            <td class="mono">${percent.format(share)}%</td>
            <td>${provText}</td>
          `;

          tr.addEventListener("click", () => {
            updateDetailPanel(day);
          });
          tbody.append(tr);
        }

        $("tableRangeMeta").textContent =
          `Showing: ${rows.length} selected dates (${currentStartDate} → ${currentEndDate})`;
      }

      function renderProviders() {
        const totalAi = data.totals.ai_attributed_commits || 1;
        $("workstationsDenominator").textContent =
          `Commits · % of ${number.format(data.totals.ai_attributed_commits)} ` +
          "AI-attributed · all time";
        $("providerFacts").replaceChildren(...data.providers.map(row => {
          const fact = document.createElement("li");
          fact.textContent = `${row.display_name}: ${number.format(row.actor_presences)} ` +
            `AI actor presences · ${number.format(row.active_days)} active days`;
          return fact;
        }));
        $("providerList").replaceChildren(...data.providers.map((row) => {
          const accent = colorFor(row.provider);
          const button = document.createElement("button");
          button.type = "button";
          button.className = "provider-row";
          button.dataset.provider = row.provider;
          button.setAttribute("aria-current", String(selected === row.provider));
          button.setAttribute("aria-label", `Highlight ${row.display_name}: ` +
            `${number.format(row.attributed_commits)} attributed commits`);
          button.style.setProperty("--provider-accent", accent);

          const head = document.createElement("span");
          head.className = "provider-row-head";
          const name = document.createElement("span");
          name.className = "provider-name";
          const tool = document.createElementNS(SVG_NS, "svg");
          tool.setAttribute("class", "workbench-tool");
          tool.setAttribute("viewBox", "0 0 12 12");
          tool.setAttribute("aria-hidden", "true");
          tool.innerHTML = '<path d="M 2 10 L 7 5 M 5 3 L 8 1 L 10 3 L 8 6 Z"' +
            ' fill="#94a3b8" stroke="#78350f" stroke-width="1"/>';
          name.append(
            providerIcon(row.provider, row.display_name, "row"),
            document.createTextNode(row.display_name),
            tool
          );
          const count = document.createElement("span");
          count.className = "provider-count";
          const shareStr = pctLabel(row.attributed_commits, data.totals.ai_attributed_commits);
          count.textContent = `${number.format(row.attributed_commits)} (${shareStr})`;
          head.append(name, count);

          const track = document.createElement("span");
          track.className = "provider-track";
          const fill = document.createElement("span");
          fill.className = "provider-fill";
          const rawPct = (row.attributed_commits / totalAi) * 100;
          fill.style.width = `${rawPct}%`;
          track.append(fill);

          const detail = document.createElement("span");
          detail.className = "provider-detail sr-only";
          detail.textContent = `${number.format(row.actor_presences)} presences · ` +
            `${number.format(row.active_days)} active days · ` +
            `${shareStr} of ${number.format(data.totals.ai_attributed_commits)} total AI`;
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
        const total = data.evidence_records.total_records || 1;
        const totalRec = data.evidence_records.total_records;
        $("evidenceTotal").textContent = `${number.format(totalRec)} records`;

        // 3D Geological Rock Stratum
        const stratumContainer = $("rockStratumContainer");
        stratumContainer.replaceChildren();
        const sSvg = document.createElementNS(SVG_NS, "svg");
        sSvg.setAttribute("viewBox", "0 0 340 32");
        sSvg.setAttribute("class", "rock-stratum-svg");

        const stratumW = 328;
        let currX = 6;
        for (const entry of entries) {
          const segW = (entry.value / total) * stratumW;
          if (segW <= 0) continue;
          const pal = evidence3D[entry.key] || evidence3D.unknown;

          // Top facet
          const topF = document.createElementNS(SVG_NS, "path");
          topF.setAttribute(
            "d",
            `M ${currX} 8 L ${currX + 3} 4 L ${currX + segW + 3} 4 L ${currX + segW} 8 Z`
          );
          topF.setAttribute("fill", pal.top);
          sSvg.append(topF);

          // Front facet
          const frontF = document.createElementNS(SVG_NS, "rect");
          frontF.setAttribute("x", String(currX));
          frontF.setAttribute("y", "8");
          frontF.setAttribute("width", String(segW));
          frontF.setAttribute("height", "16");
          frontF.setAttribute("fill", pal.front);
          sSvg.append(frontF);

          currX += segW;
        }

        // Side facet of the stratum
        const lastPal = entries.length
          ? (evidence3D[entries[entries.length - 1].key] || evidence3D.unknown)
          : evidence3D.unknown;
        const sideF = document.createElementNS(SVG_NS, "path");
        sideF.setAttribute(
          "d",
          `M ${currX} 8 L ${currX + 3} 4 L ${currX + 3} 20 L ${currX} 24 Z`
        );
        sideF.setAttribute("fill", lastPal.side);
        sSvg.append(sideF);

        // Bedrock foundation beneath stratum
        const bedF = document.createElementNS(SVG_NS, "rect");
        bedF.setAttribute("x", "6");
        bedF.setAttribute("y", "24");
        bedF.setAttribute("width", String(stratumW));
        bedF.setAttribute("height", "4");
        bedF.setAttribute("fill", getPalette().stoneFront);
        sSvg.append(bedF);

        const bedSide = document.createElementNS(SVG_NS, "path");
        bedSide.setAttribute(
          "d",
          `M ${currX} 24 L ${currX + 3} 20 L ${currX + 3} 24 L ${currX} 28 Z`
        );
        bedSide.setAttribute("fill", getPalette().stoneSide);
        sSvg.append(bedSide);
        stratumContainer.append(sSvg);

        // Fallback track for compatibility
        $("evidenceTrack").replaceChildren(...entries.map((entry) => {
          const segment = document.createElement("span");
          segment.className = "evidence-segment";
          segment.style.width = `${(entry.value / total) * 100}%`;
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

      function updateAnimState() {
        const isPaused = !animRunning || document.hidden;
        document.documentElement.classList.toggle("actors-paused", isPaused);
        const btn = $("animToggleBtn");
        if (btn) {
          btn.textContent = animRunning ? "⏸ Pause" : "▶ Play";
          btn.setAttribute(
            "aria-label",
            animRunning ? "Pause character animation" : "Play character animation"
          );
          btn.setAttribute("aria-pressed", String(!animRunning));
        }
      }

      function render() {
        renderMetrics();
        renderCalendar();
        renderDailyTable();
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

      // Preset buttons
      ["28d", "84d", "365d", "all"].forEach((preset) => {
        const btnId = preset === "all" ? "presetAll" : `preset${preset.slice(0, -1)}`;
        const btn = $(btnId);
        if (btn) {
          btn.addEventListener("click", () => {
            activePreset = preset;
            const r = computePresetRange(preset);
            currentStartDate = r.start;
            currentEndDate = r.end;
            lastValidStartDate = currentStartDate;
            lastValidEndDate = currentEndDate;
            $("customStartDate").value = currentStartDate;
            $("customEndDate").value = currentEndDate;
            $("dateRangeError").textContent = "";
            document.querySelectorAll(".range-btn[data-preset]").forEach((b) => {
              b.setAttribute("aria-pressed", String(b.dataset.preset === preset));
            });
            render();
          });
        }
      });

      // Apply custom range
      $("applyCustomRangeBtn").addEventListener("click", () => {
        const sVal = $("customStartDate").value;
        const eVal = $("customEndDate").value;
        const err = $("dateRangeError");
        if (!sVal || !eVal) {
          err.textContent = "Start and end dates are required.";
          return;
        }
        if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(sVal) ||
            !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(eVal)) {
          err.textContent = "Invalid date format.";
          $("customStartDate").value = lastValidStartDate;
          $("customEndDate").value = lastValidEndDate;
          return;
        }
        if (sVal > eVal) {
          err.textContent = "Invalid range: start date must precede or equal end date.";
          $("customStartDate").value = lastValidStartDate;
          $("customEndDate").value = lastValidEndDate;
          return;
        }
        if (sVal < minPublishableDate || eVal > maxPublishableDate) {
          err.textContent = "Dates must be within publishable extent (" +
            minPublishableDate + " to " + maxPublishableDate + ").";
          $("customStartDate").value = lastValidStartDate;
          $("customEndDate").value = lastValidEndDate;
          return;
        }
        err.textContent = "";
        activePreset = "custom";
        currentStartDate = sVal;
        currentEndDate = eVal;
        lastValidStartDate = sVal;
        lastValidEndDate = eVal;
        document.querySelectorAll(".range-btn[data-preset]").forEach((b) => {
          b.setAttribute("aria-pressed", "false");
        });
        render();
      });

      $("zoomToggleBtn").addEventListener("click", () => {
        isZoomed = !isZoomed;
        $("zoomToggleBtn").textContent = isZoomed ? "Zoom: Compact" : "Zoom: Standard";
        $("zoomToggleBtn").setAttribute("aria-pressed", String(isZoomed));
        renderCalendar();
      });

      $("animToggleBtn").addEventListener("click", () => {
        animRunning = !animRunning;
        updateAnimState();
      });

      document.addEventListener("visibilitychange", () => {
        updateAnimState();
      });

      window.addEventListener("resize", () => {
        renderCalendar();
      });

      document.querySelectorAll(".sort-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const col = btn.dataset.sort;
          if (sortCol === col) {
            sortDir = sortDir === "asc" ? "desc" : "asc";
          } else {
            sortCol = col;
            sortDir = "desc";
          }
          document.querySelectorAll(".sort-icon").forEach(el => el.textContent = "");
          const icon = $(`sortIcon-${col}`);
          if (icon) icon.textContent = sortDir === "asc" ? "▲" : "▼";
          renderDailyTable();
        });
      });

      window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          hideTooltip();
        }
      });

      $("snapshotDate").textContent = data.generated_on;
      $("snapshotDate").setAttribute("datetime", data.generated_on);
      $("periodLabel").textContent = data.period.label;
      $("schemaLabel").textContent = `schema ${data.schema_version}`;
      $("footSnapshot").textContent =
        `Snapshot ${data.generated_on} UTC · ${data.period.label} · aiprofile`;

      initDates();
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
    payload = (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    return _HTML_PREFIX + payload + _HTML_SUFFIX.replace(
        "__PROVIDER_GLYPHS__", _PROVIDER_GLYPHS_JSON
    ).replace("__VOXEL_ACTORS__", _ACTOR_BODIES_JSON)
