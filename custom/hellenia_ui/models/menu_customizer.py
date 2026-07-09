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

# Submenús operativos de primer nivel bajo account.menu_finance (sin asientos/apuntes en raíz)
FINANCE_OPERATIONAL_XMLIDS = (
    "account.menu_board_journal_1",
    "account.menu_finance_receivables",
    "account.menu_finance_payables",
    "account.menu_finance_entries",
    "account.menu_finance_reports",
    "account.menu_finance_configuration",
    "hellenia_ui.menu_finance_payments_root",
)

# Secuencias raíz Contabilidad (HELLENIA-MENU-UAT-2)
FINANCE_CHILD_SEQUENCES = {
    "account.menu_board_journal_1": 1,
    "account.menu_finance_receivables": 2,
    "account.menu_finance_payables": 3,
    "hellenia_ui.menu_finance_payments_root": 4,
    "account.menu_finance_entries": 5,
    "account.account_audit_menu": 6,
    "account.menu_finance_reports": 7,
    "justech_l10n_do_reports.menu_justech_do_audit_root": 8,
    "account.menu_finance_configuration": 9,
    "justech_report_design.menu_justech_delivery_note_account": 25,
}

# Secuencias bajo Contabilidad operativa (menu_finance_entries)
ACCOUNTING_HUB_CHILD_SEQUENCES = {
    "account.menu_action_move_journal_line_form": 1,
    "account.menu_action_account_moves_all": 2,
    "account_asset.menu_action_account_asset_form": 3,
    "account_loans.menu_action_loans": 4,
    "account_accountant.menu_account_reconcile": 5,
    "account_accountant.menu_action_change_lock_date": 6,
    "account.menu_action_secure_entries": 7,
}

RECEIVABLES_CHILD_SEQUENCES = {
    "account.menu_action_move_out_invoice_type": 1,
    "account.menu_action_move_out_refund_type": 2,
    "account.menu_action_account_payments_receivable": 3,
    "justech_l10n_do_treasury.menu_treasury_open_payments_customer": 4,
    "account.menu_account_customer": 5,
    "account.product_product_menu_sellable": 6,
}

PAYABLES_CHILD_SEQUENCES = {
    "account.menu_action_move_in_invoice_type": 1,
    "account.menu_action_move_in_refund_type": 2,
    "account.menu_action_account_payments_payable": 3,
    "justech_l10n_do_treasury.menu_treasury_open_payments_vendor": 4,
    "account.menu_account_supplier": 5,
    "account.product_product_menu_purchasable": 6,
}

PAYMENTS_HUB_CHILD_SEQUENCES = {
    "hellenia_ui.menu_finance_payments_customer": 1,
    "hellenia_ui.menu_finance_payments_vendor": 2,
    "hellenia_ui.menu_finance_open_payments_customer": 3,
    "hellenia_ui.menu_finance_open_payments_vendor": 4,
    "hellenia_ui.menu_finance_bank_reconciliation": 5,
}

REPORTS_CHILD_SEQUENCES = {
    "account.account_reports_legal_statements_menu": 1,
    "account_reports.account_reports_audit_menu": 2,
    "account.account_reports_partners_reports_menu": 3,
    "account.account_reports_taxes_and_fiscal_menu": 4,
    "account.account_reports_management_menu": 5,
}

LEGAL_REPORTS_SEQUENCES = {
    "account_reports.menu_action_account_report_balance_sheet": 1,
    "account_reports.menu_action_account_report_profit_and_loss": 2,
    "account_reports.menu_action_account_report_general_ledger": 3,
    "account_reports.menu_action_account_report_coa": 4,
}

