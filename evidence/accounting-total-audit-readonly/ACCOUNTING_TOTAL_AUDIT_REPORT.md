# Informe — Auditoría contable total (solo lectura)

**Fecha:** 2026-07-05  
**Modo:** P1/P2 read-only — sin create/write/unlink, sin `-u` módulos  
**Evidencia:** `evidence/accounting-total-audit-readonly/`  
**Script:** `scripts/accounting-total-audit-readonly.py`  
**Runner:** `scripts/run-accounting-total-audit-readonly.sh`

---

## 1. Resumen ejecutivo

| Ambiente | Estado auditoría | Críticos | Altos | Veredicto integridad núcleo |
|----------|------------------|----------|-------|----------------------------|
| **DEV** | **Bloqueado** | — | 1 (infra) | No evaluable — `odoo shell` no inicia |
| **TEST** | Completado | 0 | 1 | **PASS** estructural (768 asientos, YTD cuadrado) |
| **PROD** | Completado | 0 | 3 | **PASS** estructural (9 asientos smoke, YTD cuadrado) |

**Conclusión:** La contabilidad núcleo en TEST y PROD está **estructuralmente sana** (asientos balanceados, sin conciliaciones huérfanas, pagos con asiento). Persisten **riesgos fiscales y de madurez operativa** que impiden certificación go-live comercial.

**PROD confirmado read-only:** solo `odoo shell` + SELECT/search; sin modificaciones.

---

## 2. DEV — No auditable (infraestructura)

`odoo shell` falla **antes** de ejecutar el script, al cargar contexto de usuario:

```
UndefinedColumn: column res_partner.justech_do_partner_id_type does not exist
```

- Código custom declara campos fiscales en `res.partner`; BD DEV no migrada.
- Módulo `justech_l10n_do_reports` omitido por dependencia `hellenia_account` no cargada.
- **Acción requerida (fuera de este alcance):** `-u` módulos fiscales en DEV — **no ejecutado** por restricción.

Evidencia: `dev-raw.txt`, `dev-environment-blocked.json`

---

## 3. Qué está correcto

### TEST (`hellenia_test`)

| Área | Estado |
|------|--------|
| Plan cuentas (291) + cuentas clave | OK |
| Diarios operativos (INV, FACTU, BNKD/BNKU, CSH1, STJ, POSS…) | OK |
| Categorías producto con GL ingreso/gasto | OK (0 sin cuenta) |
| Asientos posted balanceados | OK (768 moves, 0 descuadrados) |
| YTD débito = crédito | OK (1,960,120.82) |
| Compras posted | OK (147 facturas proveedor) |
| Pagos con asiento | OK (205) |
| Conciliaciones huérfanas | OK (0) |
| ITBIS 18% ventas/compras | OK |
| POS configurado | OK (Punto de Venta Hellenia, journal POSS) |
| `account_reports` | Instalado |
| Ecuación balance A ≈ L+E | OK |

### PROD (`hellenia_prod`)

| Área | Estado |
|------|--------|
| Integridad asientos (9 posted) | OK |
| YTD cuadrado (94,400.00) | OK |
| Pagos con asiento (3/3) | OK |
| Retenciones con GL | OK (Phase 22 histórico) |
| NCF sin duplicados | OK |
| Conciliaciones huérfanas | OK |

---

## 4. Qué falta / no probado

| ID | Área | TEST | PROD |
|----|------|------|------|
| GAP-01 | Escenarios controlados S01–S18 (matriz go-live) | Parcial (datos reales TEST) | No (smoke) |
| GAP-02 | Notas crédito/débito fiscales masivas | Pocos registros | 0 NC posted |
| GAP-03 | Cierre período contable formal | No validado | No |
| GAP-04 | Conciliación bancaria con extractos | No validado | No |
| GAP-05 | Certificación PDF estados financieros (contador) | Pendiente | Pendiente |
| GAP-06 | POS → GL cierre sesión E2E certificado | POS activo TEST, no certificado contable | POS sin config |

---

## 5. Qué está mal configurado

| ID | Sev. | Hallazgo | TEST | PROD | Corrección |
|----|------|----------|------|------|------------|
| FISC-01 | **Alto** | Facturas posted sin RNC en partner | 235 facturas | 5 (SMOKE) | **Config/datos** — limpiar partners, RNC obligatorio |
| FISC-03 | Medio | Facturas cliente posted sin NCF | 15 | 0 | **Config/código** — revisar hook NCF / facturas legacy |
| FISC-04 | **Alto** | Rango NCF B02 bajo | — | 94 restantes | **Config** — activar rangos, no usar PROD para pruebas |
| POS-01 | **Alto** | POS instalado sin `pos.config` | — | Sí | **Config** — parametrizar PROD o desinstalar |
| JRN-01 | Medio | Diario `BNK1` no existe (usa BNKD/BNKU) | Sí | Sí | **Documentación** — actualizar Golden Config YAML |
| PRD-03 | Medio | Productos venta sin impuesto | 5 | 5 | **Config** — asignar ITBIS 18% |
| SAL-01 | Medio | Facturas `paid` con residual 0 pero estado inconsistente | Revisar | INV/00003 | **Operativo** |

