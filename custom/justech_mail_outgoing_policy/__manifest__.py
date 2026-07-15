{
    "name": "Justech Mail Outgoing Policy",
    "version": "19.0.1.1.0",
    "category": "Productivity/Discuss",
    "summary": "From de notificaciones por empresa + Reply-To del usuario emisor",
    "description": """
Política de correo saliente multiempresa (Microsoft 365 / Outlook).

Evita SendAsDenied forzando por empresa:

- JUSTECH: From notifications@justech.do
- Just Office: From notificaciones@just-offices.com
- Reply-To: correo del usuario que originó la comunicación

Mapa escalable en parámetro JSON `justech_mail.company_policies`
(Plug Safe / Omni se agregan sin cambiar código).
    """,
    "author": "Justech",
    "website": "https://www.justech.com",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "data/ir_config_parameter.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
