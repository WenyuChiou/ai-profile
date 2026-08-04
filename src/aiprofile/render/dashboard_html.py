"""Self-contained interactive dashboard renderer.

The dashboard is a pure function of the validated, privacy-safe ``VizStats``
contract. It never reads Git, SQLite, configuration, the clock, or the
network. All CSS, JavaScript, and aggregate data are embedded in one HTML
document so users may open it locally or publish it as a static page.
"""

from __future__ import annotations

import json

from ..viz import VizStats, to_json_dict
from .brand import BRAND
from .themes import MODEL_CATEGORY_COLORS

_PROVIDER_GLYPHS_JSON = json.dumps(
    {slug: spec.path for slug, spec in sorted(BRAND.items())},
    ensure_ascii=True,
    separators=(",", ":"),
    sort_keys=True,
)
_MODEL_CATEGORY_COLORS_JSON = json.dumps(
    MODEL_CATEGORY_COLORS,
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
  <title>AI collaboration evidence ledger</title>
  <style>
    :root {
      color-scheme: light;
      --canvas: #f3f7fb;
      --surface: #fbfdff;
      --surface-raised: #ffffff;
      --surface-subtle: #edf4fb;
      --surface-blue: #d9eaff;
      --border: #c2d3e5;
      --border-strong: #7590aa;
      --text: #172033;
      --muted: #52647a;
      --faint: #65758a;
      --accent: #005cc5;
      --model-accent: #3d5a80;
      --success: #1a7f37;
      --warning: #9a6700;
      --warning-strong: #7d4e00;
      --shadow: 0 16px 40px rgba(42, 76, 102, 0.10);
      --grid-empty: #e5eef7;
      --calendar-active-border: #52647a;
      --focus: #005cc5;
      --display: "IBM Plex Sans Condensed", "Aptos Display", "Segoe UI",
        "DejaVu Sans Condensed", "Liberation Sans Narrow", sans-serif;
      --body: "IBM Plex Sans", "Aptos", "Segoe UI", "Noto Sans",
        "DejaVu Sans", sans-serif;
      --mono: "IBM Plex Mono", "Cascadia Mono", "SFMono-Regular",
        "DejaVu Sans Mono", Consolas, monospace;
      --space-1: 0.25rem;
      --space-2: 0.5rem;
      --space-3: 0.75rem;
      --space-4: 1rem;
      --space-5: 1.25rem;
      --space-6: 1.5rem;
      --space-8: 2rem;
      --space-10: 2.5rem;
      --space-12: 3rem;
      --radius-sm: 0.25rem;
      --radius-md: 0.5rem;
      --radius-lg: 0.75rem;
    }

    @media (prefers-color-scheme: dark) {
      :root:not([data-theme="light"]) {
        color-scheme: dark;
        --canvas: #0b1625;
        --surface: #111923;
        --surface-raised: #142b45;
        --surface-subtle: #122a43;
        --surface-blue: #153756;
        --border: #34526f;
        --border-strong: #6683a0;
        --text: #eff6ff;
        --muted: #b5c7da;
        --faint: #9fb2c6;
        --accent: #8bc8ff;
        --model-accent: #9ecbff;
        --success: #3fb950;
        --warning: #eac54f;
        --warning-strong: #fae17d;
        --shadow: 0 18px 44px rgba(0, 0, 0, 0.32);
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
      --surface-blue: #153756;
      --border: #34526f;
      --border-strong: #6683a0;
      --text: #eff6ff;
      --muted: #b5c7da;
      --faint: #9fb2c6;
      --accent: #8bc8ff;
      --model-accent: #9ecbff;
      --success: #3fb950;
      --warning: #eac54f;
      --warning-strong: #fae17d;
      --shadow: 0 18px 44px rgba(0, 0, 0, 0.32);
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
    [tabindex="0"]:focus-visible {
      outline: 0.1875rem solid color-mix(in srgb, var(--focus) 55%, transparent);
      outline-offset: 0.1875rem;
    }

    .shell {
      width: min(100% - 2rem, 76rem);
      min-width: 0;
      margin: 0 auto;
      padding: clamp(2rem, 6vw, 5rem) 0 5rem;
    }

    .masthead {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: var(--space-12);
      align-items: start;
      margin-bottom: var(--space-12);
      padding-top: var(--space-5);
      border-top: 1px solid var(--border-strong);
    }

    .masthead > *,
    .hero-grid > *,
    .dashboard-grid > * {
      min-width: 0;
    }

    .eyebrow,
    .section-kicker {
      display: flex;
      gap: var(--space-2);
      align-items: center;
      margin: 0 0 var(--space-3);
      color: var(--muted);
      font-family: var(--mono);
      font-size: 0.8125rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      line-height: 1.4;
      text-transform: uppercase;
    }

    .eyebrow::before,
    .section-kicker::before {
      content: "";
      flex: 0 0 auto;
      width: 0.25rem;
      height: 0.75rem;
      border-radius: 0.125rem;
      background: var(--border-strong);
    }

    .eyebrow::after,
    .section-kicker::after {
      content: "";
      flex: 0 0 auto;
      width: 0.75rem;
      height: 1px;
      margin-left: -0.25rem;
      background: var(--border-strong);
    }

    .title {
      max-width: 17ch;
      margin: 0;
      font-family: var(--display);
      font-size: clamp(2.6rem, 5.8vw, 4.85rem);
      font-stretch: condensed;
      font-weight: 680;
      letter-spacing: -0.035em;
      line-height: 0.98;
      text-wrap: balance;
    }

    .lede {
      max-width: 44rem;
      margin: var(--space-5) 0 0;
      color: var(--muted);
      font-size: clamp(1rem, 1.8vw, 1.125rem);
      line-height: 1.68;
    }

    .utility {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: var(--space-3);
    }

    .theme-toggle {
      min-height: 2.75rem;
      padding: 0 var(--space-4);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      background: var(--surface-blue);
      color: var(--text);
      cursor: pointer;
      font-family: var(--mono);
      font-size: 0.8125rem;
      font-weight: 650;
      letter-spacing: 0.03em;
    }

    .theme-toggle:hover {
      border-color: var(--border-strong);
      background: var(--surface-raised);
    }

    .generated {
      color: var(--muted);
      padding-left: var(--space-4);
      border-left: 1px solid var(--border);
      font-family: var(--mono);
      font-size: 0.8125rem;
      line-height: 1.5;
      text-align: right;
    }

    .control-deck {
      position: sticky;
      z-index: 10;
      top: var(--space-3);
      display: flex;
      gap: var(--space-4);
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--space-8);
      padding: var(--space-4);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      background: var(--surface);
      box-shadow: var(--shadow);
    }

    .filter-label {
      flex: 0 0 auto;
      padding-left: var(--space-2);
      color: var(--muted);
      font-family: var(--mono);
      font-size: 0.8125rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .filters {
      display: flex;
      flex: 1 1 auto;
      gap: var(--space-2);
      overflow-x: auto;
      scrollbar-width: thin;
    }

    .filter {
      flex: 0 0 auto;
      min-height: 2.75rem;
      padding: 0 var(--space-4);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      background: var(--surface);
      color: var(--muted);
      cursor: pointer;
      font-size: 0.875rem;
      font-weight: 650;
      transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
    }

    .filter:hover {
      border-color: var(--provider-accent, var(--accent));
      color: var(--text);
    }

    .filter[aria-pressed="true"] {
      border-color: color-mix(in srgb, var(--provider-accent, var(--accent)) 72%, var(--border));
      background: color-mix(in srgb, var(--provider-accent, var(--accent)) 13%, var(--surface));
      color: var(--text);
      box-shadow:
        inset 0 0 0 1px
        color-mix(in srgb, var(--provider-accent, var(--accent)) 18%, transparent);
    }

    .provider-icon {
      display: inline-block;
      flex: 0 0 auto;
      width: 1rem;
      height: 1rem;
      color: var(--provider-accent, var(--accent));
      vertical-align: -0.14rem;
    }

    .filter .provider-icon {
      margin-right: var(--space-2);
    }

    .provider-icon--row {
      width: 1.25rem;
      height: 1.25rem;
      padding: 0.18rem;
      border: 1px solid color-mix(in srgb, var(--provider-accent) 38%, var(--border));
      border-radius: var(--radius-sm);
      background: color-mix(in srgb, var(--provider-accent) 10%, var(--surface));
    }

    .hero-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.7fr) minmax(17rem, 0.75fr);
      gap: var(--space-6);
      margin-bottom: var(--space-6);
    }

    .panel {
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      background: var(--surface);
    }

    .hero-panel {
      min-height: 22rem;
      padding: clamp(2rem, 4vw, 3rem);
      border-top: 0.25rem solid var(--active-accent, var(--accent));
      background: var(--surface);
    }

    .hero-label {
      margin: 0;
      color: var(--muted);
      font-size: 1rem;
      font-weight: 650;
      letter-spacing: 0.01em;
    }

    .hero-value {
      margin: var(--space-4) 0 0;
      color: var(--active-accent, var(--accent));
      font-family: var(--display);
      font-size: clamp(4.5rem, 11vw, 7.6rem);
      font-stretch: condensed;
      font-weight: 720;
      letter-spacing: -0.055em;
      line-height: 0.9;
    }

    .hero-context {
      max-width: 34rem;
      margin: var(--space-6) 0 0;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.62;
    }

    .share-track {
      width: min(100%, 34rem);
      height: 0.55rem;
      margin-top: var(--space-6);
      overflow: hidden;
      border-radius: 0.125rem;
      background: var(--grid-empty);
    }

    .share-fill {
      width: 0;
      height: 100%;
      border-radius: inherit;
      background: var(--active-accent, var(--accent));
      transition: width 420ms cubic-bezier(0.16, 1, 0.3, 1);
    }

    .hero-ratio {
      position: relative;
      z-index: 1;
      display: flex;
      justify-content: space-between;
      width: min(100%, 34rem);
      margin-top: var(--space-2);
      color: var(--faint);
      font-family: var(--mono);
      font-size: 0.8125rem;
    }

    .ledger {
      display: grid;
      grid-template-rows: repeat(3, 1fr);
      overflow: hidden;
    }

    .ledger-item {
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-height: 7rem;
      padding: var(--space-5) var(--space-6);
      border-bottom: 1px solid var(--border);
    }

    .ledger-item:first-child {
      background: color-mix(in srgb, var(--surface-blue) 44%, var(--surface));
    }

    .ledger-item:last-child {
      border-inline-start: 0.25rem solid var(--warning);
      background: var(--surface);
    }

    .ledger-item:last-child {
      border-bottom: 0;
    }

    .ledger-value {
      margin: 0;
      font-family: var(--mono);
      font-size: clamp(1.75rem, 4vw, 2.65rem);
      font-weight: 720;
      letter-spacing: -0.045em;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }

    .ledger-label {
      margin: var(--space-2) 0 0;
      color: var(--muted);
      font-size: 0.875rem;
      line-height: 1.5;
    }

    .ledger-detail {
      margin: var(--space-1) 0 0;
      color: var(--faint);
      font-size: 0.8125rem;
      line-height: 1.45;
    }

    .dashboard-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.55fr) minmax(19rem, 0.8fr);
      gap: var(--space-6);
      align-items: start;
    }

    .activity-panel,
    .providers-panel,
    .models-panel,
    .evidence-panel,
    .notes-panel {
      padding: clamp(1.5rem, 3vw, 2.25rem);
    }

    .activity-panel {
      min-width: 0;
      background: var(--surface);
    }

    .panel-heading {
      display: flex;
      gap: var(--space-4);
      align-items: end;
      justify-content: space-between;
      margin-bottom: var(--space-6);
    }

    .panel-title {
      margin: 0;
      font-family: var(--display);
      font-size: clamp(1.65rem, 3vw, 2.25rem);
      font-stretch: condensed;
      font-weight: 680;
      letter-spacing: -0.015em;
      line-height: 1.08;
    }

    .panel-meta {
      margin: 0;
      color: var(--muted);
      font-family: var(--mono);
      font-size: 0.8125rem;
      line-height: 1.5;
      text-align: right;
    }

    .calendar-scroll {
      width: 100%;
      min-width: 0;
      max-width: 100%;
      overflow-x: auto;
      padding: var(--space-2) var(--space-1) var(--space-4);
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
      transition: transform 120ms ease, border-color 120ms ease;
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
      min-height: 10rem;
      place-items: center;
      border: 1px dashed var(--border);
      border-radius: var(--radius-md);
      color: var(--muted);
      text-align: center;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-4);
      align-items: center;
      justify-content: space-between;
      margin-top: var(--space-4);
      color: var(--muted);
      font-size: 0.8125rem;
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
      gap: var(--space-3);
    }

    .models-panel {
      grid-column: 1 / -1;
    }

    .model-list {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: var(--space-4);
    }

    .model-row {
      display: grid;
      gap: var(--space-2);
      min-width: 0;
      padding: var(--space-3);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      background: var(--surface);
    }

    .model-row-head {
      display: flex;
      gap: var(--space-2);
      align-items: baseline;
      justify-content: space-between;
    }

    .model-name {
      display: inline-flex;
      gap: var(--space-2);
      align-items: center;
      color: var(--text);
      font-size: 0.9375rem;
      font-weight: 700;
    }

    .model-mark {
      display: inline-grid;
      width: 1.35rem;
      height: 1.35rem;
      flex: 0 0 auto;
      place-items: center;
      border: 1px solid var(--border);
      border-radius: 0.3rem;
      background: var(--grid-empty);
      color: var(--muted);
      font-family: var(--mono);
      font-size: 0.8125rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }

    .model-count {
      font-family: var(--mono);
      font-size: 0.875rem;
      font-weight: 700;
    }

    .model-track {
      height: 0.38rem;
      overflow: hidden;
      border-radius: 0.125rem;
      background: var(--grid-empty);
    }

    .model-fill {
      height: 100%;
      border-radius: inherit;
      background: var(--model-accent);
    }

    .model-detail {
      color: var(--muted);
      font-family: var(--mono);
      font-size: 0.8125rem;
      line-height: 1.5;
    }

    .model-empty {
      min-height: 4rem;
      padding: var(--space-3);
      border: 1px dashed var(--border);
      border-radius: var(--radius-md);
      color: var(--muted);
    }

    .providers-panel .panel-title {
      font-size: clamp(1.55rem, 2.5vw, 2rem);
    }

    .provider-row {
      display: grid;
      gap: var(--space-2);
      width: 100%;
      min-height: 4rem;
      padding: var(--space-3);
      border: 1px solid transparent;
      border-radius: var(--radius-md);
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
      font-size: 0.9375rem;
      font-weight: 700;
    }

    .provider-count {
      font-family: var(--mono);
      font-size: 0.875rem;
      font-weight: 700;
    }

    .provider-track {
      height: 0.38rem;
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
      font-family: var(--mono);
      font-size: 0.8125rem;
      line-height: 1.5;
    }

    .evidence-track {
      display: flex;
      height: 0.72rem;
      margin: var(--space-5) 0;
      overflow: hidden;
      border-radius: 0.125rem;
      background: var(--grid-empty);
    }

    .evidence-panel {
      display: grid;
      grid-column: 1 / -1;
      grid-template-columns: minmax(15rem, 0.62fr) minmax(0, 1.38fr);
      gap: var(--space-4) var(--space-8);
      align-items: center;
      border-top: 0.25rem solid var(--warning);
      background: var(--surface);
    }

    .evidence-panel .panel-heading {
      display: grid;
      grid-row: 1 / span 2;
      align-self: center;
      justify-content: stretch;
      margin-bottom: 0;
    }

    .evidence-panel .panel-meta {
      margin-top: var(--space-3);
      text-align: left;
    }

    .evidence-segment {
      min-width: 0;
      height: 100%;
    }

    .evidence-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: var(--space-3) var(--space-4);
    }

    .evidence-item {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: var(--space-2);
      align-items: center;
      min-width: 0;
      color: var(--muted);
      font-size: 0.8125rem;
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
      font-weight: 700;
    }

    .notes-panel {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: var(--space-8);
      margin-top: var(--space-4);
      border-top: 0.1875rem solid var(--border-strong);
      box-shadow: none;
    }

    .note-title {
      margin: 0 0 var(--space-2);
      font-family: var(--mono);
      font-size: 0.8125rem;
      font-weight: 750;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .note-copy {
      margin: 0;
      color: var(--muted);
      font-size: 0.875rem;
      line-height: 1.68;
    }

    .tooltip {
      position: fixed;
      z-index: 30;
      width: max-content;
      max-width: min(18rem, calc(100vw - 2rem));
      padding: var(--space-3) var(--space-4);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-sm);
      background: var(--surface-raised);
      box-shadow: var(--shadow);
      color: var(--text);
      font-size: 0.8125rem;
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
      font-weight: 750;
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

    @media (min-width: 38.01rem) {
      .provider-list {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 54rem) {
      .masthead,
      .hero-grid,
      .dashboard-grid {
        grid-template-columns: 1fr;
      }

      .utility {
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
      }

      .generated {
        text-align: left;
      }

      .ledger {
        grid-template-columns: repeat(3, 1fr);
        grid-template-rows: 1fr;
      }

      .ledger-item {
        min-height: 6.5rem;
        border-right: 1px solid var(--border);
        border-bottom: 0;
      }

      .ledger-item:last-child {
        border-right: 0;
      }

      .activity-panel {
        grid-row: auto;
      }

      .evidence-panel {
        display: block;
      }

      .models-panel {
        grid-column: auto;
      }

      .model-list {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .evidence-panel .panel-heading {
        display: flex;
        margin-bottom: var(--space-6);
      }

      .evidence-panel .panel-meta {
        margin-top: 0;
        text-align: right;
      }
    }

    @media (max-width: 38rem) {
      .shell {
        width: min(100% - 1rem, 74rem);
        padding-top: var(--space-6);
      }

      .masthead {
        gap: var(--space-5);
        margin-bottom: var(--space-8);
      }

      .title {
        overflow-wrap: anywhere;
        font-size: clamp(2.35rem, 11.5vw, 3.5rem);
      }

      .utility {
        flex-direction: column;
        align-items: flex-start;
      }

      .generated {
        max-width: 100%;
        overflow-wrap: anywhere;
      }

      .control-deck {
        position: static;
        display: grid;
        grid-template-columns: minmax(0, 1fr);
        width: 100%;
      }

      .filter-label {
        padding-left: 0;
      }

      .filters {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(5.25rem, 1fr));
        overflow-x: visible;
      }

      .filter {
        width: 100%;
        padding-inline: var(--space-2);
      }

      .hero-panel {
        min-height: 20rem;
      }

      .ledger {
        grid-template-columns: 1fr;
      }

      .ledger-item {
        min-height: 5.5rem;
        border-right: 0;
        border-bottom: 1px solid var(--border);
      }

      .panel-heading {
        display: grid;
      }

      .panel-meta {
        text-align: left;
      }

      .evidence-grid,
      .notes-panel,
      .model-list {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 22rem) {
      .filters {
        grid-template-columns: minmax(0, 1fr);
      }

      .hero-panel,
      .activity-panel,
      .providers-panel,
      .evidence-panel,
      .notes-panel {
        padding: var(--space-4);
      }

      .panel-heading > *,
      .provider-row {
        min-width: 0;
        max-width: 100%;
      }

      .panel-title,
      .panel-meta,
      .section-kicker,
      .provider-name,
      .provider-detail,
      .evidence-item {
        overflow-wrap: anywhere;
      }

      .evidence-panel .panel-heading {
        display: grid;
      }

      .evidence-panel .panel-meta {
        text-align: left;
      }

      .provider-row-head,
      .legend-scale {
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
      *,
      *::before,
      *::after {
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="masthead">
      <div>
        <p class="eyebrow">AI collaboration / evidence ledger</p>
        <h1 class="title">Evidence-backed AI collaboration.</h1>
        <p class="lede">
          Explicit Git provenance, aggregated locally. Review the published
          all-provider record or one participating AI provider without turning
          unrecorded history into a guess.
        </p>
      </div>
      <div class="utility">
        <button class="theme-toggle" id="themeToggle" type="button"
                aria-label="Theme: auto. Activate for light theme">Theme: auto</button>
        <div class="generated" id="generatedMeta"></div>
      </div>
    </header>

    <section class="control-deck" aria-label="Dashboard filters">
      <span class="filter-label">Provider view</span>
      <div class="filters" id="providerFilters" role="group"
           aria-label="Filter dashboard by AI provider"></div>
    </section>

    <p class="sr-only" id="selectionStatus" role="status" aria-live="polite"></p>

    <section class="hero-grid" aria-label="Selected collaboration summary">
      <article class="panel hero-panel" id="heroPanel">
        <p class="hero-label" id="heroLabel">AI-attributed commits</p>
        <p class="hero-value" id="heroValue">0</p>
        <p class="hero-context" id="heroContext"></p>
        <div class="share-track" aria-hidden="true">
          <div class="share-fill" id="shareFill"></div>
        </div>
        <div class="hero-ratio">
          <span id="shareText">0% of commits scanned</span>
          <span id="commitTotal">0 total</span>
        </div>
      </article>

      <aside class="panel ledger"
             aria-label="Collaboration metrics; unattributed commits remain all records">
        <div class="ledger-item">
          <p class="ledger-value" id="presenceValue">0</p>
          <p class="ledger-label" id="presenceLabel">AI actor presences</p>
        </div>
        <div class="ledger-item">
          <p class="ledger-value" id="daysValue">0</p>
          <p class="ledger-label">Active AI days</p>
        </div>
        <div class="ledger-item">
          <p class="ledger-value" id="unknownValue">0</p>
          <p class="ledger-label">Unattributed commits</p>
          <p class="ledger-detail">No explicit AI or human declaration recorded.</p>
        </div>
      </aside>
    </section>

    <section class="dashboard-grid">
      <article class="panel activity-panel">
        <div class="panel-heading">
          <div>
            <p class="section-kicker">Daily record</p>
            <h2 class="panel-title">Collaboration rhythm</h2>
          </div>
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
      </article>

      <article class="panel providers-panel">
        <div class="panel-heading">
          <div>
            <p class="section-kicker">Provider ledger</p>
            <h2 class="panel-title">Who participated</h2>
          </div>
          <p class="panel-meta">Attributed commits<br>not mutually exclusive</p>
        </div>
        <div class="provider-list" id="providerList"></div>
      </article>

      <article class="panel models-panel">
        <div class="panel-heading">
          <div>
            <p class="section-kicker">Explicit model evidence</p>
            <h2 class="panel-title">Model contribution</h2>
          </div>
          <p class="panel-meta">All AI view · family categories<br>not mutually exclusive</p>
        </div>
        <div class="model-list" id="modelList"></div>
      </article>

      <article class="panel evidence-panel">
        <div class="panel-heading">
          <div>
            <p class="section-kicker">All ACE records</p>
            <h2 class="panel-title">Evidence quality</h2>
          </div>
          <p class="panel-meta" id="evidenceTotal"></p>
        </div>
        <div class="evidence-track" id="evidenceTrack" aria-hidden="true"></div>
        <div class="evidence-grid" id="evidenceGrid"></div>
      </article>
    </section>

    <section class="panel notes-panel" aria-label="Metric and privacy definitions">
      <div>
        <h2 class="note-title">Unique commits</h2>
        <p class="note-copy">
          The all-provider view counts a commit once when at least one explicit AI actor
          is present. Provider totals may overlap when several actors share one commit.
        </p>
      </div>
      <div>
        <h2 class="note-title">Improve future attribution</h2>
        <p class="note-copy">
          Add an <code>AI-*</code> trailer to future commits. Historical commits without
          explicit evidence remain unattributed; they are never inferred from source-code style.
        </p>
      </div>
      <div>
        <h2 class="note-title">Privacy boundary</h2>
        <p class="note-copy" id="privacyCopy"></p>
      </div>
    </section>
  </main>

  <div class="tooltip" id="tooltip" role="tooltip" hidden></div>
  <script type="application/json" id="profileData">"""

_HTML_SUFFIX = """</script>
  <script>
    (() => {
      "use strict";

      const data = JSON.parse(document.getElementById("profileData").textContent);
      const providerGlyphs = __PROVIDER_GLYPHS__;
      const SVG_NS = "http:" + "//www.w3.org/2000/svg";
      const $ = (id) => document.getElementById(id);
      const number = new Intl.NumberFormat("en-US");
      const percent = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
      const modelMarks = {
        claude: "Cl",
        gpt: "Gp",
        gemini: "Ge",
        llama: "Ll",
        mistral: "Mi",
        deepseek: "Ds",
        qwen: "Qw",
        grok: "Gk",
        kimi: "Km",
        other: "+",
        unknown: "?"
      };
      // Stable category-keyed colours keep a family visually consistent when
      // the ledger gains a new row.  These are small categorical marks/bars;
      // labels and counts remain text-colour so colour is never the only
      // channel.  The neutral buckets intentionally share the model token.
      const modelColors = __MODEL_CATEGORY_COLORS__;
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

      function modelColor(category) {
        let mode = theme;
        if (mode === "auto") {
          mode = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark" : "light";
        }
        const palette = modelColors[mode === "dark" ? "github-dark" : "github-light"];
        const neutral = palette && palette.unknown
          ? palette.unknown : (mode === "dark" ? "#b5c7da" : "#52647a");
        return (palette && palette[category]) || neutral;
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

      function honestPercentLabel(numerator, denominator) {
        if (!denominator || numerator === 0) return "0%";
        if (numerator === denominator) return "100%";
        const rounded = Math.round((numerator / denominator) * 100);
        if (rounded === 0) return "<1%";
        if (rounded === 100) return ">99%";
        return `${rounded}%`;
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

      function renderHero() {
        const row = selectedRow();
        const commitCount = row ? row.attributed_commits : data.totals.ai_attributed_commits;
        const presenceCount = row ? row.actor_presences : data.totals.ai_actor_presences;
        const dayCount = row ? row.active_days : data.totals.active_ai_days;
        const denominator = data.totals.commits_scanned;
        const share = denominator ? (commitCount / denominator) * 100 : 0;
        const accent = selectedAccent();

        $("heroPanel").style.setProperty("--active-accent", accent);
        $("heroLabel").textContent = row
          ? `${row.display_name}-attributed commits`
          : "Unique AI-attributed commits";
        $("heroValue").textContent = number.format(commitCount);
        $("heroContext").textContent = row
          ? `${row.display_name} appears in ${number.format(commitCount)} unique commits. ` +
            "A commit may also include another AI provider."
          : `${number.format(commitCount)} commits contain at least one explicit AI actor. ` +
            "Each commit is counted once in this all-provider view.";
        $("shareFill").style.width = `${Math.min(100, share)}%`;
        $("shareText").textContent = `${percent.format(share)}% of commits scanned`;
        $("commitTotal").textContent = `${number.format(denominator)} total`;
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
      }

      function renderModels() {
        const list = $("modelList");
        if (!data.models.length) {
          const empty = document.createElement("div");
          empty.className = "model-empty";
          empty.textContent = data.totals.ai_actor_presences
            ? "No explicit model-family evidence published."
            : "No model contribution recorded yet.";
          list.replaceChildren(empty);
          return;
        }
        const max = Math.max(...data.models.map((row) => row.attributed_commits), 1);
        list.replaceChildren(...data.models.map((row) => {
          const item = document.createElement("div");
          item.className = "model-row";
          const head = document.createElement("div");
          head.className = "model-row-head";
          const name = document.createElement("span");
          name.className = "model-name";
          const mark = document.createElement("span");
          mark.className = "model-mark";
          mark.setAttribute("aria-hidden", "true");
          mark.textContent = modelMarks[row.category] || "?";
          const categoryColor = modelColor(row.category);
          mark.style.color = categoryColor;
          mark.style.borderColor = categoryColor;
          name.append(mark, document.createTextNode(row.display_name));
          const count = document.createElement("span");
          count.className = "model-count";
          count.textContent = number.format(row.attributed_commits);
          head.append(name, count);
          const track = document.createElement("div");
          track.className = "model-track";
          const fill = document.createElement("div");
          fill.className = "model-fill";
          fill.style.width = `${(row.attributed_commits / max) * 100}%`;
          fill.style.background = categoryColor;
          track.append(fill);
          const detail = document.createElement("div");
          detail.className = "model-detail";
          const denominator = data.totals.ai_attributed_commits;
          const share = honestPercentLabel(row.attributed_commits, denominator);
          detail.textContent = `${share} of ${number.format(denominator)} unique ` +
            `AI-attributed commits · ${number.format(row.actor_presences)} presences · ` +
            `${number.format(row.active_days)} active days`;
          item.append(head, track, detail);
          return item;
        }));
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
        renderHero();
        renderCalendar();
        renderModels();
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
      // changes. Re-render the small inline model marks as well so an `auto`
      // dashboard never leaves light categorical colours on a dark surface
      // (or the reverse). The legacy branch keeps this working in older
      // WebKit without adding a dependency or a network path.
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

      $("generatedMeta").textContent =
        `${data.period.label} · generated ${data.generated_on} UTC · schema ${data.schema_version}`;
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
    ).replace("__MODEL_CATEGORY_COLORS__", _MODEL_CATEGORY_COLORS_JSON)
