# -*- coding: utf-8 -*-


def migrate(cr, version):
    """SMTP @helleniadr.com sin owner personal (usable por todos los usuarios)."""
    cr.execute(
        """
        UPDATE ir_mail_server
           SET owner_user_id = NULL
         WHERE owner_user_id IS NOT NULL
           AND (
                lower(coalesce(smtp_user, '')) LIKE '%%helleniadr.com%%'
             OR lower(coalesce(from_filter, '')) LIKE '%%helleniadr.com%%'
             OR lower(coalesce(name, '')) LIKE '%%helleniadr.com%%'
           )
        """
    )
