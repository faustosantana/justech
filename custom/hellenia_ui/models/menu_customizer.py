from odoo import api, models

# Menús de aplicaciones fuera del alcance operativo Hellenia
HIDE_MENU_XMLIDS = (
    "crm.crm_menu_root",
    "point_of_sale.menu_point_root",
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
)


class HelleniaUiMenuCustomizer(models.AbstractModel):
    _name = "hellenia.ui.menu.customizer"
    _description = "Hellenia UI — menú principal y ocultación de apps"

    @api.model
    def apply_menu_labels(self):
        """Nombres visibles en español en todos los idiomas activos."""
        updates = {
            "account.menu_finance": "Contabilidad",
            "base.menu_administration": "Configuración",
            "sale.sale_menu_root": "Ventas",
            "purchase.menu_purchase_root": "Compras",
            "stock.menu_stock_root": "Inventario",
            "contacts.menu_contacts": "Contactos",
        }
        langs = self.env["res.lang"].search([("active", "=", True)]).mapped("code")
        if not langs:
            langs = ["es_DO", "es_419", "en_US"]
        for xmlid, label in updates.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            for lang in langs:
                menu.with_context(lang=lang).write({"name": label})

    @api.model
    def hide_unused_menus(self):
        """Oculta módulos y menús técnicos no utilizados por Hellenia."""
        for xmlid in HIDE_MENU_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and menu.active:
                menu.active = False
