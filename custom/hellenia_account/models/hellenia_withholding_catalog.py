"""Catálogo configurable de retenciones RD — motor contable Hellenia."""
from __future__ import annotations

from odoo import api, fields, models


class HelleniaWithholdingCatalog(models.Model):
    _name = "hellenia.withholding.catalog"
    _description = "Catálogo retenciones República Dominicana"
    _order = "sequence, name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(string="Código técnico", required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    tax_id = fields.Many2one(
        "account.tax",
        string="Impuesto retención",
        domain="[('amount', '<', 0)]",
        help="Impuesto de retención definido en l10n_do (no inventar tasas).",
    )
    withholding_type = fields.Selection(
        [
            ("isr", "ISR"),
            ("itbis", "ITBIS"),
            ("gov", "Gobierno"),
            ("informal", "Proveedor informal"),
            ("fees", "Honorarios"),
        ],
        string="Tipo",
        required=True,
        default="isr",
    )
    rate = fields.Float(
        string="Porcentaje",
        help="Porcentaje documentado del impuesto vinculado (referencia).",
    )
    base_type = fields.Selection(
        [
            ("untaxed", "Base imponible"),
            ("itbis", "ITBIS facturado"),
        ],
        string="Base de cálculo",
        required=True,
        default="untaxed",
        help="Base imponible: subtotal sin impuestos. ITBIS facturado: monto ITBIS de la factura.",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Cuenta contable",
        compute="_compute_account_id",
        store=True,
        readonly=False,
    )
    partner_scope = fields.Selection(
        [
            ("customer", "Cliente"),
            ("supplier", "Proveedor"),
            ("both", "Cliente y proveedor"),
        ],
        string="Aplica a",
        required=True,
        default="both",
    )
    move_scope = fields.Selection(
        [
            ("sale", "Venta"),
            ("purchase", "Compra"),
            ("both", "Venta y compra"),
        ],
        string="Tipo de factura",
        required=True,
        default="both",
    )
    affects_606 = fields.Boolean(string="Afecta reporte 606")
    affects_607 = fields.Boolean(string="Afecta reporte 607")
    tax_use = fields.Selection(
        related="tax_id.type_tax_use",
        string="Uso impuesto",
        store=True,
    )
    notes = fields.Text(string="Notas contables")

    _sql_constraints = [
        (
            "hellenia_wh_catalog_code_company_uniq",
            "unique(code, company_id)",
            "El código de retención debe ser único por compañía.",
        ),
    ]

    @api.depends("tax_id", "tax_id.invoice_repartition_line_ids.account_id")
    def _compute_account_id(self):
        for rec in self:
            account = False
            if rec.tax_id:
                rep = rec.tax_id.invoice_repartition_line_ids.filtered(
                    lambda l: l.repartition_type == "tax"
                )[:1]
                account = rep.account_id
            rec.account_id = account

    def _itbis_amount(self, move):
        """Monto ITBIS positivo de la factura."""
        move.ensure_one()
        tax_lines = move.line_ids.filtered(
            lambda l: l.tax_line_id and l.tax_line_id.amount > 0 and l.tax_line_id.type_tax_use in ("sale", "purchase")
        )
        if tax_lines:
            return abs(sum(tax_lines.mapped("balance")))
        return abs(move.amount_tax) if move.amount_tax else 0.0

    def _base_amount(self, move):
        self.ensure_one()
        if self.base_type == "itbis":
            return self._itbis_amount(move)
        return abs(move.amount_untaxed)

    def compute_withholding_amount(self, move):
        """Calcula monto retenido para una factura según configuración del catálogo."""
        self.ensure_one()
        if not self.tax_id:
            return 0.0
        base = self._base_amount(move)
        if not base:
            return 0.0
        # Usar tasa del impuesto l10n_do (no hardcodear en wizard)
        return abs(self.tax_id.amount / 100.0 * base)

    def _applies_to_move(self, move, partner_type):
        self.ensure_one()
        if self.partner_scope == "customer" and partner_type != "customer":
            return False
        if self.partner_scope == "supplier" and partner_type != "supplier":
            return False
        if self.move_scope == "sale" and move.move_type not in ("out_invoice", "out_refund"):
            return False
        if self.move_scope == "purchase" and move.move_type not in ("in_invoice", "in_refund"):
            return False
        if self.tax_use == "sale" and move.move_type not in ("out_invoice", "out_refund"):
            return False
        if self.tax_use == "purchase" and move.move_type not in ("in_invoice", "in_refund"):
            return False
        return True

    @api.model
    def _catalog_specs(self):
        """Especificación upgrade-safe — impuestos l10n_do documentados."""
        return [
            {
                "code": "wh_none",
                "name": "Ninguna",
                "tax_name": False,
                "tax_use": False,
                "withholding_type": "isr",
                "base_type": "untaxed",
                "partner_scope": "both",
                "move_scope": "both",
                "affects_606": False,
                "affects_607": False,
                "active": False,
                "sequence": 0,
                "notes": "Opción por defecto: sin retenciones en la factura.",
            },
            {
                "code": "wh_isr_gov",
                "name": "Retención 5% Gobierno",
                "tax_name": "-5% ISR Gov.",
                "tax_use": "sale",
                "withholding_type": "gov",
                "base_type": "untaxed",
                "partner_scope": "customer",
                "move_scope": "sale",
                "affects_606": False,
                "affects_607": True,
                "sequence": 10,
                "notes": "ISR 5% sobre base imponible — ventas a entidades gubernamentales.",
            },
            {
                "code": "wh_itbis_30",
                "name": "Retención ITBIS 30%",
                "tax_name": "-30% ITBIS Leg. (N02-05)",
                "tax_use": "purchase",
                "withholding_type": "itbis",
                "base_type": "itbis",
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "sequence": 20,
                "notes": "30% del ITBIS facturado — servicios legales N02-05.",
            },
            {
                "code": "wh_itbis_100",
                "name": "Retención ITBIS 100%",
                "tax_name": "-100% ITBIS (N07-09)",
                "tax_use": "purchase",
                "withholding_type": "itbis",
                "base_type": "itbis",
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "sequence": 25,
                "notes": "100% del ITBIS facturado — N07-09.",
            },
            {
                "code": "wh_isr_10",
                "name": "Retención proveedor informal 10%",
                "tax_name": "-10% ISR Fee",
                "tax_use": "purchase",
                "withholding_type": "informal",
                "base_type": "untaxed",
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "sequence": 30,
                "notes": "ISR 10% sobre base imponible — proveedor informal.",
            },
            {
                "code": "wh_itbis_75",
                "name": "Retención ITBIS informal 75%",
                "tax_name": "-75% ITBIS (N08-10)",
                "tax_use": "purchase",
                "withholding_type": "itbis",
                "base_type": "itbis",
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "sequence": 40,
                "notes": "75% del ITBIS facturado — proveedor informal N08-10.",
            },
            {
                "code": "wh_isr_2",
                "name": "Retención ISR 2%",
                "tax_name": "-2% ISR (N07-07)",
                "tax_use": "purchase",
                "withholding_type": "isr",
                "base_type": "untaxed",
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "sequence": 50,
                "notes": "ISR 2% sobre base imponible — N07-07.",
            },
            {
                "code": "wh_isr_fees_10",
                "name": "Retención honorarios 10%",
                "tax_name": "-10% ISR Rent.",
                "tax_use": "purchase",
                "withholding_type": "fees",
                "base_type": "untaxed",
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "sequence": 60,
                "notes": "ISR 10% sobre base imponible — honorarios/alquiler.",
            },
        ]

    @api.model
    def sync_catalog_from_taxes(self, company=None):
        """Sincroniza catálogo con impuestos l10n_do existentes."""
        company = company or self.env.company
        Tax = self.env["account.tax"]
        Catalog = self.env["hellenia.withholding.catalog"]
        result = []
        for spec in self._catalog_specs():
            tax = False
            if spec.get("tax_name") and spec.get("tax_use"):
                tax = Tax.search(
                    [
                        ("name", "=", spec["tax_name"]),
                        ("type_tax_use", "=", spec["tax_use"]),
                        ("company_id", "=", company.id),
                    ],
                    limit=1,
                )
                if tax and not tax.active:
                    tax.active = True
            vals = {
                "name": spec["name"],
                "code": spec["code"],
                "sequence": spec.get("sequence", 10),
                "withholding_type": spec["withholding_type"],
                "base_type": spec["base_type"],
                "partner_scope": spec["partner_scope"],
                "move_scope": spec["move_scope"],
                "affects_606": spec["affects_606"],
                "affects_607": spec["affects_607"],
                "notes": spec.get("notes"),
                "active": spec.get("active", True) and bool(tax or spec["code"] == "wh_none"),
                "company_id": company.id,
                "tax_id": tax.id if tax else False,
                "rate": abs(tax.amount) if tax else 0.0,
            }
            rec = Catalog.search([("code", "=", spec["code"]), ("company_id", "=", company.id)], limit=1)
            if rec:
                rec.write(vals)
            else:
                rec = Catalog.create(vals)
            result.append({"code": spec["code"], "id": rec.id, "tax": tax.name if tax else None, "active": rec.active})
        return result
