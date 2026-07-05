# Justech Modules — Official Install Order

**Generated:** F31.1.5 (topological sort on Odoo `depends`)  
**Full graph:** `evidence/f31-1-5-platform-final/DEPENDENCY_GRAPH.md`

## Order

1. `justech_modules`
2. `justech_core`
3. `justech_l10n_do_base`
4. `hellenia_base`
5. `justech_l10n_do_ncf`
6. `hellenia_ui`
7. `hellenia_account`
8. `justech_l10n_do_reports`
9. `hellenia_reports`
10. `hellenia_ux`
11. `justech_report_design`
12. `hellenia_inventory`
13. `hellenia_pos`

## Notes

- Odoo resolves `depends` automatically during `-i` / `-u`
- Commercial dependencies (`justech_register.dependencies`) are enforced by `check_dependencies()` at activation time
- No circular commercial dependencies detected (F31.1.5)

## Recommended Install Command (new instance)

Install platform first, then fiscal, then Hellenia stack:

```
justech_modules, justech_core, justech_l10n_do_base, justech_l10n_do_ncf,
justech_l10n_do_reports, hellenia_base, hellenia_ui, hellenia_account,
hellenia_reports, hellenia_ux, justech_report_design, hellenia_inventory, hellenia_pos
```

Or install `hellenia_ux` as meta-module if a consolidated manifest is added later.
