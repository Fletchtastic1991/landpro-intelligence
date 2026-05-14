# Stub — fence engine coming soon

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def fence_health():
    return {"status": "ok", "router": "fence"}