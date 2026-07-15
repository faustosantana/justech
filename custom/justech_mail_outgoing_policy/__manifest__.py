{
    "name": "Justech Mail Outgoing Policy",
    "version": "19.0.1.0.0",
    "category": "Productivity/Discuss",
    "summary": "From fijo notifications@ + Reply-To del usuario emisor",
    "description": """
Política de correo saliente Justech (Microsoft 365 / Outlook).

Evita el error SendAsDenied forzando:

- From: Notificaciones Justech <notifications@justech.do>
- Reply-To: correo del usuario/partner que generó el mensaje

Configurable por parámetros del sistema. No altera plantillas ni
módulos fiscales. Multiempresa: solo aplica a dominios configurados
(por defecto justech.do).
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
