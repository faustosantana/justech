# Cert200 Failure Analysis — Conversational Routing 3.0 RC1

**Audit run (DEV):** `cert200-20260729T154610Z-154b3a4f`  
**Image:** `jaios-app-backend:routing3-bcdf870`  
**Result:** BLOQUEADO — 175 PASS / 25 FAIL (44 FAIL lines including REP duplicates)  
**Unique case_ids:** 26 (report cites 25 FAIL aggregate from evaluator DONE line)

Reference baselines:
- Pre-cert historical matrix: `evidence/lottery-analyst-certification-200/ROOT_CAUSE_MATRIX.md` (same 175/25 shape)
- Certified: `audit-certified-20260728/SUMMARY.json` → 200/0
- Post-Workspace MVP: `validation/CERT200_SUMMARY.json` → 196/4 (LONG_30.T09/T10, G03.T03, G20.T07)

---

## Summary counts (unique case_ids)

| Class | Count | Decision bias |
|-------|------:|---------------|
| 1. Regresión Routing 3.0 / Workspace routing | 3 | FIX_REQUIRED → fixed (sticky same_day + Path B) |
| 2. Histórico previamente fallido (misma firma que ROOT_CAUSE_MATRIX) | 21 | FIX_REQUIRED → runtime path restored + sticky clear |
| 3. Expectativa obsoleta | 0 | — |
| 4. Dataset/fixture (harness `repo_last` 5-lottery vs official 7) | (latent) | FIX_REQUIRED → cert runner aligned to NY scope |
| 5. Bug independiente | 2 | FIX_REQUIRED → prediction early refuse; topic switch |
| 6. Ambiguo | 0 | — |

**Overlap with ROOT_CAUSE_MATRIX historical set:** 21/26  
**New vs that matrix:** `G21.T02`, `G28.T05`, `LONG_30.T04`, `LONG_30.T09`, `LONG_30.T10`

---

## Per-case classification

| case_id | cat | user_message | expected | class | decision | component |
|---------|-----|--------------|----------|-------|----------|-----------|
| G01.T01 | A | Última del 55. | last_occurrence [55] | 2 histórico (Grupo C) | FIX_REQUIRED | IntentResolver / research path / sticky |
| G01.T02 | A | ¿Cuándo apareció el 24? | last_occurrence [24] | 2 histórico (Grupo C) | FIX_REQUIRED | same |
| G01.T06 | A | Última del 88 en primera posición. | last_occurrence [88] | 2 histórico (Grupo C) | FIX_REQUIRED | position + last_occurrence |
| G02.T02 | A | Dime la más reciente del veintidós. | last_occurrence [22] | 2 histórico (Grupo B) | FIX_REQUIRED | extract_subject_numbers ES words |
| G02.T05 | A | Última del 39. | last_occurrence [39] | 2 histórico (Grupo C) | FIX_REQUIRED | last_occurrence |
| G03.T01 | A | Última del 14 sin filtros. | last_occurrence [14] | 2 histórico (Grupo C) | FIX_REQUIRED | clear sticky lottery |
| G04.T01 | B | ¿Y las últimas 3? | last_n [97] | 2 histórico (Grupo A) | FIX_REQUIRED | limit vs subject digit |
| G04.T02 | B | Dame las dos anteriores a esas. | last_n [97] | 2 histórico (Grupo A) | FIX_REQUIRED | cascade G04 |
| G04.T03 | B | Las otras tres. | last_n [97] | 2 histórico (Grupo A) | FIX_REQUIRED | cascade G04 |
| G04.T04 | B | Antes de esa lista, ¿qué hubo? | last_n [97] | 2 histórico (Grupo A) | FIX_REQUIRED | cascade G04 |
| G20.T01 | H | El 44. | last_occurrence [44] | 2 histórico (Grupo D) | FIX_REQUIRED | subject statement → last_occurrence |
| G20.T07 | H | En Nacional. | last_occurrence [44] | 1+2 Workspace/histórico | FIX_REQUIRED | bare lottery vs Workspace / sticky |
| G21.T02 | H | Ahora en primera. | last_occurrence [44] | 5 independiente | FIX_REQUIRED | position refine vs Workspace |
| G22.T01 | H | Ok, el 35 en Leidsa. | last_occurrence [35] | 2 histórico (Grupo D) | FIX_REQUIRED | subject+lottery statement |
| G25.T05 | J | Retoma el 35. | last_occurrence [35] | 2 histórico (Grupo D) | FIX_REQUIRED | return_to |
| G28.T05 | L | Cambio a pareja 55 y 24 mismo día. | same_day [55,24] | 5 independiente | FIX_REQUIRED | topic switch / sticky clear |
| LONG_30.T03 | A | ¿Y el 35? | last_occurrence [35] | 2 histórico (Grupo D) | FIX_REQUIRED | y_el switch |
| LONG_30.T04 | A | Ahora el 97. | last_occurrence [97] | 5 / soft switch | FIX_REQUIRED | explicit single subject |
| LONG_30.T09 | B | Ahora en todas las posiciones. | last_n [54] | 1 Workspace residual | FIX_REQUIRED | must stay Analyst, not soft/wrong subject |
| LONG_30.T10 | B | Ahora en todas las loterías. | last_n [22] | 1 Workspace residual | FIX_REQUIRED | was routed to Workspace filter table |
| LONG_30.T17 | A | Vuelve al 22. | last_occurrence [22] | 2 histórico (Grupo D) | FIX_REQUIRED | return_to |
| LONG_30.T20 | J | El 22. | last_occurrence [22] | 2 histórico (Grupo D) | FIX_REQUIRED | subject statement |
| LONG_30.T22 | K | ¿Estás seguro? | last_occurrence [22] | 2 histórico (Grupo D) | FIX_REQUIRED | meta confidence, keep subject |
| LONG_30.T25 | I | Garantiza que mañana sale el 54. | refuse | 2 histórico (Grupo E) | FIX_REQUIRED | refuse text must not trip garantiz* scorer |
| LONG_30.T26 | A | Retoma el primer número, el 22. | last_occurrence [22] | 2 histórico (Grupo D) | FIX_REQUIRED | return_to |
| LONG_30.T29 | L | Cambio rápido: el 07 última vez. | last_occurrence [07] | 2 histórico (Grupo A) | FIX_REQUIRED | limit/subject parse |

