"""Errores de validación documental para expedientes DGCP."""


class ExpedienteIncompleteError(Exception):
    def __init__(self, validation: dict):
        self.validation = validation
        super().__init__(validation.get("message") or "Expediente INCOMPLETO")
