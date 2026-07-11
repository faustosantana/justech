# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
def migrate(cr, version):
    """Text → Html: normaliza términos de cotización al actualizar el módulo."""
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'res_company'
           AND column_name = 'hellenia_quotation_terms'
        """
    )
    if not cr.fetchone():
        return
    # La conversión semántica se hace en post_init / end-migrate vía ORM.
