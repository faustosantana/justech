# -*- coding: utf-8 -*-
"""Etiquetas UX Compras: action RFQ (fuente + términos es_*)."""


def migrate(cr, version):
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
        WHERE module = 'purchase' AND name = 'purchase_rfq'
          AND model = 'ir.actions.act_window'
        LIMIT 1
        """
    )
    row = cr.fetchone()
    if not row:
        return
    action_id = row[0]
    # Odoo 19 table
    cr.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN ('ir_act_window', 'ir_actions_act_window')
        """
    )
    tables = [r[0] for r in cr.fetchall()]
    for table in tables:
        cr.execute(
            f"UPDATE {table} SET name = %s WHERE id = %s",
            ("Solicitudes de Orden", action_id),
        )
    # Traducciones legacy (si existen)
    cr.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'ir_translation'
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            UPDATE ir_translation
               SET value = %s
             WHERE type = 'model'
               AND name = 'ir.actions.act_window,name'
               AND res_id = %s
               AND lang LIKE 'es_%%'
            """,
            ("Solicitudes de Orden", action_id),
        )
