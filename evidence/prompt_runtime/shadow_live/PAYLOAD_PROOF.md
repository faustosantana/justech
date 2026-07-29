# PAYLOAD_PROOF — Prompt Runtime Shadow Live

**DEV image:** `jaios-app-backend:prompt-runtime-1.0-shadow-7769337`  
**Mode:** `shadow` · Studio enabled · `SHADOW_LLM=true` (during capture)  
**Active version:** `7.0.0-rc2` · id `45bf3281-a0c9-4792-80c4-9033d48d8f81`  
**Hash:** `e3389d1de28bdf78a4979a17c5d2ab7673e4d04607f280f02dc357ffddaf00a5`

## Demonstrated

| Check | Result |
|-------|--------|
| User-facing source | **legacy** (`prompt_source=legacy`, `legacy_prompt_used=true`) |
| Shadow prepared | **true** |
| Studio prompt hash | matches active rc2 hash |
| Same Evidence Package | **true** |
| User sees only legacy path answer | **yes** (interpretive template after guard on RAW) |
| Fallback to legacy on studio load failure | not triggered (`fallback_used=false` on selector) |
| PROD untouched | `lottery-routing3-rc1-2bf9c94` healthy |

## Latencies (proof turn)

- Legacy Huawei call ≈ **20.9s** (then factual guard failed → rich local template shown)
- Studio shadow call ≈ **32.6s**
- Total wall ≈ **55.9s**

## Note on forensics

With `SHADOW_LLM=true`, the second Huawei call may overwrite `04_prompt_compiled.txt` with the Studio system prompt. Selector metadata remains the source of truth for which prompt was user-facing (`legacy`).

## Artifact

See `PAYLOAD_PROOF.json` in this folder.
