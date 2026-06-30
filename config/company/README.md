# Configuración maestra (Golden Configuration) — Hellenia

Archivos versionados para replicar la parametrización DEV → TEST → PROD.

| Archivo | Contenido |
|---------|-----------|
| [company.yaml](company.yaml) | Datos legales y regionales |
| [banks.yaml](banks.yaml) | Banco López de Haro — estructura |
| [journals.yaml](journals.yaml) | Diarios plan `do` |
| [payment_methods.yaml](payment_methods.yaml) | Métodos de pago estándar |
| [inventory_categories.yaml](inventory_categories.yaml) | Árbol categorías producto |
| [taxes.yaml](taxes.yaml) | Impuestos y posiciones fiscales RD |
| [company_metadata.yaml](company_metadata.yaml) | Metadatos fase, backup, scripts |

**Aplicar en DEV:** `scripts/apply-phase3-golden-config.py` (odoo shell)  
**Validar:** `scripts/validate-phase3-golden-config.py`

Ver [docs/PHASE3_IMPLEMENTATION_REPORT.md](../docs/PHASE3_IMPLEMENTATION_REPORT.md).
