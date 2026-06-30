"""Configuración bancos, diarios y métodos de pago Hellenia."""
from __future__ import annotations

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

BANK_NAME = "Banco López de Haro"
BANK_ACCOUNTS = (
    {"label": "Cuenta corriente DOP", "currency": "DOP", "acc_number": "4040043811", "journal_code": "BNKD"},
    {"label": "Cuenta ahorro USD", "currency": "USD", "acc_number": "4010461048", "journal_code": "BNKU"},
)

# Métodos de pago por diario (código método Odoo, tipo, etiqueta español)
JOURNAL_PAYMENT_METHODS = {
    "CSH1": [
        ("manual", "inbound", "Efectivo"),
        ("manual", "outbound", "Efectivo"),
    ],
    "BNKD": [
        ("manual", "inbound", "Transferencia"),
        ("manual", "inbound", "Tarjeta"),
        ("manual", "outbound", "Transferencia"),
        ("check_printing", "outbound", "Cheque"),
    ],
    "BNKU": [
        ("manual", "inbound", "Transferencia"),
        ("manual", "inbound", "Tarjeta"),
        ("manual", "outbound", "Transferencia"),
        ("check_printing", "outbound", "Cheque"),
    ],
}

JOURNAL_SPECS = {
    "CSH1": {"name": "Caja / Efectivo", "type": "cash", "currency": False},
    "BNKD": {"name": "Banco López de Haro DOP", "type": "bank", "currency": "DOP"},
    "BNKU": {"name": "Banco López de Haro USD", "type": "bank", "currency": "USD"},
}

GENERIC_METHOD_LABELS = frozenset({"Manual Payment", "Checks", "Check", "Manual"})


class HelleniaAccountPaymentSetup(models.AbstractModel):
    _name = "hellenia.account.payment.setup"
    _description = "Hellenia — bancos, diarios y métodos de pago"

    @api.model
    def _get_or_create_bank(self):
        Bank = self.env["res.bank"]
        bank = Bank.search([("name", "=", BANK_NAME)], limit=1)
        if not bank:
            bank = Bank.create({"name": BANK_NAME})
        return bank

    @api.model
    def _ensure_partner_bank(self, company, bank, spec):
        currency = self.env["res.currency"].search([("name", "=", spec["currency"])], limit=1)
        PartnerBank = self.env["res.partner.bank"]
        rec = PartnerBank.search(
            [
                ("partner_id", "=", company.partner_id.id),
                ("acc_number", "=", spec["acc_number"]),
            ],
            limit=1,
        )
        vals = {
            "partner_id": company.partner_id.id,
            "bank_id": bank.id,
            "currency_id": currency.id,
            "acc_number": spec["acc_number"],
            "acc_holder_name": company.name,
        }
        if rec:
            rec.write(vals)
        else:
            rec = PartnerBank.create(vals)
        return rec

    @api.model
    def _ensure_journal(self, company, code, spec, partner_bank=None):
        Journal = self.env["account.journal"]
        journal = Journal.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)
        currency = False
        if spec.get("currency"):
            currency = self.env["res.currency"].search([("name", "=", spec["currency"])], limit=1)
        vals = {
            "name": spec["name"],
            "code": code,
            "type": spec["type"],
            "company_id": company.id,
        }
        if currency:
            vals["currency_id"] = currency.id
        if partner_bank and spec["type"] == "bank":
            vals["bank_account_id"] = partner_bank.id
        if journal:
            journal.write(vals)
        else:
            journal = Journal.create(vals)
        return journal

    @api.model
    def _ensure_payment_method_lines(self, journal, methods):
        Method = self.env["account.payment.method"]
        Line = self.env["account.payment.method.line"]
        created_labels = []
        for pm_code, pm_type, label in methods:
            method = Method.search([("code", "=", pm_code), ("payment_type", "=", pm_type)], limit=1)
            if not method:
                _logger.warning("Hellenia payment setup: método %s/%s no encontrado", pm_code, pm_type)
                continue
            line = Line.search(
                [
                    ("journal_id", "=", journal.id),
                    ("payment_method_id", "=", method.id),
                    ("name", "=", label),
                ],
                limit=1,
            )
            if line:
                if line.name != label:
                    line.name = label
            else:
                line = Line.create(
                    {
                        "journal_id": journal.id,
                        "payment_method_id": method.id,
                        "name": label,
                    }
                )
            created_labels.append(label)

        # Renombrar líneas genéricas duplicadas (no eliminar — Odoo puede requerirlas)
        for line in Line.search([("journal_id", "=", journal.id)]):
            if line.name in GENERIC_METHOD_LABELS and line.name not in created_labels:
                replacement = next(
                    (
                        lbl
                        for _code, ptype, lbl in methods
                        if line.payment_method_id.code == _code and line.payment_method_id.payment_type == ptype
                    ),
                    None,
                )
                if replacement and not Line.search_count(
                    [("journal_id", "=", journal.id), ("name", "=", replacement)], limit=1
                ):
                    line.name = replacement
                    created_labels.append(replacement)
        return created_labels

    @api.model
    def configure_banks_and_payments(self):
        """Configura cuentas bancarias, diarios y métodos de pago Hellenia."""
        company = self.env.company
        bank = self._get_or_create_bank()
        partner_banks = {}
        journals = {}

        for spec in BANK_ACCOUNTS:
            pb = self._ensure_partner_bank(company, bank, spec)
            partner_banks[spec["journal_code"]] = pb
            jspec = JOURNAL_SPECS[spec["journal_code"]]
            journals[spec["journal_code"]] = self._ensure_journal(
                company, spec["journal_code"], jspec, partner_bank=pb
            )

        journals["CSH1"] = self._ensure_journal(company, "CSH1", JOURNAL_SPECS["CSH1"])

        legacy = self.env["account.journal"].search(
            [("code", "=", "BNK1"), ("company_id", "=", company.id)], limit=1
        )
        if legacy and legacy.id not in [j.id for j in journals.values()]:
            if not self.env["account.move"].search_count([("journal_id", "=", legacy.id)], limit=1):
                legacy.active = False
            else:
                legacy.write({"name": "Banco (legacy)"})

        payment_lines = {}
        for code, methods in JOURNAL_PAYMENT_METHODS.items():
            journal = journals.get(code)
            if journal:
                payment_lines[code] = self._ensure_payment_method_lines(journal, methods)

        return {
            "banks": [s["acc_number"] for s in BANK_ACCOUNTS],
            "journals": {k: v.code for k, v in journals.items()},
            "payment_lines": payment_lines,
        }

    @api.model
    def configure_withholding_reference(self):
        """Activa impuestos retención RD clave y documenta estado."""
        Tax = self.env["account.tax"]
        keys = [
            ("-5% ISR Gov.", "sale"),
            ("-30% ITBIS Leg. (N02-05)", "purchase"),
            ("-10% ISR Fee", "purchase"),
            ("-75% ITBIS (N08-10)", "purchase"),
        ]
        result = []
        for name, use in keys:
            tax = Tax.search(
                [("name", "=", name), ("type_tax_use", "=", use), ("company_id", "=", self.env.company.id)],
                limit=1,
            )
            if tax and not tax.active:
                tax.active = True
            result.append({"name": name, "found": bool(tax), "active": tax.active if tax else False})
        prof = Tax.search(
            [("name", "=", "-30% ITBIS Prof. (N02-05)"), ("company_id", "=", self.env.company.id)], limit=1
        )
        if prof and not prof.active:
            prof.active = True
            result.append({"name": prof.name, "found": True, "active": True})
        return result
