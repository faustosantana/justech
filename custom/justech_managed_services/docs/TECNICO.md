# Documentación técnica — justech_managed_services

## Modelo principal

**`justech.managed.service.assessment`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | Char | Secuencia `LEV-%(range_year)s-####` (`use_date_range=True`) |
| `form_data` | Json | Respuestas de secciones 2–16 |
| `org_*` | Char | Sección 1 desnormalizada para prefill desde `res.partner` |
| `access_token` | Char | `secrets.token_urlsafe(32)` |
| `public_url` | Char computed | `{web.base.url}/servicios/levantamiento/{token}` |

### Herencias

- `mail.thread`, `mail.activity.mixin`
- `res.partner` → `justech_ms_assessment_count`, `action_view_justech_ms_assessments`
- `crm.lead` → idem

## API pública (website)

| Ruta | Tipo | Método modelo |
|------|------|---------------|
| `GET /servicios/levantamiento/<token>` | http | `public_get_by_token` |
| `POST .../save` | json | `public_save_partial` |
| `POST .../submit` | json | `public_submit` |

Estados de acceso devueltos por `public_get_by_token`: `ok`, `invalid`, `cancelled`, `inactive`, `expired`, `submitted`.

## Esquema `form_data`

Las claves deben coincidir con los atributos `name` del formulario HTML público.

### Sección 1 — Organización (también campos `org_*` en modelo)

| Clave | Tipo | Descripción |
|-------|------|-------------|
| `org_company_name` | string | Nombre de la empresa |
| `org_vat` | string | RNC |
| `org_address` | string | Dirección principal |
| `org_responsible` | string | Nombre del responsable |
| `org_job` | string | Cargo |
| `org_email` | string | Correo |
| `org_phone` | string | Teléfono |

### Sección 2 — Usuarios

| Clave | Tipo | Valores |
|-------|------|---------|
| `employee_count_range` | selection | `1_25`, `26_50`, `51_100`, `101_250`, `250_plus` |
| `support_users_count` | integer | Cantidad de usuarios con soporte |
| `work_mode` | selection | `presencial`, `remota`, `hibrida` |

### Sección 3 — Oficinas

| Clave | Tipo | Valores |
|-------|------|---------|
| `office_count` | integer | Cantidad de oficinas |
| `office_locations` | text | Ciudades/ubicaciones |
| `offices_connected` | selection | `si`, `no`, `parcialmente`, `no_sabemos` |

### Sección 4 — Equipos

| Clave | Tipo | Valores |
|-------|------|---------|
| `qty_desktop` | integer | Escritorio |
| `qty_laptop` | integer | Laptops |
| `qty_physical_server` | integer | Servidores físicos |
| `qty_virtual_server` | integer | Servidores virtuales |
| `qty_printer` | integer | Impresoras |
| `qty_mobile` | integer | Móviles |
| `qty_wireless_ap` | integer | Access points |
| `qty_network` | integer | Equipos de red |
| `brands` | array | `dell`, `hp`, `lenovo`, `apple`, `cisco`, `huawei`, `fortinet`, `ubiquiti`, `otras` |

### Sección 5 — Plataformas

| Clave | Tipo | Valores |
|-------|------|---------|
| `platforms` | array | `m365`, `google_workspace`, `azure`, `aws`, `ad_local`, `entra_id`, `vmware`, `hyper_v`, `vpn`, `firewall`, `antivirus`, `backup`, `erp`, `financial`, `document_mgmt`, `voip`, `cctv`, `access_control` |
| `erp_main` | string | ERP principal |
| `critical_apps` | text | Aplicaciones críticas |
| `other_platforms` | text | Otras plataformas |

### Sección 6 — Servicios a tercerizar

| Clave | Tipo | Valores (`outsource_services[]`) |
|-------|------|----------------------------------|
| `outsource_services` | array | `mesa_ayuda`, `soporte_remoto`, `soporte_presencial`, `mant_preventivo`, `mant_correctivo`, `admin_servidores`, `admin_redes`, `admin_m365`, `admin_usuarios`, `gestion_respaldos`, `ciberseguridad`, `antivirus`, `gestion_activos`, `gestion_inventario`, `coord_proveedores`, `instalacion_equipos`, `config_computadoras`, `gestion_garantias`, `soporte_impresoras`, `soporte_aplicaciones`, `reportes_servicio`, `otro` |

### Sección 7 — Niveles de soporte

| Clave | Tipo | Valores |
|-------|------|---------|
| `support_levels` | array | `nivel_1`, `nivel_2`, `nivel_3`, `coord_fabricantes` |

