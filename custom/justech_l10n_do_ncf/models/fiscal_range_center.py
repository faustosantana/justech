"""Centro único de administración fiscal (menú Rangos).

Unifica Ventas / Compras Emitidos / Compras Recibidos sin menús duplicados.
No inventa rangos ni consume secuencias.
"""
from odoo import _, api, fields, models

_DocType = "justech.do.fiscal.document.type"
_RECEIVED_PREFIXES = (
    "B01",
    "B02",
    "B03",
    "B04",
    "B14",
    "B15",
    "B16",
    "E31",
    "E32",
    "E33",
    "E34",
    "E41",
    "E43",
    "E44",
    "E45",
    "E46",
    "E47",
)
_PURCHASE_ISSUED = ("B11", "B13", "B17")


class JustechDoFiscalRangeCenter(models.Model):
    _name = "justech.do.fiscal.range.center"
    _description = "Centro de Administración Fiscal — Rangos"
    _rec_name = "name"

    name = fields.Char(default="Rangos", readonly=True)
    flow_filter = fields.Selection(
        selection=[
            ("all", "Todos"),
            ("sale", "Ventas"),
            ("purchase_issued", "Compras Emitidos"),
            ("purchase_received", "Compras Recibidos"),
        ],
        string="Tipo de Flujo",
        default="all",
        required=True,
    )
    line_ids = fields.One2many(
        "justech.do.fiscal.range.center.line",
        "center_id",
        string="Tipos",
    )
    # KPI Ventas
    sale_types_count = fields.Integer(compute="_compute_kpis")
    sale_active_count = fields.Integer(compute="_compute_kpis")
    sale_pending_count = fields.Integer(compute="_compute_kpis")
    sale_expired_count = fields.Integer(compute="_compute_kpis")
    # KPI Compras Emitidos
    issued_types_count = fields.Integer(compute="_compute_kpis")
    issued_active_count = fields.Integer(compute="_compute_kpis")
    issued_no_range_count = fields.Integer(compute="_compute_kpis")
    issued_expired_count = fields.Integer(compute="_compute_kpis")
    # KPI Compras Recibidos
    received_types_count = fields.Integer(compute="_compute_kpis")
    received_active_count = fields.Integer(compute="_compute_kpis")
    received_disabled_count = fields.Integer(compute="_compute_kpis")
    received_historic_count = fields.Integer(compute="_compute_kpis")

    @api.depends(
        "line_ids",
        "line_ids.flow",
        "line_ids.status",
        "line_ids.active_flag",
        "line_ids.usage_count",
    )
    def _compute_kpis(self):
        for center in self:
            sales = center.line_ids.filtered(lambda l: l.flow == "sale")
            issued = center.line_ids.filtered(lambda l: l.flow == "purchase_issued")
            received = center.line_ids.filtered(lambda l: l.flow == "purchase_received")
            center.sale_types_count = len(sales)
            center.sale_active_count = len(sales.filtered(lambda l: l.status == "active"))
            center.sale_pending_count = len(
                sales.filtered(lambda l: l.status in ("no_range", "inactive", "draft"))
            )
            center.sale_expired_count = len(
                sales.filtered(lambda l: l.status in ("expired", "depleted"))
            )
            center.issued_types_count = len(issued)
            center.issued_active_count = len(
                issued.filtered(lambda l: l.status == "active")
            )
            center.issued_no_range_count = len(
                issued.filtered(lambda l: l.status == "no_range")
            )
            center.issued_expired_count = len(
                issued.filtered(lambda l: l.status in ("expired", "depleted"))
            )
            center.received_types_count = len(received)
            center.received_active_count = len(
                received.filtered(lambda l: l.active_flag)
            )
            center.received_disabled_count = len(
                received.filtered(lambda l: not l.active_flag)
            )
            center.received_historic_count = len(
                received.filtered(lambda l: l.usage_count > 0)
            )

    @api.model
    def get_or_create(self):
        center = self.sudo().search([], limit=1)
        if not center:
            center = self.sudo().create({"name": "Rangos"})
        center.sudo().refresh_lines()
        return center

    def refresh_lines(self):
        """Reconstruye filas administrativas sin inventar rangos ni NCF."""
        self.ensure_one()
        Line = self.env["justech.do.fiscal.range.center.line"].sudo()
        existing = {(l.flow, l.company_id.id or 0, l.prefix): l for l in self.line_ids}
        keep = set()
        vals_list = []

        DocType = self.env[_DocType]
        companies = self.env["res.company"].search([])
        Range = self.env["justech.do.ncf.range"]
        Config = self.env["justech.do.purchase.emission.config"]
        Latam = self.env["l10n_latam.document.type"]

        # Ventas: tipos venta × empresa + rango activo si existe
        sale_docs = DocType.search([("is_sale_document", "=", True)])
        for company in companies:
            for doc in sale_docs:
                prefix = doc.prefix
                key = ("sale", company.id, prefix)
                keep.add(key)
                rng = Range.search(
                    [
                        ("company_id", "=", company.id),
                        ("document_type_id", "=", doc.id),
                        ("state", "=", "active"),
                    ],
                    order="date_to desc, id desc",
                    limit=1,
                )
                if not rng:
                    rng = Range.search(
                        [
                            ("company_id", "=", company.id),
                            ("document_type_id", "=", doc.id),
                        ],
                        order="date_to desc, id desc",
                        limit=1,
                    )
                payload = self._vals_from_range(
                    flow="sale",
                    company=company,
                    prefix=prefix,
                    name=doc.name,
                    origin="justech",
                    consumes=True,
                    rng=rng,
                    document_type=doc,
                )
                vals_list.append((key, payload))

        # Compras emitidos: configs B11/B13/B17 por empresa
        Config.ensure_configs_for_companies(companies)
        configs = Config.search([("company_id", "in", companies.ids)])
        for cfg in configs:
            prefix = cfg.prefix
            if prefix not in _PURCHASE_ISSUED:
                continue
            key = ("purchase_issued", cfg.company_id.id, prefix)
            keep.add(key)
            payload = {
                "center_id": self.id,
                "flow": "purchase_issued",
                "company_id": cfg.company_id.id,
                "prefix": prefix,
                "code": cfg.code or prefix[-2:],
                "name": cfg.name_full or cfg.document_type_id.name,
                "origin": "justech",
                "consumes_sequence": True,
                "status": cfg.status or "no_range",
                "status_label": cfg.status_label or "Sin rango autorizado",
                "active_flag": bool(cfg.emission_enabled),
                "range_id": cfg.range_id.id if cfg.range_id else False,
                "emission_config_id": cfg.id,
                "document_type_id": cfg.document_type_id.id,
                "sequence_start": cfg.sequence_start or 0,
                "sequence_end": cfg.sequence_end or 0,
                "next_sequence": cfg.range_id.next_sequence if cfg.range_id else 0,
                "next_ncf": cfg.next_ncf or False,
                "remaining_count": cfg.range_id.remaining_count if cfg.range_id else 0,
                "date_from": cfg.authorization_date,
                "date_to": cfg.expiration_date,
                "journal_names": ", ".join(cfg.range_id.journal_ids.mapped("name"))
                if cfg.range_id
                else False,
                "participates_606": True,
                "participates_607": False,
                "participates_608": True,
                "participates_609": prefix == "B17",
                "participates_623": False,
            }
            vals_list.append((key, payload))

        # Compras recibidos: LATAM global (sin empresa / sin rango)
        latam_types = Latam.search([("doc_code_prefix", "in", list(_RECEIVED_PREFIXES))])
        for latam in latam_types:
            prefix = (latam.doc_code_prefix or "").strip().upper()
            key = ("purchase_received", 0, prefix)
            keep.add(key)
            usage = 0
            last_used = False
            if "justech_do_usage_count" in latam._fields:
                usage = latam.justech_do_usage_count
                last_used = latam.justech_do_last_used
            else:
                Move = self.env["account.move"]
                domain = [
                    ("l10n_latam_document_type_id", "=", latam.id),
                    ("move_type", "in", ("in_invoice", "in_refund")),
                ]
                usage = Move.search_count(domain)
                last = Move.search(domain, order="write_date desc", limit=1)
                last_used = last.write_date if last else False
            is_ecf = prefix.startswith("E")
            payload = {
                "center_id": self.id,
                "flow": "purchase_received",
                "company_id": False,
                "prefix": prefix,
                "code": prefix[1:] if len(prefix) == 3 else prefix,
                "name": latam.name,
                "origin": "latam",
                "consumes_sequence": False,
                "status": "active" if latam.active else "inactive",
                "status_label": "Activo" if latam.active else "Deshabilitado",
                "active_flag": bool(latam.active),
                "latam_document_type_id": latam.id,
                "usage_count": usage,
                "last_used": last_used,
                "is_electronic_supplier": is_ecf,
                "is_received_document": True,
                "document_category": "e-CF" if is_ecf else "B",
                "participates_606": True,
                "participates_607": False,
                "participates_608": False,
                "participates_609": False,
                "participates_623": False,
                "help_text": (
                    "Documento recibido del proveedor. NCF manual. "
                    "No consume rangos ni secuencias Justech."
                ),
            }
            vals_list.append((key, payload))

        for key, payload in vals_list:
            rec = existing.get(key)
            if rec:
                rec.write(payload)
            else:
                Line.create(payload)

        for key, rec in existing.items():
            if key not in keep:
                rec.unlink()
        return True

    def _vals_from_range(
        self, flow, company, prefix, name, origin, consumes, rng, document_type
    ):
        status = "no_range"
        status_label = "Sin rango autorizado"
        if rng:
            status = rng.state
            labels = dict(rng._fields["state"]._description_selection(self.env))
            status_label = labels.get(rng.state, rng.state)
            if rng.state == "draft":
                status_label = "Inactivo"
        return {
            "center_id": self.id,
            "flow": flow,
            "company_id": company.id,
            "prefix": prefix,
            "code": document_type.code if document_type else prefix[-2:],
            "name": name,
            "origin": origin,
            "consumes_sequence": consumes,
            "status": status if status != "draft" else "inactive",
            "status_label": status_label,
            "active_flag": bool(rng and rng.state == "active"),
            "range_id": rng.id if rng else False,
            "document_type_id": document_type.id if document_type else False,
            "sequence_start": rng.sequence_start if rng else 0,
            "sequence_end": rng.sequence_end if rng else 0,
            "next_sequence": rng.next_sequence if rng else 0,
            "next_ncf": rng.next_ncf_display if rng else False,
            "remaining_count": rng.remaining_count if rng else 0,
            "date_from": rng.date_from if rng else False,
            "date_to": rng.date_to if rng else False,
            "journal_names": ", ".join(rng.journal_ids.mapped("name")) if rng else False,
            "participates_606": False,
            "participates_607": True,
            "participates_608": True,
            "participates_609": False,
            "participates_623": False,
        }

    @api.onchange("flow_filter")
    def _onchange_flow_filter(self):
        # Solo UX; las líneas se filtran en la vista por domain.
        return

    def action_refresh(self):
        self.ensure_one()
        # Lectura operativa: refresh técnico con sudo (no altera rangos/NCF).
        self.sudo().refresh_lines()
        return self.action_open()

    @api.model
    def action_open(self):
        center = self.get_or_create()
        return {
            "type": "ir.actions.act_window",
            "name": _("Rangos"),
            "res_model": self._name,
            "res_id": center.id,
            "view_mode": "form",
            "target": "current",
            "context": {"form_view_initial_mode": "edit"},
        }


