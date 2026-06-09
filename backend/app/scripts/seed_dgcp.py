"""Seed DGCP opportunities for demo tenant. Run: python -m app.scripts.seed_dgcp"""

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.tenant import Tenant


OPPORTUNITIES = [
    {
        "code": "DGCP-2026-0142",
        "institution": "Ministerio de Educación (MINERD)",
        "title": "Adquisición de equipos de cómputo para centros educativos — Región Norte",
        "amount": Decimal("48500000.00"),
        "probability": 78,
        "score": 85,
        "status": "to_bid",
        "deadline": date(2026, 7, 15),
        "justech_potential_amount": Decimal("12125000.00"),
        "description": "Licitación pública nacional para suministro e instalación de 2,400 equipos de cómputo.",
        "full_info": {
            "tipo_proceso": "Licitación Pública Nacional",
            "modalidad": "Compra de bienes",
            "ubicacion": "Santiago, Puerto Plata, Valverde",
            "contacto": "direccion.compras@minerd.gob.do",
        },
        "similar_history": [
            {"code": "DGCP-2024-0891", "resultado": "Adjudicado", "monto": 42000000, "ganador": "TechDominicana SRL"},
            {"code": "DGCP-2023-0445", "resultado": "Desierto", "monto": 38000000},
        ],
        "risks": [
            {"nivel": "medio", "descripcion": "Plazo de entrega agresivo (90 días)"},
            {"nivel": "bajo", "descripcion": "Requisito de garantía de seriedad 5%"},
        ],
        "ai_recommendations": [
            "Preparar propuesta técnica destacando soporte post-venta regional",
            "Considerar alianza con distribuidor autorizado HP/Lenovo",
            "Revisar experiencia previa MINERD en licitaciones similares",
        ],
        "suggested_action": "preparar_propuesta",
    },
    {
        "code": "DGCP-2026-0198",
        "institution": "Hospital Dr. Salvador B. Gautier",
        "title": "Suministro de licencias Microsoft 365 y servicios de migración cloud",
        "amount": Decimal("12800000.00"),
        "probability": 92,
        "score": 91,
        "status": "to_bid",
        "deadline": date(2026, 6, 28),
        "justech_potential_amount": Decimal("9600000.00"),
        "description": "Migración de 1,200 usuarios a Microsoft 365 E3 con soporte 24 meses.",
        "full_info": {
            "tipo_proceso": "Contratación Menor",
            "modalidad": "Servicios TI",
            "usuarios": 1200,
            "duracion_meses": 24,
        },
        "similar_history": [
            {"code": "DGCP-2025-0234", "resultado": "Adjudicado Justech", "monto": 8500000},
        ],
        "risks": [
            {"nivel": "bajo", "descripcion": "Competencia limitada en sector salud"},
        ],
        "ai_recommendations": [
            "Justech tiene historial adjudicado — prioridad alta",
            "Incluir plan de migración por fases con zero-downtime",
        ],
        "suggested_action": "licitar_inmediato",
    },
    {
        "code": "DGCP-2026-0205",
        "institution": "Dirección General de Aduanas (DGA)",
        "title": "Desarrollo e implementación de portal de trámites aduaneros",
        "amount": Decimal("72000000.00"),
        "probability": 45,
        "score": 62,
        "status": "to_review",
        "deadline": date(2026, 8, 10),
        "justech_potential_amount": Decimal("28800000.00"),
        "description": "Plataforma web para gestión de declaraciones aduaneras y seguimiento en tiempo real.",
        "full_info": {
            "tipo_proceso": "Licitación Pública Internacional",
            "stack_requerido": ["Java", "PostgreSQL", "API REST"],
            "duracion_proyecto_meses": 18,
        },
        "similar_history": [
            {"code": "DGCP-2024-1200", "resultado": "Adjudicado", "monto": 65000000, "ganador": "GlobalSoft Inc"},
        ],
        "risks": [
            {"nivel": "alto", "descripcion": "Requisito de certificación ISO 27001"},
            {"nivel": "alto", "descripcion": "Competencia internacional fuerte"},
            {"nivel": "medio", "descripcion": "Integración con sistemas legacy ASYCUDA"},
        ],
        "ai_recommendations": [
            "Evaluar partnership con integrador certificado ISO 27001",
            "Solicitar aclaratoria sobre requisitos de residencia de datos",
        ],
        "suggested_action": "evaluar_alianza",
    },
    {
        "code": "DGCP-2026-0211",
        "institution": "Instituto Nacional de Tránsito (INTRANT)",
        "title": "Mantenimiento y soporte de infraestructura de red y datacenter",
        "amount": Decimal("9600000.00"),
        "probability": 68,
        "score": 74,
        "status": "to_review",
        "deadline": date(2026, 7, 5),
        "justech_potential_amount": Decimal("7200000.00"),
        "description": "Contrato de 12 meses para soporte NOC 24/7 de infraestructura crítica.",
        "full_info": {"tipo_proceso": "Contratación Directa", "sla": "99.5% uptime"},
        "similar_history": [],
        "risks": [
            {"nivel": "medio", "descripcion": "Requiere personal on-site en Santo Domingo"},
        ],
        "ai_recommendations": [
            "Verificar capacidad del equipo NOC actual",
            "Incluir propuesta de monitoreo con PRTG/Zabbix",
        ],
        "suggested_action": "revisar_capacidad",
    },
    {
        "code": "DGCP-2026-0220",
        "institution": "Procuraduría General de la República",
        "title": "Adquisición de servidores y almacenamiento para archivo digital",
        "amount": Decimal("34500000.00"),
        "probability": 55,
        "score": 70,
        "status": "detected",
        "deadline": date(2026, 9, 1),
        "justech_potential_amount": Decimal("13800000.00"),
        "description": "Infraestructura hiperconvergente para digitalización de expedientes judiciales.",
        "full_info": {"capacidad_tb": 500, "redundancia": "N+1"},
        "similar_history": [
            {"code": "DGCP-2025-0088", "resultado": "En evaluación", "monto": 30000000},
        ],
        "risks": [
            {"nivel": "medio", "descripcion": "Especificaciones técnicas muy detalladas — riesgo de no conformidad"},
        ],
        "ai_recommendations": [
            "Revisar matriz de cumplimiento técnico antes de decidir",
        ],
        "suggested_action": "analizar_requisitos",
    },
    {
        "code": "DGCP-2026-0233",
        "institution": "Ministerio de Hacienda",
        "title": "Consultoría para modernización del sistema de facturación electrónica",
        "amount": Decimal("18500000.00"),
        "probability": 35,
        "score": 48,
        "status": "discarded",
        "deadline": date(2026, 5, 30),
        "justech_potential_amount": Decimal("0.00"),
        "description": "Estudio y roadmap de migración del sistema e-CF a arquitectura microservicios.",
        "full_info": {"duracion_meses": 6, "entregables": 12},
        "similar_history": [],
        "risks": [
            {"nivel": "alto", "descripcion": "Justech no tiene experiencia en facturación electrónica gubernamental"},
            {"nivel": "alto", "descripcion": "Plazo de preparación insuficiente"},
        ],
        "ai_recommendations": [
            "Descartar — fuera del core de competencias Justech",
        ],
        "suggested_action": "descartar",
    },
    {
        "code": "DGCP-2026-0240",
        "institution": "Ayuntamiento Santo Domingo Este",
        "title": "Implementación de sistema de gestión documental y firma digital",
        "amount": Decimal("8200000.00"),
        "probability": 82,
        "score": 88,
        "status": "to_bid",
        "deadline": date(2026, 7, 20),
        "justech_potential_amount": Decimal("6560000.00"),
        "description": "Solución ECM con flujos de aprobación y firma digital para 45 departamentos.",
        "full_info": {"usuarios": 450, "integracion": "SAP municipal"},
        "similar_history": [
            {"code": "DGCP-2024-0555", "resultado": "Adjudicado Justech", "monto": 6000000},
        ],
        "risks": [
            {"nivel": "bajo", "descripcion": "Cliente recurrente con buena relación"},
        ],
        "ai_recommendations": [
            "Alta probabilidad — replicar propuesta ganadora 2024",
            "Agendar reunión con director de compras municipal",
        ],
        "suggested_action": "licitar_inmediato",
    },
    {
        "code": "DGCP-2026-0255",
        "institution": "Corporación del Acueducto y Alcantarillado (CAASD)",
        "title": "Suministro e instalación de red de fibra óptica institucional",
        "amount": Decimal("22000000.00"),
        "probability": 40,
        "score": 55,
        "status": "to_review",
        "deadline": date(2026, 8, 25),
        "justech_potential_amount": Decimal("5500000.00"),
        "description": "Despliegue de 45 km de fibra óptica entre plantas de tratamiento y oficinas centrales.",
        "full_info": {"tipo_fibra": "Monomodo OS2", "puntos": 28},
        "similar_history": [],
        "risks": [
            {"nivel": "alto", "descripcion": "Requiere certificación de instalador de fibra"},
            {"nivel": "medio", "descripcion": "Obra civil incluida en alcance"},
        ],
        "ai_recommendations": [
            "Subcontratar instalación certificada",
            "Evaluar margen neto después de subcontratación",
        ],
        "suggested_action": "evaluar_subcontrato",
    },
    {
        "code": "DGCP-2026-0267",
        "institution": "Superintendencia de Bancos (SIB)",
        "title": "Plataforma de análisis de datos regulatorios y reportes automatizados",
        "amount": Decimal("55000000.00"),
        "probability": 28,
        "score": 42,
        "status": "discarded",
        "deadline": date(2026, 6, 15),
        "justech_potential_amount": Decimal("0.00"),
        "description": "Data warehouse y dashboards para supervisión del sistema financiero nacional.",
        "full_info": {"volumen_datos_tb": 80, "herramienta_bi": "Power BI / Tableau"},
        "similar_history": [
            {"code": "DGCP-2023-0999", "resultado": "Adjudicado", "monto": 48000000, "ganador": "DataCorp RD"},
        ],
        "risks": [
            {"nivel": "alto", "descripcion": "Requiere clearance de seguridad nivel 3"},
            {"nivel": "alto", "descripcion": "Competidor DataCorp tiene ventaja histórica"},
        ],
        "ai_recommendations": [
            "Descartar por barreras de entrada regulatorias",
        ],
        "suggested_action": "descartar",
    },
    {
        "code": "DGCP-2026-0278",
        "institution": "Ministerio de Industria y Comercio (MICM)",
        "title": "Desarrollo de portal único de inversiones y trámites empresariales",
        "amount": Decimal("41000000.00"),
        "probability": 72,
        "score": 80,
        "status": "detected",
        "deadline": date(2026, 10, 12),
        "justech_potential_amount": Decimal("20500000.00"),
        "description": "Portal ciudadano para registro de empresas, permisos y seguimiento de trámites MICM.",
        "full_info": {
            "tipo_proceso": "Licitación Pública Nacional",
            "integraciones": ["DGII", "TSS", "Registro Mercantil"],
        },
        "similar_history": [
            {"code": "DGCP-2025-0312", "resultado": "Adjudicado", "monto": 35000000, "ganador": "CivicTech RD"},
        ],
        "risks": [
            {"nivel": "medio", "descripcion": "Múltiples integraciones gubernamentales"},
            {"nivel": "bajo", "descripcion": "Alineado con stack Justech (Next.js + FastAPI)"},
        ],
        "ai_recommendations": [
            "Oportunidad estratégica — alineada con expertise JAIOS",
            "Iniciar análisis de integraciones DGII/TSS",
            "Preparar demo del portal con datos ficticios",
        ],
        "suggested_action": "preparar_propuesta",
    },
]


async def seed_dgcp() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.slug == "justech"))
        tenant = result.scalar_one_or_none()
        if not tenant:
            print("Tenant 'justech' not found. Run seed first.")
            return

        existing = await db.execute(
            select(DGCPOpportunity).where(DGCPOpportunity.tenant_id == tenant.id).limit(1)
        )
        if existing.scalar_one_or_none():
            print("DGCP opportunities already seeded.")
            return

        for data in OPPORTUNITIES:
            db.add(DGCPOpportunity(tenant_id=tenant.id, **data))

        await db.commit()
        print(f"Seeded {len(OPPORTUNITIES)} DGCP opportunities for tenant '{tenant.slug}'.")


if __name__ == "__main__":
    asyncio.run(seed_dgcp())
