from odoo import api, models

# Menús de aplicaciones fuera del alcance operativo Hellenia
HIDE_MENU_XMLIDS = (
    "crm.crm_menu_root",
    "point_of_sale.menu_point_root",
    "point_of_sale.menu_point_ofsale",
    "website.menu_website",
    "website.menu_website_configuration",
    "mrp.mrp_menu_root",
    "project.menu_main_pm",
    "helpdesk.helpdesk_menu_root",
    "hr.menu_hr_root",
    "fleet.fleet_vehicles",
    "lunch.menu_lunch",
    "survey.menu_surveys",
    "mass_mailing.mass_mailing_menu_root",
    "social.menu_social_global",
    "planning.planning_menu_root",
    "sign.menu_document",
    "documents.menu_root",
    "stock_barcode.stock_barcode_menu",
    "base.menu_tests",
    "spreadsheet_dashboard.spreadsheet_dashboard_menu_root",
    "utm.menu_link_tracker_root",
)

# Contenedores EE duplicados que no deben aparecer bajo Contabilidad
HIDE_ACCOUNTING_DUPLICATE_XMLIDS = (
    "account_accountant.menu_accounting",
    "accountant.menu_accounting",
)

# Nunca promover a hijo directo de Contabilidad (abre Ajustes o duplica estructura)
FINANCE_NEVER_ROOT_CHILDREN = (
    "account.menu_account_config",
    "account_accountant.menu_accounting",
    "accountant.menu_accounting",
)

# Submenús operativos que pertenecen bajo account.menu_finance
FINANCE_OPERATIONAL_XMLIDS = (
    "account.menu_board_journal_1",
    "account.menu_finance_receivables",
    "account.menu_finance_payables",
    "account.menu_action_move_journal_line_form",
    "account.menu_action_account_moves_all",
    "account.menu_finance_entries",
    "account.menu_finance_reports",
    "account.menu_finance_configuration",
)

# Secuencias del menú Contabilidad (Dashboard primero → abre tablero, no Ajustes)
FINANCE_CHILD_SEQUENCES = {
    "account.menu_board_journal_1": 1,
    "account.menu_finance_receivables": 10,
    "account.menu_finance_payables": 20,
    "account.menu_action_move_journal_line_form": 30,
    "account.menu_action_account_moves_all": 40,
    "account.menu_finance_reports": 50,
    "account.menu_finance_configuration": 90,
}

# Etiquetas español — raíz y submenús contables
MENU_LABELS_ES = {
    "account.menu_finance": "Contabilidad",
    "base.menu_administration": "Configuración",
    "sale.sale_menu_root": "Ventas",
    "purchase.menu_purchase_root": "Compras",
    "stock.menu_stock_root": "Inventario",
    "contacts.menu_contacts": "Contactos",
    "account.menu_board_journal_1": "Tablero",
    "account.menu_finance_receivables": "Clientes",
    "account.menu_finance_payables": "Proveedores",
    "account.menu_action_move_journal_line_form": "Asientos contables",
    "account.menu_action_account_moves_all": "Apuntes contables",
    "account.menu_finance_reports": "Reportes",
    "account.menu_finance_configuration": "Configuración",
    "account.menu_account_config": "Ajustes",
}

# Etiquetas español — Localización Justech
JUSTECH_MENU_LABELS_ES = {
    "justech_l10n_do_base.menu_justech_do_fiscal_root": "Localización Dominicana",
    "justech_l10n_do_base.menu_justech_do_document_types": "Tipos de NCF",
    "justech_l10n_do_ncf.menu_justech_do_ncf_ranges": "Rangos NCF",
    "justech_l10n_do_ncf.menu_justech_do_ncf_consumption": "Consumo NCF",
    "justech_l10n_do_base.menu_justech_do_fiscal_config": "Configuración fiscal",
    "justech_l10n_do_reports.menu_justech_do_reports_root": "Reportes DGII",
    "justech_l10n_do_reports.menu_justech_do_report_606": "606 — Compras",
    "justech_l10n_do_reports.menu_justech_do_report_607": "607 — Ventas",
    "justech_l10n_do_reports.menu_justech_do_report_608": "608 — Anulados",
    "justech_l10n_do_reports.menu_justech_do_reports_history": "Historial fiscal",
    "justech_l10n_do_reports.menu_justech_do_audit_root": "Auditoría",
    "justech_l10n_do_reports.menu_justech_do_audit_consumption": "Consumo NCF",
    "justech_l10n_do_reports.menu_justech_do_audit_voided": "NCF anulados",
}


