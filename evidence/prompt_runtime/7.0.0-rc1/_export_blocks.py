import json
import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory


async def main() -> None:
    async with async_session_factory() as db:
        r = await db.execute(
            text("SELECT blocks FROM lottery_ai_prompt_versions WHERE version=:v"),
            {"v": "draft-20260729120453"},
        )
        blocks = r.scalar_one()
    with open("/tmp/prompt_studio_blocks_clean.json", "w", encoding="utf-8") as f:
        json.dump(blocks, f, ensure_ascii=False, indent=2)
    print("keys", sorted(blocks.keys()))
    print("sum", sum(len(v or "") for v in blocks.values()))
    for k in sorted(blocks.keys()):
        print(f"{k}\t{len(blocks[k] or '')}")


if __name__ == "__main__":
    asyncio.run(main())
