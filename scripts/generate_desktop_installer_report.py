#!/usr/bin/env python3
"""Genera reporte final de instaladores JAIOS Desktop."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"
QA = ROOT / ".qa"
OUT = QA / "desktop-installers"
REPORT = QA / "desktop-installer-report.md"
ENV_LOG = QA / "desktop-build-env.log"


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def find_artifacts() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"mac": [], "windows": []}
    for sub, key in [("mac", "mac"), ("windows", "windows")]:
        d = OUT / sub
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() in {".dmg", ".msi", ".exe", ".pkg"}:
                result[key].append(str(p.relative_to(ROOT)))
            elif p.is_dir() and p.suffix == ".app":
                result[key].append(str(p.relative_to(ROOT)))
    bundle = DESKTOP / "src-tauri" / "target" / "release" / "bundle"
    if bundle.exists():
        for p in bundle.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".dmg", ".msi", ".exe"}:
                rel = str(p.relative_to(ROOT))
                bucket = "mac" if p.suffix.lower() == ".dmg" or ".app" in rel else "windows"
                if rel not in result[bucket]:
                    result[bucket].append(rel)
    return result


def tool_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name, cmd in [
        ("node", ["node", "-v"]),
        ("npm", ["npm", "-v"]),
        ("rustc", ["rustc", "--version"]),
        ("cargo", ["cargo", "--version"]),
        ("tauri", ["cargo", "tauri", "--version"]),
    ]:
        if shutil.which(cmd[0]):
            code, out = run(cmd, cwd=DESKTOP)
            versions[name] = out.split("\n")[0] if code == 0 else "error"
        else:
            versions[name] = "no instalado"
    return versions


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    pkg = json.loads((DESKTOP / "package.json").read_text())
    version = pkg.get("version", "0.1.0")
    artifacts = find_artifacts()
    versions = tool_versions()
    env_log_tail = ""
    if ENV_LOG.exists():
        env_log_tail = ENV_LOG.read_text(encoding="utf-8")[-1200:]

    ssl_workaround = "strict-ssl false" in env_log_tail.lower()

    mac_dmg = [a for a in artifacts["mac"] if a.endswith(".dmg")]
    mac_app = [a for a in artifacts["mac"] if a.endswith(".app")]
    win_msi = [a for a in artifacts["windows"] if a.endswith(".msi")]
    win_exe = [a for a in artifacts["windows"] if a.endswith(".exe")]

    lines = [
        "# JAIOS Desktop — Reporte de instaladores",
        "",
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        f"Versión: {version}",
        f"Plataforma build: {platform.system()} {platform.machine()}",
        "",
        "## Entorno",
        "",
    ]
    for k, v in versions.items():
        lines.append(f"- **{k}**: `{v}`")
    lines.extend(
        [
            "",
            "## Configuración predeterminada embebida",
            "",
            "- Server URL: `http://100.81.128.32:3000`",
            "- Tenant: `justech`",
            "- HTTPS requerido: `false` (Tailscale/LAN)",
            "- Producción futura: `https://jaios.justech.do`",
            "",
            "## Artefactos generados",
            "",
        ]
    )

    def section(title: str, paths: list[str]) -> None:
        lines.append(f"### {title}")
        if paths:
            for p in paths:
                lines.append(f"- `{p}`")
        else:
            lines.append("- *(no generado en este entorno)*")
        lines.append("")

    section("Mac .dmg", mac_dmg)
    section("Mac .app", mac_app)
    section("Windows .msi", win_msi)
    section("Windows setup .exe", win_exe)

    lines.extend(
        [
            "## Errores y soluciones",
            "",
        ]
    )
    if ssl_workaround:
        lines.append(
            "- npm falló por certificado SSL → se aplicó `strict-ssl false` temporal durante install y se restauró `true`."
        )
    else:
        lines.append("- npm install: sin workaround SSL registrado.")
    if not win_msi and not win_exe:
        lines.append(
            "- Windows: build no ejecutado localmente. Use GitHub Actions `desktop-windows-build.yml` o `make desktop-build-windows` en PC Windows."
        )

    lines.extend(
        [
            "",
            "## GitHub Actions",
            "",
            "- `.github/workflows/desktop-mac-build.yml` — artefactos dmg + app zip",
            "- `.github/workflows/desktop-windows-build.yml` — artefactos msi + setup exe",
            "",
            "## Pruebas realizadas",
            "",
            "- [ ] Abrir .app / .dmg en macOS (revisión Fausto)",
            "- [ ] Pantalla Bienvenido + servidor prellenado",
            "- [ ] Probar conexión → login → dashboard",
            "- [ ] Assistant (Cmd+Shift+J)",
            "- [ ] Logout y reabrir",
            "",
            "## Pendientes honestos",
            "",
        ]
    )
    if not mac_dmg:
        lines.append("- Falta `.dmg` en este entorno — ejecutar build en Mac con entorno preparado.")
    if not mac_app:
        lines.append("- Falta `.app` empaquetado.")
    if not win_msi:
        lines.append("- Falta `.msi` — requiere runner Windows o CI.")
    if mac_dmg and mac_app:
        lines.append("- Validación visual en Mac pendiente de Fausto.")
    if win_msi or win_exe:
        lines.append("- Validación en Windows pendiente.")

    if env_log_tail:
        lines.extend(["", "## Log prepare (últimas líneas)", "", "```", env_log_tail, "```"])

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Reporte: {REPORT}")


if __name__ == "__main__":
    main()
