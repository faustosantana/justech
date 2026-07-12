{
    "name": "Justech e-CF Signature",
    "version": "19.0.1.1.0",
    "category": "Accounting/Localizations",
    "summary": "Firma XMLDSig e-CF según instructivo oficial DGII (RSA-SHA256)",
    "author": "Justech",
    "website": "https://justech.do",
    "license": "LGPL-3",
    "depends": ["justech_ecf_core"],
    "external_dependencies": {"python": ["cryptography"]},
    "data": [
        "security/ir.model.access.csv",
        "wizards/certificate_wizard_views.xml",
    ],
    "installable": True,
}
