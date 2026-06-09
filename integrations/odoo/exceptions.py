class OdooReadOnlyError(Exception):
    """Raised when a write operation is attempted against Odoo in read-only mode."""

    MESSAGE = "Odoo está en modo solo lectura"

    def __init__(self, method: str | None = None, model: str | None = None):
        self.method = method
        self.model = model
        detail = self.MESSAGE
        if method and model:
            detail = f"{self.MESSAGE} (bloqueado: {model}.{method})"
        super().__init__(detail)


class OdooNotConfiguredError(Exception):
    def __init__(self, message: str = "Odoo no conectado"):
        super().__init__(message)


class OdooConnectionError(Exception):
    pass
