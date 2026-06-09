"""Microsoft 365 integration — Graph API (Fase 4, estructura base)."""

from integrations.microsoft365.client import M365Client
from integrations.microsoft365.config import M365Config

__all__ = ["M365Client", "M365Config"]
