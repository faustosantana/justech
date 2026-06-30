from odoo import api, models


class HelleniaUiMenuCustomizer(models.AbstractModel):
    _name = "hellenia.ui.menu.customizer"
    _description = "Hellenia UI — etiquetas de menú principal"

    @api.model
    def apply_menu_labels(self):
        """Aplicar nombres visibles en todos los idiomas activos de Hellenia."""
        updates = {
            "account.menu_finance": "Contabilidad",
            "base.menu_administration": "Configuración",
        }
        langs = self.env["res.lang"].search([("active", "=", True)]).mapped("code")
        if not langs:
            langs = ["es_DO", "en_US"]
        for xmlid, label in updates.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            for lang in langs:
                menu.with_context(lang=lang).write({"name": label})