---

## 6. Riesgos contables

| ID | Riesgo | Sev. | Mitigación |
|----|--------|------|------------|
| R-C1 | TEST con volumen real pero sin cierre período certificado | Medio | Cierre mensual piloto |
| R-C2 | POS TEST operativo sin certificación cierre → GL | Alto | Escenario S14 en TEST |
| R-C3 | PROD base smoke — no representa operación comercial | Alto | No declarar go-live PROD |
| R-C4 | Productos sin impuesto (5) | Medio | Corregir catálogo |

---

## 7. Riesgos fiscales

| ID | Riesgo | Sev. | Mitigación |
|----|--------|------|------------|
| R-F1 | 235 facturas TEST sin RNC partner | **Crítico operativo** | Limpieza maestros + regla bloqueo |
| R-F2 | 15 facturas TEST sin NCF | Alto | Auditar origen (pre-NCF / manual) |
| R-F3 | PROD NCF B02 casi agotado | Alto | Nuevos rangos antes de operar |
| R-F4 | 608/606 no certificados con volumen TEST | Medio | Export DGII período piloto |

---

## 8. Recomendaciones priorizadas

1. **Bloqueante fiscal:** exigir RNC en partners antes de postear facturas (`justech_l10n_do_ncf` / validación UI).
2. **Limpiar TEST:** partners de prueba sin RNC; reclasificar o cancelar facturas inválidas.
3. **PROD:** no operar comercialmente; ampliar rangos NCF; configurar POS o quitar módulo.
4. **DEV:** migrar esquema (`-u` módulos Justech) antes de usar como referencia.
5. **Contador (Glys Nuñez):** validar rubros ingreso 4101xxxx por línea negocio; firmar estados tras cierre jun-2026.
6. **Siguiente fase (post-aprobación):** escenarios S01–S18 en TEST + informe visual reportes.

---

## 9. Matriz: configuración vs código vs contador

| Tema | Config | Código | Contador |
|------|--------|--------|----------|
| RNC obligatorio facturas | Partners | Validación pre-post | Validar política |
| NCF faltantes legacy | Secuencias | Hook `_post` | — |
| Productos sin ITBIS | `account.tax` en producto | — | — |
| Diarios BNKD vs BNK1 | Renombrar o doc YAML | — | Aprobar convención |
| POS PROD vacío | `pos.config` | `hellenia_pos` | Política caja |
| Cierre período | Contabilidad | — | **Sign-off** |
| GL categorías arte/mobiliario | `product.category` | — | **Rubros 4101** |

---

## 10. Plan de corrección propuesto (sin ejecutar)

| Fase | Acción | Ambiente | Esfuerzo |
|------|--------|----------|----------|
| C1 | Limpieza partners + RNC | TEST | 1–2 días |
| C2 | ITBIS en 5 productos | TEST/PROD | 1 h |
| C3 | Investigar 15 facturas sin NCF | TEST | 0.5 día |
| C4 | Escenarios S01–S18 | TEST | 1 semana |
| C5 | Sync esquema DEV | DEV | 2 h (requiere aprobación `-u`) |
| C6 | PROD rangos NCF + POS config | PROD | Tras aprobación explícita |

---

## 11. Archivos de evidencia

| Archivo | Contenido |
|---------|-----------|
| `test.json` | Auditoría completa TEST |
| `prod.json` | Auditoría completa PROD |
| `dev-environment-blocked.json` | DEV bloqueado |
| `test-raw.txt` / `prod-raw.txt` | Log odoo shell |
| `dev-raw.txt` | Error esquema DEV |

---

## 12. Veredicto

| Decisión | Recomendación |
|----------|---------------|
| Integridad contable núcleo TEST | **GO** con reservas fiscales |
| Integridad contable núcleo PROD | **GO** solo smoke — no comercial |
| Go-live comercial | **NO GO** hasta FISC-01 resuelto + escenarios S01–S18 |
| Implementar `justech_modules` (JM1) | **Esperar** revisión de este informe |

---

*Informe generado automáticamente — solo lectura, sin cambios en TEST/PROD.*
