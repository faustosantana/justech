#!/usr/bin/env bash
# Fase 10 — Auditoría infraestructura (solo lectura)
set -uo pipefail

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
OUT="${1:-evidence/phase10-infra-audit.txt}"
mkdir -p "$(dirname "$OUT")"

{
  echo "=== PHASE 10 INFRA AUDIT $TS ==="
  echo "## HOSTNAME"; hostname
  echo "## DISK"; df -h / /opt /var/lib/docker 2>/dev/null
  echo "## MEMORY"; free -h
  echo "## CPU"; echo "cores=$(nproc)"; lscpu 2>/dev/null | grep -E "Model name|CPU\\(s\\)|Thread" | head -5
  echo "## SWAP"; swapon --show 2>/dev/null || echo none
  echo "## DOCKER"; docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
  echo "## NETWORKS"; docker network ls
  echo "## VOLUMES"; docker volume ls | head -30
  echo "## DNS odoo"; dig +short odoo.hellenia.cloud A
  echo "## DNS dev"; dig +short dev.hellenia.cloud A
  echo "## DNS test"; dig +short test.hellenia.cloud A
  echo "## SSL odoo"; curl -sI https://odoo.hellenia.cloud/ 2>&1 | head -5
  echo "## SSL dev dates"; echo | openssl s_client -connect dev.hellenia.cloud:443 -servername dev.hellenia.cloud 2>/dev/null | openssl x509 -noout -dates -issuer 2>/dev/null
  echo "## SSL test dates"; echo | openssl s_client -connect test.hellenia.cloud:443 -servername test.hellenia.cloud 2>/dev/null | openssl x509 -noout -dates 2>/dev/null
  echo "## TRAEFIK labels test"; docker inspect hellenia-test-odoo-1 --format '{{range $k,$v := .Config.Labels}}{{$k}}={{$v}}{{"\n"}}{{end}}' 2>/dev/null | grep traefik || echo n/a
  echo "## BACKUPS dev"; ls -lt /opt/odoo-projects/hellenia/backups/dev/ 2>/dev/null | head -4
  echo "## BACKUPS test"; ls -lt /opt/odoo-projects/hellenia/backups/test/ 2>/dev/null | head -4
  echo "## BACKUPS production"; ls -lt /opt/odoo-projects/hellenia/backups/production/ 2>/dev/null | head -4
  echo "## ODOO-PECV"; docker ps --filter name=odoo-pecv --format "{{.Names}} {{.Status}}"
  echo "## FAIL2BAN"; systemctl is-active fail2ban 2>/dev/null || echo inactive
  echo "## UFW"; ufw status 2>/dev/null | head -8 || echo n/a
  echo "## CRON root"; crontab -l 2>/dev/null | head -15 || echo no_crontab
  echo "## UNATTENDED"; dpkg -l unattended-upgrades 2>/dev/null | tail -1 || echo n/a
} > "$OUT" 2>&1

echo "Wrote $OUT ($(wc -c < "$OUT") bytes)"
