import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import embed, chat, graph, study_planner, search, agent_routes

app = FastAPI(
    title="NOTSY AI Service",
    description="AI Service for NOTSY - Multi-Agent Learning System with RAG, Embeddings, and Knowledge Graph Generation",
    version="2.0.0"
)

# CORS middleware — origins whitelisted via ALLOWED_ORIGINS env var (comma-separated).
# Falls back to localhost only so wildcard "*" is never used in production.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(embed.router, prefix="/embed", tags=["Embeddings"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(graph.router, prefix="/graph", tags=["Knowledge Graph"])
app.include_router(study_planner.router, prefix="", tags=["Study Planner"])
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(agent_routes.router, prefix="/agent", tags=["Agent"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "notsy-ai-service"}


@app.get("/registry")
async def get_registry():
    """Root-level registry endpoint for backend proxy"""
    from app.api.agent_routes import get_agent_registry
    return await get_agent_registry()


@app.get("/")
async def root():
    return {
        "service": "NOTSY AI Service",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }
