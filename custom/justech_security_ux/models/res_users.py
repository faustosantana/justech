# -*- coding: utf-8 -*-
"""Permisos Justech — interfaz sobre res.groups reales (sync quirúrgico)."""
from odoo import api, fields, models

from .modules_registry import JX_MODULES


def _level_fname(key):
    return "jx_lvl_%s" % key


def _cap_fname(code):
    return "jx_cap_%s" % code


def _show_fname(key):
    return "jx_show_%s" % key


def _card_fname(key):
    return "jx_card_%s" % key


class ResUsers(models.Model):
    _inherit = "res.users"

    jx_help = fields.Char(
        string="Ayuda",
        default=(
            "Configure varios módulos a la vez. Cada sección modifica solo sus "
            "grupos Odoo. Use Permisos Avanzados solo para excepciones técnicas."
        ),
    )
    jx_summary_modules = fields.Text(
        string="Módulos con acceso", compute="_compute_jx_summary"
    )
    jx_summary_can = fields.Text(string="Puede", compute="_compute_jx_summary")
    jx_summary_cannot = fields.Text(string="No puede", compute="_compute_jx_summary")
    jx_summary_warnings = fields.Text(
        string="Advertencias", compute="_compute_jx_summary"
    )
    jx_tech_detail = fields.Text(
        string="Implementación técnica", compute="_compute_jx_summary"
    )

    # ------------------------------------------------------------------ registry helpers
    @api.model
    def _jx_modules(self):
        return JX_MODULES

    @api.model
    def _jx_module_installed(self, module_name):
        return bool(
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", module_name), ("state", "=", "installed")], limit=1)
        )

    @api.model
    def _jx_section_visible(self, section):
        for mod in section.get("modules") or ():
            if not self._jx_module_installed(mod):
                return False
        return True

    @api.model
    def _jx_resolve(self, xmlids):
        groups = self.env["res.groups"]
        for xmlid in xmlids or ():
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    @api.model
    def _jx_level_by_code(self, section, code):
        for level in section.get("levels") or ():
            if level["code"] == code:
                return level
        return None

    @api.model
    def _jx_cap_by_code(self, code):
        for section in JX_MODULES:
            for cap in section.get("caps") or ():
                if cap["code"] == code:
                    return cap, section
        return None, None

    def _jx_user_has_all(self, user, xmlids):
        if not xmlids:
            return False
        for xmlid in xmlids:
            if not self.env.ref(xmlid, raise_if_not_found=False):
                return False
            if not user.has_group(xmlid):
                return False
        return True

    def _jx_detect_level(self, user, section):
        best = "none"
        best_idx = -1
        for idx, level in enumerate(section.get("levels") or ()):
            if level["code"] == "none":
                continue
            # level may require optional modules
            for mod in level.get("modules") or ():
                if not self._jx_module_installed(mod):
                    break
            else:
                if level["xmlids"] and self._jx_user_has_all(user, level["xmlids"]):
                    if idx > best_idx:
                        best = level["code"]
                        best_idx = idx
        return best

    def _jx_ladder_groups(self, section):
        groups = self.env["res.groups"]
        for level in section.get("levels") or ():
            groups |= self._jx_resolve(level.get("xmlids"))
        groups |= self._jx_resolve(section.get("ladder_extra_xmlids"))
        return groups

    def _jx_apply_group_delta(self, user, add_groups, remove_groups):
        """Add/remove ONLY the given groups; never wipe group_ids / company_ids."""
        commands = []
        for group in add_groups:
            if group not in user.group_ids:
                commands.append((4, group.id))
        for group in remove_groups:
            if group in user.group_ids:
                commands.append((3, group.id))
        if commands:
            user.with_context(justech_security_ux_sync=True).write(
                {"group_ids": commands}
            )

    def _jx_sync_level(self, user, section_key, selected_code):
        section = next((s for s in JX_MODULES if s["key"] == section_key), None)
        if not section:
            return
        ladder = self._jx_ladder_groups(section)
        if not ladder and selected_code == "none":
            return
        level = self._jx_level_by_code(section, selected_code) or {
            "code": "none",
            "xmlids": (),
        }
        desired = self._jx_resolve(level.get("xmlids"))
        # Quitar otros del mismo ladder (solo membrecías explícitas)
        remove = ladder - desired
        self._jx_apply_group_delta(user, desired, remove)

    def _jx_sync_cap(self, user, cap_code, enabled):
        cap, section = self._jx_cap_by_code(cap_code)
        if not cap:
            return
        # Alias a nivel Contabilidad/Facturación: no tocar fuera de ese grupo
        groups = self._jx_resolve(cap.get("xmlids"))
        if not groups:
            return
        if enabled:
            self._jx_apply_group_delta(user, groups, self.env["res.groups"])
        else:
            # No retirar si el grupo es el nivel deseado de Contabilidad
            alias = cap.get("aliases_level")
            if alias:
                mod_key, level_code = alias
                lvl_fname = _level_fname(mod_key)
                if lvl_fname in user._fields and user[lvl_fname] == level_code:
                    return
                # Si el nivel efectivo de accounting es >= invoice, no forzar retiro
                # al desmarcar el atajo de Pagos (evita pelea entre secciones)
                if mod_key == "accounting" and self._jx_user_has_all(
                    user, ("account.group_account_invoice",)
                ):
                    # Permitir retiro solo si el usuario pidió none en accounting
                    if lvl_fname in user._fields and user[lvl_fname] != "none":
                        return
            self._jx_apply_group_delta(user, self.env["res.groups"], groups)

    # ------------------------------------------------------------------ field factory (declared below explicitly for Odoo)

    # Visibility
    jx_show_sales = fields.Boolean(compute="_compute_jx_show")
    jx_show_purchase = fields.Boolean(compute="_compute_jx_show")
    jx_show_inventory = fields.Boolean(compute="_compute_jx_show")
    jx_show_accounting = fields.Boolean(compute="_compute_jx_show")
    jx_show_fiscal = fields.Boolean(compute="_compute_jx_show")
    jx_show_payments = fields.Boolean(compute="_compute_jx_show")
    jx_show_withholding = fields.Boolean(compute="_compute_jx_show")
    jx_show_ecf = fields.Boolean(compute="_compute_jx_show")
    jx_show_warranty = fields.Boolean(compute="_compute_jx_show")
    jx_show_fees = fields.Boolean(compute="_compute_jx_show")
    jx_show_crm = fields.Boolean(compute="_compute_jx_show")
    jx_show_hr = fields.Boolean(compute="_compute_jx_show")
    jx_show_admin = fields.Boolean(compute="_compute_jx_show")

    # Levels
    jx_lvl_sales = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("own", "Usuario: solo sus documentos"),
            ("all", "Usuario: todos los documentos"),
            ("manager", "Administrador"),
        ],
        string="Nivel Ventas",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_sales",
    )
    jx_lvl_purchase = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
        ],
        string="Nivel Compras",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_purchase",
    )
    jx_lvl_inventory = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("user", "Usuario"),
            ("manager", "Administrador"),
        ],
        string="Nivel Inventario",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_inventory",
    )
    jx_lvl_accounting = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("invoice", "Facturación"),
            ("accountant", "Contabilidad"),
            ("manager", "Administrador"),
        ],
        string="Nivel Contabilidad",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_accounting",
    )
    jx_lvl_fiscal = fields.Selection(
        selection=[
            ("none", "Sin acceso fiscal"),
            ("user", "Usuario Fiscal"),
            ("officer", "Responsable Fiscal"),
            ("admin", "Administrador Fiscal"),
        ],
        string="Nivel Fiscal",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_fiscal",
    )
    jx_lvl_withholding = fields.Selection(
        selection=[
            ("none", "Sin administración de catálogo"),
            ("catalog_admin", "Administrador de Retenciones"),
        ],
        string="Nivel Retenciones",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_withholding",
    )
    jx_lvl_ecf = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("readonly", "Solo lectura e-CF"),
            ("operator", "Operador e-CF"),
            ("responsible", "Responsable e-CF"),
            ("admin", "Administrador e-CF"),
        ],
        string="Nivel e-CF",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_ecf",
    )
    jx_lvl_warranty = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("user", "Usuario de Garantías"),
            ("manager", "Administrador de Garantías"),
        ],
        string="Nivel Garantías",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_warranty",
    )
    jx_lvl_fees = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("user", "Usuario Fees"),
            ("manager", "Responsable Fees"),
        ],
        string="Nivel Fees",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_fees",
    )
    jx_lvl_crm = fields.Selection(
        selection=[
            ("none", "Sin flag de Leads"),
            ("leads", "Usar Leads"),
        ],
        string="Nivel CRM",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_crm",
    )
    jx_lvl_hr = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("user", "Encargado"),
            ("manager", "Administrador"),
        ],
        string="Nivel RRHH",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_hr",
    )
    jx_lvl_admin = fields.Selection(
        selection=[
            ("none", "Sin acceso"),
            ("user", "Usuario consola Justech"),
            ("manager", "Administrador Justech"),
        ],
        string="Nivel Administración Justech",
        compute="_compute_jx_levels",
        inverse="_inverse_jx_lvl_admin",
    )

    # Cards
    jx_card_sales = fields.Text(compute="_compute_jx_cards")
    jx_card_purchase = fields.Text(compute="_compute_jx_cards")
    jx_card_inventory = fields.Text(compute="_compute_jx_cards")
    jx_card_accounting = fields.Text(compute="_compute_jx_cards")
    jx_card_fiscal = fields.Text(compute="_compute_jx_cards")
    jx_card_payments = fields.Text(compute="_compute_jx_cards")
    jx_card_withholding = fields.Text(compute="_compute_jx_cards")
    jx_card_ecf = fields.Text(compute="_compute_jx_cards")
    jx_card_warranty = fields.Text(compute="_compute_jx_cards")
    jx_card_fees = fields.Text(compute="_compute_jx_cards")
    jx_card_crm = fields.Text(compute="_compute_jx_cards")
    jx_card_hr = fields.Text(compute="_compute_jx_cards")
    jx_card_admin = fields.Text(compute="_compute_jx_cards")

    # Caps
    jx_cap_so_discount = fields.Boolean(
        string="Aplicar descuentos en líneas",
        compute="_compute_jx_caps",
        inverse="_inverse_jx_cap_so_discount",
        help="sale.group_discount_per_so_line",
    )
    jx_cap_so_credit_note = fields.Boolean(
        string="Emitir notas de crédito fiscales",
        compute="_compute_jx_caps",
        inverse="_inverse_jx_cap_so_credit_note",
    )
    jx_cap_so_cancel_fiscal = fields.Boolean(
        string="Cancelar facturas fiscales",
        compute="_compute_jx_caps",
        inverse="_inverse_jx_cap_so_cancel_fiscal",
    )
    jx_cap_stk_lots = fields.Boolean(
        string="Registrar seriales / lotes",
        compute="_compute_jx_caps",
        inverse="_inverse_jx_cap_stk_lots",
    )
    jx_cap_pay_invoice_access = fields.Boolean(
        string="Acceso a facturación y pagos (grupo Odoo)",
        compute="_compute_jx_caps",
        inverse="_inverse_jx_cap_pay_invoice_access",
        help=(
            "ADVERTENCIA: account.group_account_invoice concede facturación + "
            "cobros + pagos + aplicación. No hay segregación fina."
        ),
    )
    jx_cap_pay_bank_validate = fields.Boolean(
        string="Validar / administrar cuentas bancarias",
        compute="_compute_jx_caps",
        inverse="_inverse_jx_cap_pay_bank_validate",
    )
    jx_cap_ecf_auditor = fields.Boolean(
        string="Auditor e-CF",
        compute="_compute_jx_caps",
        inverse="_inverse_jx_cap_ecf_auditor",
    )

    # ------------------------------------------------------------------ computes / inverses
    @api.depends_context("uid")
    def _compute_jx_show(self):
        visibility = {
            s["key"]: self._jx_section_visible(s) for s in JX_MODULES
        }
        for user in self:
            for key, visible in visibility.items():
                fname = _show_fname(key)
                if fname in user._fields:
                    user[fname] = visible

    @api.depends("group_ids")
    def _compute_jx_levels(self):
        by_key = {s["key"]: s for s in JX_MODULES}
        for user in self:
            for key, section in by_key.items():
                fname = _level_fname(key)
                if fname not in user._fields:
                    continue
                if not section.get("levels"):
                    continue
                user[fname] = self._jx_detect_level(user, section)

    @api.depends("group_ids")
    def _compute_jx_caps(self):
        for user in self:
            for section in JX_MODULES:
                for cap in section.get("caps") or ():
                    fname = _cap_fname(cap["code"])
                    if fname not in user._fields:
                        continue
                    mods_ok = True
                    for mod in cap.get("modules") or ():
                        if not self._jx_module_installed(mod):
                            mods_ok = False
                            break
                    user[fname] = bool(
                        mods_ok and self._jx_user_has_all(user, cap.get("xmlids"))
                    )

    @api.depends(
        "group_ids",
        "jx_lvl_sales",
        "jx_lvl_purchase",
        "jx_lvl_inventory",
        "jx_lvl_accounting",
        "jx_lvl_fiscal",
        "jx_lvl_withholding",
        "jx_lvl_ecf",
        "jx_lvl_warranty",
        "jx_lvl_fees",
        "jx_lvl_crm",
        "jx_lvl_hr",
        "jx_lvl_admin",
    )
    def _compute_jx_cards(self):
        for user in self:
            for section in JX_MODULES:
                fname = _card_fname(section["key"])
                if fname not in user._fields:
                    continue
                lines = []
                notes = section.get("notes") or ()
                if notes:
                    lines.extend(notes)
                    lines.append("")
                lvl_fname = _level_fname(section["key"])
                level = None
                if lvl_fname in user._fields and section.get("levels"):
                    level = self._jx_level_by_code(section, user[lvl_fname])
                if level:
                    lines.append(level["label"])
                    lines.append("Riesgo: %s" % level.get("risk", "—"))
                    if level.get("can"):
                        lines.append("Puede:")
                        lines.extend("• %s" % x for x in level["can"])
                    if level.get("cannot"):
                        lines.append("No puede:")
                        lines.extend("• %s" % x for x in level["cannot"])
                    if level.get("warning"):
                        lines.append("")
                        lines.append("⚠ %s" % level["warning"])
                    if level.get("xmlids"):
                        lines.append("")
                        lines.append("Ver implementación técnica:")
                        lines.extend("• %s" % x for x in level["xmlids"])
                elif section.get("caps") and not section.get("levels"):
                    lines.append("Capacidades asignables (grupos reales):")
                    for cap in section["caps"]:
                        on = user[_cap_fname(cap["code"])] if _cap_fname(cap["code"]) in user._fields else False
                        mark = "✓" if on else "☐"
                        lines.append("%s %s" % (mark, cap["label"]))
                        if cap.get("warning"):
                            lines.append("  ⚠ %s" % cap["warning"])
                user[fname] = "\n".join(lines) if lines else "—"

    @api.depends("group_ids", "company_ids")
    def _compute_jx_summary(self):
        for user in self:
            modules_lines = []
            can, cannot, warnings, tech = [], [], [], []
            for section in JX_MODULES:
                if not self._jx_section_visible(section):
                    continue
                lvl_fname = _level_fname(section["key"])
                if lvl_fname in user._fields and section.get("levels"):
                    code = user[lvl_fname]
                    level = self._jx_level_by_code(section, code)
                    if level and code != "none":
                        modules_lines.append(
                            "• %s: %s" % (section["label"], level["label"])
                        )
                        can.extend(level.get("can") or ())
                        cannot.extend(level.get("cannot") or ())
                        if level.get("warning"):
                            warnings.append("• %s: %s" % (section["label"], level["warning"]))
                        for xmlid in level.get("xmlids") or ():
                            tech.append("• %s → %s" % (section["label"], xmlid))
                for cap in section.get("caps") or ():
                    fname = _cap_fname(cap["code"])
                    if fname in user._fields and user[fname]:
                        can.extend(cap.get("can") or ())
                        if cap.get("warning"):
                            warnings.append("• %s" % cap["warning"])
                        for xmlid in cap.get("xmlids") or ():
                            tech.append("• %s → %s" % (cap["label"], xmlid))
            if len(user.company_ids) > 1:
                warnings.append(
                    "• El usuario tiene acceso a %s empresas." % len(user.company_ids)
                )
            # dedupe preserve order
            def uniq(seq):
                seen = set()
                out = []
                for item in seq:
                    if item in seen:
                        continue
                    seen.add(item)
                    out.append(item)
                return out

            user.jx_summary_modules = (
                "\n".join(modules_lines) if modules_lines else "—"
            )
            user.jx_summary_can = (
                "\n".join("• %s" % x for x in uniq(can)) if can else "—"
            )
            user.jx_summary_cannot = (
                "\n".join("• %s" % x for x in uniq(cannot)[:12]) if cannot else "—"
            )
            user.jx_summary_warnings = (
                "\n".join(uniq(warnings)) if warnings else "—"
            )
            user.jx_tech_detail = "\n".join(uniq(tech)) if tech else "—"

    # Level inverses (surgical per module)
    def _inverse_jx_lvl_sales(self):
        for u in self:
            self._jx_sync_level(u, "sales", u.jx_lvl_sales or "none")

    def _inverse_jx_lvl_purchase(self):
        for u in self:
            self._jx_sync_level(u, "purchase", u.jx_lvl_purchase or "none")

    def _inverse_jx_lvl_inventory(self):
        for u in self:
            self._jx_sync_level(u, "inventory", u.jx_lvl_inventory or "none")

    def _inverse_jx_lvl_accounting(self):
        for u in self:
            self._jx_sync_level(u, "accounting", u.jx_lvl_accounting or "none")

    def _inverse_jx_lvl_fiscal(self):
        for u in self:
            self._jx_sync_level(u, "fiscal", u.jx_lvl_fiscal or "none")

    def _inverse_jx_lvl_withholding(self):
        for u in self:
            self._jx_sync_level(u, "withholding", u.jx_lvl_withholding or "none")

    def _inverse_jx_lvl_ecf(self):
        for u in self:
            self._jx_sync_level(u, "ecf", u.jx_lvl_ecf or "none")

    def _inverse_jx_lvl_warranty(self):
        for u in self:
            self._jx_sync_level(u, "warranty", u.jx_lvl_warranty or "none")

    def _inverse_jx_lvl_fees(self):
        for u in self:
            self._jx_sync_level(u, "fees", u.jx_lvl_fees or "none")

    def _inverse_jx_lvl_crm(self):
        for u in self:
            self._jx_sync_level(u, "crm", u.jx_lvl_crm or "none")

    def _inverse_jx_lvl_hr(self):
        for u in self:
            self._jx_sync_level(u, "hr", u.jx_lvl_hr or "none")

    def _inverse_jx_lvl_admin(self):
        for u in self:
            self._jx_sync_level(u, "admin", u.jx_lvl_admin or "none")

    # Cap inverses
    def _inverse_jx_cap_so_discount(self):
        for u in self:
            self._jx_sync_cap(u, "so_discount", bool(u.jx_cap_so_discount))

    def _inverse_jx_cap_so_credit_note(self):
        for u in self:
            self._jx_sync_cap(u, "so_credit_note", bool(u.jx_cap_so_credit_note))

    def _inverse_jx_cap_so_cancel_fiscal(self):
        for u in self:
            self._jx_sync_cap(u, "so_cancel_fiscal", bool(u.jx_cap_so_cancel_fiscal))

    def _inverse_jx_cap_stk_lots(self):
        for u in self:
            self._jx_sync_cap(u, "stk_lots", bool(u.jx_cap_stk_lots))

    def _inverse_jx_cap_pay_invoice_access(self):
        for u in self:
            # Mantener coherencia con nivel Contabilidad
            if u.jx_cap_pay_invoice_access:
                if u.jx_lvl_accounting in (False, "none"):
                    u.with_context(justech_security_ux_skip_level_reenter=True)
                    self._jx_sync_level(u, "accounting", "invoice")
                else:
                    self._jx_sync_cap(u, "pay_invoice_access", True)
            else:
                if u.jx_lvl_accounting == "invoice":
                    self._jx_sync_level(u, "accounting", "none")
                elif u.jx_lvl_accounting in ("accountant", "manager"):
                    # no degradar niveles superiores desde el atajo de Pagos
                    return
                else:
                    self._jx_sync_cap(u, "pay_invoice_access", False)

    def _inverse_jx_cap_pay_bank_validate(self):
        for u in self:
            self._jx_sync_cap(u, "pay_bank_validate", bool(u.jx_cap_pay_bank_validate))

    def _inverse_jx_cap_ecf_auditor(self):
        for u in self:
            self._jx_sync_cap(u, "ecf_auditor", bool(u.jx_cap_ecf_auditor))
