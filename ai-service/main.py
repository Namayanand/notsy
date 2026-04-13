from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import embed, chat, graph

app = FastAPI(
    title="NOTSY AI Service",
    description="AI Service for NOTSY - RAG Engine, Embeddings, and Knowledge Graph Generation",
    version="1.0.0"
)

# CORS middleware - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(embed.router, prefix="/embed", tags=["Embeddings"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(graph.router, prefix="/graph", tags=["Knowledge Graph"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "notsy-ai-service"}


@app.get("/")
async def root():
    return {
        "service": "NOTSY AI Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
