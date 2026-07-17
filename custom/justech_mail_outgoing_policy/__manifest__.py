{
    "name": "Justech Mail Outgoing Policy",
    "version": "19.0.1.1.0",
    "category": "Productivity/Discuss",
    "summary": "Company-first mail identity (From / Reply-To / alias / SMTP domain)",
    "description": """
Política de correo saliente multiempresa (company-first).

Fuente de verdad: res.company del documento (company_id), nunca env.company
ni un alias de otro dominio.

Helper único: res.company._get_company_mail_identity()

- From / dominio / logo / layout según company_id
- Reply-To del usuario emisor
- Helpdesk: alias_domain debe coincidir con company.alias_domain
- Bloqueo si el alias del equipo pertenece a otra empresa
    """,
    "author": "Justech",
    "website": "https://www.justech.com",
    "license": "LGPL-3",
    "depends": ["mail", "helpdesk"],
    "data": [
        "data/ir_config_parameter.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
