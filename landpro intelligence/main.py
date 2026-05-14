# main.py
# ─────────────────────────────────────────────────────────────────────────────
# This is the FRONT DOOR of your Python service.
# It starts the server and registers all the routes (URL endpoints).
#
# Think of it like index.ts in your TypeScript project.
# ─────────────────────────────────────────────────────────────────────────────

# FastAPI is the web framework — it handles HTTP requests (like Express in Node)
from fastapi import FastAPI

# CORS = Cross-Origin Resource Sharing
# Without this, your TypeScript frontend will be BLOCKED from calling this server
# (browsers block requests between different origins by default)
from fastapi.middleware.cors import CORSMiddleware

# Import our routers (each router handles one section of the API)
from routers import clearing
from routers import fence

# Create the FastAPI app — this is your server
app = FastAPI(
    title="LandPro Intelligence API",
    description="Python intelligence layer for LandPro — clearing, fence, and terrain analysis",
    version="0.1.0"
)

# ─── CORS Setup ───────────────────────────────────────────────────────────────
# This tells the server: "it's okay if requests come from these addresses"
# During development, your frontend runs on localhost:5173 (Vite) or localhost:3000 (Next.js)
# In production, this would be your real domain (e.g. landpro.ai)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # Next.js frontend (future)
        "http://localhost:5173",    # Vite frontend (current)
        "http://localhost:5174",    # Vite sometimes uses this port too
    ],
    allow_credentials=True,
    allow_methods=["*"],    # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],    # Allow any headers
)

# ─── Register Routers ─────────────────────────────────────────────────────────
# This says: "if someone calls /clearing/..., use the clearing router"
# "if someone calls /fence/..., use the fence router"

app.include_router(clearing.router, prefix="/clearing", tags=["Clearing"])
app.include_router(fence.router,    prefix="/fence",    tags=["Fence"])


# ─── Health Check ─────────────────────────────────────────────────────────────
# A simple endpoint that just says "I'm alive"
# Your frontend can call this to check if the Python server is running

@app.get("/")
def health_check():
    return {
        "status": "running",
        "service": "LandPro Intelligence API",
        "version": "0.1.0"
    }


# ─── Run the server ───────────────────────────────────────────────────────────
# This only runs if you execute this file directly: python main.py
# uvicorn is the server that actually handles HTTP connections

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",     # "in the file called main, find the variable called app"
        host="0.0.0.0", # listen on all network interfaces
        port=8000,      # run on port 8000
        reload=True     # auto-restart when you save changes (great for development)
    )