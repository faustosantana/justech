# NCF Alerts Baseline v1 — Congelamiento oficial

| Campo | Valor |
|---|---|
| **Fecha** | 2026-07-16 |
| **Tag Git** | `ncf-alerts-baseline-v1` |
| **Commit SHA (BASELINE)** | `aaea7f5f4730a038f005a3e6010354f9da64963a` |
| **Módulo** | `justech_l10n_do_ncf` |
| **Versión del módulo** | `19.0.2.14.0` |
| **Entorno de referencia** | Producción `justgroup.app` (BD `justech`) |

---

## Motivo del congelamiento

El comportamiento de Alertas NCF quedó estable en Producción tras UAT DEV y despliegue controlado:

- Alertas **internas** (sin SMTP / sin `mail.mail` nuevo).
- **Una** actividad consolidada por empresa.
- Consolidación y cierre automáticos.
- HTML renderizado correctamente (sin etiquetas crudas visibles).
- Multiempresa aislada (JUSTECH, PlugSafe, Just Office, Omni Solutions).

A partir de este baseline **no se modifica** la lógica de alertas salvo incidencia reproducible o solicitud funcional aprobada.

---

## Comportamiento funcional esperado

1. El cron / proceso consolidado evalúa rangos por empresa.
2. Si hay rangos en preventivo / crítico / agotado / próximo a vencer / vencido:
   - Se crea o actualiza **una** `mail.activity` en `res.company`.
   - Summary: `Revisar rangos NCF con disponibilidad crítica`.
   - Asignatario: Responsable Fiscal → Administrador Fiscal → fallback controlado.
3. Segunda ejecución: **no duplica**; actualiza la actividad existente.
4. Si todos los rangos vuelven a estado normal: la actividad se **cierra**.
5. Actividades legacy por rango se cierran con feedback de consolidación (no se eliminan).
6. `message_post` solo como `mail.mt_note` sin `partner_ids` (sin correo).
7. **Nunca** se crea `mail.mail` ni se fuerza envío SMTP por este flujo.

---

## Limitaciones conocidas

- El fallback de asignatario puede usar un administrador con acceso a la empresa si no hay Responsable Fiscal.
- Actividades legacy históricas pueden existir cerradas; no se borran.
- Umbrales preventivo/crítico/días de vencimiento se heredan de compañía (y opcionales por rango); no forman parte de cambios posteriores sin aprobación.
- Tres registros `mail.mail` previos al baseline (estado `exception`, ~2026-07-16 21:11 UTC) pueden existir por la versión anterior de alertas; el baseline exige **cero nuevos** `mail.mail` NCF desde el deploy de este commit.

---

## Riesgos aceptados

- Congelar implica que mejoras cosméticas o refactors del flujo de alertas quedan fuera de alcance operativo.
- Si cambia el modelo de grupos fiscales, el asignatario puede caer en fallback hasta reconfiguración.
- El chatter de compañía puede recibir notas internas; no generan correo.

---

## Evidencia UAT (DEV)

| Ítem | Ubicación |
|---|---|
| Causa raíz | `evidence/ncf-alerts-consolidate-dev/fase0/00_CAUSA_RAIZ.md` |
| Script UAT | `evidence/ncf-alerts-consolidate-dev/uat_consolidate.py` |
| Resultados | `evidence/ncf-alerts-consolidate-dev/uat_results.json` |
| Cierre | `evidence/ncf-alerts-consolidate-dev/00_CIERRE.md` |
| Capturas | `evidence/ncf-alerts-consolidate-dev/capturas/` |

Veredicto DEV: **UAT ALERTAS NCF INTERNAS Y CONSOLIDADAS — PASS**.

---

## Evidencia Producción

| Ítem | Valor |
|---|---|
| Commit desplegado | `aaea7f5f4730a038f005a3e6010354f9da64963a` |
| Backup | `/opt/odoo-backups/ncf-alerts-consol-prod-20260716_225540` |
| Restore test | PASS |
| Cierre | `evidence/ncf-alerts-consol-prod-20260716/00_CIERRE.md` |
| `mail.mail` NCF nuevos post-deploy | 0 |
| Fingerprint rangos vs FASE 0 | sin cambio |
| GL | balanceado |
| Actividades legacy cerradas | 21 |

Veredicto Prod: **PASS — ALERTAS NCF INTERNAS CONSOLIDADAS DESPLEGADAS**.

---

## Checklist de validación (regresión permanente)

- [ ] Nunca se crea `mail.mail` por alertas NCF.
- [ ] Nunca se envía correo SMTP por este flujo.
- [ ] Máximo una actividad consolidada abierta por empresa.
- [ ] Segunda ejecución no duplica; actualiza.
- [ ] Al normalizar rangos, la actividad se cierra.
- [ ] Multiempresa 4/4 sin datos cruzados.
- [ ] HTML sin etiquetas crudas visibles (`&lt;p&gt;`, etc.).
- [ ] `next_sequence` / NCF consumidos / documentos históricos: 0 cambios por el flujo de alertas.
- [ ] Tests automáticos `test_ncf_alerts_consolidated_baseline.py` PASS.

---

## Rollback asociado

1. Restaurar módulo desde backup:
   `/opt/odoo-backups/ncf-alerts-consol-prod-20260716_225540/modules/justech_l10n_do_ncf_pre.tar.gz`
2. Alternativa Git: checkout de archivos del módulo en el commit previo funcional (`a4118ab…` / versión `19.0.2.13.0`).
3. `-u justech_l10n_do_ncf` (solo ese módulo).
4. Reiniciar servicio Odoo.
5. Confirmar fingerprints de rangos / GL / secuencias del backup FASE 0.
6. **No improvisar** correcciones en Producción.

Rollback de datos (solo si el restore test previo sigue válido):

- Dump: `…/justech.dump`
- Filestore: `…/filestore_justech.tar.gz`

---

## Protección de código

Bloques `PROTECTED BASELINE` en:

- `custom/justech_l10n_do_ncf/models/ncf_range.py` (constante, consolidación, cron)

Cualquier cambio requiere: Auditoría → Backup → Aprobación → UAT DEV → UAT Producción.

---

## Referencias

- Commit: `aaea7f5f4730a038f005a3e6010354f9da64963a`
- Tag: `ncf-alerts-baseline-v1`
- Directiva Maestra Justgroup / Justech
