import logging
import json
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = 10
    user_id: Optional[int] = None
    notebook_id: Optional[int] = None


@router.post("/semantic")
async def semantic_search(request: SemanticSearchRequest):
    """Perform semantic search across user's indexed content."""
    try:
        # Query the vector store
        results = vector_store.semantic_search(
            query=request.query,
            n_results=request.limit,
            notebook_id=request.notebook_id,
            user_id=request.user_id
        )

        return {
            "results": results.get("documents", []),
            "metadatas": results.get("metadatas", []),
            "distances": results.get("distances", [])
        }

    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return {"results": [], "error": str(e)}


@router.post("/global")
async def global_search(request: SemanticSearchRequest):
    """Global semantic search across all user's content and curated base."""
    try:
        results = vector_store.global_search(
            query=request.query,
            n_results=request.limit
        )

        return {
            "results": results.get("documents", []),
            "metadatas": results.get("metadatas", []),
            "distances": results.get("distances", [])
        }

    except Exception as e:
        logger.error(f"Global search error: {e}")
        return {"results": [], "error": str(e)}
