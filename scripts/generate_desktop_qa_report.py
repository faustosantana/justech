#!/usr/bin/env python3
"""Genera reporte QA de JAIOS Desktop — validación parcial."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"
QA = ROOT / ".qa"
REPORT = QA / "desktop-app-report.md"


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []

    for name, path in [
        ("package.json", DESKTOP / "package.json"),
        ("tauri.conf.json", DESKTOP / "src-tauri" / "tauri.conf.json"),
        ("Cargo.toml", DESKTOP / "src-tauri" / "Cargo.toml"),
        ("capabilities", DESKTOP / "src-tauri" / "capabilities" / "default.json"),
    ]:
        checks.append({"name": name, "ok": path.exists(), "detail": str(path)})

    code, out = run(["npm", "run", "build"], cwd=DESKTOP)
    checks.append({"name": "vite build", "ok": code == 0, "detail": out[-500:] if out else ""})

    rustc = shutil.which("rustc")
    cargo = shutil.which("cargo")
    if cargo and rustc:
        code, out = run(["cargo", "check"], cwd=DESKTOP / "src-tauri")
        checks.append({"name": "cargo check", "ok": code == 0, "detail": out[-800:] if out else ""})
    else:
        checks.append({
            "name": "cargo check",
            "ok": False,
            "detail": "Rust toolchain no instalado en este entorno",
        })

    pkg = json.loads((DESKTOP / "package.json").read_text())
    version = pkg.get("version", "0.1.0")

    lines = [
        "# JAIOS Desktop — Reporte QA",
        "",
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        f"Versión app: {version}",
        "",
        "**Estado: Validación parcial** — pendiente revisión de Fausto en Mac/Windows físicos.",
        "",
        "## Arquitectura",
        "",
        "- Cliente Tauri (React + Rust) — **sin PostgreSQL/Docker local**",
        "- Servidor central: backend JAIOS + PostgreSQL + Redis + Qdrant",
        "- Token en Keychain (macOS) / Credential Manager (Windows)",
        "",
        "## Checks automáticos",
        "",
    ]
    for c in checks:
        mark = "✅" if c["ok"] else "❌"
        lines.append(f"- {mark} **{c['name']}**")
        if c.get("detail"):
            lines.append(f"  - `{str(c['detail'])[:240]}`")

    lines.extend(
        [
            "",
            "## Funciones v1 implementadas",
            "",
            "1. Configuración inicial (URL servidor, test conexión, guardar)",
            "2. Login (token seguro, recordar sesión, logout)",
            "3. Ventana principal con JAIOS Web + inyección de token",
            "4. Assistant flotante (Cmd/Ctrl+Shift+J)",
            "5. Notificaciones (poll + native toast)",
            "6. Captura de pantalla → subida a /documents",
            "7. Seguridad: sin password en disco, HTTPS opcional en prod",
            "8. updater.toml preparado para auto-update futuro",
            "",
            "## Pendiente validación manual",
            "",
            "- Abrir .app en macOS",
            "- Abrir .exe en Windows",
            "- Login contra servidor real",
            "- Dashboard carga con permisos/company context",
            "- Assistant responde contra Odoo live",
            "- Logout limpia Keychain",
            "",
            "## Comandos",
            "",
            "```bash",
            "make desktop-dev",
            "make desktop-build-mac",
            "make desktop-build-windows",
            "make desktop-qa-report",
            "```",
        ]
    )

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Reporte: {REPORT}")


if __name__ == "__main__":
    main()
