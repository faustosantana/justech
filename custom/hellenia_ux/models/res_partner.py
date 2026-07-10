# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import RedirectWarning, UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    _HELLENIA_SYSTEM_XMLIDS = (
        "base.partner_root",
        "base.public_partner",
        "base.partner_admin",
    )

    def _hellenia_system_partner_ids(self):
        ids = set()
        for xmlid in self._HELLENIA_SYSTEM_XMLIDS:
            try:
                ids.add(self.env.ref(xmlid).id)
            except ValueError:
                continue
        return ids

    def _hellenia_related_companies(self):
        self.ensure_one()
        return self.env["res.company"].sudo().search([("partner_id", "=", self.id)])

    def _hellenia_related_users(self):
        self.ensure_one()
        return self.env["res.users"].sudo().with_context(active_test=False).search(
            [("partner_id", "=", self.id)]
        )

    def _hellenia_operational_counts(self):
        """Conteos de operaciones comerciales/contables (sin sudo de escritura)."""
        self.ensure_one()
        Partner = self
        counts = {
            "invoices": 0,
            "payments": 0,
            "sale_orders": 0,
            "purchase_orders": 0,
            "pickings": 0,
        }
        if "account.move" in self.env:
            counts["invoices"] = (
                self.env["account.move"]
                .sudo()
                .search_count([("partner_id", "=", Partner.id)])
            )
        if "account.payment" in self.env:
            counts["payments"] = (
                self.env["account.payment"]
                .sudo()
                .search_count([("partner_id", "=", Partner.id)])
            )
        if "sale.order" in self.env:
            counts["sale_orders"] = (
                self.env["sale.order"]
                .sudo()
                .search_count([("partner_id", "=", Partner.id)])
            )
        if "purchase.order" in self.env:
            counts["purchase_orders"] = (
                self.env["purchase.order"]
                .sudo()
                .search_count([("partner_id", "=", Partner.id)])
            )
        if "stock.picking" in self.env:
            counts["pickings"] = (
                self.env["stock.picking"]
                .sudo()
                .search_count([("partner_id", "=", Partner.id)])
            )
        return counts

    def _hellenia_get_delete_blocker(self):
        """Clasifica por qué no se puede eliminar. Retorna dict o None."""
        self.ensure_one()
        if self.id in self._hellenia_system_partner_ids():
            return {
                "reason": "system",
                "partner": self,
                "message": _(
                    "Este contacto es un registro de sistema y no puede eliminarse."
                ),
            }

        companies = self._hellenia_related_companies()
        if companies:
            company = companies[0]
            return {
                "reason": "company",
                "partner": self,
                "company": company,
                "message": _(
                    "Este contacto representa a la empresa %(company)s y forma parte "
                    "de su configuración legal y contable. No puede eliminarse. "
                    "Puedes editar sus datos o asignar otro contacto principal a la empresa."
                )
                % {"company": company.name},
            }

        users = self._hellenia_related_users()
        if users:
            user = users[0]
            return {
                "reason": "user",
                "partner": self,
                "user": user,
                "message": _(
                    "Este contacto pertenece al usuario %(login)s. "
                    "Primero debes desactivar o eliminar el usuario relacionado."
                )
                % {"login": user.login},
            }

        counts = self._hellenia_operational_counts()
        if any(counts.values()):
            parts = []
            if counts["invoices"]:
                parts.append(_("%s factura(s)") % counts["invoices"])
            if counts["payments"]:
                parts.append(_("%s pago(s)") % counts["payments"])
            if counts["sale_orders"]:
                parts.append(_("%s venta(s)") % counts["sale_orders"])
            if counts["purchase_orders"]:
                parts.append(_("%s compra(s)") % counts["purchase_orders"])
            if counts["pickings"]:
                parts.append(_("%s operación(es) de inventario") % counts["pickings"])
            detail = ", ".join(parts)
            return {
                "reason": "documents",
                "partner": self,
                "counts": counts,
                "message": _(
                    "Este contacto posee operaciones relacionadas (%(detail)s) y no "
                    "puede eliminarse. Puedes archivarlo para que deje de aparecer "
                    "en la operación diaria."
                )
                % {"detail": detail},
            }
        return None

    def _hellenia_raise_delete_blocker(self, blocker):
        """Lanza RedirectWarning hacia el wizard UX (sin jerga técnica)."""
        action = self.env.ref("hellenia_ux.action_hellenia_partner_delete_guard")
        partner = blocker["partner"]
        context = {
            "default_partner_id": partner.id,
            "default_block_reason": blocker["reason"],
            "default_message": blocker["message"],
        }
        if blocker.get("company"):
            context["default_company_id"] = blocker["company"].id
        if blocker.get("user"):
            context["default_user_id"] = blocker["user"].id

        button = {
            "company": _("Ver opciones"),
            "user": _("Ver usuario relacionado"),
            "documents": _("Archivar contacto"),
            "system": _("Entendido"),
        }.get(blocker["reason"], _("Entendido"))

        raise RedirectWarning(blocker["message"], action.id, button, additional_context=context)

    def unlink(self):
        for partner in self:
            blocker = partner._hellenia_get_delete_blocker()
            if blocker:
                partner._hellenia_raise_delete_blocker(blocker)
        try:
            return super().unlink()
        except Exception as exc:
            # Última red de seguridad: nunca mostrar FK / res.company / partner_id.
            text = str(exc).lower()
            if any(
                token in text
                for token in (
                    "foreign key",
                    "res_company",
                    "partner_id",
                    "violates",
                    "constraint",
                )
            ):
                raise UserError(
                    _(
                        "No se puede eliminar este contacto porque está vinculado a "
                        "la configuración de una empresa, un usuario u otros registros "
                        "del sistema. Edita sus datos o archívalo si ya no debe usarse "
                        "en la operación diaria."
                    )
                ) from None
            raise