class HelleniaUiMenuCustomizer(models.AbstractModel):
    _name = "hellenia.ui.menu.customizer"
    _description = "Hellenia UI — menú principal y ocultación de apps"

    @api.model
    def _active_langs(self):
        langs = self.env["res.lang"].search([("active", "=", True)]).mapped("code")
        return langs or ["es_DO", "es_419", "en_US"]

    @api.model
    def _set_menu_label(self, xmlid, label):
        menu = self.env.ref(xmlid, raise_if_not_found=False)
        if not menu:
            return False
        for lang in self._active_langs():
            menu.with_context(lang=lang).write({"name": label})
        return True

    @api.model
    def apply_menu_labels(self):
        """Nombres visibles en español en todos los idiomas activos."""
        for xmlid, label in MENU_LABELS_ES.items():
            self._set_menu_label(xmlid, label)
        for xmlid, label in JUSTECH_MENU_LABELS_ES.items():
            self._set_menu_label(xmlid, label)

    @api.model
    def hide_unused_menus(self):
        """Oculta módulos y menús técnicos no utilizados por Hellenia."""
        for xmlid in HIDE_MENU_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and menu.active:
                menu.active = False
        for xmlid in HIDE_ACCOUNTING_DUPLICATE_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and menu.active:
                menu.active = False

    @api.model
    def repair_accounting_menu_tree(self):
        """Reorganiza el árbol Contabilidad: tablero primero, sin duplicados ni Ajustes en raíz."""
        finance = self.env.ref("account.menu_finance", raise_if_not_found=False)
        if not finance:
            return

        finance.active = True
        finance.name = "Contabilidad"

        config_parent = self.env.ref("account.menu_finance_configuration", raise_if_not_found=False)
        settings = self.env.ref("account.menu_account_config", raise_if_not_found=False)

        # Ajustes debe vivir bajo Configuración contable, nunca como hijo directo de Contabilidad
        if settings and config_parent:
            if settings.parent_id != config_parent:
                settings.parent_id = config_parent.id
            settings.active = True

        # Desactivar contenedores EE duplicados
        for xid in HIDE_ACCOUNTING_DUPLICATE_XMLIDS:
            menu = self.env.ref(xid, raise_if_not_found=False)
            if menu and menu.active:
                menu.active = False

        # Reparentar solo submenús operativos huérfanos o bajo contenedores inactivos
        for xid in FINANCE_OPERATIONAL_XMLIDS:
            menu = self.env.ref(xid, raise_if_not_found=False)
            if not menu:
                continue
            parent = menu.parent_id
            if parent != finance and (not parent or not parent.active or parent.id == finance.id):
                menu.parent_id = finance.id
            menu.active = True

        # Sacar Settings/Ajustes y duplicados EE del nivel raíz de Contabilidad
        for child in self.env["ir.ui.menu"].search([("parent_id", "=", finance.id)]):
            xml_rec = self.env["ir.model.data"].search(
                [("model", "=", "ir.ui.menu"), ("res_id", "=", child.id)], limit=1
            )
            xid = f"{xml_rec.module}.{xml_rec.name}" if xml_rec else None
            if xid in FINANCE_NEVER_ROOT_CHILDREN or child.name in ("Settings", "Ajustes", "Accounting"):
                if settings and child.id == settings.id:
                    child.parent_id = config_parent.id if config_parent else child.parent_id
                elif xid in HIDE_ACCOUNTING_DUPLICATE_XMLIDS or child.name == "Accounting":
                    child.active = False
                elif child.name in ("Settings", "Ajustes") and config_parent:
                    child.parent_id = config_parent.id

        # Secuencias: Tablero primero para que Contabilidad abra el dashboard
        for xid, seq in FINANCE_CHILD_SEQUENCES.items():
            menu = self.env.ref(xid, raise_if_not_found=False)
            if menu:
                menu.sequence = seq

        if settings:
            settings.sequence = 1

        # Acción por defecto de Contabilidad → tablero contable
        dashboard = self.env.ref("account.menu_board_journal_1", raise_if_not_found=False)
        if dashboard and dashboard.action:
            finance.action = dashboard.action

        # Contenedores huérfanos con hijos contables
        orphans = self.env["ir.ui.menu"].search(
            [
                ("parent_id", "=", False),
                ("id", "!=", finance.id),
                ("name", "in", ["Accounting", "Contabilidad", "Invoicing", "Facturación"]),
            ]
        )
        for orphan in orphans:
            children = self.env["ir.ui.menu"].search([("parent_id", "=", orphan.id)])
            for child in children:
                xid_data = self.env["ir.model.data"].search(
                    [("model", "=", "ir.ui.menu"), ("res_id", "=", child.id)], limit=1
                )
                xid = f"{xid_data.module}.{xid_data.name}" if xid_data else None
                if xid in FINANCE_OPERATIONAL_XMLIDS or xid in FINANCE_NEVER_ROOT_CHILDREN:
                    if xid == "account.menu_account_config" and config_parent:
                        child.parent_id = config_parent.id
                    elif xid not in FINANCE_NEVER_ROOT_CHILDREN:
                        child.parent_id = finance.id
            orphan.active = False

    @api.model
    def integrate_justech_menus(self):
        """Asegura que la localización Justech quede integrada bajo Contabilidad."""
        fiscal_root = self.env.ref("justech_l10n_do_base.menu_justech_do_fiscal_root", raise_if_not_found=False)
        config_parent = self.env.ref("account.menu_finance_configuration", raise_if_not_found=False)
        reports_parent = self.env.ref("account.menu_finance_reports", raise_if_not_found=False)

        if fiscal_root and config_parent and fiscal_root.parent_id != config_parent:
            fiscal_root.parent_id = config_parent.id
            fiscal_root.active = True

        reports_root = self.env.ref("justech_l10n_do_reports.menu_justech_do_reports_root", raise_if_not_found=False)
        if reports_root and reports_parent and reports_root.parent_id != reports_parent:
            reports_root.parent_id = reports_parent.id
            reports_root.active = True

        audit_root = self.env.ref("justech_l10n_do_reports.menu_justech_do_audit_root", raise_if_not_found=False)
        finance = self.env.ref("account.menu_finance", raise_if_not_found=False)
        if audit_root and finance and audit_root.parent_id != finance:
            audit_root.parent_id = finance.id
            audit_root.sequence = 55
            audit_root.active = True

        for xmlid, label in JUSTECH_MENU_LABELS_ES.items():
            self._set_menu_label(xmlid, label)

    @api.model
    def apply_all(self):
        """Aplica todas las personalizaciones de menú en orden seguro."""
        self.apply_menu_labels()
        self.hide_unused_menus()
        self.repair_accounting_menu_tree()
        self.integrate_justech_menus()
