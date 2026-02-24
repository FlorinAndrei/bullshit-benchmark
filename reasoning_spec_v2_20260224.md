# Benchmark V2 Reasoning Spec (Post-Debrief)

Date: 2026-02-24 (UTC)

## Scope

This document captures:
1. What went wrong in the reasoning-level setup and validation process.
2. What was corrected.
3. The current validated model + reasoning-level spec.
4. Quality gates required before any future production run.

Artifacts referenced in this debrief:
- `/Users/peter/bullshit-benchmark/runs_live/reasoning_matrix_live_20260224_nomax`
- `/Users/peter/bullshit-benchmark/share/reasoning_level_live_audit_20260224.md`
- `/Users/peter/bullshit-benchmark/share/reasoning_level_live_audit_20260224.json`
- `/Users/peter/bullshit-benchmark/share/reasoning_level_live_matrix_20260224.csv`

## Debrief: What Went Wrong

1. We initially assigned reasoning levels by assumption instead of verification.
- Some models do not support every level.
- Some models require reasoning to be enabled and reject `none`.
- Some models support `minimal` distinctly from `none`.

2. We had a normalization bug that collapsed `minimal` to `none`.
- This creates fake duplicates and invalidates reasoning-level sweeps.
- This is now fixed in code.

3. We used a token cap during validation (`--max-tokens 120` then `800`) that introduced false failures.
- Errors were `empty response_text` with `finish_reason=length`.
- This was not a reasoning-level compatibility failure.
- Validation now runs with no output cap (`max_tokens=0`, omitted from API payload).

4. Provider routing varied across reasoning levels for some models.
- OpenRouter may route different levels of the same model to different providers.
- This can confound level comparisons (you may compare provider differences, not just reasoning differences).

5. OpenAI coverage was incomplete at first.
- Additional OpenAI models were added to the config and validated.

## Corrections Applied

1. `minimal` no longer aliases to `none`.
- Code change in `scripts/openrouter_benchmark.py`.

2. Model list and per-model reasoning levels were reworked from live validation.
- Configs updated:
  - `/Users/peter/bullshit-benchmark/config.v2.json`
  - `/Users/peter/bullshit-benchmark/config.example.json`
  - `/Users/peter/bullshit-benchmark/config.json`

3. Anthropic older models are now run without explicit reasoning levels.
- As requested:
  - `anthropic/claude-opus-4.5`
  - `anthropic/claude-sonnet-4.5`
  - `anthropic/claude-opus-4.1`
  - `anthropic/claude-sonnet-4`
  - `anthropic/claude-haiku-4.5`
- These use `reasoning=default` (no explicit `reasoning` object).

4. Live matrix run completed across all configured model rows with full raw logging.
- Run: `/Users/peter/bullshit-benchmark/runs_live/reasoning_matrix_live_20260224_nomax`
- Result: `62/62` valid responses, `0` errors.
- Pair integrity: `62 expected`, `62 actual`, `0 missing`, `0 unexpected`, `0 duplicates`.

## Current Validated Spec

Questions source:
- `questions_v2.json`

Collection behavior:
- omit response system prompt: `true`
- response reasoning default: `off`
- per-model reasoning map only
- store request messages: enabled for validation runs
- store raw response payload: enabled for validation runs

### Model Matrix (Current)

Anthropic:
- `anthropic/claude-opus-4.6`: `none`
- `anthropic/claude-sonnet-4.6`: `none`
- `anthropic/claude-opus-4.5`: `default`
- `anthropic/claude-sonnet-4.5`: `default`
- `anthropic/claude-opus-4.1`: `default`
- `anthropic/claude-sonnet-4`: `default`
- `anthropic/claude-haiku-4.5`: `default`

Google:
- `google/gemini-3.1-pro-preview`: `low, medium, high`
- `google/gemini-3-flash-preview`: `none, low, medium, high`

xAI:
- `x-ai/grok-4.1-fast`: `none, low, medium, high`

Bytedance Seed:
- `bytedance-seed/seed-1.6`: `none, low, medium, high`

OpenAI:
- `openai/gpt-5.2`: `none, low, medium, high, xhigh`
- `openai/gpt-5.2-pro`: `minimal, low, medium, high, xhigh`
- `openai/gpt-5.1`: `none, low, medium, high`
- `openai/gpt-5-mini`: `minimal, low, medium, high`
- `openai/o3`: `low, medium, high`
- `openai/o4-mini`: `low, medium, high`

Other:
- `z-ai/glm-5`: `none, low, medium, high`
- `baidu/ernie-4.5-300b-a47b`: `default`
- `qwen/qwen3.5-397b-a17b`: `none, low, medium, high`
- `moonshotai/kimi-k2.5`: `none, low, medium, high`
- `minimax/minimax-m2.5`: `low, medium, high`

Totals:
- base models: `22`
- model rows: `62`

## Reasoning-Level Signal Check (From Live Run)

What we checked:
1. Every configured pair returned a valid response.
2. Response hashes differed across levels for sweeped models (no immediate duplicate-level collapse).
3. Reasoning-token metrics (where exposed by provider) varied across levels for sweeped models.

Observed outcome:
- No suspicious normalization signal was detected by our current heuristics.
- Important caveat: one-question validation is a compatibility check, not a behavioral benchmark.

## Provider-Routing Confound (Still Open)

Models that used multiple providers across their tested levels in the live run:
- `google/gemini-3-flash-preview`
- `minimax/minimax-m2.5`
- `moonshotai/kimi-k2.5`
- `qwen/qwen3.5-397b-a17b`
- `z-ai/glm-5`

Impact:
- Cross-level comparisons for these models are not fully clean unless provider routing is controlled.

Required fix for strict science:
- Add provider pinning support in requests (`provider.order` + `allow_fallbacks=false`) for sweeped models.
- Keep `require_parameters=true` when reasoning is explicitly set.

## Mandatory Gates Before Production Benchmark Runs

Gate A: Compatibility matrix
- Run one-question matrix over all configured model rows.
- Must pass `100%` valid rows.

Gate B: Pair integrity
- Actual `(model_id, reasoning_level)` set must exactly equal configured set.
- No missing or duplicate pairs.

Gate C: No artificial truncation
- Do not set `--max-tokens` for compatibility validation.

Gate D: Routing sanity
- For models with reasoning sweeps, prefer single-provider routing.
- If not pinned, mark those model-level comparisons as provider-confounded.

Gate E: Logging
- Validation runs must include:
  - `--store-request-messages`
  - `--store-response-raw`

## Recommended Next Changes

Priority 1:
- Implement model-level provider preference/pinning in collect.

Priority 2:
- Add an automated preflight command that executes gates A-E and outputs a pass/fail report.

Priority 3:
- If needed, reduce sweep levels for models with weak separation signal after multi-question probing.

## OpenRouter Model Availability Note

As of 2026-02-24, `x-ai/grok-4.2` is not present in OpenRouter's live models API.
Current xAI entries include `x-ai/grok-4.1-fast`, `x-ai/grok-4-fast`, `x-ai/grok-4`, etc.

## Reference Links

- OpenRouter models API: `https://openrouter.ai/api/v1/models`
- OpenRouter provider routing docs: `https://openrouter.ai/docs/guides/routing/provider-selection`
- OpenRouter reasoning docs: `https://openrouter.ai/docs/use-cases/reasoning-tokens`
- Claude 4.6 migration notes: `https://openrouter.ai/docs/guides/guides/model-migrations/claude-4-6`
