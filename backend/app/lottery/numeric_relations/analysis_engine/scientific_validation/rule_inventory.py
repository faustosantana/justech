"""Rule inventory — classify implemented rules by evidence status."""

from __future__ import annotations

from typing import Any


def build_rule_inventory(*, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    m = metrics or {}
    socio_rate = (m.get("calibration") or {}).get("details", {}).get("perfil_socio", {}).get(
        "methodology_match_rate"
    )
    return {
        "version": "phase2-rule-inventory-1.0",
        "rules": [
            {
                "id": "R01_FULL_GRAPH_BEFORE_DISCOVERY",
                "statement": "Construir grafo completo de todos los observados antes de descubrir candidatos.",
                "status": "confirmada_por_evidencia",
                "evidence": "tests graph_complete_before_discovery; stages ordenados",
            },
            {
                "id": "R02_T1_MOTHER_COMPANIONS",
                "statement": "Tabla 1: número observado como código madre → compañeros T1.",
                "status": "confirmada_por_evidencia",
                "evidence": "fórmulas validadas + reconstrucción M1/M4/M5",
            },
            {
                "id": "R03_T2_CONFIRMATION",
                "statement": "Tabla 2: confirmador = observado ∈ vecinos T2 del candidato T1.",
                "status": "confirmada_por_evidencia",
                "evidence": "strengthen_official geometry; M1/M3/M4/M5",
            },
            {
                "id": "R04_NO_EARLY_GREEDY",
                "statement": "Prohibido elegir el primer match T1+confirmación sin comparar alternativas.",
                "status": "confirmada_por_evidencia",
                "evidence": "orchestrator + tests anti-greedy",
            },
            {
                "id": "R05_COMPANION_NEIGHBOR_SEPARATION",
                "statement": "COMPAÑERO_T1 ≠ VECINO_T2; no reetiquetar.",
                "status": "confirmada_por_evidencia",
                "evidence": "M5 labeling tests; guardrail NO_TABLE_CONFUSION",
            },
            {
                "id": "R06_FUERTE_REQUIRES_T1xT2_STRICT",
                "statement": "En perfiles estricto/socio, FUERTE_PRINCIPAL requiere T1 + confirmación T2.",
                "status": "confirmada_por_evidencia",
                "evidence": f"perfil_socio methodology_match_rate={socio_rate}",
            },
            {
                "id": "R07_DIRECT_T2_SEPARATE",
                "statement": "VECINO_T2_DIRECTO se clasifica aparte y no se eleva a fuerte oficial.",
                "status": "confirmada_por_evidencia",
                "evidence": "M2 41+62→75",
            },
            {
                "id": "R08_T2_GROUP_SPECIFICITY",
                "statement": "Entre varios VECINO_T2_DIRECTO, preferir grupos T2 más pequeños.",
                "status": "inferida",
                "evidence": "calibración ad-hoc para M2; pendiente validación ciega amplia",
            },
            {
                "id": "R09_DERIVATION_DEPTH_CAP",
                "statement": "Derivaciones limitadas a profundidad ≤ 2 con penalización.",
                "status": "regla_pendiente_de_validacion",
                "evidence": "implementada; aporte predictivo no demostrado vs sin_derivaciones",
            },
            {
                "id": "R10_MULTI_CONFIRMER_BOOST",
                "statement": "Más confirmadores T2 aumentan score (MULTI_CONFIRMATION_SUPPORT).",
                "status": "inferida",
                "evidence": "M3 35 tiene 2 confirmadores vs 22 con 1",
            },
            {
                "id": "R11_DEFAULT_FIRST_POSITION",
                "statement": "Si no se especifica posición, usar primera.",
                "status": "confirmada_por_evidencia",
                "evidence": "input_normalizer + tests",
            },
            {
                "id": "R12_SAME_DAY_CHAIN",
                "statement": "Tras cumplimiento, se puede abrir nuevo análisis el mismo día.",
                "status": "inferida",
                "evidence": "reconstrucción workflow junio 2026; no es fórmula de fuerte",
            },
            {
                "id": "R13_PARTIAL_SELECTION_MULTI_FUERTE",
                "statement": "Cuando hay varios oficiales el mismo día, el socio elige un subconjunto (p.ej. solo 29).",
                "status": "hipotesis",
                "evidence": "analyst_workflow — pendiente formalizar",
            },
            {
                "id": "R14_WEIGHT_PROFILE_SOCIO",
                "statement": "Pesos del perfil socio reproducen mejor el fuerte histórico oficial.",
                "status": "regla_pendiente_de_validacion",
                "evidence": "se completa tras calibration lab de esta fase",
            },
            {
                "id": "R15_NO_ML_FOR_FUERTE",
                "statement": "La decisión del fuerte es determinística; ML solo mide/compara.",
                "status": "confirmada_por_evidencia",
                "evidence": "arquitectura Phase 2 / Fase J",
            },
        ],
        "pending_to_discover": [
            "Regla de desempate cuando hay ≥2 FUERTE_OFICIAL el mismo día",
            "Política de inclusión de posiciones 2/3 en entradas",
            "Cuándo el socio ignora un oficial con menos confirmadores",
            "Cadenas F→F+1 día siguiente más allá del cierre simple",
            "Uso real de derivaciones nivel 2 en análisis manuales",
        ],
    }