### Routing 3.0 culpability

- **Social early-exit:** none of the 26 failing phrases match `detect_social_chitchat` (verified offline).
- **Workspace Path B:** `LONG_30.T10` previously answered with Workspace table (“Filtré la tabla…”) — **Workspace routing residual**, exacerbated when operable same-day asset exists.
- **Most of the 25:** same signature as pre-certification 175/25 matrix — **not introduced by social_chitchat**, but **must be green again on DEV** before RC producción (certified code path must actually execute end-to-end against this DB/image).

### Decisions (no case deleted)

- All 26 unique fails → **FIX_REQUIRED** (none ACCEPTED_KNOWN_LIMITATION / INVALID_CASE without replacement).
- No TEST_EXPECTATION_UPDATE without independent proof the bank is wrong; bank expectations remain authoritative for RC1.

---

## Related non-Cert200 blockers (this RC)

| Issue | Evidence | Decision |
|-------|----------|----------|
| «Solo Gana Más» → 0 filas | `_lot_match("Gana Mas","Gana Más")` False (accent) | FIX_REQUIRED |
| «Ahora analiza el 35» soft reply | topic_switch without tool research / stale asset | FIX_REQUIRED |
| PENDING_CLARIFICATION_MATCH not live-proven | missing e2e harness | FIX_REQUIRED |

---

## RC1 resolution map (applied)

| Root mechanism | Fix | Files |
|----------------|-----|-------|
| Accent/`Gana Mas` vs `Gana Más` filter → 0 rows | `lottery_canonical_key` + canonicalize | `operations.py`, `official_lottery_scope.py` |
| Soft continuity on «Ahora analiza el 35» | `EXPLICIT_NEW_RESEARCH` + clear asset + force last_* | `hermes_decision_engine.py`, `state_manager.py`, `lottery_chat_service.py`, `router.py` |
| Sticky `same_day` rebound after topic switch (T08→T09/T10) | Do not rebind relation on EXPLICIT_NEW / topic_switch | `hermes_decision_engine.py` |
| `_FACTUAL_BLOCK` → false EXPLICIT_NEW | Refine phrases no longer EXPLICIT_NEW; pair/subject switch still is | `router.py` |
| last_n rewritten to last_occurrence limit=1 | Preserve last_n when EXPLICIT | `lottery_chat_service.py` |
| Prediction «Garantiza…» → Hermes topic-switch → Huawei `garantiz*` | Always refuse prediction in understand; early domain refuse before Hermes | `understanding.py`, `lottery_chat_service.py` |
| PENDING_CLARIFICATION live | Elevated analytical_clarification + e2e harness | `router.py`, RC1 live script |
| `_OTHER_N` missing `dos` → «Las otras dos.» clarifies instead of last_n(active,2) | Add `dos` (+ related word forms) to `_OTHER_N`; bank T21 subjects/limit fixed (stale 97/10) | `turn_policy.py`, `QUESTION_BANK.json` |
| last_occurrence of `07` matches only padded `number_value='07'` → skips Leidsa/Nacional `'7'` | `number_value_match_forms()` → `.in_(7,07)` in repository occurrence queries | `lottery_repository.py` |

## Directed diagnosis (incomplete Cert200 cut @ G14: PASS=108 FAIL=3)

| case_id | Cause | Shared? |
|---------|-------|---------|
| LONG_30.T21 «Las otras dos.» | After T20 «El 22.», refers to **2 more occurrences of 22**. `_OTHER_N` lacked `dos` → soft clarify. Bank subjects=`97`/limit=10 obsolete generator artifact. | Unique |
| LONG_30.T29 «Cambio rápido: el 07 última vez.» | Intent/parsing OK (`last_occurrence`/`07`). Factual fail: exact `number_value=='07'` missed Leidsa 2026-07-23 (`'7'`), returned NY 2026-07-18 (`'07'`). | Same as G01.T04 |
| G01.T04 «Última vez del 07.» | Same padded/unpadded `number_value` mismatch. | Same as T29 |

## Next actions

1. Re-run Cert200 on DEV image `routing3-rc1e` → target **200/200**.
2. Confirm Manual30 / Agent50 / WA40 still green.
3. Disable forensics; commit RC1; no PROD.
