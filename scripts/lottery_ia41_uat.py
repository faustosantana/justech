#!/usr/bin/env python3
import asyncio
import json
from uuid import UUID

from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.lottery_chat_service import LotteryChatService


async def turn(svc, sid, q):
    r = await svc.send_message(sid, q)
    tr = r.get("runtime_trace") or {}
    return {
        "q": q,
        "a": (r["message"]["content"] or "")[:320],
        "intent": tr.get("intent"),
        "tools": tr.get("tools_executed"),
        "provider": tr.get("provider_used"),
        "model": tr.get("model_used"),
        "prompt": tr.get("prompt_version"),
    }


async def main():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == "admin@justech.do"))).scalar_one()
        row = (
            await db.execute(
                text("select tenant_id from tenant_memberships where user_id=:u limit 1"),
                {"u": str(user.id)},
            )
        ).first()
        svc = LotteryChatService(
            db,
            tenant_id=UUID(str(row[0])),
            user_id=user.id,
            role="admin",
            is_superadmin=True,
        )
        s = await svc.create_session(title="UAT IA4.1")
        qs = [
            "¿Cuándo fue que salió el 57 por última vez?",
            "En Leidsa.",
            "¿Ha salido más este año que el año pasado?",
            "¿Y ese mismo número en las demás?",
            "Dame los que están fríos.",
            "Pero frío por tiempo, no por frecuencia.",
            "¿Eso quiere decir que va a salir?",
            "¿Qué tan confiable es ese análisis?",
            "Hazme un análisis de la Real.",
            "¿Cuál lotería está más actualizada?",
        ]
        out = []
        for q in qs:
            out.append(await turn(svc, s.id, q))
        await db.commit()
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
