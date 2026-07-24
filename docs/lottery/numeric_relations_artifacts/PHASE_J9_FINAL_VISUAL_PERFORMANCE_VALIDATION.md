# J-9 — Validación visual, rendimiento y preparación final (DEV)

**Fecha:** 2026-07-24  
**Rama:** `feature/nr-number-visual-explorer-j9`  
**Base funcional previa:** `e84b811` (J-9.6)  
**Producción:** intacta — **no se desplegó**  
**Veredicto:** **GO PARA DESPLIEGUE** (solo tras autorización expresa; este documento no autoriza Prod)

---

## 1. Entorno validado

| Componente | Valor |
|------------|-------|
| API DEV | `http://127.0.0.1:8001` — `scripts/j9_nr_dev_server.py` |
| Frontend DEV | `http://127.0.0.1:3011` — ruta `/lottery/admin/control-center/motor/historial-numero` |
| DB | `jaios_lottery_dev` @ `127.0.0.1:5433` |
| Health | `database_target=jaios_lottery_dev`, `production_forbidden=true` |
| Auth UAT | `uat-nr-admin@example.com` / tenant `uat-numeric-relations` |
| Contenedor PG | `jaios-lottery-pg-dev` |

Prevalidación: sin apuntar a Producción. Si algún servicio hubiera apuntado a Prod se habría detenido el trabajo.

---

## 2. Commit / servicios remontados

Servicios remontados en DEV con la rama J-9:

- Backend slim J-9 (auth + lottery + NR histórico) sobre DSN exclusivo DEV.
- Frontend rebuild (`node:22-alpine npm run build`) y `jaios-cc-dev-web` en `:3011`.
- Migraciones / rutas J-9 disponibles vía OpenAPI bajo  
  `/api/v1/lottery/admin/numeric-relations/history/numbers/*`.

Evidencia: `phase_j9/00_prevalidation.txt`, `01_health.json`, `frontend_build.txt`, `scripts/j9_nr_dev_server.py`.

---

## 3. DB utilizada

Solo `jaios_lottery_dev` (puerto **5433**). Sin escritura a histórico. Sin sync. Sin tocar Prod.

---

## 4. Rutas probadas

- UI: `/lottery/admin/control-center/motor/historial-numero` → HTTP 200, título **HISTORIAL DEL NÚMERO**
- Login UAT admin OK
- Assets y navegación Control Center OK

---

## 5. APIs probadas

| Endpoint POST | Resultado |
|---------------|-----------|
| `/history/numbers/profile` | OK |
| `/history/numbers/occurrences` | OK |
| `/history/numbers/occurrences/detail` | OK |
| `/history/numbers/occurrences/next-draws` | OK |
| `/history/numbers/compare` | OK |
| `/history/numbers/why-strengthened` | OK |

Prefijo completo: `/api/v1/lottery/admin/numeric-relations/...`

---

## 6. Casos visuales (datos reales DEV)

| Caso | Qué se usó | Resultado UI |
|------|------------|--------------|
| A Frecuente | Número **35**, 2015–2016, todas las loterías visibles | Expediente completo, 365 apariciones, gráficas, parciales |
| B Negativa | Apariciones filtradas / listado sin confirmación | Lenguaje **NO SE DIO LA CONDICIÓN** |
| C Parcial | 35 con confirmación incompleta de compañeros | **SE DIO PARCIALMENTE** |
| D Multi-confirmadores | Candidato **86** con confirmadores **19** y **46** (`case_fixtures.json`) | Árbol + “por qué se fortaleció” |
| E Muestra pequeña | 35, 2015-01-01→2015-01-07 | **2** apariciones, **Muestra muy baja** |
| F Censurado | Ancla sin 7 posteriores | Texto: no había suficientes sorteos posteriores (no solo `censored=true`) |
| Positiva plena | Número **50**, filtro “Condición positiva” | **SÍ, SE DIO LA CONDICIÓN** (49 de 356 en 2015–2016) |

---

## 7. Veinte capturas

Carpeta: `docs/lottery/numeric_relations_artifacts/phase_j9/screenshots/`

| # | Archivo | Descripción breve |
|---|---------|-------------------|
| 01 | `01_busqueda_historial_numero.png` | Buscador HISTORIAL DEL NÚMERO |
| 02 | `02_expediente_general_numero_35.png` | Expediente general del 35 |
| 03 | `03_condicion_positiva.png` | Número 50 — filtro positiva — “SÍ, SE DIO LA CONDICIÓN” |
| 04 | `04_condicion_negativa.png` | Condición negativa en lenguaje claro |
| 05 | `05_condicion_parcial.png` | Condición parcial |
| 06 | `06_arbol_relaciones.png` | Árbol de relaciones del caso |
| 07 | `07_candidato_fortalecido.png` | Candidato fortalecido |
| 08 | `08_por_que_se_fortalecio.png` | Panel “por qué se fortaleció” |
| 09 | `09_todas_las_apariciones.png` | Listado de apariciones |
| 10 | `10_siete_sorteos_posteriores.png` | Siete sorteos posteriores |
| 11 | `11_reproductor_del_caso.png` | Reproductor del caso |
| 12 | `12_grafica_apariciones_por_ano.png` | Gráfica por año/mes |
| 13 | `13_grafica_por_loteria.png` | Gráfica por lotería |
| 14 | `14_grafica_ciclo_respuesta.png` | Gráfica de ciclo / respuesta |
| 15 | `15_comparacion_35_vs_40.png` | Comparador 35 vs 40 |
| 16 | `16_evidencia_tecnica.png` | Evidencia técnica colapsable (JSON) |
| 17 | `17_vista_movil.png` | Viewport móvil (~390px) |
| 18 | `18_muestra_pequena.png` | Muestra muy baja (2 apariciones) |
| 19 | `19_evento_censurado.png` | Evento sin seguimiento completo |
| 20 | `20_panel_metodologia.png` | Metodología en cinco pasos |

