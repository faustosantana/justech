# -*- coding: utf-8 -*-
"""Post-instalación: visibilidad del Centro Fiscal para administradores."""


def post_init_hook(env):
    manager = env.ref(
        "justech_fiscal_admin.group_justech_fiscal_admin_manager",
        raise_if_not_found=False,
    )
    if not manager:
        return
    groups_to_link = [
        env.ref("base.group_system", raise_if_not_found=False),
        env.ref("account.group_account_manager", raise_if_not_found=False),
        env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager", raise_if_not_found=False),
    ]
    for grp in groups_to_link:
        if grp and manager not in grp.implied_ids:
            grp.write({"implied_ids": [(4, manager.id)]})
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    if admin and manager not in admin.group_ids:
        admin.write({"group_ids": [(4, manager.id)]})
