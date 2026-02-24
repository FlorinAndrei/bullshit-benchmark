#!/usr/bin/env python3
"""Generate a standalone copy of viewer/index.html with embedded canonical dataset files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate standalone index explorer HTML.")
    parser.add_argument(
        "--source-html",
        default="viewer/index.html",
        help="Path to source index HTML.",
    )
    parser.add_argument("--responses-jsonl", required=True, help="Path to responses.jsonl")
    parser.add_argument("--collection-stats-json", required=True, help="Path to collection_stats.json")
    parser.add_argument("--panel-summary-json", required=True, help="Path to panel_summary.json")
    parser.add_argument("--aggregate-summary-json", required=True, help="Path to aggregate_summary.json")
    parser.add_argument("--aggregate-jsonl", required=True, help="Path to aggregate.jsonl")
    parser.add_argument("--manifest-json", required=False, help="Path to manifest.json")
    parser.add_argument(
        "--output-html",
        default="viewer/index_standalone.html",
        help="Path to write standalone HTML.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def canonicalize_key(path: str) -> list[str]:
    key = path.replace("\\", "/").strip()
    keys = [key]
    stripped = key.lstrip("./")
    if stripped not in keys:
        keys.append(stripped)
    if stripped.startswith("viewer/"):
        short = stripped[len("viewer/") :]
        if short not in keys:
            keys.append(short)
    else:
        with_viewer = f"viewer/{stripped}"
        if with_viewer not in keys:
            keys.append(with_viewer)
    return keys


def build_embedded_map(args: argparse.Namespace) -> dict[str, str]:
    file_pairs = [
        (args.responses_jsonl, "viewer/data/latest/responses.jsonl"),
        (args.collection_stats_json, "viewer/data/latest/collection_stats.json"),
        (args.panel_summary_json, "viewer/data/latest/panel_summary.json"),
        (args.aggregate_summary_json, "viewer/data/latest/aggregate_summary.json"),
        (args.aggregate_jsonl, "viewer/data/latest/aggregate.jsonl"),
    ]

    if args.manifest_json:
        file_pairs.append((args.manifest_json, "viewer/data/latest/manifest.json"))

    embedded: dict[str, str] = {}
    for source, target_key in file_pairs:
        content = read_text(Path(source))
        for key in canonicalize_key(target_key):
            embedded[key] = content
    return embedded


def inject_embedded_data(source_html: str, embedded: dict[str, str]) -> str:
    payload = json.dumps(embedded, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    injection = (
        "  <script>\n"
        "    window.__BULLSHIT_BENCHMARK_EMBEDDED_FILES__ = "
        f"{payload};\n"
        "  </script>\n\n"
    )

    marker = "  <script>\n    const DEFAULT_PATHS = {"
    idx = source_html.find(marker)
    if idx == -1:
        marker = "<script>"
        idx = source_html.find(marker)
        if idx == -1:
            raise RuntimeError("Could not find <script> tag in source HTML")
    return source_html[:idx] + injection + source_html[idx:]


def main() -> int:
    args = parse_args()
    source_path = Path(args.source_html)
    output_path = Path(args.output_html)

    source_html = read_text(source_path)
    embedded_map = build_embedded_map(args)
    standalone_html = inject_embedded_data(source_html, embedded_map)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(standalone_html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
