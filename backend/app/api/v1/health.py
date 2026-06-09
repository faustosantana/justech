from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "jaios-api", "version": "0.1.0"}
