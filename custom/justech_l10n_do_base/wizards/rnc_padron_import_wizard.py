# -*- coding: utf-8 -*-
"""Importación idempotente del padrón RNC (TXT/CSV)."""
from __future__ import annotations

import base64
import csv
import io
from datetime import datetime

from odoo import _, fields, models
from odoo.exceptions import UserError


class JustechDoRncPadronImportWizard(models.TransientModel):
    _name = "justech.do.rnc.padron.import.wizard"
    _description = "Actualizar padrón RNC"

    data_file = fields.Binary(string="Archivo TXT/CSV", required=True)
    filename = fields.Char(string="Nombre de archivo")
    delimiter = fields.Selection(
        [
            ("|", "Pipe |"),
            (",", "Coma ,"),
            (";", "Punto y coma ;"),
            ("\t", "Tabulador"),
        ],
        string="Separador",
        default="|",
        required=True,
    )
    has_header = fields.Boolean(string="Primera fila es encabezado", default=False)
    replace_all = fields.Boolean(
        string="Reemplazar padrón completo",
        default=False,
        help="Si se marca, archiva el padrón actual antes de importar. "
        "Por defecto actualiza/inserta por RNC (idempotente).",
    )
    source = fields.Char(string="Fuente", default="dgii_txt", required=True)
    result_log = fields.Text(string="Resultado", readonly=True)

    def _justech_parse_dgii_row(self, row):
        """Parsea fila DGII oficial o formato simple Justech.

        DGII (DGII_RNC.TXT):
          RNC|Razón|Nombre comercial|Actividad|...|Fecha|Estado|Categoría

        Formato simple:
          RNC|Razón|[Comercial]|[Estado]|[Categoría]|[Actividad]
        """
        if not row or not any((c or "").strip() for c in row):
            return None
        rnc_raw = row[0] if len(row) > 0 else ""
        name = (row[1] if len(row) > 1 else "").strip()
        trade = (row[2] if len(row) > 2 else "").strip() or False

        # Detectar formato oficial DGII: estado/categoría al final.
        is_dgii = len(row) >= 10 and (row[9] or "").strip().upper() in {
            "ACTIVO",
            "SUSPENDIDO",
            "INACTIVO",
            "ACTIVE",
            "INACTIVE",
        }
        if is_dgii:
            activity = (row[3] if len(row) > 3 else "").strip() or False
            state_raw = (row[9] if len(row) > 9 else "").strip().lower()
            category = (row[10] if len(row) > 10 else "").strip() or False
        else:
            state_raw = (row[3] if len(row) > 3 else "").strip().lower()
            category = (row[4] if len(row) > 4 else "").strip() or False
            activity = (row[5] if len(row) > 5 else "").strip() or False

        Padron = self.env["justech.do.rnc.padron"]
        rnc = Padron.normalize_rnc(rnc_raw)
        if not rnc or not name:
            return None
        if len(rnc) not in (9, 11):
            return None

        state = "active"
        if state_raw in ("inactive", "inactivo", "suspendido", "0", "n"):
            state = "inactive"
        elif state_raw and state_raw not in (
            "active",
            "activo",
            "1",
            "s",
            "si",
            "sí",
            "normal",
        ):
            # "normal" a veces viene en categoría, no en estado
            if state_raw not in ("",):
                state = "unknown"

        if is_dgii:
            if state_raw in ("activo", "active"):
                state = "active"
            elif state_raw in ("suspendido", "inactivo", "inactive"):
                state = "inactive"

        return {
            "rnc": rnc,
            "name": name,
            "trade_name": trade,
            "state": state,
            "category": category,
            "economic_activity": activity,
        }

    def action_import(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError(_("Seleccione un archivo."))
        raw = base64.b64decode(self.data_file)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        reader = csv.reader(io.StringIO(text), delimiter=self.delimiter)
        rows = list(reader)
        if not rows:
            raise UserError(_("El archivo está vacío."))
        if self.has_header:
            rows = rows[1:]

        Padron = self.env["justech.do.rnc.padron"].sudo()
        sync_date = fields.Datetime.now()
        if self.replace_all:
            Padron.search([]).write({"active": False})

        created = updated = skipped = 0
        for row in rows:
            parsed = self._justech_parse_dgii_row(row)
            if not parsed:
                skipped += 1
                continue
            vals = {
                **parsed,
                "source": self.source,
                "sync_date": sync_date,
                "active": True,
            }
            existing = Padron.with_context(active_test=False).search(
                [("rnc", "=", parsed["rnc"])], limit=1
            )
            if existing:
                existing.write(vals)
                updated += 1
            else:
                Padron.create(vals)
                created += 1

        self.result_log = _(
            "Importación %(when)s\n"
            "Creados: %(c)s\n"
            "Actualizados: %(u)s\n"
            "Omitidos: %(s)s\n"
            "Total activo: %(t)s"
        ) % {
            "when": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "c": created,
            "u": updated,
            "s": skipped,
            "t": Padron.search_count([]),
        }
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
