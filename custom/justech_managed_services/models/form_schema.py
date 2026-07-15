# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
"""Fuente única de verdad del formulario público de levantamientos.

Cada campo define:
- key técnica (clave de form_data / name HTML sin [])
- etiqueta visible en español
- sección (1-16)
- tipo (char, text, number, select, multiselect, boolean)
- opciones (value -> etiqueta) cuando aplica
- storage: column (org_*) o json
"""

SECTION_LABELS = {
    1: "Información de la organización",
    2: "Usuarios",
    3: "Oficinas y ubicaciones",
    4: "Equipos tecnológicos",
    5: "Plataformas y servicios actuales",
    6: "Servicios que desean tercerizar",
    7: "Niveles de soporte",
    8: "Horario de cobertura",
    9: "Modalidad del servicio",
    10: "Volumen de soporte",
    11: "Soporte actual",
    12: "Prioridades y SLA",
    13: "Seguridad y cumplimiento",
    14: "Objetivo de la tercerización",
    15: "Inicio y presupuesto",
    16: "Comentarios finales",
}

FORM_FIELDS = {
    # Sección 1
    "org_company_name": {
        "section": 1,
        "label": "Nombre de la empresa",
        "type": "char",
        "storage": "column",
    },
    "org_vat": {
        "section": 1,
        "label": "RNC",
        "type": "char",
        "storage": "column",
    },
    "org_address": {
        "section": 1,
        "label": "Dirección principal",
        "type": "char",
        "storage": "column",
    },
    "org_responsible": {
        "section": 1,
        "label": "Nombre del responsable",
        "type": "char",
        "storage": "column",
    },
    "org_job": {
        "section": 1,
        "label": "Cargo",
        "type": "char",
        "storage": "column",
    },
    "org_email": {
        "section": 1,
        "label": "Correo electrónico",
        "type": "char",
        "storage": "column",
    },
    "org_phone": {
        "section": 1,
        "label": "Teléfono",
        "type": "char",
        "storage": "column",
    },
    # Sección 2
    "employee_count_range": {
        "section": 2,
        "label": "Cantidad aproximada de empleados",
        "type": "select",
        "storage": "json",
        "options": {
            "1_25": "1 a 25",
            "26_50": "26 a 50",
            "51_100": "51 a 100",
            "101_250": "101 a 250",
            "250_plus": "Más de 250",
        },
    },
    "support_users_count": {
        "section": 2,
        "label": "Usuarios que requieren soporte",
        "type": "number",
        "storage": "json",
    },
    "work_mode": {
        "section": 2,
        "label": "Modalidad de trabajo",
        "type": "select",
        "storage": "json",
        "options": {
            "presencial": "Presencial",
            "remota": "Remota",
            "hibrida": "Híbrida",
        },
    },
    # Sección 3
    "office_count": {
        "section": 3,
        "label": "Cantidad de oficinas o sucursales",
        "type": "number",
        "storage": "json",
    },
    "office_locations": {
        "section": 3,
        "label": "Ciudades o ubicaciones",
        "type": "text",
        "storage": "json",
    },
    "offices_connected": {
        "section": 3,
        "label": "¿Oficinas conectadas entre sí?",
        "type": "select",
        "storage": "json",
        "options": {
            "si": "Sí",
            "no": "No",
            "parcialmente": "Parcialmente",
            "no_sabemos": "No sabemos",
        },
    },
    # Sección 4
    "qty_desktop": {
        "section": 4,
        "label": "Computadoras de escritorio",
        "type": "number",
        "storage": "json",
    },
    "qty_laptop": {
        "section": 4,
        "label": "Laptops",
        "type": "number",
        "storage": "json",
    },
    "qty_physical_server": {
        "section": 4,
        "label": "Servidores físicos",
        "type": "number",
        "storage": "json",
    },
    "qty_virtual_server": {
        "section": 4,
        "label": "Servidores virtuales",
        "type": "number",
        "storage": "json",
    },
    "qty_printer": {
        "section": 4,
        "label": "Impresoras",
        "type": "number",
        "storage": "json",
    },
    "qty_mobile": {
        "section": 4,
        "label": "Dispositivos móviles",
        "type": "number",
        "storage": "json",
    },
    "qty_wireless_ap": {
        "section": 4,
        "label": "Puntos de acceso inalámbrico",
        "type": "number",
        "storage": "json",
    },
    "qty_network": {
        "section": 4,
        "label": "Equipos de red",
        "type": "number",
        "storage": "json",
    },
    "brands": {
        "section": 4,
        "label": "Marcas utilizadas",
        "type": "multiselect",
        "storage": "json",
        "options": {
            "dell": "Dell",
            "hp": "HP",
            "lenovo": "Lenovo",
            "apple": "Apple",
            "cisco": "Cisco",
            "huawei": "Huawei",
            "fortinet": "Fortinet",
            "ubiquiti": "Ubiquiti",
            "otras": "Otras",
        },
    },
    # Sección 5
    "platforms": {
        "section": 5,
        "label": "Plataformas y servicios actuales",
        "type": "multiselect",
        "storage": "json",
        "options": {
            "m365": "Microsoft 365",
            "google_workspace": "Google Workspace",
            "azure": "Microsoft Azure",
            "aws": "Amazon Web Services",
            "ad_local": "Active Directory local",
            "entra_id": "Microsoft Entra ID",
            "vmware": "VMware",
            "hyper_v": "Hyper-V",
            "vpn": "VPN",
            "firewall": "Firewall empresarial",
            "antivirus": "Antivirus corporativo",
            "backup": "Sistema de respaldo",
            "erp": "ERP",
            "financial": "Sistema financiero",
            "document_mgmt": "Gestión documental",
            "voip": "Telefonía IP",
            "cctv": "CCTV",
            "access_control": "Control de acceso",
        },
    },
    "erp_main": {
        "section": 5,
        "label": "ERP o sistema principal",
        "type": "char",
        "storage": "json",
    },
    "critical_apps": {
        "section": 5,
        "label": "Aplicaciones críticas",
        "type": "text",
        "storage": "json",
    },
    "other_platforms": {
        "section": 5,
        "label": "Otras plataformas",
        "type": "text",
        "storage": "json",
    },
    # Sección 6
    "outsource_services": {
        "section": 6,
        "label": "Servicios que desean tercerizar",
        "type": "multiselect",
        "storage": "json",
        "options": {
            "mesa_ayuda": "Mesa de ayuda",
            "soporte_remoto": "Soporte remoto",
            "soporte_presencial": "Soporte presencial",
            "mant_preventivo": "Mantenimiento preventivo",
            "mant_correctivo": "Mantenimiento correctivo",
            "admin_servidores": "Administración de servidores",
            "admin_redes": "Administración de redes",
            "admin_m365": "Administración de Microsoft 365",
            "admin_usuarios": "Administración de usuarios y accesos",
            "gestion_respaldos": "Gestión de respaldos",
            "ciberseguridad": "Ciberseguridad",
            "antivirus": "Antivirus",
            "gestion_activos": "Gestión de activos",
            "gestion_inventario": "Gestión de inventario",
            "coord_proveedores": "Coordinación con proveedores",
            "instalacion_equipos": "Instalación de equipos",
            "config_computadoras": "Configuración de computadoras",
            "gestion_garantias": "Gestión de garantías",
            "soporte_impresoras": "Soporte a impresoras",
            "soporte_aplicaciones": "Soporte a aplicaciones",
            "reportes_servicio": "Reportes del servicio",
            "otro": "Otro",
        },
    },
    # Sección 7
    "support_levels": {
        "section": 7,
        "label": "Niveles de soporte requeridos",
        "type": "multiselect",
        "storage": "json",
        "options": {
            "nivel_1": "Nivel 1",
            "nivel_2": "Nivel 2",
            "nivel_3": "Nivel 3",
            "coord_fabricantes": "Coordinación con fabricantes o proveedores",
        },
    },
    # Sección 8
    "coverage_schedule": {
        "section": 8,
        "label": "Cobertura",
        "type": "select",
        "storage": "json",
        "options": {
            "laboral": "Lunes a viernes en horario laboral",
            "lunes_sabado": "Lunes a sábado",
            "extendido": "Horario extendido",
            "24x7": "24 horas, 7 días",
            "guardia": "Guardia para emergencias",
            "personalizado": "Horario personalizado",
        },
    },
    "coverage_start_time": {
        "section": 8,
        "label": "Hora de inicio",
        "type": "char",
        "storage": "json",
    },
    "coverage_end_time": {
        "section": 8,
        "label": "Hora de finalización",
        "type": "char",
        "storage": "json",
    },
    "holidays_operation": {
        "section": 8,
        "label": "Operación en días feriados",
        "type": "text",
        "storage": "json",
    },
    "custom_schedule_comment": {
        "section": 8,
        "label": "Comentario de horario personalizado",
        "type": "text",
        "storage": "json",
    },
    # Sección 9
    "service_modality": {
        "section": 9,
        "label": "Modalidad del servicio",
        "type": "select",
        "storage": "json",
        "options": {
            "remoto_principal": "Soporte principalmente remoto",
            "remoto_visitas": "Soporte remoto con visitas programadas",
            "presencial_parcial": "Técnico presencial algunos días",
            "presencial_completo": "Técnico presencial a tiempo completo",
            "equipo_dedicado": "Equipo dedicado",
            "equipo_compartido": "Equipo compartido",
            "bolsa_horas": "Bolsa de horas",
            "recomendacion_justech": "Recomendación de Justech",
        },
    },
    "onsite_frequency": {
        "section": 9,
        "label": "Frecuencia presencial",
        "type": "select",
        "storage": "json",
        "options": {
            "incidencia": "Cuando ocurra una incidencia",
            "mensual_1": "Una vez al mes",
            "mensual_2": "Dos veces al mes",
            "semanal_1": "Una vez por semana",
            "varios_dias": "Varios días por semana",
            "permanente": "Presencia permanente",
        },
    },
    # Sección 10
    "monthly_requests_range": {
        "section": 10,
        "label": "Cantidad aproximada de solicitudes mensuales",
        "type": "select",
        "storage": "json",
        "options": {
            "lt_25": "Menos de 25",
            "25_50": "25 a 50",
            "51_100": "51 a 100",
            "101_200": "101 a 200",
            "gt_200": "Más de 200",
            "sin_info": "No cuentan con información",
        },
    },
    "frequent_requests": {
        "section": 10,
        "label": "Solicitudes frecuentes",
        "type": "multiselect",
        "storage": "json",
        "options": {
            "passwords": "Contraseñas",
            "access": "Accesos",
            "email": "Correo",
            "pc_failures": "Fallas de computadoras",
            "printers": "Impresoras",
            "internet": "Internet",
            "networks": "Redes",
            "applications": "Aplicaciones",
            "m365": "Microsoft 365",
            "software_install": "Instalación de programas",
            "servers": "Servidores",
            "security": "Seguridad",
            "other": "Otros",
        },
    },
    # Sección 11
    "current_support_provider": {
        "section": 11,
        "label": "¿Quién brinda el soporte?",
        "type": "select",
        "storage": "json",
        "options": {
            "interno": "Personal interno",
            "externo": "Proveedor externo",
            "mixto": "Personal interno y proveedor",
            "sin_estructura": "No existe estructura formal",
        },
    },
    "uses_ticket_platform": {
        "section": 11,
        "label": "¿Utilizan plataforma de tickets?",
        "type": "boolean",
        "storage": "json",
    },
    "ticket_platform_name": {
        "section": 11,
        "label": "Nombre de la plataforma",
        "type": "char",
        "storage": "json",
    },
    "has_inventory": {
        "section": 11,
        "label": "¿Tienen inventario actualizado?",
        "type": "boolean",
        "storage": "json",
    },
    "has_documentation": {
        "section": 11,
        "label": "¿Tienen documentación técnica?",
        "type": "boolean",
        "storage": "json",
    },
    "has_procedures": {
        "section": 11,
        "label": "¿Tienen procedimientos de soporte?",
        "type": "boolean",
        "storage": "json",
    },
    "has_monthly_reports": {
        "section": 11,
        "label": "¿Tienen reportes mensuales?",
        "type": "boolean",
        "storage": "json",
    },
    # Sección 12
    "critical_response_time": {
        "section": 12,
        "label": "Tiempo esperado de respuesta (incidencias críticas)",
        "type": "select",
        "storage": "json",
        "options": {
            "15_min": "15 minutos",
            "30_min": "30 minutos",
            "1_hora": "1 hora",
            "2_horas": "2 horas",
            "recomendacion_justech": "Recomendación de Justech",
        },
    },
    "critical_situations": {
        "section": 12,
        "label": "Situaciones críticas",
        "type": "multiselect",
        "storage": "json",
        "options": {
            "sin_internet": "Empresa sin internet",
            "servidor_caido": "Servidor principal fuera de servicio",
            "sistema_financiero": "Sistema financiero no disponible",
            "incidente_seguridad": "Incidente de seguridad",
            "correo_caido": "Correo fuera de servicio",
            "oficina_parada": "Oficina completa sin operación",
            "otra": "Otra",
        },
    },
    "other_critical_situation": {
        "section": 12,
        "label": "Otra situación crítica",
        "type": "char",
        "storage": "json",
    },
    # Sección 13
    "security_items": {
        "section": 13,
        "label": "Seguridad y cumplimiento",
        "type": "multiselect",
        "storage": "json",
        "options": {
            "politicas_seguridad": "Políticas de seguridad",
            "politicas_respaldo": "Políticas de respaldo",
            "continuidad": "Plan de continuidad",
            "auditorias": "Auditorías periódicas",
            "info_financiera": "Información financiera sensible",
            "regulatorio": "Requerimientos regulatorios",
            "apoyo_controles": "Necesidad de apoyo para establecer controles",
        },
    },
    "applicable_regulations": {
        "section": 13,
        "label": "Regulaciones aplicables",
        "type": "text",
        "storage": "json",
    },
    "confidentiality_requirements": {
        "section": 13,
        "label": "Requisitos de confidencialidad",
        "type": "text",
        "storage": "json",
    },
    "technician_access_requirements": {
        "section": 13,
        "label": "Requisitos para acceso de técnicos",
        "type": "text",
        "storage": "json",
    },
    "nda_required": {
        "section": 13,
        "label": "Necesidad de NDA",
        "type": "boolean",
        "storage": "json",
    },
    # Sección 14
    "outsourcing_objectives": {
        "section": 14,
        "label": "Objetivo de la tercerización",
        "type": "multiselect",
        "storage": "json",
        "options": {
            "tiempos_respuesta": "Mejorar tiempos de respuesta",
            "reducir_interrupciones": "Reducir interrupciones",
            "especialistas": "Contar con especialistas",
            "reducir_costos": "Reducir costos",
            "ampliar_horario": "Ampliar horario",
            "mejorar_seguridad": "Mejorar seguridad",
            "formalizar_procesos": "Formalizar procesos",
            "obtener_reportes": "Obtener reportes",
            "complementar_interno": "Complementar personal interno",
            "sustituir_soporte": "Sustituir soporte actual",
            "enfoque_estrategico": "Concentrar el equipo interno en funciones estratégicas",
        },
    },
    # Sección 15
    "expected_start": {
        "section": 15,
        "label": "Fecha esperada de inicio",
        "type": "select",
        "storage": "json",
        "options": {
            "inmediato": "Inmediatamente",
            "30_dias": "Dentro de 30 días",
            "60_dias": "Dentro de 60 días",
            "90_dias": "Dentro de 90 días",
            "por_definir": "Por definir",
        },
    },
    "budget_status": {
        "section": 15,
        "label": "Presupuesto",
        "type": "select",
        "storage": "json",
        "options": {
            "definido": "Existe presupuesto definido",
            "alternativas": "Desean recibir alternativas",
            "no_indicar": "No desean indicarlo",
            "por_definir": "Por definir",
        },
    },
    "approximate_budget": {
        "section": 15,
        "label": "Presupuesto aproximado (opcional)",
        "type": "char",
        "storage": "json",
    },
    # Sección 16
    "final_comments": {
        "section": 16,
        "label": "Comentarios finales",
        "type": "text",
        "storage": "json",
    },
    # Meta revisión (no cuentan para % de secciones 1-16)
    "completed_by_name": {
        "section": 17,
        "label": "Nombre de quien completa",
        "type": "char",
        "storage": "meta",
    },
    "completed_by_job": {
        "section": 17,
        "label": "Cargo de quien completa",
        "type": "char",
        "storage": "meta",
    },
}


def _fields_by_storage(storage):
    return [key for key, meta in FORM_FIELDS.items() if meta.get("storage") == storage]


ORG_FIELD_MAP = {key: key for key in _fields_by_storage("column")}
FORM_TRACKED_KEYS = _fields_by_storage("json")
FIELD_LABELS = {key: meta["label"] for key, meta in FORM_FIELDS.items()}
OPTION_LABELS = {
    key: meta.get("options") or {}
    for key, meta in FORM_FIELDS.items()
    if meta.get("options")
}


def is_value_filled(value):
    """Regla única de completitud para backend y cliente."""
    if value is None or value is False:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, dict, tuple, set)) and not value:
        return False
    return True


def format_field_value(key, value):
    """Formato de impresión legible en español."""
    meta = FORM_FIELDS.get(key) or {}
    ftype = meta.get("type")
    options = meta.get("options") or {}

    if ftype == "boolean":
        if value is True or value == "true" or value == 1 or value == "1":
            return "Sí"
        if value is False or value == "false" or value == 0 or value == "0":
            return "No"
        return ""

    if ftype == "multiselect":
        items = value if isinstance(value, (list, tuple)) else ([value] if value else [])
        labels = [options.get(str(item), str(item)) for item in items if item not in (None, "")]
        return ", ".join(labels)

    if ftype == "select":
        if value in (None, ""):
            return ""
        return options.get(str(value), str(value))

    if value in (None, False):
        return ""
    return str(value)


