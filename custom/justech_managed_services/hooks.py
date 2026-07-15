# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)


def post_init_hook(env):
    """Semilla del catálogo/plantillas y vínculo demo Credicefi."""
    from .models.form_catalog import seed_form_catalog

    seed_form_catalog(env)
    partner = env["res.partner"].search(
        [
            ("name", "ilike", "credicefi"),
            ("name", "not ilike", "DEMO DEV"),
        ],
        limit=1,
    )
    demo_assessment = env.ref(
        "justech_managed_services.demo_assessment_credicefi",
        raise_if_not_found=False,
    )
    if partner and demo_assessment:
        demo_assessment.write(
            {
                "partner_id": partner.id,
                "email": partner.email or demo_assessment.email,
            }
        )
