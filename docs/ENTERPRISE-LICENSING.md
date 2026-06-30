# Licenciamiento Odoo Enterprise — Política oficial

**Suscripción Hellenia:** `M260616306091776`  
**Fecha:** 2026-06-30  
**Alcance:** Interpretación basada **únicamente** en documentación oficial Odoo 19.0. Sin suposiciones.

---

## Fuentes oficiales consultadas

| Documento | URL |
|-----------|-----|
| On-premise — Register / Duplicate | https://www.odoo.com/documentation/19.0/administration/on_premise.html |
| Neutralized database | https://www.odoo.com/documentation/19.0/administration/neutralized_database.html |
| CLI — neutralize / db duplicate | https://www.odoo.com/documentation/19.0/developer/reference/cli.html |
| Source install — Git Enterprise | https://www.odoo.com/documentation/19.0/administration/on_premise/source.html |
| Docker Hub (imagen oficial) | https://hub.docker.com/_/odoo |

---

## 1. Registro de suscripción (vinculación)

### Texto oficial

> *"To register your database, enter your subscription code in the banner in the app dashboard."*  
> — [On-premise](https://www.odoo.com/documentation/19.0/administration/on_premise.html)

> *"Ensure that no other database is linked to the subscription code, as **only one database can be linked per subscription**."*  
> — [On-premise — Registration error](https://www.odoo.com/documentation/19.0/administration/on_premise.html)

### Qué documenta Odoo

| Concepto | Política oficial documentada |
|----------|------------------------------|
| Código de suscripción | Se ingresa en el banner de la BD |
| Vinculación | **Una** BD vinculada al código por suscripción |
| Validación | Conexión saliente permanente a `services.odoo.com:80` (Odoo 18+) |
| Estado contrato | Debe mostrar **"In Progress"** en cuenta Odoo |
| Usuarios | Aviso 30 días si usuarios internos exceden lo contratado |

### Qué NO documenta Odoo

La documentación oficial **no define** explícitamente:

- Un límite de **instancias Docker** o servidores físicos
- Un límite de **contenedores Odoo** ejecutándose simultáneamente
- Si DEV y TEST pueden coexistir como BDs separadas sin duplicación
- Si se requieren suscripciones adicionales para ambientes de desarrollo

> **Regla de interpretación Hellenia:** Solo afirmamos lo que la documentación cita. Lo no documentado se marca como *no especificado oficialmente*.

---

## 2. Bases de desarrollo y prueba

### Texto oficial

> *"**Tip:** If a test or a development database is needed, you can **duplicate a database**."*  
> — [On-premise — Registration error](https://www.odoo.com/documentation/19.0/administration/on_premise.html)

> *"Duplicate a database by accessing the database manager on your server (`/web/database/manager`). Typically, you want to duplicate your **production database into a neutralized testing database**. It can be done by checking the **neutralize** box when prompted."*  
> — [On-premise — Duplicate a database](https://www.odoo.com/documentation/19.0/administration/on_premise.html)

### Qué documenta Odoo

| Escenario | Método oficial documentado |
|-----------|---------------------------|
| BD de prueba | Duplicar BD existente |
| BD de desarrollo | Duplicar BD existente (mismo tip) |
| Neutralización en duplicado | Checkbox **neutralize** en `/web/database/manager` |
| CLI duplicado | `odoo-bin db duplicate <source> <target> -n` (flag `-n` = neutralize) |
| CLI neutralizar | `odoo-bin neutralize -d <database>` |

### Implicación para Hellenia

La documentación oficial orienta ambientes no productivos hacia **duplicación + neutralización** de una BD ya existente, no hacia un segundo registro del mismo código de suscripción.

---

## 3. Bases duplicadas

### Texto oficial

> *"Verify that no databases share the same **UUID** (Universally Unique Identifier) by opening your Odoo Contract. If two or more databases share the same UUID, their name will be displayed."*  
> — [On-premise — Registration error](https://www.odoo.com/documentation/19.0/administration/on_premise.html)

### Qué documenta Odoo

| Regla | Detalle oficial |
|-------|-----------------|
| UUID único | Dos o más BDs con el mismo UUID generan error de registro |
| Detección | El contrato Odoo muestra nombres de BDs con UUID duplicado |
| Resolución documentada | Cambiar UUID manualmente de la(s) BD o abrir ticket de soporte |

### Comandos CLI oficiales para duplicación

```
$ odoo-bin db duplicate <source> <target>
$ odoo-bin db duplicate <source> <target> -n    # con neutralización
```

```
$ odoo-bin --addons-path <PATH,...> neutralize -d <database>
```

— [CLI reference](https://www.odoo.com/documentation/19.0/developer/reference/cli.html)

---

## 4. Neutralización de bases

### Texto oficial

> *"A **neutralized database** is a non-production database on which several parameters are deactivated."*  
> — [Neutralized database](https://www.odoo.com/documentation/19.0/administration/neutralized_database.html)

> *"**Note:** Any testing database created is a neutralized database:*
> - *testing backup databases*
> - *duplicate databases*
> - *for Odoo.sh: staging and development databases"*  
> — [Neutralized database](https://www.odoo.com/documentation/19.0/administration/neutralized_database.html)

### Funcionalidades desactivadas (lista oficial no exhaustiva)

| Funcionalidad | Estado en BD neutralizada |
|---------------|---------------------------|
| Acciones planificadas (cron) | Desactivadas |
| Emails salientes | Desactivados |
| Sincronización bancaria | Desactivada |
| Proveedores de pago | Desactivados |
| Métodos de entrega | Desactivados |
| Tokens IAP | Desactivados |
| Visibilidad website (SEO) | Desactivada |
| Identificación visual | Banner rojo en pantalla |

### Métodos oficiales de neutralización

| Método | Cuándo |
|--------|--------|
| UI `/web/database/manager` | Al duplicar, marcar checkbox **neutralize** |
| CLI `odoo-bin neutralize -d <db>` | Sobre BD existente |
| CLI `odoo-bin db duplicate ... -n` | Al duplicar con flag neutralize |

---

## 5. Ambientes Docker

### Texto oficial

> *"**Note:** Although there is no official Odoo Enterprise Docker image, the Enterprise modules can be mounted by using the above mentioned method."*  
> — [Docker Hub — odoo](https://hub.docker.com/_/odoo)

> *"**Run multiple Odoo instances**"*
> ```
> $ docker run -p 8070:8069 --name odoo2 --link db:db -t odoo
> $ docker run -p 8071:8069 --name odoo3 --link db:db -t odoo
> ```
> — [Docker Hub — odoo](https://hub.docker.com/_/odoo)

### Qué documenta Odoo sobre Docker

| Tema | Política oficial |
|------|------------------|
| Imagen Enterprise | **No existe** imagen Docker Enterprise oficial |
| Enterprise en Docker | Montar módulos Enterprise como volumen (`/mnt/extra-addons` o equivalente) |
| Múltiples instancias | Documentado explícitamente — varios contenedores Odoo sobre misma BD PostgreSQL |
| Licenciamiento por contenedor | **No documentado** |

### Implicación para Hellenia

DEV, TEST y futura PROD como stacks Docker separados es compatible con la documentación oficial de Docker. La restricción de licencia aplica al **registro de BD** (UUID + código), no al número de contenedores documentado.

---

## 6. DEV / TEST bajo una misma suscripción Enterprise

### Hechos documentados oficialmente

| # | Hecho oficial | Fuente |
|---|---------------|--------|
| 1 | Un código de suscripción → una BD **vinculada** | on_premise.html |
| 2 | BD de test/dev → **duplicar** BD existente | on_premise.html |
| 3 | BD de test → **neutralizar** | on_premise.html + neutralized_database.html |
| 4 | UUID debe ser único por BD registrada | on_premise.html |
| 5 | Código Enterprise Git requiere suscripción activa + usuario GitHub vinculado | source.html |

### Lo que la documentación NO especifica

- Si `hellenia_dev` y `hellenia_test` pueden registrarse ambas con `M260616306091776` → **No** (contradice regla #1)
- Si ambas pueden operar como duplicados neutralizados de una BD maestra → **Sí**, alineado con reglas #2 y #3
- Si se necesita segunda suscripción para DEV paralelo a PROD registrado → **No documentado**; contactar Account Manager

---

## 7. Arquitectura permanente Hellenia (alineada a documentación oficial)

Flujo definitivo del proyecto — **no temporal**:

```
DEV  ──►  TEST  ──►  PRODUCCIÓN
```

### Modelo operativo según política oficial

```
                    ┌─────────────────────────────────────┐
                    │  BD con código M260616306091776   │
                    │  vinculado (una sola a la vez)    │
                    └─────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
     duplicar + neutralize   duplicar + neutralize    (BD maestra
              │                       │                registrada)
              ▼                       ▼
           DEV                    TEST              PRODUCCIÓN
     (hellenia_dev)          (hellenia_test)      (futuro odoo.hellenia.cloud)
```

### Fases del ciclo de vida

| Fase del proyecto | BD registrada (código activo) | DEV | TEST |
|-------------------|-------------------------------|-----|------|
| **Implementación** (ahora) | `hellenia_dev` | BD de construcción | Duplicado neutralizado de DEV |
| **UAT / pre-go-live** | `hellenia_dev` o `hellenia_test`* | Desarrollo continuo | Pruebas de aceptación |
| **Producción** | `hellenia_prod` (futura) | Duplicado neutralizado de PROD | Duplicado neutralizado de PROD |

\* Durante implementación, la BD donde se construye es la candidata a registro. TEST se alimenta por duplicación oficial.

### Transición a producción (oficial)

1. Estabilizar configuración en DEV
2. Duplicar DEV → TEST con neutralize (validación UAT)
3. En go-live: crear/migrar PROD, **vincular código a PROD**
4. Refrescar DEV y TEST como duplicados neutralizados de PROD
5. Mantener DEV → TEST → PROD como pipeline permanente de promoción de cambios custom

> La re-vinculación del código al pasar de DEV a PROD es consecuencia directa de la regla oficial *"only one database can be linked per subscription"*.

---

## 8. Matriz de consultas frecuentes (solo hechos oficiales)

| Pregunta | Respuesta según documentación oficial |
|----------|---------------------------------------|
| ¿Cuántas BDs pueden vincular un código? | **Una** |
| ¿Cómo obtener BD de test? | **Duplicar** BD existente |
| ¿Cómo obtener BD de dev? | **Duplicar** BD existente (mismo tip oficial) |
| ¿Qué es una BD neutralizada? | BD no productiva con procesos sensibles desactivados |
| ¿Cómo neutralizar? | Checkbox en manager, CLI `neutralize`, o `db duplicate -n` |
| ¿Pueden coexistir UUID iguales? | **No** — error de registro |
| ¿Existe imagen Docker Enterprise? | **No** — montar addons Enterprise |
| ¿Múltiples contenedores Odoo? | **Sí** — documentado en Docker Hub |
| ¿Segunda suscripción para DEV+PROD? | **No documentado** |

---

## 9. Acciones pendientes de verificación contractual

Estos puntos **no están** en la documentación técnica pública y requieren confirmación en portal o Account Manager:

| # | Verificar en portal Odoo |
|---|--------------------------|
| 1 | Usuarios internos incluidos en contrato |
| 2 | Fecha de renovación |
| 3 | Estado **In Progress** |
| 4 | Usuario(s) GitHub autorizados |
| 5 | BD actualmente vinculada (ninguna confirmada) |

---

## Referencias cruzadas

- [E0.5-SUBSCRIPTION-VALIDATION.md](E0.5-SUBSCRIPTION-VALIDATION.md) — Checklist portal
- [ARCHITECTURE.md](ARCHITECTURE.md) — Arquitectura DEV → TEST → PROD
- [UPGRADE-PATH.md](UPGRADE-PATH.md) — Actualizaciones Odoo 20+
- [E1-CHECKLIST.md](E1-CHECKLIST.md) — Validación final pre-E1
