"""Errores de resolución de plantillas oficiales — sin fallback a stubs locales."""

from __future__ import annotations


class OfficialTemplateUnavailableError(FileNotFoundError):
    """La plantilla está indexada en M365 pero no se pudo obtener el DOCX oficial."""

    def __init__(self, form_type: str, template_name: str | None = None, *, detail: str | None = None):
        self.form_type = form_type
        self.template_name = template_name
        msg = detail or (
            f"Plantilla oficial no disponible para {form_type}"
            + (f" ({template_name})" if template_name else "")
            + ". Reconecte la cuenta M365 (Cuentas M365 → OAuth) y sincronice el repositorio DGCP."
        )
        super().__init__(msg)


class StubTemplateBlockedError(OfficialTemplateUnavailableError):
    """Se detectó plantilla stub/simplificada — generación bloqueada."""

    def __init__(self, form_type: str, template_name: str | None = None, *, detail: str | None = None):
        msg = detail or (
            f"Plantilla stub o simplificada detectada para {form_type}"
            + (f" ({template_name})" if template_name else "")
            + ". Solo se permiten plantillas oficiales del repositorio M365/DGCP."
        )
        super().__init__(form_type, template_name, detail=msg)
