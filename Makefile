.PHONY: help up down build logs migrate seed test lint qa-backend qa-frontend-build qa-odoo-e2e qa-odoo-ui qa-self-heal qa-e2e prices-sync desktop-dev desktop-build-mac desktop-build-windows desktop-qa-report

help:
	@echo "JAIOS — Justech AI Operating System"
	@echo ""
	@echo "  make up        Start all services"
	@echo "  make down      Stop all services"
	@echo "  make build     Build Docker images"
	@echo "  make logs      Tail service logs"
	@echo "  make migrate   Run Alembic migrations"
	@echo "  make seed      Seed initial data"
	@echo "  make test      Run backend tests"
	@echo "  make lint      Run linters"
	@echo "  make qa-backend       build + up + migrate + pytest"
	@echo "  make qa-frontend-build  next build en contenedor frontend"
	@echo "  make qa-odoo-e2e      pytest live Odoo (API real)"
	@echo "  make qa-odoo-ui       capa datos UI (requiere tokens en .qa/)"
	@echo "  make qa-self-heal     Self-Healing QA Loop (logs, heal .next, rutas, APIs)"
	@echo "  make qa-e2e           Playwright E2E funcional + evidencia en .qa/e2e/"
	@echo "  make desktop-dev      Tauri dev — app desktop JAIOS"
	@echo "  make desktop-prepare  Rust + Tauri CLI + npm install (automático)"
	@echo "  make desktop-build-mac     Build .app/.dmg (macOS)"
	@echo "  make desktop-build-windows Build .msi/.exe (Windows)"
	@echo "  make desktop-qa-report  build shell + reporte .qa/desktop-app-report.md"
	@echo "  make prices-sync      Indexar listas de precios desde 03_PROVEEDORES"

up:
	docker compose up -d

down:
	docker compose down

build:
	@chmod +x scripts/docker_build.sh
	@./scripts/docker_build.sh

logs:
	docker compose logs -f

migrate:
	docker compose exec backend python -m app.scripts.bootstrap_migrations
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.scripts.seed

seed-suppliers:
	docker compose exec backend python -m app.scripts.seed_suppliers --odoo --limit 300

seed-dgcp:
	docker compose exec backend python -m app.scripts.seed_dgcp

test:
	docker compose exec backend pytest

lint:
	docker compose exec backend ruff check app
	docker compose exec frontend npm run lint

qa-backend: build up migrate test

# NUNCA ejecutar build con next dev activo — corrompe middleware.js
qa-frontend-build:
	docker compose stop frontend
	docker compose run --rm frontend npm run build
	docker compose up -d frontend

qa-self-heal:
	@chmod +x scripts/qa_self_heal.sh
	@./scripts/qa_self_heal.sh

qa-e2e:
	@chmod +x scripts/run_e2e_qa.sh
	@./scripts/run_e2e_qa.sh

qa-odoo-e2e:
	docker compose exec backend pytest tests/test_odoo_e2e_live.py tests/test_odoo_account_linking.py tests/test_odoo_normalize.py -v

qa-odoo-ui:
	@mkdir -p .qa
	docker compose exec backend python -m app.scripts.e2e_auth_token /app/.qa/e2e-tokens.json
	docker compose exec frontend node scripts/e2e-odoo-ui.mjs

prices-sync:
	@mkdir -p .qa
	docker compose exec backend alembic upgrade head
	docker compose exec backend python scripts/audit_price_index.py --report /app/.qa/price-index-audit.md
	docker compose exec backend python scripts/sync_price_lists.py --report /app/.qa/prices-sync-report.md
	docker compose exec backend python scripts/audit_laptop_classification.py --report /app/.qa/laptop-classification-audit.md
	docker compose exec backend python scripts/generate_price_qa_reports.py

price-audit:
	@mkdir -p .qa
	docker compose exec backend python scripts/audit_price_index.py --report /app/.qa/price-index-audit.md
	docker compose exec backend python scripts/audit_laptop_classification.py --report /app/.qa/laptop-classification-audit.md

desktop-prepare:
	@chmod +x scripts/desktop_prepare_build_env.sh
	@./scripts/desktop_prepare_build_env.sh

desktop-dev:
	@cd desktop && npm install && npm run desktop:dev

desktop-build-mac:
	@chmod +x scripts/desktop_build_installers.sh
	@./scripts/desktop_build_installers.sh

desktop-build-windows:
	@chmod +x scripts/desktop_build_windows.sh
	@./scripts/desktop_build_windows.sh

desktop-download-windows:
	@chmod +x scripts/download_windows_desktop_artifacts.sh
	@./scripts/download_windows_desktop_artifacts.sh

desktop-qa-report:
	@mkdir -p .qa
	@cd desktop && npm install && npm run build
	@echo "Generando reporte desktop…"
	@python3 scripts/generate_desktop_qa_report.py
