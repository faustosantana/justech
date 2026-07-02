# -*- coding: utf-8 -*-
"""Preparación usuarios certificación manual Fase 20.1 en TEST."""
from odoo import Command

DB = env.cr.dbname
if DB != "hellenia_test":
    raise SystemExit(f"ABORT: solo hellenia_test, actual={DB}")

PASSWORD = "CertFiscal20!"
FISCAL_LOGIN = "usuario.contabilidad.demo15"
SUPER_LOGIN = "it@justech.do"

fiscal_group = env.ref("justech_l10n_do_base.group_justech_do_fiscal_user")
manager_group = env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager")
account_user = env.ref("account.group_account_user")
account_invoice = env.ref("account.group_account_invoice")

Users = env["res.users"].sudo()

fiscal = Users.search([("login", "=", FISCAL_LOGIN)], limit=1)
if fiscal:
    fiscal.write(
        {
            "password": PASSWORD,
            "group_ids": [
                Command.link(account_user.id),
                Command.link(account_invoice.id),
                Command.link(fiscal_group.id),
            ],
        }
    )
    print(f"OK fiscal={FISCAL_LOGIN} id={fiscal.id}")

supervisor = Users.search([("login", "=", SUPER_LOGIN)], limit=1)
if supervisor:
    supervisor.write(
        {
            "password": PASSWORD,
            "group_ids": [
                Command.link(manager_group.id),
            ],
        }
    )
    print(f"OK supervisor={SUPER_LOGIN} id={supervisor.id}")

env.cr.commit()
print(f"CERT_USERS_READY password={PASSWORD}")
