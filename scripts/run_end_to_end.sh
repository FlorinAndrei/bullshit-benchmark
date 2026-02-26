#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_end_to_end.sh [options]

Runs the full benchmark flow:
  1) collect
  2) grade-panel
  3) publish latest viewer dataset

Options:
  --config <path>              Config file (default: config.json)
  --output-dir <dir>           Output base dir (default: runs)
  --run-id <id>                Explicit run id (default: auto timestamp)
  --panel-id <id>              Explicit panel id (default: <run-id>_panel)
  --models <list>              Comma-separated model list (overrides config.json)
  --collect-endpoint <url>     OpenAI-compatible endpoint for collect (default: OpenRouter)
  --collect-api-key <key>      API key for collect endpoint (not needed for Ollama)
  --ollama-mode                Sequential model execution with unload between models
  --merge                      Merge new results into existing viewer data instead of replacing
  --dry-run                    Pass --dry-run to collect and grade-panel
  --serve                      Start local HTTP server after publish
  --port <port>                HTTP server port for --serve (default: 8877)
  -h, --help                   Show this help
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

CONFIG_PATH="config.json"
OUTPUT_DIR="runs"
RUN_ID=""
PANEL_ID=""
MODELS=""
COLLECT_ENDPOINT=""
COLLECT_API_KEY=""
OLLAMA_MODE=0
MERGE=0
DRY_RUN=0
SERVE=0
PORT=8877

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG_PATH="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --run-id)
      RUN_ID="${2:-}"
      shift 2
      ;;
    --panel-id)
      PANEL_ID="${2:-}"
      shift 2
      ;;
    --models)
      MODELS="${2:-}"
      shift 2
      ;;
    --collect-endpoint)
      COLLECT_ENDPOINT="${2:-}"
      shift 2
      ;;
    --collect-api-key)
      COLLECT_API_KEY="${2:-}"
      shift 2
      ;;
    --ollama-mode)
      OLLAMA_MODE=1
      shift
      ;;
    --merge)
      MERGE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --serve)
      SERVE=1
      shift
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Config file not found: ${CONFIG_PATH}" >&2
  exit 1
fi

if [[ "${DRY_RUN}" -ne 1 ]]; then
  if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    if [[ -z "${COLLECT_ENDPOINT}" ]]; then
      echo "OPENROUTER_API_KEY is required unless --collect-endpoint or --dry-run is used." >&2
      exit 1
    else
      echo "Warning: OPENROUTER_API_KEY not set. Collect will use ${COLLECT_ENDPOINT}." >&2
      echo "         Grade-panel will fail unless OPENROUTER_API_KEY is set." >&2
    fi
  fi
fi

if [[ -z "${RUN_ID}" ]]; then
  RUN_ID="run_$(date -u +%Y%m%d_%H%M%S)"
fi
if [[ -z "${PANEL_ID}" ]]; then
  PANEL_ID="${RUN_ID}_panel"
fi

RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
PANEL_DIR="${RUN_DIR}/grade_panels/${PANEL_ID}"
RESPONSES_FILE="${RUN_DIR}/responses.jsonl"
COLLECTION_STATS_FILE="${RUN_DIR}/collection_stats.json"
PANEL_SUMMARY_FILE="${PANEL_DIR}/panel_summary.json"

collect_cmd=(
  python3 scripts/openrouter_benchmark.py collect
  --config "${CONFIG_PATH}"
  --output-dir "${OUTPUT_DIR}"
  --run-id "${RUN_ID}"
)
if [[ -n "${MODELS}" ]]; then
  collect_cmd+=(--models "${MODELS}")
fi
if [[ -n "${COLLECT_ENDPOINT}" ]]; then
  collect_cmd+=(--collect-endpoint "${COLLECT_ENDPOINT}")
fi
if [[ -n "${COLLECT_API_KEY}" ]]; then
  collect_cmd+=(--collect-api-key "${COLLECT_API_KEY}")
fi
if [[ "${OLLAMA_MODE}" -eq 1 ]]; then
  collect_cmd+=(--ollama-mode)
fi
if [[ "${DRY_RUN}" -eq 1 ]]; then
  collect_cmd+=(--dry-run)
fi

echo "==> Collect: ${RUN_ID}"
"${collect_cmd[@]}"

panel_cmd=(
  python3 scripts/openrouter_benchmark.py grade-panel
  --config "${CONFIG_PATH}"
  --responses-file "${RESPONSES_FILE}"
  --output-dir "${RUN_DIR}"
  --panel-id "${PANEL_ID}"
)
if [[ "${DRY_RUN}" -eq 1 ]]; then
  panel_cmd+=(--dry-run)
fi
panel_cmd+=(--no-fail-on-error)

echo "==> Grade panel: ${PANEL_ID}"
"${panel_cmd[@]}"

if [[ ! -f "${PANEL_SUMMARY_FILE}" ]]; then
  echo "Panel summary not found: ${PANEL_SUMMARY_FILE}" >&2
  exit 1
fi

AGGREGATE_DIR="$(
  python3 - <<'PY' "${PANEL_SUMMARY_FILE}"
import json
import pathlib
import sys

panel_summary_path = pathlib.Path(sys.argv[1])
payload = json.loads(panel_summary_path.read_text(encoding="utf-8"))
aggregate_dir = str(payload.get("aggregate_dir", "")).strip()
print(aggregate_dir)
PY
)"

if [[ -z "${AGGREGATE_DIR}" ]]; then
  echo "aggregate_dir missing in ${PANEL_SUMMARY_FILE}" >&2
  exit 1
fi

AGGREGATE_SUMMARY_FILE="${AGGREGATE_DIR}/aggregate_summary.json"
AGGREGATE_ROWS_FILE="${AGGREGATE_DIR}/aggregate.jsonl"

echo "==> Publish viewer dataset"
publish_cmd=(
  ./scripts/publish_latest_to_viewer.sh
  --responses-file "${RESPONSES_FILE}"
  --collection-stats "${COLLECTION_STATS_FILE}"
  --panel-summary "${PANEL_SUMMARY_FILE}"
  --aggregate-summary "${AGGREGATE_SUMMARY_FILE}"
  --aggregate-rows "${AGGREGATE_ROWS_FILE}"
)
if [[ "${MERGE}" -eq 1 ]]; then
  publish_cmd+=(--merge)
fi
"${publish_cmd[@]}"

echo ""
echo "Complete."
echo "Run ID: ${RUN_ID}"
echo "Panel ID: ${PANEL_ID}"
echo "Viewer data: ${ROOT_DIR}/data/latest"
echo "Open UI after serving:"
echo "  /viewer/index.html"

if [[ "${SERVE}" -eq 1 ]]; then
  echo ""
  echo "Starting local server on port ${PORT}..."
  python3 -m http.server "${PORT}"
fi
