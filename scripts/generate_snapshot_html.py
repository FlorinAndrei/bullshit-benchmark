#!/usr/bin/env python3
"""Generate a self-contained benchmark snapshot HTML from benchmark artifacts."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a standalone benchmark snapshot HTML."
    )
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--aggregate-jsonl", required=False, default="")
    parser.add_argument("--manifest-json", required=False, default="")
    parser.add_argument("--output-html", required=True)
    return parser.parse_args()


def read_json(path: pathlib.Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    # Some historical artifacts may contain raw newlines inside quoted strings.
    # Parse as a stream of JSON objects and normalize in-string newlines to \\n.
    text = path.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    buf: list[str] = []
    depth = 0
    in_string = False
    escaped = False

    for index, ch in enumerate(text):
        if depth == 0:
            if ch.isspace():
                continue
            if ch != "{":
                raise ValueError(
                    f"Expected '{{' starting JSON object at {path} char {index}, got {ch!r}"
                )
            depth = 1
            buf = ["{"]
            in_string = False
            escaped = False
            continue

        if in_string:
            if escaped:
                buf.append(ch)
                escaped = False
                continue
            if ch == "\\":
                buf.append(ch)
                escaped = True
                continue
            if ch == "\"":
                buf.append(ch)
                in_string = False
                continue
            if ch == "\n":
                buf.append("\\n")
                continue
            if ch == "\r":
                buf.append("\\r")
                continue
            buf.append(ch)
            continue

        if ch == "\"":
            buf.append(ch)
            in_string = True
            continue
        if ch == "{":
            buf.append(ch)
            depth += 1
            continue
        if ch == "}":
            buf.append(ch)
            depth -= 1
            if depth == 0:
                candidate = "".join(buf)
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON object parsed from {path}: {exc}"
                    ) from exc
                if not isinstance(parsed, dict):
                    raise ValueError(f"Expected object JSON while parsing {path}")
                rows.append(parsed)
                buf = []
            continue

        buf.append(ch)

    if depth != 0 or buf:
        raise ValueError(f"Unclosed JSON object while parsing {path}")
    return rows


def main() -> int:
    args = parse_args()

    summary_path = pathlib.Path(args.summary_json)
    summary = read_json(summary_path)

    manifest: dict[str, Any] = {}
    if args.manifest_json:
        manifest_path = pathlib.Path(args.manifest_json)
        if manifest_path.exists():
            manifest = read_json(manifest_path)

    all_rows: list[dict[str, Any]] = []
    if args.aggregate_jsonl:
        aggregate_path = pathlib.Path(args.aggregate_jsonl)
        if not aggregate_path.exists():
            raise FileNotFoundError(f"Aggregate JSONL not found: {aggregate_path}")
        all_rows = read_jsonl(aggregate_path)

    payload_summary = json.dumps(summary, ensure_ascii=False).replace("</", "<\\/")
    payload_manifest = json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/")
    payload_rows = json.dumps(all_rows, ensure_ascii=False).replace("</", "<\\/")

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Bullshit Benchmark - Snapshot</title>
  <style>
    :root {{
      --bg: #f5f6f8;
      --panel: #fff;
      --ink: #1f2328;
      --muted: #66707a;
      --line: #dbe2e8;
      --shadow: 0 8px 24px rgba(16, 24, 40, 0.06);
      --radius: 12px;
      --green: #1f9d55;
      --amber: #c57a00;
      --red: #c13d36;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: \"Avenir Next\", \"Segoe UI\", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    .page {{
      width: min(1300px, 95vw);
      margin: 20px auto 36px;
      display: grid;
      gap: 12px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 14px;
    }}
    h1 {{
      margin: 0 0 4px;
      font-family: \"Rockwell\", \"Georgia\", serif;
      font-size: 1.45rem;
    }}
    h2 {{
      margin: 0 0 10px;
      font-family: \"Rockwell\", \"Georgia\", serif;
      font-size: 1.02rem;
    }}
    .muted {{ color: var(--muted); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 9px;
    }}
    .stat {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 9px;
      background: #fbfcfd;
    }}
    .k {{
      font-size: 0.76rem;
      color: var(--muted);
      text-transform: uppercase;
      margin-bottom: 4px;
      letter-spacing: 0.03em;
    }}
    .v {{
      font-size: 1.1rem;
      font-weight: 700;
      word-break: break-word;
    }}
    .filters {{
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr;
      gap: 8px;
      align-items: end;
      margin-bottom: 8px;
    }}
    .row-filters {{
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
      gap: 8px;
      align-items: end;
      margin-bottom: 8px;
    }}
    label {{
      display: grid;
      gap: 4px;
      font-size: 0.82rem;
      color: #3f4952;
    }}
    input, select, button {{
      border: 1px solid #c7d2da;
      border-radius: 9px;
      padding: 8px 9px;
      font-size: 0.9rem;
      background: #fff;
      color: var(--ink);
    }}
    button {{
      cursor: pointer;
      background: #f4f7fa;
    }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 10px;
      max-height: 620px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }}
    th, td {{
      text-align: left;
      padding: 8px 9px;
      border-bottom: 1px solid #edf1f5;
      white-space: nowrap;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 2;
      background: #f7fafc;
      color: #3f4952;
      font-size: 0.8rem;
    }}
    tr.row-clickable {{ cursor: pointer; }}
    tr.row-selected {{ background: #eef5ff; }}
    .pill {{
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.74rem;
      font-weight: 700;
      display: inline-block;
      min-width: 56px;
      text-align: center;
    }}
    .green {{ background: #e6f7ee; color: #107743; }}
    .amber {{ background: #fff3e0; color: #8a5a00; }}
    .red {{ background: #fde9e8; color: #9d2c26; }}
    .error {{ background: #f0f2f5; color: #5a6570; }}
    .pager {{
      margin-top: 8px;
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .detail-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      background: #fafbfc;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      max-height: 300px;
      overflow: auto;
      font-size: 0.82rem;
    }}
    .small {{ font-size: 0.82rem; }}
    @media (max-width: 980px) {{
      .stats {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .filters {{ grid-template-columns: 1fr 1fr; }}
      .row-filters {{ grid-template-columns: 1fr 1fr; }}
      .detail-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class=\"page\">
    <section class=\"panel\">
      <h1>Bullshit Benchmark - Snapshot</h1>
      <p class=\"muted\" id=\"metaLine\"></p>
    </section>

    <section class=\"panel\">
      <h2>At a Glance</h2>
      <div class=\"stats\" id=\"stats\"></div>
    </section>

    <section class=\"panel\">
      <h2>Leaderboard</h2>
      <div class=\"filters\">
        <label>
          <span>Search model</span>
          <input id=\"searchInput\" type=\"text\" placeholder=\"e.g. claude, gpt, gemini\">
        </label>
        <label>
          <span>Org</span>
          <select id=\"orgSelect\"></select>
        </label>
        <label>
          <span>Reasoning</span>
          <select id=\"reasoningSelect\"></select>
        </label>
        <label>
          <span>Sort</span>
          <select id=\"sortSelect\">
            <option value=\"avg_desc\">Avg score (high to low)</option>
            <option value=\"avg_asc\">Avg score (low to high)</option>
            <option value=\"green_desc\">Green rate (high to low)</option>
            <option value=\"red_asc\">Red rate (low to high)</option>
            <option value=\"model_asc\">Model (A-Z)</option>
          </select>
        </label>
      </div>
      <p class=\"muted\" id=\"tableMeta\"></p>
      <div class=\"table-wrap\">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Model</th>
              <th>Org</th>
              <th>Reasoning</th>
              <th>Avg</th>
              <th>Green</th>
              <th>Red</th>
              <th>2/1/0</th>
              <th>Rows</th>
              <th>Errors</th>
            </tr>
          </thead>
          <tbody id=\"tableBody\"></tbody>
        </table>
      </div>
    </section>

    <section class=\"panel\">
      <h2>All Rows</h2>
      <div class=\"row-filters\">
        <label>
          <span>Search row</span>
          <input id=\"rowSearchInput\" type=\"text\" placeholder=\"sample id, model, question id, technique\">
        </label>
        <label>
          <span>Model</span>
          <select id=\"rowModelSelect\"></select>
        </label>
        <label>
          <span>Technique</span>
          <select id=\"rowTechniqueSelect\"></select>
        </label>
        <label>
          <span>Band</span>
          <select id=\"rowBandSelect\">
            <option value=\"all\">All</option>
            <option value=\"green\">Green</option>
            <option value=\"amber\">Amber</option>
            <option value=\"red\">Red</option>
            <option value=\"error\">Error</option>
          </select>
        </label>
        <label>
          <span>Rows per page</span>
          <select id=\"rowPageSizeSelect\">
            <option value=\"25\">25</option>
            <option value=\"50\">50</option>
            <option value=\"100\" selected>100</option>
            <option value=\"250\">250</option>
          </select>
        </label>
      </div>
      <p class=\"muted\" id=\"rowMeta\"></p>
      <div class=\"table-wrap\" style=\"max-height: 460px;\">
        <table>
          <thead>
            <tr>
              <th>Sample</th>
              <th>Model</th>
              <th>QID</th>
              <th>Technique</th>
              <th>Score</th>
              <th>Band</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody id=\"rowTableBody\"></tbody>
        </table>
      </div>
      <div class=\"pager\">
        <button type=\"button\" id=\"prevPageBtn\">Prev</button>
        <span class=\"small muted\" id=\"pageLabel\"></span>
        <button type=\"button\" id=\"nextPageBtn\">Next</button>
      </div>
    </section>

    <section class=\"panel\">
      <h2>Selected Row Detail</h2>
      <p class=\"muted\" id=\"detailMeta\">Select a row above to inspect full response and judge notes.</p>
      <div class=\"detail-grid\">
        <div>
          <p class=\"small\"><strong>Question</strong></p>
          <pre id=\"detailQuestion\"></pre>
        </div>
        <div>
          <p class=\"small\"><strong>Nonsensical Element</strong></p>
          <pre id=\"detailNonsense\"></pre>
        </div>
      </div>
      <div style=\"margin-top: 10px;\">
        <p class=\"small\"><strong>Model Response</strong></p>
        <pre id=\"detailResponse\"></pre>
      </div>
      <div style=\"margin-top: 10px;\">
        <p class=\"small\"><strong>Judges</strong></p>
        <pre id=\"detailJudges\"></pre>
      </div>
      <div style=\"margin-top: 10px;\">
        <p class=\"small\"><strong>Raw Row JSON</strong></p>
        <pre id=\"detailJson\"></pre>
      </div>
    </section>
  </div>

  <script>
    const SUMMARY = {payload_summary};
    const MANIFEST = {payload_manifest};
    const ALL_ROWS = {payload_rows};

    const state = {{
      leaderboardRows: Array.isArray(SUMMARY.leaderboard) ? SUMMARY.leaderboard : [],
      allRows: Array.isArray(ALL_ROWS) ? ALL_ROWS : [],
      rowPage: 1,
      selectedSampleId: "",
    }};

    const el = {{}};

    function fmt(value, digits = 4) {{
      return Number.isFinite(value) ? Number(value).toFixed(digits) : "-";
    }}

    function pct(value) {{
      return Number.isFinite(value) ? `${{(value * 100).toFixed(1)}}%` : "-";
    }}

    function modelParts(modelLabel) {{
      const text = String(modelLabel || "");
      const slashIdx = text.indexOf("/");
      const org = slashIdx >= 0 ? text.slice(0, slashIdx) : "unknown";
      const match = text.match(/@reasoning=([^@]+)$/);
      const reasoning = match ? match[1] : "default";
      return {{ org, reasoning }};
    }}

    function uniqueSorted(values) {{
      return [...new Set(values)].sort((a, b) => String(a).localeCompare(String(b)));
    }}

    function fillSelect(select, values, allLabel = "All") {{
      const current = select.value;
      select.innerHTML = "";
      const allOpt = document.createElement("option");
      allOpt.value = "all";
      allOpt.textContent = allLabel;
      select.appendChild(allOpt);
      values.forEach((value) => {{
        const opt = document.createElement("option");
        opt.value = String(value);
        opt.textContent = String(value);
        select.appendChild(opt);
      }});
      if ([...select.options].some((opt) => opt.value === current)) {{
        select.value = current;
      }}
    }}

    function scoreBandForRow(row) {{
      const score = row ? row.consensus_score : null;
      if (row && row.status === "error") {{
        return {{ key: "error", label: "Error" }};
      }}
      if (!Number.isFinite(score)) {{
        return {{ key: "error", label: "Error" }};
      }}
      if (score >= 1.5) {{
        return {{ key: "green", label: "Green" }};
      }}
      if (score >= 0.5) {{
        return {{ key: "amber", label: "Amber" }};
      }}
      return {{ key: "red", label: "Red" }};
    }}

    function renderStats() {{
      const top = state.leaderboardRows[0] || null;
      const rel = SUMMARY.reliability || {{}};
      const items = [
        ["Models", state.leaderboardRows.length],
        ["Rows scored", SUMMARY.total_scored_records ?? "-"],
        ["Rows errors", SUMMARY.total_error_records ?? "-"],
        ["Pairwise agreement", pct(rel.average_pairwise_agreement)],
        ["Krippendorff alpha", fmt(rel.krippendorff_alpha_ordinal, 3)],
        ["Top model", top ? top.model : "-"],
      ];
      el.stats.innerHTML = items.map(([k, v]) => `
        <div class="stat">
          <div class="k">${{k}}</div>
          <div class="v">${{v}}</div>
        </div>
      `).join("");
    }}

    function filteredLeaderboardRows() {{
      const search = el.searchInput.value.trim().toLowerCase();
      const selectedOrg = el.orgSelect.value;
      const selectedReasoning = el.reasoningSelect.value;
      const sort = el.sortSelect.value;

      let rows = [...state.leaderboardRows];
      rows = rows.filter((row) => {{
        const model = String(row.model || "");
        const {{ org, reasoning }} = modelParts(model);
        if (selectedOrg !== "all" && org !== selectedOrg) return false;
        if (selectedReasoning !== "all" && reasoning !== selectedReasoning) return false;
        if (search && !model.toLowerCase().includes(search)) return false;
        return true;
      }});

      rows.sort((a, b) => {{
        if (sort === "avg_asc") return (a.avg_score ?? -999) - (b.avg_score ?? -999);
        if (sort === "green_desc") return (b.detection_rate_score_2 ?? -999) - (a.detection_rate_score_2 ?? -999);
        if (sort === "red_asc") return (a.full_engagement_rate_score_0 ?? 999) - (b.full_engagement_rate_score_0 ?? 999);
        if (sort === "model_asc") return String(a.model || "").localeCompare(String(b.model || ""));
        return (b.avg_score ?? -999) - (a.avg_score ?? -999);
      }});

      return rows;
    }}

    function renderLeaderboardTable() {{
      const rows = filteredLeaderboardRows();
      el.tableMeta.textContent = `Showing ${{rows.length}} leaderboard rows.`;
      el.tableBody.innerHTML = rows.map((row, idx) => {{
        const {{ org, reasoning }} = modelParts(row.model);
        return `
          <tr>
            <td>${{idx + 1}}</td>
            <td>${{row.model || ""}}</td>
            <td>${{org}}</td>
            <td>${{reasoning}}</td>
            <td>${{fmt(row.avg_score)}}</td>
            <td>${{pct(row.detection_rate_score_2)}}</td>
            <td>${{pct(row.full_engagement_rate_score_0)}}</td>
            <td>${{row.score_2 ?? 0}}/${{row.score_1 ?? 0}}/${{row.score_0 ?? 0}}</td>
            <td>${{row.nonsense_count ?? row.count ?? "-"}}</td>
            <td>${{row.error_count ?? 0}}</td>
          </tr>
        `;
      }}).join("");
    }}

    function filteredAllRows() {{
      const search = el.rowSearchInput.value.trim().toLowerCase();
      const modelFilter = el.rowModelSelect.value;
      const techniqueFilter = el.rowTechniqueSelect.value;
      const bandFilter = el.rowBandSelect.value;

      let rows = [...state.allRows];
      rows = rows.filter((row) => {{
        const model = String(row.model || "");
        const sampleId = String(row.sample_id || "");
        const qid = String(row.question_id || "");
        const technique = String(row.technique || "");
        if (modelFilter !== "all" && model !== modelFilter) return false;
        if (techniqueFilter !== "all" && technique !== techniqueFilter) return false;
        if (bandFilter !== "all" && scoreBandForRow(row).key !== bandFilter) return false;
        if (
          search
          && !model.toLowerCase().includes(search)
          && !sampleId.toLowerCase().includes(search)
          && !qid.toLowerCase().includes(search)
          && !technique.toLowerCase().includes(search)
        ) {{
          return false;
        }}
        return true;
      }});

      rows.sort((a, b) => {{
        const modelCmp = String(a.model || "").localeCompare(String(b.model || ""));
        if (modelCmp !== 0) return modelCmp;
        const runA = Number.isFinite(a.run_index) ? a.run_index : 0;
        const runB = Number.isFinite(b.run_index) ? b.run_index : 0;
        if (runA !== runB) return runA - runB;
        return String(a.question_id || "").localeCompare(String(b.question_id || ""));
      }});

      return rows;
    }}

    function getPageSize() {{
      const parsed = Number.parseInt(el.rowPageSizeSelect.value, 10);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : 100;
    }}

    function renderDetail(row) {{
      if (!row) {{
        el.detailMeta.textContent = "Select a row above to inspect full response and judge notes.";
        el.detailQuestion.textContent = "";
        el.detailNonsense.textContent = "";
        el.detailResponse.textContent = "";
        el.detailJudges.textContent = "";
        el.detailJson.textContent = "";
        return;
      }}

      const score = Number.isFinite(row.consensus_score) ? row.consensus_score.toFixed(3) : "-";
      el.detailMeta.textContent = `${{row.sample_id || ""}} | model=${{row.model || ""}} | question=${{row.question_id || ""}} | score=${{score}} | status=${{row.status || ""}}`;
      el.detailQuestion.textContent = String(row.question || "");
      el.detailNonsense.textContent = String(row.nonsensical_element || "");
      el.detailResponse.textContent = String(row.response_text || "");

      const judges = [];
      for (let index = 1; index <= 6; index += 1) {{
        const model = row[`judge_${{index}}_model`];
        const status = row[`judge_${{index}}_status`];
        const scoreValue = row[`judge_${{index}}_score`];
        const justification = row[`judge_${{index}}_justification`];
        const error = row[`judge_${{index}}_error`];
        if (model === undefined && status === undefined && scoreValue === undefined && !error) {{
          continue;
        }}
        judges.push(
          `Judge ${{index}}\\n`
          + `model: ${{model ?? ""}}\\n`
          + `status: ${{status ?? ""}}\\n`
          + `score: ${{scoreValue ?? ""}}\\n`
          + `justification: ${{justification ?? ""}}\\n`
          + `error: ${{error ?? ""}}`
        );
      }}

      el.detailJudges.textContent = judges.length ? judges.join("\\n\\n") : "No judge fields found in row.";
      el.detailJson.textContent = JSON.stringify(row, null, 2);
    }}

    function renderAllRowsTable() {{
      const rows = filteredAllRows();
      const pageSize = getPageSize();
      const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
      if (state.rowPage > totalPages) {{
        state.rowPage = totalPages;
      }}
      if (state.rowPage < 1) {{
        state.rowPage = 1;
      }}

      const start = (state.rowPage - 1) * pageSize;
      const end = start + pageSize;
      const pageRows = rows.slice(start, end);

      el.rowMeta.textContent = `Showing ${{pageRows.length}} rows (page ${{state.rowPage}}/${{totalPages}}) out of ${{rows.length}} filtered rows.`;
      el.pageLabel.textContent = `Page ${{state.rowPage}} of ${{totalPages}}`;

      el.rowTableBody.innerHTML = pageRows.map((row) => {{
        const score = Number.isFinite(row.consensus_score) ? row.consensus_score.toFixed(3) : "-";
        const band = scoreBandForRow(row);
        const selectedClass = String(row.sample_id || "") === state.selectedSampleId ? "row-selected" : "";
        return `
          <tr class="row-clickable ${{selectedClass}}" data-sample-id="${{String(row.sample_id || "")}}">
            <td>${{String(row.sample_id || "")}}</td>
            <td>${{String(row.model || "")}}</td>
            <td>${{String(row.question_id || "")}}</td>
            <td>${{String(row.technique || "")}}</td>
            <td>${{score}}</td>
            <td><span class="pill ${{band.key}}">${{band.label}}</span></td>
            <td>${{String(row.status || "")}}</td>
          </tr>
        `;
      }}).join("");

      if (state.selectedSampleId) {{
        const selectedRow = rows.find((row) => String(row.sample_id || "") === state.selectedSampleId)
          || state.allRows.find((row) => String(row.sample_id || "") === state.selectedSampleId)
          || null;
        renderDetail(selectedRow);
      }} else {{
        renderDetail(null);
      }}
    }}

    function init() {{
      el.metaLine = document.getElementById("metaLine");
      el.stats = document.getElementById("stats");

      el.searchInput = document.getElementById("searchInput");
      el.orgSelect = document.getElementById("orgSelect");
      el.reasoningSelect = document.getElementById("reasoningSelect");
      el.sortSelect = document.getElementById("sortSelect");
      el.tableMeta = document.getElementById("tableMeta");
      el.tableBody = document.getElementById("tableBody");

      el.rowSearchInput = document.getElementById("rowSearchInput");
      el.rowModelSelect = document.getElementById("rowModelSelect");
      el.rowTechniqueSelect = document.getElementById("rowTechniqueSelect");
      el.rowBandSelect = document.getElementById("rowBandSelect");
      el.rowPageSizeSelect = document.getElementById("rowPageSizeSelect");
      el.rowMeta = document.getElementById("rowMeta");
      el.rowTableBody = document.getElementById("rowTableBody");
      el.prevPageBtn = document.getElementById("prevPageBtn");
      el.nextPageBtn = document.getElementById("nextPageBtn");
      el.pageLabel = document.getElementById("pageLabel");

      el.detailMeta = document.getElementById("detailMeta");
      el.detailQuestion = document.getElementById("detailQuestion");
      el.detailNonsense = document.getElementById("detailNonsense");
      el.detailResponse = document.getElementById("detailResponse");
      el.detailJudges = document.getElementById("detailJudges");
      el.detailJson = document.getElementById("detailJson");

      const generatedAt = String(MANIFEST.generated_at_utc || SUMMARY.timestamp_utc || "").trim();
      const totalRows = Array.isArray(state.allRows) ? state.allRows.length : 0;
      el.metaLine.textContent = `Standalone snapshot | generated: ${{generatedAt || "n/a"}} | rows embedded: ${{totalRows}}`;

      fillSelect(el.orgSelect, uniqueSorted(state.leaderboardRows.map((row) => modelParts(row.model).org)));
      fillSelect(el.reasoningSelect, uniqueSorted(state.leaderboardRows.map((row) => modelParts(row.model).reasoning)));

      fillSelect(el.rowModelSelect, uniqueSorted(state.allRows.map((row) => String(row.model || ""))));
      fillSelect(el.rowTechniqueSelect, uniqueSorted(state.allRows.map((row) => String(row.technique || ""))));

      [el.searchInput, el.orgSelect, el.reasoningSelect, el.sortSelect].forEach((node) => {{
        node.addEventListener("input", renderLeaderboardTable);
        node.addEventListener("change", renderLeaderboardTable);
      }});

      [el.rowSearchInput, el.rowModelSelect, el.rowTechniqueSelect, el.rowBandSelect, el.rowPageSizeSelect].forEach((node) => {{
        const rerender = () => {{
          state.rowPage = 1;
          renderAllRowsTable();
        }};
        node.addEventListener("input", rerender);
        node.addEventListener("change", rerender);
      }});

      el.prevPageBtn.addEventListener("click", () => {{
        state.rowPage -= 1;
        renderAllRowsTable();
      }});
      el.nextPageBtn.addEventListener("click", () => {{
        state.rowPage += 1;
        renderAllRowsTable();
      }});

      el.rowTableBody.addEventListener("click", (event) => {{
        const target = event.target;
        if (!(target instanceof Element)) return;
        const tr = target.closest("tr[data-sample-id]");
        if (!tr) return;
        const sampleId = String(tr.getAttribute("data-sample-id") || "");
        if (!sampleId) return;
        state.selectedSampleId = sampleId;
        renderAllRowsTable();
      }});

      renderStats();
      renderLeaderboardTable();
      renderAllRowsTable();
    }}

    init();
  </script>
</body>
</html>
"""

    output_path = pathlib.Path(args.output_html)
    output_path.write_text(html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
