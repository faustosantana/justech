# Diff / traceback — RPC Centro Fiscal

## Traceback original

```
RPC_ERROR
TypeError: not enough arguments for format string
justech_fiscal_admin → open_for_user → health_check
→ justech.do.ncf.diagnostic.service → _check_ranges
```

## Antes

```python
_("%(name)s tiene %(rem)s NCF restantes (%.1f%% usado).",
  name=row["name"], rem=row["remaining_count"], pct=row["pct_used"])
```

## Después

```python
_("%(name)s tiene %(rem)s NCF restantes (%(pct).1f%% usado.") % {
    "name": name or _("Rango sin nombre"),
    "rem": rem if rem is not None else 0,
    "pct": float(pct or 0.0),
}
```

Archivo: `custom/justech_l10n_do_ncf/services/ncf_diagnostic_service.py`
Versión módulo: `19.0.2.4.1`