class JustechDoFiscalRangeCenterLine(models.Model):
    _name = "justech.do.fiscal.range.center.line"
    _description = "Línea del Centro de Rangos Fiscales"
    _order = "flow, company_id, prefix"

    center_id = fields.Many2one(
        "justech.do.fiscal.range.center",
        required=True,
        ondelete="cascade",
        index=True,
    )
    flow = fields.Selection(
        selection=[
            ("sale", "Ventas"),
            ("purchase_issued", "Compras Emitidos"),
            ("purchase_received", "Compras Recibidos"),
        ],
        string="Flujo",
        required=True,
        index=True,
    )
    company_id = fields.Many2one("res.company", string="Empresa", index=True)
    company_display = fields.Char(compute="_compute_company_display", store=True)
    prefix = fields.Char(string="Código", required=True, index=True)
    code = fields.Char(string="Código corto")
    name = fields.Char(string="Nombre", required=True)
    origin = fields.Selection(
        selection=[
            ("justech", "Motor Fiscal Justech"),
            ("latam", "LATAM"),
        ],
        string="Origen",
        required=True,
    )
    consumes_sequence = fields.Boolean(string="Consume secuencia")
    consumes_sequence_label = fields.Char(
        string="Consume secuencia",
        compute="_compute_consumes_label",
    )
    status = fields.Selection(
        selection=[
            ("active", "Activo"),
            ("no_range", "Sin rango"),
            ("inactive", "Inactivo"),
            ("draft", "Borrador"),
            ("expired", "Vencido"),
            ("depleted", "Agotado"),
            ("cancelled", "Cerrado"),
        ],
        string="Estado",
    )
    status_label = fields.Char(string="Estado visible")
    active_flag = fields.Boolean(string="Activo")
    range_id = fields.Many2one("justech.do.ncf.range", string="Rango", ondelete="set null")
    emission_config_id = fields.Many2one(
        "justech.do.purchase.emission.config", ondelete="set null"
    )
    document_type_id = fields.Many2one(_DocType, ondelete="set null")
    latam_document_type_id = fields.Many2one(
        "l10n_latam.document.type", ondelete="set null"
    )
    sequence_start = fields.Integer(string="Desde")
    sequence_end = fields.Integer(string="Hasta")
    next_sequence = fields.Integer(string="Próximo (núm.)")
    next_ncf = fields.Char(string="Próximo")
    remaining_count = fields.Integer(string="Disponibles")
    date_from = fields.Date(string="Vigente desde")
    date_to = fields.Date(string="Vencimiento")
    journal_names = fields.Char(string="Diario")
    responsible_name = fields.Char(string="Responsable")
    usage_count = fields.Integer(string="Usado en histórico")
    last_used = fields.Datetime(string="Último uso")
    is_electronic_supplier = fields.Boolean(string="Proveedor Electrónico")
    is_received_document = fields.Boolean(
        string="Documento Recibido",
        default=False,
        help="True solo para flujo Compras Recibidos (LATAM).",
    )
    document_category = fields.Char(string="Tipo")
    help_text = fields.Text(string="Descripción")
    participates_606 = fields.Boolean(string="606")
    participates_607 = fields.Boolean(string="607")
    participates_608 = fields.Boolean(string="608")
    participates_609 = fields.Boolean(string="609")
    participates_623 = fields.Boolean(string="623")

    @api.depends("company_id")
    def _compute_company_display(self):
        for rec in self:
            rec.company_display = rec.company_id.name if rec.company_id else "GLOBAL"

    @api.depends("consumes_sequence")
    def _compute_consumes_label(self):
        for rec in self:
            rec.consumes_sequence_label = "🟢 Sí" if rec.consumes_sequence else "⚪ No"

    def action_open_range(self):
        self.ensure_one()
        if self.range_id:
            return {
                "type": "ir.actions.act_window",
                "name": _("Administrar rango"),
                "res_model": "justech.do.ncf.range",
                "res_id": self.range_id.id,
                "view_mode": "form",
                "target": "current",
            }
        if self.flow in ("sale", "purchase_issued") and self.document_type_id:
            return {
                "type": "ir.actions.act_window",
                "name": _("Configurar rango"),
                "res_model": "justech.do.ncf.range",
                "view_mode": "list,form",
                "domain": [
                    ("company_id", "=", self.company_id.id),
                    ("document_type_id", "=", self.document_type_id.id),
                ],
                "context": {
                    "default_company_id": self.company_id.id,
                    "default_document_type_id": self.document_type_id.id,
                    "default_prefix": self.prefix,
                },
            }
        return True
