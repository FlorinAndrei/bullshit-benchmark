# Bullshit Benchmark Analysis V2

Date: 2026-02-24

## Goals

- Evaluate response models with clean prompts (no response system prompt).
- Add explicit reasoning-level sweeps across all reasoning-capable response models.
- Reduce grading cost while preserving reliability (`2 judges + disagreement-only tiebreaker`).
- Exclude control-legitimate prompts from collection; benchmark is nonsense-only.
- Keep v1 workflow intact and add v2 mechanics as an optional path.

## Data-Driven Basis

Using `runs_live/live_noncontrol_allmodels_defaulttemp_20260221_201239`:

- 2-judge agreement was `0.8633` and Krippendorff alpha was `0.8368`.
- With 3 judges, average pairwise agreement was `0.8725` and alpha was `0.8408`.
- Primary judges disagreed on `205/1500` rows (`13.67%`).
- On those disagreement rows with a 3rd judge available, the 3rd judge resolved to one side in `198/201` rows (`98.51%`).

Interpretation: a full 3-judge pass has small global reliability gains, while targeted tiebreaking captures most of the value at lower cost.

Using OpenRouter live model metadata + acceptance probes on 2026-02-24:

- Reasoning-capable in current model set:
  - `anthropic/claude-opus-4.6`
  - `anthropic/claude-sonnet-4.6`
  - `anthropic/claude-opus-4.5`
  - `anthropic/claude-sonnet-4.5`
  - `anthropic/claude-haiku-4.5`
  - `google/gemini-3.1-pro-preview`
  - `google/gemini-3-flash-preview`
  - `x-ai/grok-4.1-fast`
  - `bytedance-seed/seed-1.6`
  - `openai/gpt-5.2`
  - `z-ai/glm-5`
  - `qwen/qwen3.5-397b-a17b`
  - `moonshotai/kimi-k2.5`
  - `minimax/minimax-m2.5`
- Not reasoning-capable in current set:
  - `baidu/ernie-4.5-300b-a47b`
- Provider-level caveat observed:
  - `google/gemini-3.1-pro-preview` and `minimax/minimax-m2.5` reject `none` (reasoning mandatory).
  - OpenRouter docs for Gemini 3 map `xhigh` down to `high`, so `xhigh` is not a distinct Gemini 3 test level.
  - For models without explicit `supported_reasoning_efforts` in metadata, v2 now uses a conservative cap (`none/low/medium/high`) instead of assuming `xhigh`.

Configured per-model efforts in `config.v2.json`:
- Anthropic 4.5/4.6: `none,low,medium,high,xhigh`
- Gemini 3.1 Pro: `low,medium,high`
- Gemini 3 Flash: `none,low,medium,high`
- xAI / ByteDance / OpenAI / Z.ai GLM / Qwen / Kimi: `none,low,medium,high`
- MiniMax M2.5: `low,medium,high`

## V2 Mechanics

### Collection

- `--omit-response-system-prompt` removes system message completely.
- `--response-reasoning-effort` sets one effort level for all models.
- `--model-reasoning-efforts` allows per-model effort sweeps via JSON.
- Model variants are tracked with explicit identity fields:
  - `model_org` (e.g., `openai`)
  - `model_name` (e.g., `gpt-5.2`)
  - `model_reasoning_level` (e.g., `high`)
  - `model_row` (e.g., `gpt-5.2@reasoning=high`)
- `model` stays as a unique display key (`org/model_row`) for leaderboard grouping.

### Grading

- New `grade-panel` command:
  - run 2 primary judges on all rows
  - identify disagreement rows
  - run tiebreaker only on disagreement rows
  - synthesize a full tiebreak grade file
  - run aggregate automatically

### Aggregation

- `majority` when tiebreaker is used
- `mean` for two-judge-only panels

## Integrity Hardening (Audit Updates)

- `sample_id` is now run-namespaced and collision-resistant for model variants.
- Collect defaults now avoid storing request messages and raw provider payloads unless explicitly enabled.
- Aggregate/report now enforce source consistency by checking `responses_file` lineage across grade/aggregate artifacts.
- Panel disagreement detection now includes rows where either primary judge failed to produce a valid score.
- Aggregate summaries now handle non-integer consensus values (for example, `mean`) correctly.

## Config

`config.v2.json` encodes the baseline v2 setup:

- `num_runs = 1` by default
- no response system prompt
- per-model reasoning sweeps for all reasoning-capable models in the set
- full `none,low,medium,high,xhigh` sweep where accepted
- model-specific caveats applied where required (for example, providers that reject `none`)
- judge panel defaults in `grade_panel`
