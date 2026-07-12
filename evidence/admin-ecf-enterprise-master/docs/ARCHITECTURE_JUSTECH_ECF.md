# Arquitectura Justech e-CF

## Decisión

Se adoptó la separación en 6 módulos técnicos expuestos como **un solo producto** en Administración Justech → Justech Fiscal → Justech e-CF:

1. `justech_ecf_core` — datos, seguridad, estados, config por empresa
2. `justech_ecf_xml` — generación/validación XSD (copias oficiales DGII)
3. `justech_ecf_signature` — certificado cifrado + XMLDSig RSA-SHA256 (doc oficial Firmado de e-CF)
4. `justech_ecf_dgii` — adaptadores mock / certificación / producción (Gate)
5. `justech_ecf_queue` — cola, backoff, dead-letter, contingencia
6. `justech_ecf_admin` — hub, dashboard, asistente, integración Admin Center

## Ambientes oficiales (DGII)

- testecf / certecf / ecf — URLs `https://ecf.dgii.gov.do/{ambiente}/...`
- Producción bloqueada por defecto (`production_gate_unlocked=False`)

## Firma (oficial)

- C14N 20010315 · rsa-sha256 · sha256 digest · enveloped · URI=""

## Fuentes

Ver `dgii-source-register.md`.