AUDIT_FISCAL_CHILD_SEQUENCES = {
    "justech_l10n_do_reports.menu_justech_do_report_606": 1,
    "justech_l10n_do_reports.menu_justech_do_report_607": 2,
    "justech_l10n_do_reports.menu_justech_do_report_608": 3,
    "justech_l10n_do_reports.menu_justech_do_report_609": 4,
    "justech_l10n_do_reports.menu_justech_do_report_623": 5,
    "justech_l10n_do_ncf.menu_justech_do_ncf_consumption": 6,
    "justech_l10n_do_ncf.menu_justech_do_ncf_ranges": 7,
    "justech_l10n_do_base.menu_justech_do_document_types": 8,
    "hellenia_account.menu_hellenia_withholding_catalog": 9,
    "justech_l10n_do_reports.menu_justech_do_audit_consumption": 10,
    "justech_l10n_do_reports.menu_justech_do_audit_voided": 11,
    "justech_l10n_do_reports.menu_justech_do_reports_history": 12,
    "justech_l10n_do_reports.menu_justech_do_fiscal_review": 13,
    "justech_l10n_do_reports.menu_justech_do_fiscal_review_pending": 14,
}

# Contenedores intermedios que se ocultan tras aplanar hijos útiles
ACCOUNTING_CONTAINER_HIDE_XMLIDS = (
    "account.account_transactions_menu",
    "account.account_closing_menu",
    "accountant.account_assets_liabilities_menu",
)

# Declaración fiscal EE: visible bajo Reportes > Impuestos, no duplicada en Contabilidad
FISCAL_RETURN_MENU = "account_reports.menu_action_account_return"

# Menús contables estándar EE a reactivar (complementan personalizaciones Hellenia)
STANDARD_ACCOUNTING_RESTORE_XMLIDS = (
    "account.menu_finance_entries",
    "account_accountant.menu_account_reconcile",
    "account_accountant.menu_action_change_lock_date",
    "account_reports.menu_action_account_return",
    "account.menu_action_secure_entries",
    "account_asset.menu_action_account_asset_form",
    "account_loans.menu_action_loans",
)

# Solo traducciones claramente necesarias; nombres estándar Odoo se conservan vía PO
STANDARD_ACCOUNTING_LABELS_ES = {
    "account.menu_finance_entries": "Contabilidad",
    "account.account_audit_menu": "Revisión",
    "hellenia_ui.menu_finance_payments_root": "Pagos",
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
    "account.account_account_menu": "Contabilidad",
    "account.menu_action_account_form": "Plan de cuentas",
    "account.menu_action_tax_form": "Impuestos",
    "account.menu_action_account_journal_form": "Diarios",
    "account.menu_action_currency_form": "Monedas",
    "account.menu_action_account_fiscal_position_form": "Posiciones fiscales",
    "account.menu_action_account_payments_receivable": "Pagos",
    "account.menu_action_account_payments_payable": "Pagos",
}

# Etiquetas español — menús contables Enterprise (UX-FLOW-FIX)
ACCOUNTING_MENU_LABELS_ES = {
    "account_reports.menu_account_reports": "Informes contables",
    "account_reports.menu_action_account_report_tree": "Informes contables",
    "account_reports.menu_action_account_report_horizontal_groups": "Grupos horizontales",
    "account_reports.menu_action_return_check_templates": "Cheques",
    "account_reports.menu_action_return_types": "Tipos de declaración",
    "account_reports.menu_action_account_report_budget_tree": "Presupuestos financieros",
    "account_accountant.menu_accounting": "Contabilidad",
    "account.menu_accounting_entries": "Asientos",
    "account.menu_analytic_accounting": "Contabilidad analítica",
    "account.menu_analytic__distribution_model": "Modelos de distribución analítica",
    "account.account_analytic_def_account": "Cuentas analíticas",
    "account.account_analytic_plan_menu": "Planes analíticos",
    "account.root_payment_menu": "Pagos en línea",
    "account_payment.payment_provider_menu": "Proveedores de pago",
    "account_payment.payment_method_menu": "Métodos de pago",
    "account_payment.payment_token_menu": "Tokens de pago",
    "account_payment.payment_transaction_menu": "Transacciones de pago",
    "account.account_invoicing_menu": "Facturación",
    "account.menu_action_payment_term_form": "Términos de pago",
    "account_followup.account_followup_menu": "Niveles de seguimiento",
    "account.menu_action_incoterm_open": "Incoterms",
    "account.menu_product_product_categories": "Categorías de producto",
    "account_asset.menu_finance_config_assets": "Activos e ingresos",
    "account_asset.menu_action_account_asset_model_form": "Modelos de activos",
    "account_fiscal_categories.menu_action_account_fiscal_category_list": "Categorías fiscales",
    "account_online_synchronization.menu_action_online_link_account": "Sincronización en línea",
}

