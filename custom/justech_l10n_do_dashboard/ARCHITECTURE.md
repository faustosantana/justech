# Arquitectura — justech_l10n_do_dashboard

## Propósito

Módulo **independiente** de UX y monitoreo fiscal. Sprint 1 entrega solo la estructura
(menú, modelo placeholder, seguridad) para evolucionar KPIs sin acoplar lógica a NCF.

## Estado Sprint 1

| Componente | Estado |
|------------|--------|
| Menú Dashboard Fiscal | ✅ Shell |
| Modelo `justech.do.fiscal.dashboard` | ✅ Placeholder |
| KPIs / alertas / OWL | ⏳ Sprint 2+ |
| Integración reports/payments | ⏳ Sprint 3+ |

## Diseño objetivo (roadmap)

```mermaid
flowchart TB
    subgraph dashboard [justech_l10n_do_dashboard]
        UI[Menú / OWL Dashboard]
        KPI[KPI Service]
        ALERT[Alert Service]
        DIAG[Diagnostic Wizard]
    end
    subgraph deps [Dependencias lectura]
        BASE[justech_l10n_do_base]
        NCF[justech_l10n_do_ncf]
        REP[justech_l10n_do_reports optional]
        PAY[justech_l10n_do_payments optional]
    end
    UI --> KPI
    KPI --> NCF
    KPI --> BASE
    ALERT --> NCF
    DIAG --> BASE
    DIAG --> REP
```

## Principios

- Solo **lectura** de datos fiscales en Sprint 2 inicial.
- Widgets parametrizables por empresa (`ir.config_parameter`).
- Sin duplicar lógica de asignación NCF ni exportadores DGII.

## Dependencias actuales

```
justech_l10n_do_base, justech_l10n_do_ncf
```

Ver `diagrams/dependencies.mmd`.
