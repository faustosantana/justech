from fastapi import APIRouter

from app.api.v1 import (
    admin,
    assistant,
    auth,
    companies,
    company_context,
    dashboard,
    dgcp,
    documents,
    health,
    integrations,
    knowledge,
    llm,
    m365,
    notifications,
    odoo,
    prices,
    routing,
    search,
    tasks,
    tenants,
    users,
    work,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(admin.router)
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(llm.router)
api_router.include_router(integrations.router)
api_router.include_router(companies.router)
api_router.include_router(company_context.router)
api_router.include_router(dashboard.router)
api_router.include_router(dgcp.router)
api_router.include_router(odoo.router)
api_router.include_router(m365.router)
api_router.include_router(tasks.router)
api_router.include_router(users.router)
api_router.include_router(work.router)
api_router.include_router(notifications.router)
api_router.include_router(routing.router)
api_router.include_router(search.router)
api_router.include_router(documents.router)
api_router.include_router(knowledge.router)
api_router.include_router(prices.router)
api_router.include_router(assistant.router)