# Etiquetas español — Localización Justech
JUSTECH_MENU_LABELS_ES = {
    "justech_l10n_do_base.menu_justech_do_fiscal_root": "Localización Dominicana",
    "justech_l10n_do_base.menu_justech_do_document_types": "1. Tipos de comprobante",
    "justech_l10n_do_ncf.menu_justech_do_ncf_ranges": "2. Rangos NCF",
    "justech_l10n_do_ncf.menu_justech_do_ncf_consumption": "3. Consumo NCF",
    "justech_l10n_do_base.menu_justech_do_fiscal_config": "Configuración fiscal",
    "justech_l10n_do_reports.menu_justech_do_reports_root": "Reportes DGII",
    "justech_l10n_do_reports.menu_justech_do_report_606": "606 — Compras",
    "justech_l10n_do_reports.menu_justech_do_report_607": "607 — Ventas",
    "justech_l10n_do_reports.menu_justech_do_report_608": "608 — Anulados",
    "justech_l10n_do_reports.menu_justech_do_reports_history": "Historial fiscal",
    "justech_l10n_do_reports.menu_justech_do_audit_root": "Auditoría Fiscal",
    "justech_l10n_do_reports.menu_justech_do_audit_consumption": "Consumo NCF (auditoría)",
    "justech_l10n_do_reports.menu_justech_do_audit_voided": "NCF anulados",
    "justech_global_audit_log.menu_justech_global_audit_root": "Auditoría de Cambios",
    "justech_admin.menu_justech_modules": "Licencias y Personalizaciones",
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
            if xid in FINANCE_NEVER_ROOT_CHILDREN or child.name in ("Settings", "Ajustes"):
                if settings and child.id == settings.id:
                    child.parent_id = config_parent.id if config_parent else child.parent_id
                elif xid in HIDE_ACCOUNTING_DUPLICATE_XMLIDS:
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
        """Etiquetas Justech; estructura en restore_standard_accounting_menus()."""
        for xmlid, label in JUSTECH_MENU_LABELS_ES.items():
            self._set_menu_label(xmlid, label)

    @api.model
    def standardize_ux1_navigation(self):
        """UX-1 / GO-LIVE-UX: multimoneda nativa, Justech y Auditoría solo internos."""
        config = self.env.ref("account.menu_finance_configuration", raise_if_not_found=False)

        for xid in (
            "justech_multicurrency.menu_justech_platform_root",
            "justech_multicurrency.menu_justech_multicurrency_root",
            "justech_multicurrency.menu_justech_multicurrency_dashboard",
        ):
            menu = self.env.ref(xid, raise_if_not_found=False)
            if menu and menu.active:
                menu.active = False

        rates = self.env.ref("justech_multicurrency.menu_justech_multicurrency_rates", raise_if_not_found=False)
        if config and rates:
            rates.write({"parent_id": config.id, "active": True, "sequence": 35})

        settings = self.env.ref("justech_admin.menu_justech_settings_root", raise_if_not_found=False)
        policy = self.env.ref("justech_multicurrency.menu_justech_multicurrency_policy", raise_if_not_found=False)
        if settings and policy:
            policy.write({"parent_id": settings.id, "name": "Configuración comercial", "sequence": 50})

        audit_app = self.env.ref("justech_global_audit_log.menu_justech_global_audit_root", raise_if_not_found=False)
        admin_root = self.env.ref("base.menu_administration", raise_if_not_found=False)
        if audit_app and settings:
            audit_app.write({"parent_id": settings.id, "sequence": 60, "active": True})
        elif audit_app and admin_root:
            audit_app.write({"parent_id": admin_root.id, "sequence": 97, "active": True})

        if config:
            config.active = True
            for child in self.env["ir.ui.menu"].search([("parent_id", "=", config.id)]):
                if child.name in ("Settings", "Ajustes") and child.parent_id == config:
                    child.active = True
        self._restore_standard_accounting_config()

    @api.model
    def _restore_standard_accounting_config(self):
        """Reactiva el submenú contable estándar bajo Configuración (Plan, Impuestos, Monedas…)."""
        config = self.env.ref("account.menu_finance_configuration", raise_if_not_found=False)
        acct_sub = self.env.ref("account.account_account_menu", raise_if_not_found=False)
        if not config or not acct_sub:
            return

        acct_sub.write({"parent_id": config.id, "active": True, "sequence": 10})
        self._set_menu_label("account.account_account_menu", "Contabilidad")

        standard_children = (
            "account.menu_action_account_form",
            "account.menu_action_tax_form",
            "account.menu_action_account_journal_form",
            "account.menu_action_currency_form",
            "account.menu_action_account_fiscal_position_form",
        )
        for xid in standard_children:
            menu = self.env.ref(xid, raise_if_not_found=False)
            if not menu:
                continue
            menu.write({"parent_id": acct_sub.id, "active": True})
            label = MENU_LABELS_ES.get(xid)
            if label:
                self._set_menu_label(xid, label)

    @api.model
    def _write_menu(self, xmlid, parent_xid=None, active=True, sequence=None):
        menu = self.env.ref(xmlid, raise_if_not_found=False)
        if not menu:
            return False
        vals = {"active": active}
        if parent_xid:
            parent = self.env.ref(parent_xid, raise_if_not_found=False)
            if parent:
                vals["parent_id"] = parent.id
        if sequence is not None:
            vals["sequence"] = sequence
        menu.write(vals)
        return True

    @api.model
    def _apply_sequences(self, mapping):
        for xid, seq in mapping.items():
            menu = self.env.ref(xid, raise_if_not_found=False)
            if menu:
                menu.sequence = seq

    @api.model
    def restore_standard_accounting_menus(self):
        """Reactiva menús EE y aplica estructura HELLENIA-MENU-UAT-2 sin duplicar raíz."""
        finance = self.env.ref("account.menu_finance", raise_if_not_found=False)
        if not finance:
            return

        finance_entries = self.env.ref("account.menu_finance_entries", raise_if_not_found=False)
        payments_hub = self.env.ref("hellenia_ui.menu_finance_payments_root", raise_if_not_found=False)
        reports = self.env.ref("account.menu_finance_reports", raise_if_not_found=False)
        taxes_reports = self.env.ref("account.account_reports_taxes_and_fiscal_menu", raise_if_not_found=False)
        audit_fiscal = self.env.ref("justech_l10n_do_reports.menu_justech_do_audit_root", raise_if_not_found=False)

        if finance_entries:
            finance_entries.write({"parent_id": finance.id, "active": True})
            self._set_menu_label("account.menu_finance_entries", "Contabilidad")

        # Hub Contabilidad: asientos, apuntes, activos, préstamos, conciliar, bloqueos
        accounting_children = (
            "account.menu_action_move_journal_line_form",
            "account.menu_action_account_moves_all",
            "account_asset.menu_action_account_asset_form",
            "account_loans.menu_action_loans",
            "account_accountant.menu_account_reconcile",
            "account_accountant.menu_action_change_lock_date",
            "account.menu_action_secure_entries",
        )
        for xid in accounting_children:
            self._write_menu(xid, parent_xid="account.menu_finance_entries", active=True)

        for xid in ACCOUNTING_CONTAINER_HIDE_XMLIDS:
            self._write_menu(xid, active=False)

        # Hub Pagos (accesos centralizados; Clientes/Proveedores conservan accesos contextuales Odoo)
        if payments_hub:
            payments_hub.write({"parent_id": finance.id, "active": True})
            for xid in (
                "hellenia_ui.menu_finance_payments_customer",
                "hellenia_ui.menu_finance_payments_vendor",
                "hellenia_ui.menu_finance_open_payments_customer",
                "hellenia_ui.menu_finance_open_payments_vendor",
                "hellenia_ui.menu_finance_bank_reconciliation",
            ):
                self._write_menu(xid, parent_xid="hellenia_ui.menu_finance_payments_root", active=True)

        # Clientes / Proveedores: mantener pagos contextuales estándar
        self._write_menu(
            "account.menu_action_account_payments_receivable",
            parent_xid="account.menu_finance_receivables",
            active=True,
        )
        self._write_menu(
            "account.menu_action_account_payments_payable",
            parent_xid="account.menu_finance_payables",
            active=True,
        )

        # Declaración fiscal estándar bajo Reportes > Impuestos (no en Contabilidad)
        fiscal_return = self.env.ref(FISCAL_RETURN_MENU, raise_if_not_found=False)
        if fiscal_return and taxes_reports:
            fiscal_return.write({"parent_id": taxes_reports.id, "active": True, "sequence": 5})

        # DGII / NCF / Retenciones bajo Auditoría Fiscal
        if audit_fiscal:
            audit_fiscal.write({"parent_id": finance.id, "active": True})

            dgii_root = self.env.ref("justech_l10n_do_reports.menu_justech_do_reports_root", raise_if_not_found=False)
            if dgii_root:
                for child in self.env["ir.ui.menu"].search([("parent_id", "=", dgii_root.id)]):
                    child.write({"parent_id": audit_fiscal.id, "active": True})
                dgii_root.active = False

            for xid in (
                "justech_l10n_do_base.menu_justech_do_document_types",
                "justech_l10n_do_ncf.menu_justech_do_ncf_ranges",
                "justech_l10n_do_ncf.menu_justech_do_ncf_consumption",
                "hellenia_account.menu_hellenia_withholding_catalog",
            ):
                self._write_menu(xid, parent_xid="justech_l10n_do_reports.menu_justech_do_audit_root", active=True)

        # Revisión en raíz
        self._write_menu("account.account_audit_menu", parent_xid="account.menu_finance", active=True)

        for xid in STANDARD_ACCOUNTING_RESTORE_XMLIDS:
            menu = self.env.ref(xid, raise_if_not_found=False)
            if menu:
                menu.active = True

        for xid in ACCOUNTING_CONTAINER_HIDE_XMLIDS:
            self._write_menu(xid, active=False)

        self._set_menu_label("account_accountant.menu_account_reconcile", "Conciliar")

        for xid, label in STANDARD_ACCOUNTING_LABELS_ES.items():
            self._set_menu_label(xid, label)

        self._apply_sequences(FINANCE_CHILD_SEQUENCES)
        self._apply_sequences(ACCOUNTING_HUB_CHILD_SEQUENCES)
        self._apply_sequences(RECEIVABLES_CHILD_SEQUENCES)
        self._apply_sequences(PAYABLES_CHILD_SEQUENCES)
        self._apply_sequences(PAYMENTS_HUB_CHILD_SEQUENCES)
        self._apply_sequences(REPORTS_CHILD_SEQUENCES)
        self._apply_sequences(LEGAL_REPORTS_SEQUENCES)
        self._apply_sequences(AUDIT_FISCAL_CHILD_SEQUENCES)

        # Mayor general bajo Ledgers si existe
        ledgers = self.env.ref("account_reports.account_reports_audit_menu", raise_if_not_found=False)
        gl = self.env.ref("account_reports.menu_action_account_report_general_ledger", raise_if_not_found=False)
        if ledgers and gl and gl.parent_id != ledgers:
            gl.write({"parent_id": ledgers.id, "active": True, "sequence": 2})

        if reports:
            for menu in self.env["ir.ui.menu"].search([("id", "child_of", reports.id)]):
                data = self.env["ir.model.data"].search(
                    [("model", "=", "ir.ui.menu"), ("res_id", "=", menu.id)], limit=1
                )
                if data and data.module.startswith(("account", "stock_accountant", "purchase_accountant", "sale_account")):
                    menu.active = True

    @api.model
    def apply_accounting_menu_labels(self):
        """Traduce menús contables Enterprise visibles en español."""
        for xmlid, label in ACCOUNTING_MENU_LABELS_ES.items():
            self._set_menu_label(xmlid, label)
        # Menús identificados por nombre (sin xmlid estable entre versiones)
        name_map = {
            "Reporting": "Informes contables",
            "Multi-Ledger": "Multi-libro",
            "Tax Groups": "Grupos de impuestos",
            "Tax Units": "Unidades de impuesto",
            "Cash Roundings": "Redondeos de efectivo",
            "Account Tags": "Etiquetas contables",
            "Account Groups": "Grupos de cuentas",
            "Fiscal Years": "Años fiscales",
            "Accounting Reports": "Informes contables",
            "Horizontal Groups": "Grupos horizontales",
            "Checks": "Cheques",
            "Fiscal Categories": "Categorías fiscales",
            "Asset Models": "Modelos de activos",
            "Return Types": "Tipos de declaración",
            "Financial Budgets": "Presupuestos financieros",
            "Online Synchronization": "Sincronización en línea",
            "Invoicing": "Facturación",
            "Payment Terms": "Términos de pago",
            "Follow-up Levels": "Niveles de seguimiento",
            "Incoterms": "Incoterms",
            "Product Categories": "Categorías de producto",
            "Assets and Revenues": "Activos e ingresos",
            "Online Payments": "Pagos en línea",
            "Payment Providers": "Proveedores de pago",
            "Payment Methods": "Métodos de pago",
            "Payment Tokens": "Tokens de pago",
            "Payment Transactions": "Transacciones de pago",
            "Analytic Accounting": "Contabilidad analítica",
            "Analytic Distribution Models": "Modelos de distribución analítica",
            "Analytic Accounts": "Cuentas analíticas",
            "Analytic Plans": "Planes analíticos",
        }
        config = self.env.ref("account.menu_finance_configuration", raise_if_not_found=False)
        if config:
            for menu in self.env["ir.ui.menu"].search([("id", "child_of", config.id)]):
                new_name = name_map.get(menu.name)
                if not new_name or new_name == menu.name:
                    continue
                for lang in self._active_langs():
                    menu.with_context(lang=lang).write({"name": new_name})
        # Menús técnicos bajo Configuración (p. ej. Technical/Reporting)
        admin = self.env.ref("base.menu_administration", raise_if_not_found=False)
        if admin:
            for menu in self.env["ir.ui.menu"].search([("id", "child_of", admin.id)]):
                new_name = name_map.get(menu.name)
                if not new_name or new_name == menu.name:
                    continue
                for lang in self._active_langs():
                    menu.with_context(lang=lang).write({"name": new_name})

    @api.model
    def apply_ux_flow_fix_labels(self):
        """UX-FLOW-FIX: auditorías, licencias, NCF numerado, menús EN."""
        self.apply_accounting_menu_labels()
        for xmlid, label in JUSTECH_MENU_LABELS_ES.items():
            self._set_menu_label(xmlid, label)
        # Receivables / Payables
        self._set_menu_label("account.menu_finance_receivables", "Clientes")
        self._set_menu_label("account.menu_finance_payables", "Proveedores")

    @api.model
    def apply_all(self):
        """Aplica todas las personalizaciones de menú en orden seguro."""
        self.apply_menu_labels()
        self.hide_unused_menus()
        self.repair_accounting_menu_tree()
        self.integrate_justech_menus()
        self.standardize_ux1_navigation()
        self.restore_standard_accounting_menus()
        self.apply_ux_flow_fix_labels()
