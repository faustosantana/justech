# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from . import models


def post_init_hook(env):
    env["res.company"].hellenia_migrate_quotation_terms_to_html()
