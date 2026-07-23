# Lottery IA Hardening Report

**Date:** 2026-07-22  
**Branch:** `feature/lottery-2.0`  
**Commit:** `7e78f23` (+ config restore `d632b1b`)

## Root cause of “redacción no disponible”

| Layer | Finding |
|-------|---------|
| Flag | `assistant_synthesis_enabled=true` |
| LLMRouter defaults | openai → claude |
| `openai_api_key` | empty |
| `anthropic` | 401 Unauthorized |
| `llm_provider_configs` rows | 0 |
| Effect | `LLMProviderError` → old fallback appended internal Spanish copy |

JAIOS already had working ModelArts credentials via Hermes (`HERMES_MODEL_API_URL` / `HERMES_MODEL_API_KEY`).

## Fix applied

1. **Primary:** LLMRouter (unchanged contract).
2. **Retry:** 2 attempts on transient failures.
3. **Secondary:** `_synthesize_via_hermes()` using existing Hermes/ModelArts settings (not a new LLM engine).
4. **Local natural templates** for all major tools (Spanish, concrete figures).
5. **Sanitize:** strip/reject internal phrases (`redacción no disponible`, `synthesis failed`, etc.).
6. User-facing fallback is the natural template only — never internal status text.

## UAT autenticado (post-hardening)

Evidence: `/var/jaios/lottery-bake/lottery-2.0-stageb-20260722/ai_uat_hardening/`

- **18/18 PASS**
- **internal_msgs = 0**
- `synthesis_fallback=false` on tool answers (Hermes synthesis succeeded)
- Q1 natural: “El 15 de marzo de 2022… 01, 19, 07”
- Wall latencies ~4–25s (dominated by ModelArts synthesis)

## Residual

- Real metadata 2099 still pollutes freshness answers until metadata repair is authorized (see `REAL_METADATA_2099_AUDIT.md`).
- OpenAI/Anthropic keys remain unset; Lottery IA depends on Hermes/ModelArts path for synthesis quality.
