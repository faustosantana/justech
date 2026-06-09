"""Plataforma JAIOS — registro de módulos y roadmap (sin implementación de negocio)."""

from app.platform.modules import (
    JAIOSModule,
    ModulePhase,
    ModuleStatus,
    get_module,
    get_modules_by_phase,
    get_roadmap,
    list_modules,
    validate_dependencies,
)

__all__ = [
    "JAIOSModule",
    "ModulePhase",
    "ModuleStatus",
    "get_module",
    "get_modules_by_phase",
    "get_roadmap",
    "list_modules",
    "validate_dependencies",
]
