"""Seed initial superadmin, demo tenant y equipo operativo. Run: python -m app.scripts.seed"""

import asyncio

from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.db.session import AsyncSessionLocal
from app.models.tenant import Tenant, TenantMembership
from app.models.user import User

ADMIN_EMAIL = "admin@justech.do"
ADMIN_PASSWORD = "JaiosAdmin2026!"
TENANT_SLUG = "justech"

TEAM_USERS = [
    {
        "email": "marieli@justech.do",
        "full_name": "Marieli Rodriguez",
        "role": "usuario",
        "password": "JaiosTeam2026!",
        "department": "Operaciones",
    },
    {
        "email": "administracion@just-offices.com",
        "full_name": "Abigail Crisostomo",
        "role": "usuario",
        "password": "JaiosTeam2026!",
        "department": "Administración",
    },
    {
        "email": "administracion@justech.do",
        "full_name": "Diana Ayala",
        "role": "usuario",
        "password": "JaiosTeam2026!",
        "department": "Administración",
    },
    {
        "email": "recepcion@justech.do",
        "full_name": "Jennipher Martinez",
        "role": "usuario",
        "password": "JaiosTeam2026!",
        "department": "Recepción",
    },
    {"email": "jesus@justech.do", "full_name": "Jesús", "role": "usuario", "password": "JaiosTeam2026!", "department": "Operaciones"},
    {"email": "felipe@justech.do", "full_name": "Felipe Mejía", "role": "usuario", "password": "JaiosTeam2026!", "department": "Operaciones"},
]

# Supervisor por responsable (nombre parcial)
SUPERVISOR_BY_ASSIGNEE = {
    "Marieli": "Fausto",
    "Marieli Rodriguez": "Fausto",
    "Jennipher": "Fausto",
    "Jennipher Martinez": "Fausto",
    "Felipe": "Jesús",
    "Felipe Mejía": "Jesús",
}


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        await _ensure_core_seed(db)


async def _ensure_core_seed(db) -> None:
    legacy = await db.execute(select(User).where(User.email == "admin@jaios.local"))
    legacy_user = legacy.scalar_one_or_none()
    if legacy_user:
        legacy_user.email = ADMIN_EMAIL
        await db.flush()

    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        tenant = Tenant(slug=TENANT_SLUG, name="Justech Demo", plan="enterprise")
        db.add(tenant)
        await db.flush()

    admin = await _ensure_user(
        db,
        email=ADMIN_EMAIL,
        full_name="Fausto",
        password=ADMIN_PASSWORD,
        is_superadmin=True,
        tenant=tenant,
        role="owner",
        is_default=True,
    )

    for member in TEAM_USERS:
        if member["email"] == ADMIN_EMAIL:
            continue
        await _ensure_user(
            db,
            email=member["email"],
            full_name=member["full_name"],
            password=member["password"],
            is_superadmin=False,
            tenant=tenant,
            role=member["role"],
            is_default=False,
            department=member.get("department"),
        )

    await db.commit()
    print(f"Seed complete: admin {ADMIN_EMAIL} + {len(TEAM_USERS)} equipo operativo")


async def _ensure_user(
    db,
    *,
    email: str,
    full_name: str,
    password: str,
    is_superadmin: bool,
    tenant: Tenant,
    role: str,
    is_default: bool,
    department: str | None = None,
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            is_superadmin=is_superadmin,
        )
        db.add(user)
        await db.flush()
        print(f"  + usuario: {full_name} <{email}>")
    else:
        if user.full_name != full_name or (email == ADMIN_EMAIL and user.full_name != "Fausto"):
            user.full_name = full_name if email != ADMIN_EMAIL else "Fausto"
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
        await db.flush()

    membership_result = await db.execute(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == user.id,
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        db.add(
            TenantMembership(
                tenant_id=tenant.id,
                user_id=user.id,
                role=role,
                is_default=is_default,
                department=department,
            )
        )
    elif department and membership.department != department:
        membership.department = department
    return user


if __name__ == "__main__":
    asyncio.run(seed())
