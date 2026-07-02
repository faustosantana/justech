# -*- coding: utf-8 -*-
"""Fábrica de conduces — creación desde documentos origen sin tocar stock."""
from odoo import _, fields, models


class JustechDeliveryNoteService(models.AbstractModel):
    _name = "justech.delivery.note.service"
    _description = "Servicio de creación de Conduces"

    def _jt_delivery_note_vals_from_sale(self, order):
        order.ensure_one()
        pickings = order._jt_delivery_outgoing_pickings()
        picking = pickings[0] if len(pickings) == 1 else False
        invoices = order._jt_delivery_related_invoices()
        invoice = invoices[0] if invoices else False
        line_cmds = []
        for line in order._jt_delivery_reportable_lines().sorted(key=lambda l: l.sequence):
            product = line.product_id
            qty_del = line.qty_delivered if "qty_delivered" in line._fields else line.product_uom_qty
            line_cmds.append(
                (
                    0,
                    0,
                    {
                        "sequence": line.sequence,
                        "product_id": product.id,
                        "default_code": product.default_code or "",
                        "name": line.name,
                        "product_uom_qty": line.product_uom_qty,
                        "qty_delivered": qty_del,
                        "product_uom_id": line.product_uom_id.id,
                    },
                )
            )
        return {
            "origin_type": "sale",
            "company_id": order.company_id.id,
            "partner_id": (order.partner_shipping_id or order.partner_id).id,
            "sale_order_id": order.id,
            "invoice_id": invoice.id if invoice else False,
            "picking_id": picking.id if picking else False,
            "user_id": self.env.uid,
            "date": fields.Datetime.now(),
            "note": order.note or False,
            "state": "done",
            "line_ids": line_cmds,
        }

    def _jt_delivery_note_vals_from_invoice(self, move):
        move.ensure_one()
        so = move._jt_delivery_related_sale_order()
        pickings = move._jt_delivery_outgoing_pickings()
        picking = pickings[0] if len(pickings) == 1 else False
        line_cmds = []
        for line in move._jt_invoice_product_lines().sorted(key=lambda l: l.sequence):
            product = line.product_id
            line_cmds.append(
                (
                    0,
                    0,
                    {
                        "sequence": line.sequence,
                        "product_id": product.id if product else False,
                        "default_code": product.default_code if product else "",
                        "name": line.name,
                        "product_uom_qty": line.quantity,
                        "qty_delivered": line.quantity,
                        "product_uom_id": line.product_uom_id.id if line.product_uom_id else False,
                    },
                )
            )
        return {
            "origin_type": "invoice",
            "company_id": move.company_id.id,
            "partner_id": (move.partner_shipping_id or move.partner_id).id,
            "sale_order_id": so.id if so else False,
            "invoice_id": move.id,
            "picking_id": picking.id if picking else False,
            "user_id": self.env.uid,
            "date": fields.Datetime.now(),
            "note": move.narration or False,
            "state": "done",
            "line_ids": line_cmds,
        }

    def _jt_delivery_note_vals_from_picking(self, picking):
        picking.ensure_one()
        so = picking._jt_delivery_related_sale_order()
        invoices = picking._jt_delivery_related_invoices()
        invoice = invoices[0] if invoices else False
        line_cmds = []
        moves = picking.move_ids.filtered(
            lambda m: m.product_id and m.state != "cancel" and not getattr(m, "scrapped", False)
        )
        for move in moves.sorted(key=lambda m: (m.sequence, m.id)):
            product = move.product_id
            code = product.default_code or ""
            desc = move.description_picking or product.display_name
            uom = move.product_uom
            qty_req = move.product_uom_qty
            detail_lines = move.move_line_ids.filtered(lambda l: l.quantity > 0)
            if detail_lines:
                for ml in detail_lines.sorted(key=lambda l: l.id):
                    line_cmds.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "default_code": code,
                                "name": desc,
                                "product_uom_qty": qty_req,
                                "qty_delivered": ml.quantity,
                                "product_uom_id": (
                                    ml.product_uom_id.id if ml.product_uom_id else uom.id
                                ),
                                "lot_id": ml.lot_id.id if ml.lot_id else False,
                            },
                        )
                    )
            else:
                line_cmds.append(
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "default_code": code,
                            "name": desc,
                            "product_uom_qty": qty_req,
                            "qty_delivered": move.quantity,
                            "product_uom_id": uom.id if uom else False,
                        },
                    )
                )
        return {
            "origin_type": "picking",
            "company_id": picking.company_id.id,
            "partner_id": picking.partner_id.id,
            "sale_order_id": so.id if so else False,
            "invoice_id": invoice.id if invoice else False,
            "picking_id": picking.id,
            "user_id": self.env.uid,
            "date": fields.Datetime.now(),
            "note": picking.note or False,
            "state": "done",
            "line_ids": line_cmds,
        }
