"""Bootstrap Alembic version table when DB was provisioned before Alembic stamp.

Run automatically before `alembic upgrade head` in production workflows.
"""

import asyncio

from sqlalchemy import text

from app.db.session import engine


async def bootstrap() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS jaios"))

        version_exists = await conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_schema = 'jaios' AND table_name = 'alembic_version'"
                ")"
            )
        )
        if version_exists.scalar():
            return

        tenants_exists = await conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_schema = 'jaios' AND table_name = 'tenants'"
                ")"
            )
        )
        if tenants_exists.scalar():
            await conn.execute(
                text("CREATE TABLE IF NOT EXISTS jaios.alembic_version (version_num VARCHAR(32) NOT NULL)")
            )
            await conn.execute(
                text("INSERT INTO jaios.alembic_version (version_num) VALUES ('001')")
            )
            print("Stamped Alembic at revision 001 (existing schema detected).")


if __name__ == "__main__":
    asyncio.run(bootstrap())
