# Prompt50 Report — Shadow Live (DEV)

**Date:** 2026-07-29  
**Image:** `jaios-app-backend:prompt-runtime-1.0-shadow-7769337`  
**Mode:** shadow (user-facing legacy)

## Summary

| Metric | Value |
|--------|-------|
| Cases | 50/50 executed |
| Routing: workspace (`C*`) | `investigation_workspace` |
| Routing: social (`D*`) | local / no Huawei |
| Routing: prediction (`E*`) | local refuse |
| Routing: security (`J*`) | local |
| Huawei-eligible research (`A*`) | `huawei_modelarts` |
| Telemetry `with_shadow` in first harness | 0 (telemetry field missing until hotpatch) |
| Proof turn after telemetry hotpatch | shadow comparison present |

## Routing integrity (visible)

No Workspace→narrative contamination observed on `Muéstrame las fechas` cases (provider `investigation_workspace`).  
Social / prediction refuse stayed off Huawei.

## Studio quality (proof sample)

Studio same-day answer cited **134** (matches legacy template total) but failed factual guard on **extra_subjects** (`51`,`60`,`83`) — Studio verbosity invents related numbers.  
**Not ready for visible studio mode.**

## Recommendation

Keep **shadow** on DEV; correct Studio content / length before visible activation. Re-run Prompt50 with telemetry after image bake including `to_telemetry` prompt_runtime fields.
