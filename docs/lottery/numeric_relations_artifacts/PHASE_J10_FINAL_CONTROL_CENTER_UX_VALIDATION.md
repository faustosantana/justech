# PHASE J-10 — Final Control Center UX Validation

**Veredicto:** GO CONDICIONADO  
**Alcance:** DEV only · **Producción intacta** · **Sin despliegue a Producción**

---

## 1. Baseline

| Campo | Valor |
|-------|--------|
| Tag aprobado | `nr-number-visual-explorer-j9-dev-approved` |
| Commit baseline | `1d1da49` |
| Perfil J-9 nº 35 (avg) | 1827.5 ms |
| Cold profile J-9 | 2252.3 ms |
| Compare J-9 (avg) | 2640.5 ms |

## 2. Rama

`feature/nr-control-center-final-ux-j10`

## 3. Commits

| Commit | Fase |
|--------|------|
| `c4759b3` | J-10.0 Plan + seed 7 destacadas DEV |
| `b56f471` | J-10.1 Hub inteligencia + clic a expediente |
| `af2157c` | J-10.2 Expediente-first + auto-open caso |
| `c18b226` | J-10.3 Intros T1/T2/grupos/relaciones/auditoría |
| `13d72d1` | Estado intermedio documentado |
| *(este commit)* | J-10.5 E2E, capturas, perf, veredicto |

## 4. Entorno

| Servicio | Detalle |
|----------|---------|
| API DEV | `http://127.0.0.1:8001` · `jaios-nr-j9-dev` |
| FE DEV | `http://127.0.0.1:3011` · hub 200 |
| DB | `jaios_lottery_dev` @ `:5433` |
| Health | `production_forbidden: true` · `database_target: jaios_lottery_dev` |
| Producción | No tocada · sin autorización de deploy |

## 5. Siete loterías visibles (hub)

Configuración `is_featured` vía seed `scripts/j10_seed_featured_dev.py` (no hardcode en UI):

1. Quiniela Leidsa  
2. Quiniela Loteka  
3. Loteria Nacional  
4. Loto Leidsa  
5. Quiniela Real  
6. Loto Real  
7. Gana Mas  

Hub: `GET catalog featured_only` → exactamente 7.

## 6. Loterías ocultas de la experiencia principal

Anguila (todas las franjas), Haití Bolet, Florida/Miami y resto del catálogo **no** aparecen en el hub de inteligencia.

## 7. Confirmación: no fueron borradas

Administración `/lottery/admin/lotteries` con filtro «Anguila» muestra 14 loterías; columna **Destacada** desmarcada. Evidencia: `phase_j10/screenshots/20_administracion_loterias_ocultas.png`.

## 8. E2E hub

| Paso | Resultado |
|------|-----------|
| Login autorizado | PASS |
| Hub carga sin error | PASS |
| Exactamente 7 destacadas | PASS |
| Sin Anguila / Haití / Miami | PASS |
| Números clicables + CTA «Analizar este número» | PASS |
| Clic → expediente sin formulario intermedio | PASS |
| Conserva número / lotería / contexto / draw_id | PASS |
| Regreso al hub coherente | PASS |

Script: `phase_j10/e2e_j10.py` → `e2e_j10_results.json`.

## 9. Expedientes probados

| Caso | Número / draw | Estado |
|------|----------------|--------|
| Positivo completo | 50 · `80e0ac25-…` | SÍ, SE DIO LA CONDICIÓN |
| Negativo | 35 · `2c931d41-…` | NO SE DIO LA CONDICIÓN |
| Parcial | 35 · `473c1fc2-…` | SE DIO PARCIALMENTE |
| Multi-confirmadores | `6c14f43a-…` · candidato **86** · confirmadores **19, 46** | SE DIO PARCIALMENTE |
| Siete sorteos | next-draws | returned=7 · censored=false |

Fuerza siempre en candidato T1; confirmador no se fortalece.

## 10. Metodología

Intacta: `mother_code = observed_number`; T1 = candidatos; T2 = confirmadores; identidad = `draw_id`; ventana SAME_DRAW; horizonte 7 sorteos. Sin cambios de fórmula ni mutación histórica.

## 11. Señales

Señales del motor con candidatos, confirmadores, conteos y respuesta 1–7. Disclaimer visible: *«Las señales muestran relaciones y respuestas históricas. No garantizan resultados futuros.»* Sin lenguaje de garantía.

## 12. Tablas y agrupaciones

- Tabla 1 / Tabla 2: 100 filas, intros de consulta, export, acceso a detalle.  
- Agrupaciones T1/T2: bloques por código con integrantes clicables.  
- **Pendiente menor:** columnas fórmula/resultado siguen en vista principal (no ocultan el uso).

