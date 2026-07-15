# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    justech_ms_assessment_count = fields.Integer(
        string="Levantamientos",
        compute="_compute_justech_ms_counts",
    )
    justech_ms_service_count = fields.Integer(
        string="Servicios Administrados",
        compute="_compute_justech_ms_counts",
    )
    justech_ms_ticket_count = fields.Integer(
        string="Tickets MS",
        compute="_compute_justech_ms_counts",
    )
    justech_ms_sale_count = fields.Integer(
        string="Cotizaciones MS",
        compute="_compute_justech_ms_counts",
    )
    justech_ms_subscription_count = fields.Integer(
        string="Suscripciones MS",
        compute="_compute_justech_ms_counts",
    )

    def _compute_justech_ms_counts(self):
        Assessment = self.env["justech.managed.service.assessment"]
        Service = self.env["justech.managed.service"]
        Ticket = self.env["helpdesk.ticket"]
        Order = self.env["sale.order"]
        for partner in self:
            commercial = partner.commercial_partner_id
            if Assessment.has_access("read"):
                partner.justech_ms_assessment_count = Assessment.search_count(
                    [("partner_id", "child_of", commercial.id)]
                )
            else:
                partner.justech_ms_assessment_count = 0
            if Service.has_access("read"):
                partner.justech_ms_service_count = Service.search_count(
                    [("partner_id", "child_of", commercial.id)]
                )
            else:
                partner.justech_ms_service_count = 0
            if Ticket.has_access("read"):
                partner.justech_ms_ticket_count = Ticket.search_count(
                    [
                        ("partner_id", "child_of", commercial.id),
                        ("justech_managed_service_id", "!=", False),
                    ]
                )
            else:
                partner.justech_ms_ticket_count = 0
            if Order.has_access("read"):
                partner.justech_ms_sale_count = Order.search_count(
                    [
                        ("partner_id", "child_of", commercial.id),
                        "|",
                        ("justech_assessment_id", "!=", False),
                        ("justech_managed_service_id", "!=", False),
                    ]
                )
                partner.justech_ms_subscription_count = Order.search_count(
                    [
                        ("partner_id", "child_of", commercial.id),
                        ("is_subscription", "=", True),
                        ("justech_managed_service_id", "!=", False),
                    ]
                )
            else:
                partner.justech_ms_sale_count = 0
                partner.justech_ms_subscription_count = 0

    def action_view_justech_ms_assessments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Levantamientos",
            "res_model": "justech.managed.service.assessment",
            "view_mode": "list,form",
            "domain": [("partner_id", "child_of", self.commercial_partner_id.id)],
            "context": {"default_partner_id": self.commercial_partner_id.id},
        }

    def action_view_justech_managed_services(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Servicios Administrados",
            "res_model": "justech.managed.service",
            "view_mode": "list,form",
            "domain": [("partner_id", "child_of", self.commercial_partner_id.id)],
            "context": {
                "default_partner_id": self.commercial_partner_id.id,
                "default_state": "active",
            },
        }

    def action_view_justech_ms_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Tickets MS",
            "res_model": "helpdesk.ticket",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "child_of", self.commercial_partner_id.id),
                ("justech_managed_service_id", "!=", False),
            ],
            "context": {"default_partner_id": self.id},
        }

    def action_view_justech_ms_quotations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Cotizaciones MS",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "child_of", self.commercial_partner_id.id),
                "|",
                ("justech_assessment_id", "!=", False),
                ("justech_managed_service_id", "!=", False),
            ],
            "context": {"default_partner_id": self.commercial_partner_id.id},
        }

    def action_view_justech_ms_subscriptions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Suscripciones MS",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "child_of", self.commercial_partner_id.id),
                ("is_subscription", "=", True),
                ("justech_managed_service_id", "!=", False),
            ],
            "context": {
                "default_partner_id": self.commercial_partner_id.id,
                "default_is_subscription": True,
            },
        }
