# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
"""Constantes y esquema de form_data para levantamientos públicos."""

FORM_TRACKED_KEYS = [
    # Sección 2 — Usuarios
    "employee_count_range",
    "support_users_count",
    "work_mode",
    # Sección 3 — Oficinas
    "office_count",
    "office_locations",
    "offices_connected",
    # Sección 4 — Equipos
    "qty_desktop",
    "qty_laptop",
    "qty_physical_server",
    "qty_virtual_server",
    "qty_printer",
    "qty_mobile",
    "qty_wireless_ap",
    "qty_network",
    "brands",
    # Sección 5 — Plataformas
    "platforms",
    "erp_main",
    "critical_apps",
    "other_platforms",
    # Sección 6 — Servicios a tercerizar
    "outsource_services",
    # Sección 7 — Niveles de soporte
    "support_levels",
    # Sección 8 — Horario
    "coverage_schedule",
    "coverage_start_time",
    "coverage_end_time",
    "holidays_operation",
    "custom_schedule_comment",
    # Sección 9 — Modalidad
    "service_modality",
    "onsite_frequency",
    # Sección 10 — Volumen
    "monthly_requests_range",
    "frequent_requests",
    # Sección 11 — Soporte actual
    "current_support_provider",
    "uses_ticket_platform",
    "ticket_platform_name",
    "has_inventory",
    "has_documentation",
    "has_procedures",
    "has_monthly_reports",
    # Sección 12 — Prioridades
    "critical_response_time",
    "critical_situations",
    "other_critical_situation",
    # Sección 13 — Seguridad
    "security_items",
    "applicable_regulations",
    "confidentiality_requirements",
    "technician_access_requirements",
    "nda_required",
    # Sección 14 — Objetivos
    "outsourcing_objectives",
    # Sección 15 — Inicio y presupuesto
    "expected_start",
    "budget_status",
    "approximate_budget",
    # Sección 16 — Comentarios
    "final_comments",
]

ORG_FIELD_MAP = {
    "org_company_name": "org_company_name",
    "org_vat": "org_vat",
    "org_address": "org_address",
    "org_responsible": "org_responsible",
    "org_job": "org_job",
    "org_email": "org_email",
    "org_phone": "org_phone",
}

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
