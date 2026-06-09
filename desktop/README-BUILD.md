# JAIOS Desktop — Guía de build (técnica)

Cliente Tauri 2 + React. **No incluye backend, PostgreSQL, Docker ni Redis** — solo empaqueta la app que se conecta al servidor central.

## Requisitos

| Herramienta | Versión mínima |
|-------------|----------------|
| Node.js | 20+ |
| npm | 10+ |
| Rust | stable (via rustup) |
| Tauri CLI | 2.x |

## Preparar entorno (automático)

```bash
make desktop-prepare
# o
./scripts/desktop_prepare_build_env.sh
```

El script:

1. Instala rustup si falta Rust
2. Instala `tauri-cli` si falta
3. Ejecuta `npm install` en `desktop/`
4. Si falla por certificado SSL corporativo, aplica `strict-ssl false` solo durante la instalación y restaura `true`

Log: `.qa/desktop-build-env.log`

## Compilar Mac (.app + .dmg)

```bash
make desktop-build-mac
```

Artefactos:

- `desktop/src-tauri/target/release/bundle/dmg/JAIOS_0.1.0_*.dmg`
- `desktop/src-tauri/target/release/bundle/macos/JAIOS.app`
- Copia en `.qa/desktop-installers/mac/`

## Compilar Windows (.msi + setup.exe)

En una PC **Windows** con Visual Studio Build Tools + WebView2:

```bash
make desktop-build-windows
```

Artefactos:

- `.../bundle/msi/JAIOS_0.1.0_*.msi`
- `.../bundle/nsis/JAIOS_*_setup.exe`
- Copia en `.qa/desktop-installers/windows/`

Desde Mac **no** se genera instalador Windows real — use CI o máquina Windows.

## CI (GitHub Actions)

| Workflow | Runner | Artefactos |
|----------|--------|------------|
| `desktop-mac-build.yml` | `macos-latest` | `.dmg`, `JAIOS.app.zip` |
| `desktop-windows-build.yml` | `windows-latest` | `.msi`, `*_setup.exe` |

Disparo manual: **Actions → workflow → Run workflow**

## Configuración predeterminada embebida

Editar constantes en `desktop/src-tauri/src/config.rs`:

```rust
pub const DEFAULT_WEB_URL: &str = "http://100.81.128.32:3000";
pub const PRODUCTION_WEB_URL: &str = "https://jaios.justech.do";
pub const DEFAULT_TENANT: &str = "justech";
```

Override en build sin recompilar lógica: variable de entorno `JAIOS_SERVER_URL`.

Tras cambiar defaults, incrementar versión en `desktop/package.json` y `desktop/src-tauri/Cargo.toml`, luego rebuild.

## Desarrollo local

```bash
make desktop-dev
```

Abre ventana launcher + tray. Frontend Vite en `:1420`.

## Firmado de código (futuro)

### macOS

1. Cuenta Apple Developer
2. Certificado *Developer ID Application*
3. En `tauri.conf.json` → `bundle.macOS.signingIdentity`
4. Notarización: `xcrun notarytool` post-build

### Windows

1. Certificado de firma de código (EV recomendado)
2. `tauri.conf.json` → `bundle.windows.certificateThumbprint`
3. Timestamp server en NSIS

## Publicar versión

1. Bump `version` en `package.json`, `Cargo.toml`, `tauri.conf.json`
2. Tag git `desktop-v0.1.0`
3. Ejecutar workflows Mac + Windows
4. Subir artefactos a almacenamiento interno o activar `updater.toml` (deshabilitado en v0.1.0)
5. Distribuir `.qa/desktop-installers/` + `README-INSTALACION.md`

## Reportes

```bash
python3 scripts/generate_desktop_installer_report.py
```

Salida: `.qa/desktop-installer-report.md`

## Estructura

```
desktop/
├── src/                 # React (Setup, Login, Assistant)
├── src-tauri/           # Rust (config, auth, API, ventanas)
├── package.json
└── README-BUILD.md      # este archivo
```

## Seguridad

- Token: Keychain (macOS) / Credential Manager (Windows) via crate `keyring`
- Contraseña: nunca persistida
- Comandos: `reset_app_config`, `desktop_logout`, `clear_on_exit`