### Sección 8 — Horario

| Clave | Tipo | Valores |
|-------|------|---------|
| `coverage_schedule` | selection | `laboral`, `lunes_sabado`, `extendido`, `24x7`, `guardia`, `personalizado` |
| `coverage_start_time` | string | HH:MM |
| `coverage_end_time` | string | HH:MM |
| `holidays_operation` | text | Feriados |
| `custom_schedule_comment` | text | Comentario horario |

### Sección 9 — Modalidad

| Clave | Tipo | Valores |
|-------|------|---------|
| `service_modality` | selection | `remoto_principal`, `remoto_visitas`, `presencial_parcial`, `presencial_completo`, `equipo_dedicado`, `equipo_compartido`, `bolsa_horas`, `recomendacion_justech` |
| `onsite_frequency` | selection | `incidencia`, `mensual_1`, `mensual_2`, `semanal_1`, `varios_dias`, `permanente` |

### Sección 10 — Volumen

| Clave | Tipo | Valores |
|-------|------|---------|
| `monthly_requests_range` | selection | `lt_25`, `25_50`, `51_100`, `101_200`, `gt_200`, `sin_info` |
| `frequent_requests` | array | `passwords`, `access`, `email`, `pc_failures`, `printers`, `internet`, `networks`, `applications`, `m365`, `software_install`, `servers`, `security`, `other` |

### Sección 11 — Soporte actual

| Clave | Tipo | Valores |
|-------|------|---------|
| `current_support_provider` | selection | `interno`, `externo`, `mixto`, `sin_estructura` |
| `uses_ticket_platform` | boolean | Plataforma de tickets |
| `ticket_platform_name` | string | Nombre plataforma |
| `has_inventory` | boolean | Inventario actualizado |
| `has_documentation` | boolean | Documentación técnica |
| `has_procedures` | boolean | Procedimientos |
| `has_monthly_reports` | boolean | Reportes mensuales |

### Sección 12 — Prioridades y SLA

| Clave | Tipo | Valores |
|-------|------|---------|
| `critical_response_time` | selection | `15_min`, `30_min`, `1_hora`, `2_horas`, `recomendacion_justech` |
| `critical_situations` | array | `sin_internet`, `servidor_caido`, `sistema_financiero`, `incidente_seguridad`, `correo_caido`, `oficina_parada`, `otra` |
| `other_critical_situation` | string | Otra situación |

### Sección 13 — Seguridad

| Clave | Tipo | Valores |
|-------|------|---------|
| `security_items` | array | `politicas_seguridad`, `politicas_respaldo`, `continuidad`, `auditorias`, `info_financiera`, `regulatorio`, `apoyo_controles` |
| `applicable_regulations` | text | Regulaciones |
| `confidentiality_requirements` | text | Confidencialidad |
| `technician_access_requirements` | text | Acceso técnicos |
| `nda_required` | boolean | NDA |

### Sección 14 — Objetivos

| Clave | Tipo | Valores |
|-------|------|---------|
| `outsourcing_objectives` | array | `tiempos_respuesta`, `reducir_interrupciones`, `especialistas`, `reducir_costos`, `ampliar_horario`, `mejorar_seguridad`, `formalizar_procesos`, `obtener_reportes`, `complementar_interno`, `sustituir_soporte`, `enfoque_estrategico` |

### Sección 15 — Inicio y presupuesto

| Clave | Tipo | Valores |
|-------|------|---------|
| `expected_start` | selection | `inmediato`, `30_dias`, `60_dias`, `90_dias`, `por_definir` |
| `budget_status` | selection | `definido`, `alternativas`, `no_indicar`, `por_definir` |
| `approximate_budget` | string | Opcional |

### Sección 16 — Comentarios

| Clave | Tipo |
|-------|------|
| `final_comments` | text |

### Envío final (no en `form_data` persistente separado — campos modelo)

| Clave request | Campo modelo |
|---------------|--------------|
| `completed_by_name` | `completed_by_name` |
| `completed_by_job` | `completed_by_job` |
| `acceptance_confirmed` | `acceptance_confirmed` |

## Archivos estáticos

- `static/src/css/assessment_public.css`
- `static/src/js/assessment_public.js`
- Cargados vía `<link>` / `<script>` en plantilla QWeb (aislamiento de `website.assets_frontend`).

## Secuencia

```xml
prefix="LEV-%(range_year)s-" padding="4" use_date_range="True"
```

## Tests

`tests/test_assessment.py` — TransactionCase post_install.
