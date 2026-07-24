# GIT_CHANGE_CLASSIFICATION — I-6.5

Generado: 2026-07-24 (post-limpieza)

## Resumen

- Evidencia I-6.5 a versionar (B): **69** archivos (+ `PHASE_I_6_5_CLOSURE_REPORT.md`)
- Bootstrap backend excluido (C): **140** paths
- Tracked modificados tras restore: **1** (esperado: `.gitignore` u 0)
- Feature A ya committeado en I-1…I-6; esta fase no añade código funcional nuevo.

## A — Feature (ya en rama / chore menor)

| Archivo | Entra | Commit | Motivo | Riesgo |
|---|---|---|---|---|
| `.gitignore` (dumps + `._*`) | sí | chore/feat | Evitar dumps y AppleDouble | bajo |
| `backend/alembic/versions/061_*` + CC code | ya en HEAD | — | Committeado en I-1…I-6 | — |

## B — Evidencia / docs (entran)

| Archivo | Entra | Commit objetivo | Motivo | Riesgo |
|---|---|---|---|---|
| `docs/.../PHASE_I_6_5_CLOSURE_REPORT.md` | sí | docs | Informe + veredicto | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/GIT_CHANGE_CLASSIFICATION.md` | sí | docs | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/LOCAL_DEV_BOOTSTRAP_NOT_COMMITTED.md` | sí | docs | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/analyze_26_leidsa_k10.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/analyze_45_multi_k10.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/compare.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/compiled_draft.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/draft_create.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/login_meta.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/motors.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/prediction_34_all.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/prompt_schema.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/prompts_before.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/api_responses/tables.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/backend_tests.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/backend_tests_cc.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/backend_tests_phase_cd.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/backend_tests_summary.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/backups/jaios_lottery_dev_pre_061_20260724_084802.sha256` | sí | chore/migration-evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/backups/pre_backup_meta.txt` | sí | chore/migration-evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/benchmark/benchmark_run.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/dev_stack_evidence.md` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/e2e_api_results.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/e2e_results.md` | sí | docs | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/frontend_build.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/frontend_lint.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/frontend_npm_ci.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/frontend_typecheck.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/frontend_typecheck_branch_filter.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/git_diff_name_only.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/git_diff_stat.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/git_status_short.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/git_untracked.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/migration_061_execution.txt` | sí | chore/migration-evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/migration_061_review.md` | sí | chore/migration-evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/permissions/noperm_tables.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/playground/playground_draft.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/benchmark/13_benchmark.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/benchmark/26_benchmark_gates.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/capture_log.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/e2e_ui_log.txt` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/hub/00_control_center.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/hub/00_control_center_browser.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/01_table1.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/02_table2.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/03_groups_t1.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/04_groups_t2.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/05_relaciones.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/06_auditoria.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/14_table1_loaded.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/15_table1_number1_detail.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/16_table2_number1_detail.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/17_group_code_34.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/18_group_code_53.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/19_relaciones_n26_leidsa_k10.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/motor/20_auditoria_trace.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/permissions/27_noperm_frontend.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/permissions/28_noperm_api.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/playground/12_playground.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/playground/25_playground_run.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/predicciones/07_motors.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/predicciones/08_run.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/predicciones/21_prediction_n34.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/predicciones/22_stub_activate_attempt.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/prompt_studio/09_bloques.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/prompt_studio/10_compilado.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/prompt_studio/11_versiones.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/prompt_studio/23_bloques_help.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/screenshots/secret_scan/24_secret_blocked.png` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |
| `docs/lottery/numeric_relations_artifacts/phase_i_6_5/secret_scan/secret_block_response.json` | sí | test/evidence | Evidencia sanitizada I-6.5 | bajo |

## C — Bootstrap / DEV (NO entran)

Ver también `LOCAL_DEV_BOOTSTRAP_NOT_COMMITTED.md`.

| Archivo | Entra | Motivo | Riesgo |
|---|---|---|---|
| `phase_i_6_5/backups/*.dump` | **no** | Dump BD completo | alto |
| `backend/app/api/permission_deps.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/admin_integrations.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/ai.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/commercial_search.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/communications.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/copilot_security.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/document_templates.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/hermes.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/observations.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/settings.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/api/v1/whatsapp_webhooks.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/core/api_errors.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/core/copilot_scopes.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/core/module_access.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/core/permissions.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/models/commercial_search.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/models/company_person_role.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/models/company_representative.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/models/document_link.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/models/document_template.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/models/hermes_observed_event.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/models/price_catalog_sync.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/models/whatsapp.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/schemas/commercial_search.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/schemas/communications.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/schemas/company_representatives.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/schemas/dgcp_analysis_job.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/schemas/dgcp_autofill.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/schemas/dgcp_expediente_context.py` | no | Fill local para boot API | alto (ruido) |
| `backend/app/schemas/dgcp_historical.py` | no | Fill local para boot API | alto (ruido) |
| … +110 paths `backend/**` | no | idem | alto |
| `backend/app/services/credential_vault.py` | no | Boot integraciones | medio |
| `deps.py` / `search.py` diffs | no | Restaurados a HEAD | — |

## D — Ajenos / preexistentes

Ningún cambio ajeno se incluye. Errores tsc/lint preexistentes solo documentados en evidencia.
