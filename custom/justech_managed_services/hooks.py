# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)


def post_init_hook(env):
    """Vincula el demo a Credicefi existente en la BD si aplica."""
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
