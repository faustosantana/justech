"""Expediente prepare metrics consistency — ZIP may include reports beyond copied docs."""

from app.services.dgcp_expediente_service import (
    DGCPExpedienteService,
    ExpedienteMetricsConsistencyError,
)


def test_metrics_consistency_allows_zip_artifacts_when_no_copies():
    svc = DGCPExpedienteService.__new__(DGCPExpedienteService)
    # api/manifest agree on 0 copies; zip has generated report → must NOT raise
    svc._assert_metrics_consistency(
        api_copied=0,
        api_pct=0.0,
        manifest={"copied_documents": 0, "preparation_pct": 0.0},
        zip_content_count=1,
    )


def test_metrics_consistency_api_manifest_mismatch_raises():
    svc = DGCPExpedienteService.__new__(DGCPExpedienteService)
    try:
        svc._assert_metrics_consistency(
            api_copied=2,
            api_pct=10.0,
            manifest={"copied_documents": 1, "preparation_pct": 10.0},
            zip_content_count=2,
        )
        raised = False
    except ExpedienteMetricsConsistencyError:
        raised = True
    assert raised


def test_metrics_consistency_zip_too_small_raises():
    svc = DGCPExpedienteService.__new__(DGCPExpedienteService)
    try:
        svc._assert_metrics_consistency(
            api_copied=3,
            api_pct=20.0,
            manifest={"copied_documents": 3, "preparation_pct": 20.0},
            zip_content_count=1,
        )
        raised = False
    except ExpedienteMetricsConsistencyError:
        raised = True
    assert raised
