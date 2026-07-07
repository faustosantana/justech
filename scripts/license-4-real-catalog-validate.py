#!/usr/bin/env python3
"""LICENSE-4 real license catalog validation."""
import json
import os

FORBIDDEN = {
    "help desk",
    "gestión documental",
    "gestion documental",
    "firma digital",
    "facturación electrónica",
    "facturacion electronica",
    "portal de clientes",
    "portal de proveedores",
    "workflow compras",
    "workflow comercial",
    "ventas corporativas",
    "compras corporativas",
    "recursos humanos",
    "power bi",
    "whatsapp",
    "microsoft 365",
    "api justech",
    "dashboard gerencial",
    "multiempresa avanzada",
    "crm",
    "ventas",
    "compras",
    "inventario",
    "sales",
    "purchase",
    "stock",
    "account",
    "contacts",
}

EXPECTED_CLIENT = {
    "Fiscal RD / NCF / DGII",
    "Reportes y Documentos Corporativos",
    "UX Fiscal / Contactos y Facturas",
    "Motor Comercial Multimoneda",
    "Auditoría",
}

result = {"phase": "LICENSE-4", "status": "FAIL", "checks": {}, "modules": []}

env = env  # noqa: F821
LicenseSvc = env["justech.license.service"]
Wizard = env["justech.license.admin.wizard"]

rows = LicenseSvc.get_license_wizard_catalog()
names = [r["product_name"] for r in rows]
result["modules"] = names
result["checks"]["catalog_count"] = len(rows)
result["checks"]["max_six_for_internal"] = len(rows) <= 6

forbidden = [n for n in names if n.lower() in FORBIDDEN]
result["checks"]["no_invented_modules"] = not forbidden
result["checks"]["forbidden_hits"] = forbidden

result["checks"]["all_have_product_name"] = all(
    (r.get("product_name") or "").strip() for r in rows
)

defaults = Wizard.with_context(default_mode="create").default_get(
    ["module_line_ids"]
)
lines = defaults.get("module_line_ids") or []
result["checks"]["wizard_default_lines"] = len(lines) == len(rows)
result["checks"]["wizard_product_names"] = all(
    cmd[2].get("product_name") for cmd in lines if cmd[0] == 0
)
result["checks"]["no_product_name_error"] = result["checks"]["wizard_product_names"]

internal_group = env.ref("justech_modules.group_justech_internal_admin")
is_internal = internal_group in env.user.group_ids
if is_internal:
    result["checks"]["includes_control_justech"] = any(
        r.get("customization_code") == "control_justech_interno" for r in rows
    )
else:
    result["checks"]["client_core_modules"] = EXPECTED_CLIENT.issubset(set(names))
    result["checks"]["client_max_five"] = len(rows) <= 5

# License create dry-run (structure only)
wiz = Wizard.new(
    {
        "mode": "create",
        "company_id": env.company.id,
        "license_name": env.company.name,
        "tier": "PRO",
    }
)
commands = Wizard._build_catalog_commands()
result["checks"]["wizard_create_lines_ok"] = bool(commands) and all(
    cmd[2].get("product_name") for cmd in commands
)
sample_codes = [
    cmd[2]["product_code"]
    for cmd in commands
    if cmd[0] == 0 and cmd[2].get("product_code")
]
result["checks"]["selected_product_codes"] = bool(sample_codes)

passed = (
    result["checks"]["no_invented_modules"]
    and result["checks"]["all_have_product_name"]
    and result["checks"]["wizard_product_names"]
    and result["checks"]["wizard_create_lines_ok"]
    and result["checks"]["selected_product_codes"]
    and result["checks"].get("max_six_for_internal", True)
)
if is_internal:
    passed = passed and result["checks"].get("includes_control_justech", False)
else:
    passed = passed and result["checks"].get("client_core_modules", False)

result["status"] = "PASS" if passed else "FAIL"

out = os.environ.get("LICENSE4_EVIDENCE", "/var/lib/odoo/license-4-validation.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=2, default=str)
print("LICENSE4:", json.dumps(result))
