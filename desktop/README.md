# JAIOS Desktop — Windows / macOS

Aplicación de escritorio **Tauri 2 + React + Rust** para empleados Justech. Es un **cliente** del servidor JAIOS central.

## Arquitectura

| En el servidor (VPS/Docker) | En la PC del empleado |
|----------------------------|------------------------|
| JAIOS Backend + PostgreSQL | JAIOS Desktop (Tauri) |
| Redis, Qdrant, n8n | Login + token seguro |
| Storage documental | WebView con JAIOS Web |
| Usuarios / permisos | Assistant flotante |
| Company Context | Notificaciones + captura |

**No** se instala PostgreSQL, Docker ni bases locales en las PCs.

## Funciones v1

1. **Configuración inicial** — URL del servidor, probar conexión, guardar
2. **Login** — email/contraseña; token en Keychain (Mac) / Credential Manager (Windows)
3. **Ventana principal** — carga JAIOS Web (`/dashboard`) con sesión inyectada
4. **Assistant flotante** — `Cmd/Ctrl + Shift + J`
5. **Notificaciones** — poll al API + toast nativo
6. **Captura** — screenshot → subida a `/documents` en el servidor
7. **Seguridad** — sin password en disco; HTTPS obligatorio opcional en producción
8. **Auto-update** — estructura en `src-tauri/updater.toml` (deshabilitado)

## Requisitos desarrollo

- Node.js 20+
- Rust stable (`rustup default stable`)
- Tauri CLI: `cargo install tauri-cli --version "^2"`
- macOS: Xcode Command Line Tools
- Windows: VS Build Tools + WebView2

## Comandos

```bash
# Desde la raíz del repo JAIOS
make desktop-dev           # Tauri dev (Vite :1420 + ventanas)
make desktop-build-mac     # .app / .dmg
make desktop-build-windows # .exe (requiere Windows)
make desktop-qa-report     # build + reporte .qa/desktop-app-report.md
```

### URL del servidor

En la primera ejecución configure, por ejemplo:

- Desarrollo: `http://localhost:3000` (API derivada → `http://localhost:8000/api/v1`)
- Producción: `https://jaios.justech.do`

Variable opcional para dev: `JAIOS_SERVER_URL=http://localhost:3000`

## Atajos

| Atajo | Acción |
|-------|--------|
| `Cmd/Ctrl + Shift + J` | Abrir/cerrar Assistant |
| Bandeja → Abrir JAIOS | Ventana principal |
| Bandeja → Capturar pantalla | Screenshot al repositorio |

## Estructura

```
desktop/
  index.html              # entrada Vite
  src/                    # React (setup, login, assistant)
  src-tauri/
    src/
      config.rs           # URL servidor, persistencia local
      auth.rs             # Keychain / Credential Manager
      api.rs              # HTTP al backend central
      windows.rs          # WebView JAIOS + ventanas
      lib.rs              # tray, shortcuts, comandos Tauri
    capabilities/         # permisos Tauri 2
    updater.toml          # auto-update futuro
```

## Seguridad

- Contraseña **nunca** se guarda en disco
- JWT solo en almacén seguro del SO (`keyring`)
- Opción «Limpiar sesión al cerrar»
- `require_https` bloquea URLs HTTP fuera de localhost en producción

## Estado

**Validación parcial** — código y build web listos; builds nativos `.app`/`.exe` y pruebas en equipos de Fausto pendientes.
