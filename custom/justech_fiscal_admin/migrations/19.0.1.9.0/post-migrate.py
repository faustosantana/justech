# -*- coding: utf-8 -*-
"""P0.1 — Desactivar dual-write NCF (FISC-AUD-001).

Emisión canónica = Justech; LATAM solo entrada de compras recibidas.
No modifica documentos históricos ni la baseline de alertas.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE justech_fiscal_feature_flag
           SET enabled = false,
               readonly_flag = false,
               description = jsonb_build_object(
                   'en_US',
                   'P0.1 OFF: mirror Justech→LATAM del NCF. Emisión canónica = Justech; '
                   'compras recibidas = LATAM. Reactivar solo con aprobación.'
               )
         WHERE code = 'ncf_dual_write'
        """
    )
