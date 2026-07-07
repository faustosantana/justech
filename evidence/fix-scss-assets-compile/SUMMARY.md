# Fix compilación SCSS — web.assets_web

**Fecha:** 2026-07-07  
**Módulo:** justech_admin 19.0.2.13.1

## Causa raíz

```
Internal Error: Incompatible units: 'vw' and 'px'.
```

Sass evaluaba `min(1120px, 96vw)` como función nativa `min()` en lugar de CSS `min()`.

## Corrección

`control_center.scss` línea 498:

```scss
max-width: #{"min(1120px, 96vw)"};
```

## Validación

| Ambiente | Assets compile | Healthcheck |
|----------|----------------|-------------|
| TEST | OK (sin error Sass post-fix) | PASS |
| PROD | OK (sin `Incompatible units` en logs) | PASS |
