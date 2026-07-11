{
    "name": "Hellenia Base",
    "version": "19.0.1.2.1",
    "category": "Hidden",
    "summary": "Base configuration for Hellenia customizations",
    "description": """
Base configuration for Hellenia customizations.

Política centralizada de correo saliente (solo Hellenia):

- From: Hellenia, S.R.L. <info@helleniadr.com>
- Reply-To: usuario/autor que originó el envío (fallback info@helleniadr.com)
- SMTP @helleniadr.com siempre corporativo (nunca servidor personal)

Aplica a todos los usuarios de Hellenia; no afecta Justgroup ni otras compañías.
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "hellenia_base",
        "module_name": "Hellenia Base",
        "version": "19.0.1.2.1",
        "category": "platform",
        "country": "DO",
        "localization": "",
        "description": "Base configuration and Hellenia mail policy",
        "dependencies": ["mail"],
        "always_enabled": True,
        "required_module": True,
        "features": [
            {"code": "hellenia_base", "name": "Hellenia Base"},
            {"code": "hellenia_mail_policy", "name": "Hellenia Mail Policy"},
        ],
    },
}
