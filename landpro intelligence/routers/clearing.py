# routers/clearing.py
# ─────────────────────────────────────────────────────────────────────────────
# This is the ROUTER for clearing requests.
# It defines what URL to call and what data to send.
#
# Think of this as the waiter:
# - TypeScript places an order (sends data to /clearing/estimate)
# - This file receives the order
# - Passes it to the kitchen (clearing_engine.py)
# - Brings back the result
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter
from engines.clearing_engine import ClearingInput, ClearingResult, run_clearing_engine

# APIRouter is like a mini FastAPI app for one section of the API
# prefix="/clearing" is added in main.py, so routes here are relative
router = APIRouter()


@router.post("/estimate", response_model=ClearingResult)
def estimate_clearing(input: ClearingInput) -> ClearingResult:
    """
    Estimate clearing cost, hours, risk factors, and confidence.

    Send a POST request to /clearing/estimate with JSON like:
    {
        "acreage": 2.4,
        "vegetation": "heavy",
        "terrain": "slight_slope",
        "accessibility": "easy",
        "water": "pond_or_creek",
        "debris": "none",
        "structures": "none",
        "production_rate": "standard"
    }
    """
    # Call the engine — all the real logic lives there, not here
    result = run_clearing_engine(input)
    return result


@router.get("/health")
def clearing_health():
    """Quick check that the clearing router is working."""
    return {"status": "ok", "router": "clearing"}