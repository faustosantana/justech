"""Catálogo configurable de retenciones RD — motor contable Hellenia."""
from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HelleniaWithholdingCatalog(models.Model):
    _name = "hellenia.withholding.catalog"
    _description = "Catálogo retenciones República Dominicana"
    _order = "sequence, name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(string="Código", required=True, index=True)
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
        help="Impuesto de retención definido en l10n_do (no inventar tasas). Solo visible en administración.",
    )
    withholding_type = fields.Selection(
        [
            ("isr", "ISR"),
            ("itbis", "ITBIS"),
            ("other", "Otro"),
        ],
        string="Tipo",
        required=True,
        default="isr",
    )
    rate = fields.Float(
        string="Porcentaje",
        help="Porcentaje nominal de retención (p. ej. 100 para ITBIS 100%, 30 para ITBIS 30%).",
    )
    base_type = fields.Selection(
        [
            ("untaxed", "Base imponible"),
            ("itbis", "ITBIS facturado"),
            ("total", "Total factura"),
            ("applied_amount", "Monto aplicado"),
        ],
        string="Base de cálculo",
        required=True,
        default="untaxed",
        help=(
            "Base imponible: subtotal sin impuestos. "
            "ITBIS facturado: monto ITBIS de la factura. "
            "Total factura: importe total. "
            "Monto aplicado: monto a pagar/cobrar en el wizard."
        ),
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
            ("both", "Ambos"),
        ],
        string="Aplica a",
        required=True,
        default="both",
    )
    move_scope = fields.Selection(
        [
            ("sale", "Venta"),
            ("purchase", "Compra"),
            ("both", "Ambas"),
        ],
        string="Operación",
        required=True,
        default="both",
    )
    affects_606 = fields.Boolean(string="Afecta 606")
    affects_607 = fields.Boolean(string="Afecta 607")
    affects_623 = fields.Boolean(string="Afecta 623")
    dgii_withholding_code = fields.Char(
        string="Código retención DGII",
        help="Código para reportes DGII (606 col. T, Norma 2-05 col. H).",
        index=True,
    )
    tax_use = fields.Selection(
        related="tax_id.type_tax_use",
        string="Uso impuesto",
        store=True,
    )
    notes = fields.Text(string="Descripción / ayuda")

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
            account = rec.account_id
            if rec.tax_id:
                rep = rec.tax_id.invoice_repartition_line_ids.filtered(
                    lambda l: l.repartition_type == "tax"
                )[:1]
                if rep.account_id:
                    account = rep.account_id
            rec.account_id = account

    @api.constrains("active", "account_id", "code")
    def _check_account_required(self):
        for rec in self:
            if rec.active and rec.code not in ("RET-NONE", "wh_none") and not rec.account_id:
                raise ValidationError(
                    f"La retención «{rec.name}» debe tener cuenta contable antes de activarse."
                )

    def _itbis_amount(self, move):
        """Monto ITBIS positivo de la factura."""
        move.ensure_one()
        tax_lines = move.line_ids.filtered(
            lambda l: l.tax_line_id
            and l.tax_line_id.amount > 0
            and l.tax_line_id.type_tax_use in ("sale", "purchase")
        )
        if tax_lines:
            return abs(sum(tax_lines.mapped("balance")))
        return abs(move.amount_tax) if move.amount_tax else 0.0

    def _base_amount(self, move, applied_amount=None):
        self.ensure_one()
        if self.base_type == "itbis":
            return self._itbis_amount(move)
        if self.base_type == "total":
            return abs(move.amount_total)
        if self.base_type == "applied_amount":
            if applied_amount:
                return abs(applied_amount)
            return abs(move.amount_residual)
        return abs(move.amount_untaxed)

    def compute_withholding_amount(self, move, applied_amount=None):
        """Calcula monto retenido: base configurada × tasa nominal del catálogo."""
        self.ensure_one()
        rate = self.rate
        if not rate and self.tax_id:
            rate = abs(self.tax_id.amount)
        if not rate:
            return 0.0
        base = self._base_amount(move, applied_amount=applied_amount)
        if not base:
            return 0.0
        residual = abs(move.amount_residual)
        if (
            applied_amount
            and residual
            and self.base_type != "applied_amount"
            and applied_amount < residual - 0.009
        ):
            base = base * (applied_amount / residual)
        return abs(rate / 100.0 * base)

    def _base_label(self):
        self.ensure_one()
        labels = {
            "untaxed": "Base imponible",
            "itbis": "ITBIS facturado",
            "total": "Total factura",
            "applied_amount": "Monto aplicado",
        }
        return labels.get(self.base_type, "Base")

    def _applies_to_move(self, move, partner_type):
        """Filtra por alcance configurado en catálogo (cliente/proveedor y operación)."""
        self.ensure_one()
        if self.partner_scope == "customer" and partner_type != "customer":
            return False
        if self.partner_scope == "supplier" and partner_type != "supplier":
            return False
        if self.move_scope == "sale" and move.move_type not in ("out_invoice", "out_refund"):
            return False
        if self.move_scope == "purchase" and move.move_type not in ("in_invoice", "in_refund"):
            return False
        return True

    @api.model
    def _legacy_code_map(self):
        """Migración upgrade-safe desde códigos Fase 18."""
        return {
            "RET-NONE": "wh_none",
            "RET-GOB-5": "wh_isr_gov",
            "RET-ITBIS-30": "wh_itbis_30",
            "RET-ITBIS-100": "wh_itbis_100",
            "RET-INF-ISR-10": "wh_isr_10",
            "RET-INF-ITBIS-75": "wh_itbis_75",
            "RET-ISR-2": "wh_isr_2",
            "RET-HON-10": "wh_isr_fees_10",
        }

    @api.model
    def _catalog_specs(self):
        """Especificación upgrade-safe — impuestos l10n_do documentados."""
        return [
            {
                "code": "RET-NONE",
                "legacy_code": "wh_none",
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
                "code": "RET-GOB-5",
                "legacy_code": "wh_isr_gov",
                "name": "Retención 5% Gobierno",
                "tax_name": "-5% ISR Gov.",
                "tax_use": "sale",
                "withholding_type": "isr",
                "base_type": "untaxed",
                "withholding_rate": 5.0,
                "partner_scope": "customer",
                "move_scope": "sale",
                "affects_606": False,
                "affects_607": True,
                "affects_623": True,
                "dgii_withholding_code": "07",
                "sequence": 10,
                "notes": "ISR 5% sobre base imponible — ventas a entidades gubernamentales (607).",
            },
            {
                "code": "RET-ITBIS-30",
                "legacy_code": "wh_itbis_30",
                "name": "Retención ITBIS 30%",
                "tax_name": "-30% ITBIS Leg. (N02-05)",
                "tax_use": "purchase",
                "withholding_type": "itbis",
                "base_type": "itbis",
                "withholding_rate": 30.0,
                "partner_scope": "both",
                "move_scope": "both",
                "affects_606": True,
                "affects_607": True,
                "dgii_withholding_code": "02",
                "sequence": 20,
                "notes": "30% del ITBIS facturado — servicios legales N02-05.",
            },
            {
                "code": "RET-ITBIS-100",
                "legacy_code": "wh_itbis_100",
                "name": "Retención ITBIS 100%",
                "tax_name": "-100% ITBIS (N07-09)",
                "tax_use": "purchase",
                "withholding_type": "itbis",
                "base_type": "itbis",
                "withholding_rate": 100.0,
                "partner_scope": "both",
                "move_scope": "both",
                "affects_606": True,
                "affects_607": True,
                "dgii_withholding_code": "03",
                "sequence": 25,
                "notes": "100% del ITBIS facturado — N07-09.",
            },
            {
                "code": "RET-INF-ISR-10",
                "legacy_code": "wh_isr_10",
                "name": "Retención ISR 10% Proveedor Informal",
                "tax_name": "-10% ISR Fee",
                "tax_use": "purchase",
                "withholding_type": "isr",
                "base_type": "untaxed",
                "withholding_rate": 10.0,
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "dgii_withholding_code": "02",
                "sequence": 30,
                "notes": "ISR 10% sobre base imponible — proveedor informal (606).",
            },
            {
                "code": "RET-INF-ITBIS-75",
                "legacy_code": "wh_itbis_75",
                "name": "Retención ITBIS 75% Proveedor Informal",
                "tax_name": "-75% ITBIS (N08-10)",
                "tax_use": "purchase",
                "withholding_type": "itbis",
                "base_type": "itbis",
                "withholding_rate": 75.0,
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "dgii_withholding_code": "04",
                "sequence": 40,
                "notes": "75% del ITBIS facturado — proveedor informal N08-10 (606).",
            },
            {
                "code": "RET-ISR-2",
                "legacy_code": "wh_isr_2",
                "name": "Retención ISR 2%",
                "tax_name": "-2% ISR (N07-07)",
                "tax_use": "purchase",
                "withholding_type": "isr",
                "base_type": "untaxed",
                "withholding_rate": 2.0,
                "partner_scope": "both",
                "move_scope": "both",
                "affects_606": True,
                "affects_607": True,
                "dgii_withholding_code": "03",
                "sequence": 50,
                "notes": "ISR 2% sobre base imponible — N07-07.",
            },
            {
                "code": "RET-HON-10",
                "legacy_code": "wh_isr_fees_10",
                "name": "Retención ISR 10% Honorarios",
                "tax_name": "-10% ISR Rent.",
                "tax_use": "purchase",
                "withholding_type": "isr",
                "base_type": "untaxed",
                "withholding_rate": 10.0,
                "partner_scope": "both",
                "move_scope": "both",
                "affects_606": True,
                "affects_607": True,
                "dgii_withholding_code": "02",
                "sequence": 60,
                "notes": "ISR 10% sobre base imponible — honorarios y alquileres.",
            },
            # Retenciones adicionales l10n_do — inactivas hasta confirmación contable
            {
                "code": "RET-ITBIS-30-PROF",
                "name": "Retención ITBIS 30% Profesional",
                "tax_name": "-30% ITBIS Prof. (N02-05)",
                "tax_use": "purchase",
                "withholding_type": "itbis",
                "base_type": "itbis",
                "withholding_rate": 30.0,
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "active": False,
                "sequence": 70,
                "notes": "Variante profesional N02-05. Inactiva — confirmar con contabilidad antes de usar.",
            },
            {
                "code": "RET-ITBIS-100-N01",
                "name": "Retención ITBIS 100% N01-11",
                "tax_name": "-100% ITBIS (N01-11)",
                "tax_use": "purchase",
                "withholding_type": "itbis",
                "base_type": "itbis",
                "withholding_rate": 100.0,
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "active": False,
                "sequence": 75,
                "notes": "Norma N01-11. Inactiva — confirmar escenario contable.",
            },
            {
                "code": "RET-ITBIS-100-R293",
                "name": "Retención ITBIS 100% R293-11",
                "tax_name": "-100% ITBIS (R293-11)",
                "tax_use": "purchase",
                "withholding_type": "itbis",
                "base_type": "itbis",
                "withholding_rate": 100.0,
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "active": False,
                "sequence": 76,
                "notes": "Norma R293-11. Inactiva — confirmar escenario contable.",
            },
            {
                "code": "RET-ISR-10-L253",
                "name": "Retención ISR 10% L253-12",
                "tax_name": "-10% ISR (L253-12)",
                "tax_use": "purchase",
                "withholding_type": "isr",
                "base_type": "untaxed",
                "withholding_rate": 10.0,
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "active": False,
                "sequence": 80,
                "notes": "Norma L253-12. Inactiva — confirmar escenario contable.",
            },
            {
                "code": "RET-ISR-2-MAT",
                "name": "Retención ISR 2% Materiales",
                "tax_name": "-2% ISR Mat.",
                "tax_use": "purchase",
                "withholding_type": "isr",
                "base_type": "untaxed",
                "withholding_rate": 2.0,
                "partner_scope": "supplier",
                "move_scope": "purchase",
                "affects_606": True,
                "affects_607": False,
                "active": False,
                "sequence": 85,
                "notes": "ISR 2% materiales. Inactiva — confirmar escenario contable.",
            },
        ]

    @api.model
    def _find_catalog_record(self, spec, company):
        Catalog = self.env["hellenia.withholding.catalog"]
        rec = Catalog.search([("code", "=", spec["code"]), ("company_id", "=", company.id)], limit=1)
        if not rec and spec.get("legacy_code"):
            rec = Catalog.search(
                [("code", "=", spec["legacy_code"]), ("company_id", "=", company.id)],
                limit=1,
            )
        return rec

    @api.model
    def _domain_for_payment(self, partner_type, move_type, company=None):
        """Dominio estándar para selector del wizard de pagos."""
        company = company or self.env.company
        move_scope = "sale" if move_type in ("out_invoice", "out_refund") else "purchase"
        return [
            ("active", "=", True),
            ("code", "not in", ["RET-NONE", "wh_none"]),
            ("partner_scope", "in", [partner_type, "both"]),
            ("move_scope", "in", [move_scope, "both"]),
            ("company_id", "=", company.id),
            ("account_id", "!=", False),
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
            wants_active = spec.get("active", True)
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
                "affects_623": spec.get("affects_623", False),
                "dgii_withholding_code": spec.get("dgii_withholding_code"),
                "notes": spec.get("notes"),
                "company_id": company.id,
                "tax_id": tax.id if tax else False,
                "rate": spec.get("withholding_rate") or (abs(tax.amount) if tax else 0.0),
                "active": False,
            }
            rec = self._find_catalog_record(spec, company)
            if rec:
                rec.write(vals)
            else:
                rec = Catalog.create(vals)
            rec._compute_account_id()
            can_activate = wants_active and bool(tax) and bool(rec.account_id)
            if rec.code in ("RET-NONE", "wh_none"):
                can_activate = False
            rec.write({"active": can_activate})
            result.append(
                {
                    "code": spec["code"],
                    "id": rec.id,
                    "tax": tax.name if tax else None,
                    "active": rec.active,
                    "account": rec.account_id.code if rec.account_id else None,
                }
            )
        return result
