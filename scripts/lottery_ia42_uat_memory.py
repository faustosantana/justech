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
        "a": (r["message"]["content"] or "")[:420],
        "intent": tr.get("intent"),
        "tools": tr.get("tools_executed"),
        "provider": tr.get("provider_used"),
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
        s = await svc.create_session(title="UAT IA4.2 memoria")
        qs = [
            "¿Cuándo fue la última vez que salió el 24?",
            "En la Real y en Leidsa.",
            "¿Cuáles números salieron los siete días después en esas loterías?",
            "¿En cuál se repitió el 24?",
            "Ahora hazlo con el 57.",
            "¿Cuál es la capital de Francia?",
            "¿Qué base de datos usan?",
        ]
        out = []
        for q in qs:
            out.append(await turn(svc, s.id, q))
        await db.commit()
        # Load session context to verify last_occurrences persisted
        sess = await svc.get_session(s.id)
        v4 = (sess.context or {}).get("conversation_v4") or {}
        print(json.dumps({"turns": out, "last_occurrences": v4.get("last_occurrences"), "active": {
            "numbers": v4.get("active_numbers"),
            "lotteries": v4.get("active_lotteries"),
            "calendar_window": v4.get("calendar_window"),
            "last_intent": v4.get("last_intent"),
        }}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