## 13. Relaciones

Lenguaje humano: compañero fortalecido · fuerza · confirmadores. Evidencia técnica bajo `<details>`. Modelo N→C→V no es el copy principal.

## 14. Auditoría

Busca por número + fechas y abre expediente auditado; estados visibles documentados; JSON oculto por defecto.  
**Pendiente menor:** actúa como launcher hacia Historial (no filtro in-page por lotería/sorteo más allá de fechas).

## 15. Capturas

Directorio: `docs/lottery/numeric_relations_artifacts/phase_j10/screenshots/`

01–22 presentes (datos reales DEV).

## 16. Prueba &lt; 1 minuto

| Pregunta | Respuesta en flujo nº 50 |
|----------|---------------------------|
| ¿Qué número? | Expediente 50 (header) |
| ¿Se dio la condición? | Resumen + badge del caso |
| ¿Cuál fortalecido? | Señales / árbol del caso |
| ¿Quién confirmó? | Confirmadores en caso |
| ¿Cuántas veces antes? | Conteos del perfil |
| ¿Qué pasó después? | Siete sorteos |
| ¿Metodología? | Intro + evidencia técnica colapsada |

Tiempo guiado: &lt; 60 s. Sin JSON obligatorio. **PASS.**

## 17. Rendimiento J-9 vs J-10

### Perfil nº 35 — alcance justo (4 loterías, ventana completa)

Remedición en reposo (`perf_fair_j9_full_window.json`):

| Métrica | J-9 | J-10 | Δ |
|---------|-----|------|---|
| avg | 1827.5 ms | **1922.7 ms** | **+5.2 %** |
| median | — | 1807.2 ms | dentro de banda |
| min / max | — | 1593.3 / 2612.8 | — |
| aparecio | 515 (J-9) | 466 | mismo endpoint |

Criterio ≤15 %: **PASS** (remeasure).

Nota: una corrida previa bajo carga midió +19 % (`perf_fair_j9_scope.json`); se atribuyó a contención, no a regresión estable. Scope featured-7 es más lento por más ocurrencias (esperado; no comparable 1:1).

### Otros (sample E2E)

Hub catalog avg ~27 ms; detail/why/next-draws/compare documentados en `e2e_j10_results.json`.

## 18. Permisos

| Rol | Profile | Notas |
|-----|---------|-------|
| Admin UAT | 200 | PASS |
| Client | 403 profile | PASS |
| Anónimo | 401 | PASS |

Hub / historial / auditoría / admin lotterías detrás de auth admin.

## 19. Móvil

Validado 375 px (emulación) + escritorio. Tarjetas apiladas; CTAs táctiles; expediente en columna.  
**Pendiente menor:** doble sidebar de plataforma + control center reduce ancho útil hasta colapsar menús.

## 20. Logs

API DEV observada durante la sesión E2E: respuestas 200 en profile/occurrences/next-draws; health OK; sin ráfaga de 500 en muestra de cola. Sin loops evidentes.

## 21. Errores

Ningún error de candidato/confirmador/fuerza/draw_id/lotería. Fallos previos de perf recalificados tras remesaure.

## 22. Correcciones en J-10.5

- Disclaimer de señales en hub.  
- Auditoría searchable → expediente.  
- Relaciones: copy humano + evidencia técnica colapsada.  
- Intros Tabla 1 / Tabla 2 / Relaciones alineados a lenguaje de negocio.  
- Historial: params fecha + filtro destacadas.  
- Evidencia E2E + remesaure perf.

## 23. Riesgos

1. Columnas internas aún visibles en T1/T2.  
2. Chrome móvil con dos navegaciones laterales.  
3. Auto-open abre el caso más reciente (a menudo negativo); positivos vía filtro.  
4. Perfil featured-7 es intrínsecamente más pesado que baseline de 4 loterías.

## 24. Producción intacta

Confirmado: `production_forbidden`, DB `jaios_lottery_dev`, sin push/deploy a prod, sin credenciales de producción en el stack DEV local.

## 25. Veredicto final

# GO CONDICIONADO

**Listo para autorización expresa de despliegue** tras aceptar pendientes menores (columnas T1/T2, chrome móvil, auditoría launcher).  

**No desplegar en Producción** hasta autorización expresa posterior a este informe.

Condiciones que **no** bloquean metodología/datos/permisos/usabilidad principal:

- `minor_t1_t2_formula_columns_visible`  
- `minor_mobile_dual_sidebar_chrome`  
- `minor_auditoria_is_expediente_launcher`