def build_sections_display(raw_values):
    """Lista de secciones con filas etiqueta/valor para resumen y PDF."""
    values = dict(raw_values or {})
    sections = []
    for section_num in range(1, 17):
        rows = []
        for key, meta in FORM_FIELDS.items():
            if meta.get("section") != section_num:
                continue
            if meta.get("storage") == "meta":
                continue
            value = values.get(key)
            if not is_value_filled(value) and meta.get("type") != "boolean":
                continue
            if meta.get("type") == "boolean" and value not in (True, False, "true", "false", 1, 0, "1", "0"):
                continue
            display = format_field_value(key, value)
            if display == "" and meta.get("type") != "boolean":
                continue
            rows.append(
                {
                    "key": key,
                    "label": meta["label"],
                    "value": display,
                    "raw": value,
                    "type": meta.get("type"),
                }
            )
        sections.append(
            {
                "number": section_num,
                "title": SECTION_LABELS[section_num],
                "heading": "%s. %s" % (section_num, SECTION_LABELS[section_num]),
                "rows": rows,
            }
        )
    return sections


def compute_completion_percent(raw_values):
    """Porcentaje basado en campos de secciones 1-16 (column + json)."""
    tracked = list(ORG_FIELD_MAP.keys()) + list(FORM_TRACKED_KEYS)
    total = len(tracked)
    if not total:
        return 0.0
    data = raw_values or {}
    filled = sum(1 for key in tracked if is_value_filled(data.get(key)))
    return round((filled / total) * 100.0, 2)


def labels_payload():
    """Payload JS para etiquetas de campo y opción."""
    return {
        "field_labels": FIELD_LABELS,
        "option_labels": OPTION_LABELS,
        "section_labels": {str(k): v for k, v in SECTION_LABELS.items()},
        "tracked_keys": list(ORG_FIELD_MAP.keys()) + list(FORM_TRACKED_KEYS),
    }
