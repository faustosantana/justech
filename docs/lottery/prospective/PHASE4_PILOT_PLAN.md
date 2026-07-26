# Phase 4 — Pilot Plan (DEV/UAT)

## Goal
Operate the Complete Analysis Engine prospectively: lock predictions before draws, evaluate D+1…D+7, without retuning on historical data.

## Operational profile (frozen)
- ranking: `perfil_socio`
- tiebreak: `TIEBREAK_PROFILE_SOCIO_V1` + `EMPATE_MULTI_FUERTE`
- derivation_depth: validated default (0)
- practical threshold: 0.0

## Environments
DEV/UAT only. Production writes forbidden.

## Duration (configurable)
Recommend ≥30 days / prefer 60 / ≥100 evaluated predictions before any predictive conclusion. Not hardcoded.

## Success of this phase
Infrastructure readiness — **not** predictive success.
