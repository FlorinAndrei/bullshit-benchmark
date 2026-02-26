# CLAUDE.md

## Project Overview

Bullshit Benchmark: tests whether LLMs detect and push back on nonsensical prompts instead of confidently answering them.

## Architecture

- `scripts/openrouter_benchmark.py` — core CLI with subcommands: `collect`, `grade`, `grade-panel`, `aggregate`, `report`, `regenerate-summary`
- `scripts/run_end_to_end.sh` — full pipeline: collect → grade-panel → publish
- `scripts/publish_latest_to_viewer.sh` — publish artifacts to `data/latest/` (supports `--merge`)
- `config.json` — canonical config for models, judges, and grading parameters
- `questions.json` — benchmark question set (55 questions, v2.0)
- `viewer/index.html` — static HTML viewer, reads from `data/latest/`
- `data/latest/` — published dataset used by the viewer

## Pipeline

1. **Collect** — query models with benchmark questions, save responses to `runs/<run-id>/responses.jsonl`
2. **Grade-panel** — judge models (on OpenRouter) score each response 0-2, output in `runs/<run-id>/grade_panels/`
3. **Publish** — copy/merge artifacts into `data/latest/` for the viewer

## Key Endpoints

- Collect step supports any OpenAI-compatible endpoint via `--collect-endpoint`
- Grade step always uses OpenRouter (`OPENROUTER_API_KEY` required)
- Ollama support via `--ollama-mode` (sequential models, unload between, parallelism=1)

## Environment Variables

- `OPENROUTER_API_KEY` — required for grading (and for collect when using OpenRouter)
- `COLLECT_API_KEY` — optional, for non-OpenRouter collect endpoints
- `OPENROUTER_REFERER`, `OPENROUTER_APP_NAME` — optional OpenRouter metadata

## Common Commands

```bash
# Full run against OpenRouter
./scripts/run_end_to_end.sh

# Collect from Ollama, grade on OpenRouter, merge into viewer
./scripts/run_end_to_end.sh \
  --collect-endpoint http://<host>:11434/v1 \
  --ollama-mode \
  --models llama3:70b,mistral:7b \
  --merge

# Collect only (no grading, no OpenRouter key needed)
python3 scripts/openrouter_benchmark.py collect \
  --collect-endpoint http://<host>:11434/v1 \
  --ollama-mode \
  --models llama3:70b

# Grade a previous collect run
python3 scripts/openrouter_benchmark.py grade-panel \
  --responses-file runs/<run-id>/responses.jsonl \
  --no-fail-on-error

# Publish with merge
./scripts/publish_latest_to_viewer.sh \
  --responses-file <path> \
  --collection-stats <path> \
  --panel-summary <path> \
  --aggregate-summary <path> \
  --aggregate-rows <path> \
  --merge

# Serve viewer locally
python3 -m http.server 8877
# then open http://localhost:8877/viewer/index.html
```

## Config Notes

- `judge_max_tokens` in config.json controls max output tokens for judge calls. Default 0 means "provider default" which can be 65536 — set to 2048 to avoid OpenRouter credit reservation issues.
- `model_reasoning_efforts` in the collect section is ignored for non-OpenRouter endpoints.
- Publish `--merge` deduplicates by `(model, question_id, run_index)` — new rows overwrite old.

## Code Conventions

- Python script uses `urllib` directly (no requests/httpx dependency)
- Shell scripts use inline Python heredocs for data processing
- JSONL files may contain Unicode line separators inside JSON strings — use `split("\n")` not `splitlines()`
- `OpenRouterClient` class supports any OpenAI-compatible endpoint despite its name
