# Reporte Branding — Documentos Hellenia

**Fase:** 13.6  
**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30

---

## 1. Estado del branding

| Elemento | Implementado | Configurado PROD | Notas |
|----------|--------------|------------------|-------|
| Logo | ✅ Layout | ✅ Sí | `res.company.logo` |
| RNC | ✅ Encabezado | ✅ 133621282 | Destacado con etiqueta "RNC:" |
| Dirección | ✅ Encabezado | ✅ Sí | Widget contacto empresa |
| Teléfono | ✅ Encabezado | ✅ +1 849-434-8694 | |
| Email | ✅ Encabezado | ✅ info@helleniadr.com | |
| Website | ✅ Encabezado | ✅ hellenia.cloud | |
| Paleta colores | ✅ SCSS | ⚠️ Default | `#1a365d` / `#c9a227` — confirmar con Hellenia |
| NCF destacado | ✅ Caja corporativa | ✅ Automático | En facturas/NC |
| QR factura | ✅ Código Python | ✅ Activado | Valor = NCF |
| Términos y condiciones | ✅ Campo HTML | ❌ Pendiente | `hellenia_terms_conditions` |
| Aviso legal | ✅ Campo HTML / pie | ❌ Pendiente | `hellenia_legal_notice` |
| Firma autorizada | ✅ Campo imagen | ❌ Pendiente | `hellenia_signature_image` |
| Sello empresa | ✅ Campo imagen | ❌ Pendiente | `hellenia_stamp_image` |
| Redes sociales | ✅ Pie documento | ❌ Pendiente | Instagram, WhatsApp, Facebook |
| Marca de agua | ⏳ Futuro | — | No implementado en 13.6 |

---

## 2. Identidad visual aplicada

### Colores (SCSS)

| Rol | Hex | Uso |
|-----|-----|-----|
| Primario | `#1a365d` | Encabezado, bordes, títulos, thead tablas |
| Secundario | `#c9a227` | Línea acento, subrayado títulos |
| Texto | `#2d3748` | Cuerpo documento |
| Fondo tabla zebra | `#f7fafc` | Filas alternas |

Los colores son configurables vía `res.company.hellenia_primary_color` y `hellenia_secondary_color` (campos listos; SCSS usa valores fijos — mejora futura: inyectar dinámicamente).

### Tipografía

- **PDF:** DejaVu Sans (contenedor Odoo)
- Compatible UTF-8 y español (ñ, acentos)

### Layout

```
┌─────────────────────────────────────────────┐
│ [LOGO]              Hellenia, S.R.L.        │
│                     Dirección               │
│                     RNC: 133621282          │
│                     Tel / Email / Web       │
├─────────────────────────────────────────────┤ ← línea azul/dorado
│                                             │
│  [Dirección cliente]                        │
│                                             │
│  COTIZACIÓN Nº S00XXX                       │
│  ─────────────────                          │
│  ┌─────────────────────────────────────┐   │
│  │ Descripción │ Cant │ Precio │ ITBIS │   │
│  └─────────────────────────────────────┘   │
│                          Subtotal / Total   │
│                                             │
│  Términos y condiciones (si configurado)    │
│  [Firma]              [Sello]               │
├─────────────────────────────────────────────┤
│ Aviso legal │ redes │        Página 1 / 2  │
└─────────────────────────────────────────────┘
```

### Factura — bloque NCF

```
┌──────────────────────────────────┐
│ NCF                              │
│ B0200009903          [QR]        │
│ Factura de crédito fiscal        │
└──────────────────────────────────┘
```

---

## 3. Configuración pendiente Hellenia

| Prioridad | Acción | Dónde |
|-----------|--------|-------|
| P1 | Redactar términos y condiciones comerciales | Empresa → Documentos Hellenia |
| P1 | Redactar aviso legal facturas (texto DGII) | Empresa → Documentos Hellenia |
| P2 | Subir imagen firma autorizada | Empresa → Documentos Hellenia |
| P2 | Subir imagen sello (si aplica) | Empresa → Documentos Hellenia |
| P2 | Configurar URLs redes sociales | Empresa → Documentos Hellenia |
| P3 | Confirmar paleta colores oficial | Empresa → Documentos Hellenia |

---

## 4. Multi-empresa

Arquitectura soporta configuración por `res.company`. Hellenia opera mono-empresa.

---

## 5. Conclusión branding

| Pregunta | Respuesta |
|----------|-----------|
| ¿Infraestructura branding lista? | **Sí** |
| ¿Logo y RNC visibles? | **Sí** |
| ¿Listo para cliente final? | **Casi** — faltan textos legales y firma |
| ¿Pendientes visuales? | Términos, aviso legal, firma, sello, redes, confirmación colores |

---

## 6. Referencias

- [BRANDING_GUIDE.md](BRANDING_GUIDE.md)
- [HELLENIA_REPORTS_IMPLEMENTATION.md](HELLENIA_REPORTS_IMPLEMENTATION.md)
- [HELLENIA_PDF_UAT_REPORT.md](HELLENIA_PDF_UAT_REPORT.md)
