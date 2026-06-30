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
| [responsibles.yaml](responsibles.yaml) | Responsables funcionales |
| [suppliers.yaml](suppliers.yaml) | Proveedores planificados |
| [product_import.yaml](product_import.yaml) | Especificación importación Excel |
| [reports_priority.yaml](reports_priority.yaml) | Reportes prioritarios |

**Fase 3.5:** [PHASE35_GOLDEN_CONFIGURATION_REPORT.md](../../docs/PHASE35_GOLDEN_CONFIGURATION_REPORT.md)

**Scripts:** `scripts/apply-phase35-golden-config.py` · `scripts/validate-phase35-golden-config.py`
