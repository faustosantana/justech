from app.platform.modules import (
    ModulePhase,
    get_module,
    get_modules_by_phase,
    list_modules,
    validate_dependencies,
)


def test_all_modules_have_valid_dependencies():
    errors = validate_dependencies()
    assert errors == [], f"Dependencias inválidas: {errors}"


def test_roadmap_phase_priority():
    odoo = get_module("odoo")
    m365 = get_module("m365")
    work = get_module("work_hub")
    assert odoo is not None and odoo.phase == ModulePhase.ODOO
    assert m365 is not None and m365.phase == ModulePhase.M365
    assert work is not None and work.phase == ModulePhase.WORK
    assert odoo.phase < m365.phase < work.phase


def test_document_repository_active():
    module = get_module("document_repository")
    assert module is not None
    assert module.status == "active"
    assert module.frontend_route == "/documents"


def test_future_modules_not_active():
    future_ids = (
        "supplier_intelligence",
        "hermes_memory",
        "multi_agent",
    )
    for module_id in future_ids:
        module = get_module(module_id)
        assert module is not None
        assert module.status in ("planned", "future")


def test_price_intelligence_active():
    module = get_module("price_intelligence")
    assert module is not None
    assert module.status == "active"
    assert module.frontend_route == "/prices"


def test_delivered_modules_exist():
    for module_id in ("core", "dgcp", "odoo"):
        module = get_module(module_id)
        assert module is not None
        assert module.status in ("delivered", "active")


def test_phase_five_includes_tasks_notifications_work_hub():
    phase5 = get_modules_by_phase(ModulePhase.WORK)
    ids = {m.id for m in phase5}
    assert {"tasks", "notifications", "work_hub"}.issubset(ids)


def test_search_acceleration_active():
    module = get_module("search_acceleration")
    assert module is not None
    assert module.status == "active"
    assert module.depends_on == ("core", "enterprise_search")


def test_module_registry_count():
    assert len(list_modules()) >= 13