Todas con datos reales DEV. Sin datos inventados.

---

## 8. Prueba “menos de un minuto”

**Escenario:** número 50, 2015–2016, filtro condición positiva + Ver caso.

| # | Pregunta | Visible sin evidencia técnica |
|---|----------|-------------------------------|
| 1 | Número consultado | Sí — expediente / título |
| 2 | Cuántas veces salió | Sí — tarjetas APARECIÓ |
| 3 | Si se dio la condición | Sí — “SÍ, SE DIO LA CONDICIÓN” |
| 4 | Candidato fortalecido | Sí — narrativa + árbol |
| 5 | Confirmador | Sí — “32 confirmó al candidato 45” |
| 6 | Qué ocurrió después | Sí — siete sorteos / respuesta observada |
| 7 | Por qué | Sí — panel “por qué se fortaleció” |

**Tiempo aproximado:** &lt; 45 s tras cargar el expediente.  
**Obstáculos:** los checkboxes de lotería no reflejan estado React si se manipulan solo por DOM; usar controles React / “Usar todo el histórico”. Primera carga conviene fijar fechas antes de Analizar.  
**Correcciones visuales aplicadas:** ninguna de metodología; capturas tomadas tras estabilizar filtros y casos reales (50 para positiva plena; 35 corto para muestra pequeña).

---

## 9. Verificación de siete sorteos

Script: `phase_j9/perf_and_visual_cases.py` → `perf_and_cases.json`

- 5 anclas reales
- Comparación API vs DB DEV: **coincidencia exacta** (`seven_draws_pass: true`)
- Orden cronológico, lotería de seguimiento, números, censura cuando `next=0`
- Aclaración UI: “7 sorteos reales (no son necesariamente 7 días)”

---

## 10. Métricas de rendimiento (número 35, histórico completo, 10 corridas)

Fuente: `phase_j9/perf_and_cases.json` / `perf_run.txt`

| Operación | min | avg | p95 | max | Objetivo | Resultado |
|-----------|-----|-----|-----|-----|----------|-----------|
| Perfil | 1674.7 | **1827.5** | 2098.7 | 2252.3 | &lt; 2000 avg | **PASS avg**; cold 2252.3 (una vez) |
| Apariciones (1ª pág.) | 1709.0 | 1854.0 | 2204.4 | 2231.1 | &lt; 2000 | PASS avg |
| Detalle | 811.7 | 965.8 | 1041.5 | 1048.4 | &lt; 1500 | PASS |
| Siete sorteos | 847.8 | 957.4 | 997.9 | 998.5 | &lt; 1500 | PASS |
| Por qué se fortaleció | 1642.4 | 1829.4 | 2222.0 | 2484.2 | — | Informativo |
| Comparación 35 vs 40 | 2513.4 | 2640.5 | 2755.3 | 2786.3 | &lt; 3000 | PASS |

Errores/timeouts en batche de medición: **0**.  
Registros: perfil reportó `aparecio=515` / `sample_size=515` en ventana completa de medición.

**Justificación cold:** la primera ejecución del perfil supera levemente 2 s; caliente y promedio quedan bajo umbral. Aceptable en DEV; candidata a caché de agregados en una fase posterior **sin cambiar metodología**.

---

## 11. Permisos

Evidencia: `phase_j9/03_permissions.json`

| Actor | `/numbers/profile` |
|-------|--------------------|
| Admin UAT | **200** |
| Cliente UAT (sin admin) | **403** |
| Anónimo | **401** |

Evidencia técnica permanece detrás de la misma puerta admin. Sin exposición de secretos en respuestas.

---

## 12. Logs y estabilidad

- Escaneo del log del proceso uvicorn J-9 (`04_log_scan.txt`): **0** coincidencias de error/traceback/5xx en el tramo revisado tras las pruebas.
- E2E re-ejecutado al cierre: **50/50 PASS** (`e2e_50_rerun.txt`).
- Sin bucles ni reintentos anómalos observados en la sesión de validación.

---

## 13–15. Errores / correcciones / riesgos

**Errores J-9 encontrados en esta validación:** 0 bloqueantes.

**Correcciones aplicadas:** solo evidencias/documentación y remount DEV; **sin** cambios a fórmulas, Tabla 1/2, histórico ni `/analyze` v1.

**Riesgos residuales:**

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Perfil cold &gt; 2 s | Bajo | Medido y justificado; caché futura |
| Comparador = 2 perfiles | Medio en rangos enormes | Aceptable (&lt; 3 s en medición) |
| UX checkboxes lotería vía automatización DOM | Bajo | Usar UI React; no afecta API |

---

## 16. Pendientes (no bloquean GO)

1. Caché de agregados de perfil para cold &lt; 2 s de forma consistente.
2. Mejorar toggles masivos “solo Leidsa/Loteka/Nacional/Loto Leidsa” en UI.
3. Autorización humana expresa antes de cualquier despliegue Prod.

---

## 17. Producción intacta

Confirmado: DSN DEV-only, `production_forbidden=true`, sin deploy fuera de DEV, histórico no mutado.

---

## 18. Veredicto final

### GO PARA DESPLIEGUE

Cumple:

- DEV remontado correctamente  
- 20 capturas completas con datos reales  
- E2E 50/50 PASS (reconfirmado)  
- Siete sorteos validados API=DB  
- Metodología intacta  
- Rendimiento aceptable / cold justificado  
- Permisos PASS  
- Logs estables en la ventana revisada  
- Producción intacta  

**No desplegar en Producción hasta autorización expresa del responsable.**
