"""Fixtures pytest — evita fugas de pool asyncpg entre tests ASGI."""

import pytest


@pytest.fixture(autouse=True)
async def _dispose_db_engine_after_test():
    yield
    from app.db.session import engine

    await engine.dispose()
