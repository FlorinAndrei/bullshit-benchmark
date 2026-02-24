#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

for dir in runs share; do
  if [[ -d "${dir}" ]]; then
    rm -rf "${dir}"
    echo "Removed ${dir}/"
  fi
done

for dir in runs_*; do
  if [[ -d "${dir}" ]]; then
    rm -rf "${dir}"
    echo "Removed ${dir}/"
  fi
done

find . -maxdepth 1 -type f \( -name "tmp_*.json" -o -name "*_report.html" -o -name "*.zip" \) -print -delete

echo "Generated artifacts cleaned."
