# Build instaladores Windows JAIOS Desktop
# Ejecutar en PowerShell como administrador NO es necesario.
# Requisitos: Node 20+, Rust stable, Visual Studio Build Tools, WebView2

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== JAIOS Desktop — build Windows ===" -ForegroundColor Cyan

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Instale Node.js LTS desde https://nodejs.org"
}
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Instale Rust desde https://rustup.rs"
}

& bash -lc "./scripts/desktop_build_windows.sh"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build falló. Revise logs arriba."
}

Write-Host ""
Write-Host "Instaladores en .qa/desktop-installers/windows/" -ForegroundColor Green
Get-ChildItem ".qa/desktop-installers/windows" | Format-Table Name, Length
