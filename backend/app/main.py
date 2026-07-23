from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import AuthorizationError, JAIOSException
from integrations.odoo.exceptions import OdooReadOnlyError
from app.gateway.middleware import GatewayMiddleware
from app.services.dgcp_scheduler import start_dgcp_scheduler, stop_dgcp_scheduler
from app.services.lottery_scheduler import start_lottery_scheduler, stop_lottery_scheduler
from app.core.lottery_isolation import LotteryClientIsolationMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_dgcp_scheduler()
    # Lottery 3.0: Sync Engine runs as standalone worker when configured
    if settings.lottery_sync_worker_standalone:
        import logging

        logging.getLogger(__name__).info(
            "Lottery scheduler not started in API (LOTTERY_SYNC_WORKER_STANDALONE=true)"
        )
    else:
        start_lottery_scheduler()
    yield
    stop_lottery_scheduler()
    stop_dgcp_scheduler()


app = FastAPI(
    title=settings.app_name,
    description="JAIOS — Justech AI Operating System — Core Platform API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GatewayMiddleware)
app.add_middleware(LotteryClientIsolationMiddleware)
app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(_: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"error": exc.code, "message": exc.message},
    )


@app.exception_handler(JAIOSException)
async def jaios_exception_handler(_: Request, exc: JAIOSException) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": exc.code, "message": exc.message},
    )


@app.exception_handler(OdooReadOnlyError)
async def odoo_readonly_handler(_: Request, exc: OdooReadOnlyError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"error": "ODOO_READ_ONLY", "message": str(exc)},
    )
