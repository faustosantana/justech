# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    justech_ms_assessment_count = fields.Integer(
        string="Levantamientos",
        compute="_compute_justech_ms_links",
    )
    justech_managed_service_id = fields.Many2one(
        "justech.managed.service",
        string="Servicio Administrado",
        index=True,
        copy=False,
    )
    justech_ms_service_count = fields.Integer(
        string="Servicios Administrados",
        compute="_compute_justech_ms_links",
    )
    justech_ms_sale_count = fields.Integer(
        string="Cotizaciones MS",
        compute="_compute_justech_ms_links",
    )

    def _compute_justech_ms_links(self):
        Assessment = self.env["justech.managed.service.assessment"]
        Service = self.env["justech.managed.service"]
        Order = self.env["sale.order"]
        for lead in self:
            if Assessment.has_access("read"):
                lead.justech_ms_assessment_count = Assessment.search_count(
                    [("opportunity_id", "=", lead.id)]
                )
            else:
                lead.justech_ms_assessment_count = 0
            if Service.has_access("read"):
                lead.justech_ms_service_count = Service.search_count(
                    [
                        "|",
                        ("opportunity_id", "=", lead.id),
                        ("id", "=", lead.justech_managed_service_id.id),
                    ]
                )
            else:
                lead.justech_ms_service_count = 0
            if Order.has_access("read"):
                lead.justech_ms_sale_count = Order.search_count(
                    [
                        ("opportunity_id", "=", lead.id),
                        "|",
                        ("justech_assessment_id", "!=", False),
                        ("justech_managed_service_id", "!=", False),
                    ]
                )
            else:
                lead.justech_ms_sale_count = 0

    def action_view_justech_ms_assessments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Levantamientos",
            "res_model": "justech.managed.service.assessment",
            "view_mode": "list,form",
            "domain": [("opportunity_id", "=", self.id)],
            "context": {
                "default_opportunity_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }

    def action_view_justech_managed_service(self):
        self.ensure_one()
        services = self.env["justech.managed.service"].search(
            [
                "|",
                ("opportunity_id", "=", self.id),
                ("id", "=", self.justech_managed_service_id.id),
            ]
        )
        if len(services) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "justech.managed.service",
                "res_id": services.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": "Servicios Administrados",
            "res_model": "justech.managed.service",
            "view_mode": "list,form",
            "domain": [("id", "in", services.ids)],
            "context": {
                "default_opportunity_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }

    def action_view_justech_ms_quotations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Cotizaciones",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [
                ("opportunity_id", "=", self.id),
                "|",
                ("justech_assessment_id", "!=", False),
                ("justech_managed_service_id", "!=", False),
            ],
            "context": {
                "default_opportunity_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }

    def action_justech_create_quotation(self):
        """Crear cotización estándar vinculada a la oportunidad / levantamiento."""
        self.ensure_one()
        assessment = self.env["justech.managed.service.assessment"].search(
            [("opportunity_id", "=", self.id)], limit=1
        )
        if assessment:
            return assessment.action_create_quotation()
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_id.id,
                "opportunity_id": self.id,
                "origin": self.name,
                "user_id": self.user_id.id or self.env.user.id,
                "justech_managed_service_id": self.justech_managed_service_id.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }
