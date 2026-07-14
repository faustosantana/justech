# -*- coding: utf-8 -*-
"""Wizard modal: Anular comprobante fiscal (motivo 608 + observación)."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Catálogo DGII 608 (mismo selection que account.move.justech_do_ncf_cancel_type).
_CANCEL_TYPES = [
    ("01", "01 — Secuencia no utilizada"),
    ("02", "02 — Errores de impresión"),
    ("03", "03 — Impresión defectuosa"),
    ("04", "04 — Corrección de información"),
    ("05", "05 — Cambio de productos"),
    ("06", "06 — Devolución de productos"),
    ("07", "07 — Omisión de productos"),
    ("08", "08 — Errores en secuencias NCF"),
    ("09", "09 — Cese de operaciones"),
    ("10", "10 — Pérdida o hurto de talonario"),
    ("99", "99 — Otro"),
]


class JustechDoNcfVoidWizard(models.TransientModel):
    _name = "justech.do.ncf.void.wizard"
    _description = "Anular comprobante fiscal"

    move_id = fields.Many2one(
        "account.move", string="Factura", required=True, readonly=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="move_id.company_id", string="Empresa", readonly=True)
    partner_id = fields.Many2one(related="move_id.partner_id", string="Cliente", readonly=True)
    document_type_id = fields.Many2one(
        related="move_id.justech_do_document_type_id",
        string="Tipo de comprobante",
        readonly=True,
    )
    ncf = fields.Char(string="NCF", compute="_compute_ncf", readonly=True)

    @api.depends("move_id", "move_id.justech_do_ncf", "move_id.l10n_latam_document_number")
    def _compute_ncf(self):
        for wiz in self:
            wiz.ncf = wiz.move_id._justech_get_issued_ncf() if wiz.move_id else False
    invoice_date = fields.Date(related="move_id.invoice_date", string="Fecha de emisión", readonly=True)
    state = fields.Selection(related="move_id.state", string="Estado actual", readonly=True)
    cancel_type = fields.Selection(
        selection=_CANCEL_TYPES,
        string="Motivo de anulación",
        required=True,
        default="04",
        help="Código DGII formato 608.",
    )
    observation = fields.Text(
        string="Observación adicional",
        help="Detalle libre del motivo. Obligatoria si el motivo es «Otro».",
    )
    requester_id = fields.Many2one(
        "res.users",
        string="Usuario solicitante",
        readonly=True,
        default=lambda self: self.env.user,
    )
    help_note = fields.Html(
        string="Ayuda",
        sanitize=True,
        readonly=True,
        default=(
            "<p>Anular el NCF registra el comprobante en el <strong>608</strong>. "
            "Esta acción no equivale necesariamente a emitir una nota de crédito "
            "ni a devolver un pago.</p>"
        ),
    )

    @api.onchange("cancel_type")
    def _onchange_cancel_type(self):
        # UX: resaltar necesidad de observación cuando el motivo es Otro.
        return

    def action_confirm_void(self):
        self.ensure_one()
        move = self.move_id
        if move.justech_do_ncf_voided:
            raise UserError(_("Este comprobante fiscal ya fue anulado."))
        if move.state != "posted":
            raise UserError(_("Solo documentos publicados pueden anular el comprobante fiscal."))
        if not move._justech_get_issued_ncf():
            raise UserError(_("No hay comprobante fiscal para anular."))
        if not self.cancel_type:
            raise UserError(_("Debe indicar el motivo de anulación."))
        observation = (self.observation or "").strip()
        if self.cancel_type == "99" and not observation:
            raise UserError(
                _("Si el motivo es «Otro», debe indicar una observación adicional.")
            )
        label = dict(self._fields["cancel_type"].selection).get(self.cancel_type, self.cancel_type)
        reason = observation or label
        # Código 99 (Otro) no se exporta como código DGII nativo: mapear a 04 para 608
        # preservando el detalle en la observación/motivo.
        dgii_code = self.cancel_type if self.cancel_type != "99" else "04"
        move.write(
            {
                "justech_do_ncf_void_reason": reason,
                "justech_do_ncf_cancel_type": dgii_code,
            }
        )
        move.with_context(
            justech_void_from_wizard=True,
            justech_void_cancel_label=label,
            justech_void_observation=observation,
        ).action_void_ncf()
        return {"type": "ir.actions.act_window_close"}
