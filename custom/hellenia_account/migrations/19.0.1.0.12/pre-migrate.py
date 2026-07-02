"""Migración tablas retenciones — Fase 18.8."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'hellenia_payment_withholding_line'
        )
        """
    )
    has_line_table = cr.fetchone()[0]
    if has_line_table:
        cr.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'hellenia_payment_withholding_line'
                  AND column_name = 'register_wizard_id'
            )
            """
        )
        if cr.fetchone()[0]:
            cr.execute(
                "ALTER TABLE hellenia_payment_withholding_line "
                "RENAME TO hellenia_payment_withholding_wizard_line"
            )
            _logger.info("Renamed transient table to hellenia_payment_withholding_wizard_line")

    cr.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'hellenia_account_payment_withholding'
        )
        """
    )
    if cr.fetchone()[0]:
        cr.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'hellenia_payment_withholding_line'
            )
            """
        )
        if not cr.fetchone()[0]:
            cr.execute(
                "ALTER TABLE hellenia_account_payment_withholding "
                "RENAME TO hellenia_payment_withholding_line"
            )
            _logger.info("Renamed persistent table to hellenia_payment_withholding_line")
